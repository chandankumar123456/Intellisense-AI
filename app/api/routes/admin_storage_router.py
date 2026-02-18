# app/api/routes/admin_storage_router.py

from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel
from typing import Optional, Dict
import os
from dotenv import set_key

from app.core.admin_auth import require_admin
from app.storage import storage_manager
from app.core.logging import log_info, log_error

router = APIRouter(prefix="/admin/storage", tags=["admin-storage"])

class StorageConfigUpdate(BaseModel):
    mode: str  # "aws" or "local"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: Optional[str] = None
    s3_bucket_name: Optional[str] = None
    pinecone_api_key: Optional[str] = None

class StorageTestResult(BaseModel):
    storage_type: str
    status: str
    message: str

@router.get("/status")
async def get_storage_status(admin: dict = Depends(require_admin)):
    """Get current storage mode and adapter status."""
    return storage_manager.get_status()

@router.get("/config")
async def get_storage_config(admin: dict = Depends(require_admin)):
    """Get current redacted configuration."""
    return {
        "mode": os.getenv("STORAGE_MODE", "aws"),
        "aws_region": os.getenv("AWS_REGION", ""),
        "s3_bucket_name": os.getenv("S3_BUCKET_NAME", ""),
        "aws_credentials_configured": bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY")),
        "pinecone_configured": bool(os.getenv("PINECONE_API_KEY")),
        "runtime_switching_supported": True
    }

@router.post("/config")
async def update_storage_config(
    config: StorageConfigUpdate, 
    admin: dict = Depends(require_admin)
):
    """
    Update storage configuration and switch mode.
    Persists to .env and reinitializes StorageManager.
    """
    try:
        new_mode = config.mode.lower()
        if new_mode not in ["aws", "local"]:
            raise HTTPException(400, "Invalid mode. Must be 'aws' or 'local'.")

        env_file = ".env"
        
        # Update .env file
        set_key(env_file, "STORAGE_MODE", new_mode)
        os.environ["STORAGE_MODE"] = new_mode

        if new_mode == "aws":
            # Validate required creds if provided or check existence
            if config.aws_access_key_id:
                set_key(env_file, "AWS_ACCESS_KEY_ID", config.aws_access_key_id)
                os.environ["AWS_ACCESS_KEY_ID"] = config.aws_access_key_id
            
            if config.aws_secret_access_key:
                set_key(env_file, "AWS_SECRET_ACCESS_KEY", config.aws_secret_access_key)
                os.environ["AWS_SECRET_ACCESS_KEY"] = config.aws_secret_access_key
                
            if config.aws_region:
                set_key(env_file, "AWS_REGION", config.aws_region)
                os.environ["AWS_REGION"] = config.aws_region
                
            if config.s3_bucket_name:
                set_key(env_file, "S3_BUCKET_NAME", config.s3_bucket_name)
                os.environ["S3_BUCKET_NAME"] = config.s3_bucket_name

            if config.pinecone_api_key:
                set_key(env_file, "PINECONE_API_KEY", config.pinecone_api_key)
                os.environ["PINECONE_API_KEY"] = config.pinecone_api_key

        # Reinitialize StorageManager
        storage_manager.reinitialize(new_mode)
        
        # Verify initialization worked
        if storage_manager.state == "INITIALIZING":
             # Force a check
             try:
                 storage_manager.get_status()
             except Exception as init_error:
                 # Revert or just warn?
                 # ideally we roll back, but for now just report error
                 raise HTTPException(500, f"Configuration saved but initialization failed: {init_error}")

        log_info(f"Admin {admin.get('user_id')} switched storage mode to {new_mode}")
        return {
            "status": "success", 
            "mode": new_mode, 
            "message": "Storage configuration updated and reinitialized.",
            "state": storage_manager.state
        }

    except Exception as e:
        log_error(f"Failed to update storage config: {e}")
        raise HTTPException(500, f"Failed to update config: {str(e)}")

@router.post("/test")
async def test_storage(admin: dict = Depends(require_admin)):
    """Run a read/write test on current storage adapters."""
    results = []
    
    # Test Files
    try:
        test_filename = "admin_test_probe.txt"
        storage_manager.files.save_file(test_filename, b"test")
        content = storage_manager.files.read_file(test_filename)
        storage_manager.files.delete_file(test_filename)
        if content == b"test":
            results.append({"type": "files", "status": "success", "message": "Read/Write/Delete OK"})
        else:
            results.append({"type": "files", "status": "failed", "message": "Content mismatch"})
    except Exception as e:
        results.append({"type": "files", "status": "failed", "message": str(e)})

    # Test Metadata
    try:
        # Just a search test
        storage_manager.metadata.search({}, limit=1)
        results.append({"type": "metadata", "status": "success", "message": "Search OK"})
    except Exception as e:
         results.append({"type": "metadata", "status": "failed", "message": str(e)})

    # Test Vectors
    try:
        # Helper to check if connected (might fail if no index or creds)
        # Using a dummy query
        storage_manager.vectors.query([0.0]*384, top_k=1)
        results.append({"type": "vectors", "status": "success", "message": "Query OK"})
    except Exception as e:
        results.append({"type": "vectors", "status": "failed", "message": str(e)})

    return results

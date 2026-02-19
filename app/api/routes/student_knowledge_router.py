# app/api/routes/student_knowledge_router.py
"""
Student Knowledge REST API — Production-Hardened.
Endpoints for upload, lifecycle management, and knowledge operations.
All endpoints are student-scoped via JWT authentication.
Includes: quota enforcement, audit logging, trace serving, metrics.
"""

import json
import os
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Form, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid

from app.core.logging import log_info, log_error
from app.core.auth_utils import decode_jwt_token
from app.core.config import (
    STUDENT_MAX_UPLOAD_SIZE_MB,
    STUDENT_QUOTA_UPLOADS_PER_DAY,
    STUDENT_TRACE_DIR,
)
from app.student_knowledge.db import StudentKnowledgeDB
from app.student_knowledge.agent import StudentKnowledgeAgent
from app.student_knowledge.metrics import metrics

router = APIRouter(prefix="/student-knowledge", tags=["student-knowledge"])
bearer_scheme = HTTPBearer()


# ─── Request / Response Models ───

class UploadUrlRequest(BaseModel):
    url: str
    type: str  # "youtube" or "website"
    title: Optional[str] = None
    tags: List[str] = []


class UploadResponse(BaseModel):
    upload_id: str
    status: str
    message: str
    is_duplicate: bool = False
    existing_upload_id: Optional[str] = None


class UploadStatusResponse(BaseModel):
    upload_id: str
    student_id: str
    source_type: str
    source_uri: str
    title: Optional[str] = None
    status: str
    chunk_count: int = 0
    token_count: int = 0
    tags: List[str] = []
    notes: Optional[str] = None
    is_private: bool = False
    created_at: str = ""
    error_reason: Optional[str] = None
    trace_path: Optional[str] = None
    extraction_status: Optional[str] = None
    validation_status: Optional[str] = None
    stage_timeline: Optional[List[Dict[str, Any]]] = None


class UpdateTagsRequest(BaseModel):
    tags: Optional[List[str]] = None
    notes: Optional[str] = None


class UpdatePrivacyRequest(BaseModel):
    is_private: bool


# ─── Helpers ───

def _authenticate(credentials: HTTPAuthorizationCredentials) -> str:
    """Extract and validate student_id from JWT."""
    token = credentials.credentials
    decoded = decode_jwt_token(token)
    if not decoded:
        raise HTTPException(401, "Invalid or expired token")
    return decoded["user_id"]


def _get_db() -> StudentKnowledgeDB:
    return StudentKnowledgeDB()


def _get_agent() -> StudentKnowledgeAgent:
    return StudentKnowledgeAgent()


def _check_quota(db: StudentKnowledgeDB, student_id: str):
    """Enforce per-student daily upload quota."""
    count = db.count_uploads_today(student_id)
    if count >= STUDENT_QUOTA_UPLOADS_PER_DAY:
        raise HTTPException(
            429,
            f"Daily upload quota exceeded ({count}/{STUDENT_QUOTA_UPLOADS_PER_DAY}). Try again tomorrow."
        )


def _load_trace(student_id: str, upload_id: str) -> Optional[List[Dict[str, Any]]]:
    """Load trace timeline from persisted JSON."""
    try:
        path = os.path.join(STUDENT_TRACE_DIR, student_id, f"{upload_id}.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                trace = json.load(f)
            return trace.get("steps", [])
    except Exception:
        pass
    return None


# ─── Endpoints ───

@router.post("/upload/file", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    """Upload a file for ingestion into student knowledge base."""
    student_id = _authenticate(credentials)
    db = _get_db()
    agent = _get_agent()

    # Quota check
    _check_quota(db, student_id)

    # Read file bytes
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(400, "Empty file")

    # Size check
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > STUDENT_MAX_UPLOAD_SIZE_MB:
        raise HTTPException(400, f"File too large. Max {STUDENT_MAX_UPLOAD_SIZE_MB}MB")

    tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]
    upload_id = str(uuid.uuid4())

    db.create_upload(
        student_id=student_id,
        source_type="file",
        source_uri=file.filename or "unknown",
        provided_title=title or file.filename,
        tags=tag_list,
        upload_id=upload_id,
    )

    # Audit
    db.log_audit(student_id, "upload", upload_id, f"file:{file.filename}, size:{size_mb:.1f}MB")

    background_tasks.add_task(
        _run_file_ingestion,
        agent, file_bytes, file.filename or "unknown",
        student_id, upload_id, title, tag_list,
    )

    log_info(f"File upload queued: {upload_id} for student {student_id}")

    return UploadResponse(
        upload_id=upload_id,
        status="queued",
        message=f"File '{file.filename}' queued for processing.",
    )


@router.post("/upload/url", response_model=UploadResponse)
async def upload_url(
    request: UploadUrlRequest,
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    """Submit a YouTube or website URL for ingestion."""
    student_id = _authenticate(credentials)
    db = _get_db()
    agent = _get_agent()

    # Quota check
    _check_quota(db, student_id)

    if request.type not in ["youtube", "website"]:
        raise HTTPException(400, "type must be 'youtube' or 'website'")

    upload_id = str(uuid.uuid4())

    db.create_upload(
        student_id=student_id,
        source_type=request.type,
        source_uri=request.url,
        provided_title=request.title,
        tags=request.tags,
        upload_id=upload_id,
    )

    # Audit
    db.log_audit(student_id, "upload", upload_id, f"url:{request.url}, type:{request.type}")

    background_tasks.add_task(
        _run_url_ingestion,
        agent, request.url, request.type,
        student_id, upload_id, request.title, request.tags,
    )

    log_info(f"URL upload queued: {upload_id} for student {student_id}")

    return UploadResponse(
        upload_id=upload_id,
        status="queued",
        message=f"URL '{request.url}' queued for processing.",
    )


@router.get("/uploads", response_model=List[UploadStatusResponse])
async def list_uploads(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    """List all uploads for the authenticated student."""
    student_id = _authenticate(credentials)
    db = _get_db()

    uploads = db.list_uploads(student_id)
    return [
        UploadStatusResponse(
            upload_id=u["upload_id"],
            student_id=student_id,
            source_type=u["source_type"],
            source_uri=u["source_uri"],
            title=u.get("provided_title"),
            status=u["status"],
            chunk_count=u.get("chunk_count", 0),
            tags=u.get("tags", []),
            is_private=u.get("is_private", False),
            created_at=u.get("created_at", ""),
            error_reason=u.get("error_reason"),
            extraction_status=u.get("extraction_status"),
            validation_status=u.get("validation_status"),
        )
        for u in uploads
    ]


@router.get("/uploads/{upload_id}", response_model=UploadStatusResponse)
async def get_upload_status(
    upload_id: str,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    """Get status and details of a specific upload, including trace timeline."""
    student_id = _authenticate(credentials)
    db = _get_db()

    upload = db.get_upload(upload_id)
    if not upload:
        raise HTTPException(404, "Upload not found")

    if upload["student_id"] != student_id:
        raise HTTPException(403, "Access denied")

    # Audit access
    db.log_audit(student_id, "access", upload_id)

    # Load trace timeline
    timeline = _load_trace(student_id, upload_id)

    return UploadStatusResponse(
        upload_id=upload["upload_id"],
        student_id=upload["student_id"],
        source_type=upload["source_type"],
        source_uri=upload["source_uri"],
        title=upload.get("provided_title"),
        status=upload["status"],
        chunk_count=upload.get("chunk_count", 0),
        token_count=upload.get("token_count", 0),
        tags=upload.get("tags", []),
        notes=upload.get("notes"),
        is_private=upload.get("is_private", False),
        created_at=upload.get("created_at", ""),
        error_reason=upload.get("error_reason"),
        trace_path=upload.get("trace_path"),
        extraction_status=upload.get("extraction_status"),
        validation_status=upload.get("validation_status"),
        stage_timeline=timeline,
    )


@router.delete("/uploads/{upload_id}")
async def delete_upload(
    upload_id: str,
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    """Delete an upload and its associated vectors."""
    student_id = _authenticate(credentials)
    db = _get_db()
    agent = _get_agent()

    owner = db.get_upload_owner(upload_id)
    if not owner:
        raise HTTPException(404, "Upload not found")
    if owner != student_id:
        raise HTTPException(403, "Access denied")

    # Audit
    db.log_audit(student_id, "delete", upload_id)

    background_tasks.add_task(agent.delete_upload_vectors, upload_id, student_id)
    db.delete_upload(upload_id)

    return {"status": "deleted", "upload_id": upload_id}


@router.post("/uploads/{upload_id}/reprocess")
async def reprocess_upload(
    upload_id: str,
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    """Re-trigger ingestion for an upload."""
    student_id = _authenticate(credentials)
    db = _get_db()
    agent = _get_agent()

    upload = db.get_upload(upload_id)
    if not upload:
        raise HTTPException(404, "Upload not found")
    if upload["student_id"] != student_id:
        raise HTTPException(403, "Access denied")

    # Audit
    db.log_audit(student_id, "reprocess", upload_id, f"previous_status:{upload['status']}")

    background_tasks.add_task(agent.delete_upload_vectors, upload_id, student_id)
    db.update_status(upload_id, "queued")

    source_type = upload["source_type"]
    if source_type in ["youtube", "website"]:
        background_tasks.add_task(
            _run_url_ingestion,
            agent, upload["source_uri"], source_type,
            student_id, upload_id, upload.get("provided_title"),
            upload.get("tags", []),
        )
    else:
        db.update_status(upload_id, "error",
                         error_reason="File reprocessing requires re-upload. Please delete and upload again.")
        return {"status": "error", "message": "File content not available. Please re-upload the file."}

    return {"status": "queued", "message": "Re-processing started"}


@router.patch("/uploads/{upload_id}/tags")
async def update_upload_tags(
    upload_id: str,
    request: UpdateTagsRequest,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    """Update tags and/or notes for an upload."""
    student_id = _authenticate(credentials)
    db = _get_db()

    owner = db.get_upload_owner(upload_id)
    if not owner:
        raise HTTPException(404, "Upload not found")
    if owner != student_id:
        raise HTTPException(403, "Access denied")

    db.update_tags(upload_id, tags=request.tags, notes=request.notes)
    db.log_audit(student_id, "tag_update", upload_id)
    return {"status": "updated", "upload_id": upload_id}


@router.patch("/uploads/{upload_id}/privacy")
async def update_upload_privacy(
    upload_id: str,
    request: UpdatePrivacyRequest,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    """Toggle privacy setting for an upload."""
    student_id = _authenticate(credentials)
    db = _get_db()

    owner = db.get_upload_owner(upload_id)
    if not owner:
        raise HTTPException(404, "Upload not found")
    if owner != student_id:
        raise HTTPException(403, "Access denied")

    db.update_privacy(upload_id, request.is_private)
    db.log_audit(student_id, "privacy_change", upload_id, f"is_private:{request.is_private}")
    return {"status": "updated", "upload_id": upload_id, "is_private": request.is_private}


# ─── Metrics Endpoint ───

@router.get("/metrics")
async def get_metrics(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    """Get pipeline health metrics. Available to all authenticated users."""
    _authenticate(credentials)
    return metrics.get_all()


# ─── Background Task Wrappers ───

async def _run_file_ingestion(
    agent: StudentKnowledgeAgent,
    file_bytes: bytes,
    filename: str,
    student_id: str,
    upload_id: str,
    title: Optional[str],
    tags: List[str],
):
    """Background wrapper for file ingestion."""
    try:
        await agent.ingest_file_upload(
            file_bytes=file_bytes,
            filename=filename,
            student_id=student_id,
            upload_id=upload_id,
            provided_title=title,
            tags=tags,
        )
    except Exception as e:
        log_error(f"Background file ingestion failed: {e}")
        db = _get_db()
        db.update_status(upload_id, "error", error_reason=str(e))


async def _run_url_ingestion(
    agent: StudentKnowledgeAgent,
    url: str,
    source_type: str,
    student_id: str,
    upload_id: str,
    title: Optional[str],
    tags: List[str],
):
    """Background wrapper for URL ingestion."""
    try:
        await agent.ingest_url(
            url=url,
            source_type=source_type,
            student_id=student_id,
            upload_id=upload_id,
            provided_title=title,
            tags=tags,
        )
    except Exception as e:
        log_error(f"Background URL ingestion failed: {e}")
        db = _get_db()
        db.update_status(upload_id, "error", error_reason=str(e))

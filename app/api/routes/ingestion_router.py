# app/api/routes/ingestion_router.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Body, BackgroundTasks, Form
from pydantic import BaseModel
from typing import List, Optional
import shutil
import os
import uuid
import tempfile
import asyncio
from pypdf import PdfReader
from youtube_transcript_api import YouTubeTranscriptApi
import trafilatura

from app.core.logging import log_info, log_error
from app.rag.ingestion_pipeline import ingest_document
from app.core.config import STUDENT_VECTOR_NAMESPACE_PREFIX

router = APIRouter(prefix="/ingest", tags=["ingestion"])

class IngestUrlRequest(BaseModel):
    url: str
    type: str  # "web" or "youtube"
    user_id: str

class IngestResponse(BaseModel):
    status: str
    message: str
    document_id: str
    chunks_count: int

async def run_ingestion_task(
    text: str,
    doc_id: str,
    source_url: str,
    source_type: str,
    user_id: str,
    document_title: str
):
    """
    Background task wrapper for ingest_document.
    Calculates namespace and handles the async execution.
    """
    try:
        namespace = f"{STUDENT_VECTOR_NAMESPACE_PREFIX}{user_id}" if user_id else None
        
        log_info(f"Background ingestion starting for {doc_id} (User: {user_id}, Namespace: {namespace})")
        
        result = await ingest_document(
            text=text,
            doc_id=doc_id,
            source_url=source_url,
            source_type=source_type,
            user_id=user_id,
            document_title=document_title,
            namespace=namespace,
            # Defaults for auto-detection
            subject="",
            topic="",
            content_type="user_upload"
        )
        
        if result.get("status") == "success":
            log_info(f"Background ingestion success for {doc_id}")
        else:
            log_error(f"Background ingestion returned error for {doc_id}: {result.get('error')}")

    except Exception as e:
        log_error(f"Background ingestion execution failed for {doc_id}: {e}")
        import traceback
        log_error(traceback.format_exc())


@router.post("/file", response_model=IngestResponse)
async def ingest_file(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    doc_id = str(uuid.uuid4())
    text = ""
    
    try:
        # Save to temp file to handle reading
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        
        # Parse
        try:
            if file.filename.lower().endswith(".pdf"):
                reader = PdfReader(tmp_path)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
            elif file.filename.lower().endswith(".txt") or file.filename.lower().endswith(".md"):
                with open(tmp_path, "r", encoding="utf-8") as f:
                    text = f.read()
            else:
                # Try simple text read for others
                with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        
        if not text.strip():
            raise HTTPException(400, "Could not extract text from file.")

        # Trigger background indexing
        document_title = os.path.splitext(file.filename)[0]  # Strip extension for clean title
        
        background_tasks.add_task(
            run_ingestion_task,
            text=text,
            doc_id=doc_id,
            source_url=file.filename,
            source_type="file",
            user_id=user_id,
            document_title=document_title
        )
        
        return IngestResponse(
            status="processing",
            message=f"File {file.filename} queued for smart ingestion.",
            document_id=doc_id,
            chunks_count=len(text.split()) // 500  # Estimate
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"File ingestion error: {e}")
        raise HTTPException(500, f"Failed to process file: {str(e)}")

@router.post("/url", response_model=IngestResponse)
async def ingest_url(
    request: IngestUrlRequest,
    background_tasks: BackgroundTasks
):
    doc_id = str(uuid.uuid4())
    text = ""
    
    try:
        if request.type == "youtube":
            try:
                # Extract video ID from URL
                # Handle formats: v=ID or /ID
                video_id = ""
                if "v=" in request.url:
                    video_id = request.url.split("v=")[-1].split("&")[0]
                elif "youtu.be/" in request.url:
                    video_id = request.url.split("youtu.be/")[-1].split("?")[0]
                
                if not video_id:
                    raise HTTPException(400, "Invalid YouTube URL")

                transcript = YouTubeTranscriptApi.get_transcript(video_id)
                text = " ".join([item['text'] for item in transcript])
            except Exception as e:
                log_error(f"YouTube transcript failed: {e}")
                raise HTTPException(400, f"Failed to fetch YouTube transcript. Video might not have captions.")
                
        elif request.type == "web":
            downloaded = trafilatura.fetch_url(request.url)
            if downloaded:
                text = trafilatura.extract(downloaded)
            
            if not text:
                 raise HTTPException(400, "Failed to extract content from webpage.")
        
        if not text or not text.strip():
            raise HTTPException(400, "No content found.")

        # Trigger background indexing
        background_tasks.add_task(
            run_ingestion_task,
            text=text,
            doc_id=doc_id,
            source_url=request.url,
            source_type=request.type,
            user_id=request.user_id,
            document_title=request.url  # Use URL as title if no better option
        )
        
        return IngestResponse(
            status="processing",
            message=f"URL {request.url} queued for smart ingestion.",
            document_id=doc_id,
            chunks_count=len(text.split()) // 500
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"URL ingestion error: {e}")
        raise HTTPException(500, f"Failed to process URL: {str(e)}")

# app/api/routes/evilearn_router.py
"""
EviLearn API Router — unified endpoint for the hybrid verification agent.

Endpoints:
  POST /api/evilearn/verify    — Full claim verification pipeline
  POST /api/evilearn/ingest    — Smart ingestion with importance scoring
  GET  /api/evilearn/audit/{id} — Retrieve an audit record
  POST /api/evilearn/feedback   — Human feedback on claim verification
  POST /api/evilearn/reindex    — Force re-indexing for a document
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid
import os
import tempfile
import shutil

from app.core.logging import log_info, log_error
from app.infrastructure.audit_store import get_audit
from app.infrastructure.metadata_store import (
    search_metadata,
    get_promotion_candidates,
    get_eviction_candidates,
)

router = APIRouter(prefix="/api/evilearn", tags=["evilearn"])


# ── Request / Response Models ──

class VerifyRequest(BaseModel):
    text: str = Field(..., description="User input (question or answer) to verify")
    user_id: str = Field(default="", description="User ID")
    session_id: str = Field(default="", description="Session ID")


class IngestRequest(BaseModel):
    source_url: str = ""
    source_type: str = "note"            # pdf, web, youtube, note
    user_id: str = ""
    subject: str = ""
    topic: str = ""
    subtopic: str = ""
    syllabus_keywords: List[str] = []
    teacher_tagged_chunks: List[int] = []


class FeedbackRequest(BaseModel):
    audit_id: str
    claim_id: str
    action: str = Field(..., description="'accept' or 'reject'")
    user_id: str = ""
    comment: str = ""


class ReindexRequest(BaseModel):
    doc_id: str
    user_id: str = ""
    subject: str = ""
    topic: str = ""
    subtopic: str = ""
    syllabus_keywords: List[str] = []


# ── Dependency: get EviLearn pipeline ──

_evilearn_pipeline = None


def get_evilearn_pipeline():
    global _evilearn_pipeline
    if _evilearn_pipeline is None:
        from app.agents.claim_extraction_agent.agent import ClaimExtractionAgent
        from app.agents.retrieval_agent.utils import index, embed_text
        from langchain_groq import ChatGroq
        from dotenv import load_dotenv

        try:
            load_dotenv()
        except Exception:
            pass

        llm_client = ChatGroq(model="llama-3.1-8b-instant")
        claim_extractor = ClaimExtractionAgent(llm_client)

        from app.rag.evilearn_pipeline import EviLearnPipeline
        _evilearn_pipeline = EviLearnPipeline(
            claim_extractor=claim_extractor,
            vector_db_client=index,
            embed_fn=embed_text,
        )
    return _evilearn_pipeline


# ── Endpoints ──

@router.post("/verify")
async def verify_claims(request: VerifyRequest):
    """
    Full EviLearn verification pipeline.
    Returns the strict JSON response schema defined in the system prompt.
    """
    try:
        pipeline = get_evilearn_pipeline()
        result = await pipeline.run(
            user_input=request.text,
            user_id=request.user_id,
            session_id=request.session_id,
        )
        return result.model_dump()
    except Exception as e:
        log_error(f"EviLearn verify failed: {e}")
        import traceback
        log_error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/file")
async def ingest_file(
    file: UploadFile = File(...),
    user_id: str = Form(default=""),
    subject: str = Form(default=""),
    topic: str = Form(default=""),
    subtopic: str = Form(default=""),
    syllabus_keywords: str = Form(default=""),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Smart file ingestion with importance scoring.
    Only embeds high-importance chunks; creates metadata for all.
    """
    doc_id = str(uuid.uuid4())
    text = ""

    try:
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        # Read raw bytes for original file storage (S3 or local)
        with open(tmp_path, "rb") as rb:
            original_bytes = rb.read()

        try:
            if file.filename.lower().endswith(".pdf"):
                from pypdf import PdfReader
                reader = PdfReader(tmp_path)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
            elif file.filename.lower().endswith((".txt", ".md")):
                with open(tmp_path, "r", encoding="utf-8") as f:
                    text = f.read()
            else:
                with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        if not text.strip():
            raise HTTPException(400, "Could not extract text from file.")

        # Parse syllabus keywords
        kw_list = [kw.strip() for kw in syllabus_keywords.split(",") if kw.strip()]

        # Trigger smart ingestion in background
        from app.rag.ingestion_pipeline import ingest_document
        from app.infrastructure.document_store import store_original_file

        async def _ingest_with_original():
            """Upload original file then run smart ingestion."""
            store_original_file(doc_id, file.filename, original_bytes)
            await ingest_document(
                text=text,
                doc_id=doc_id,
                source_url=file.filename,
                source_type="pdf" if file.filename.lower().endswith(".pdf") else "note",
                user_id=user_id,
                syllabus_keywords=kw_list,
                subject=subject,
                topic=topic,
                subtopic=subtopic,
            )

        background_tasks.add_task(_ingest_with_original)

        return {
            "status": "processing",
            "message": f"File {file.filename} queued for smart ingestion.",
            "document_id": doc_id,
            "estimated_chunks": len(text.split()) // 400,
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"EviLearn file ingest error: {e}")
        raise HTTPException(500, f"Failed to process file: {str(e)}")


@router.get("/audit/{audit_id}")
async def get_audit_record(audit_id: str):
    """Retrieve a full audit record by ID."""
    record = get_audit(audit_id)
    if not record:
        raise HTTPException(404, "Audit record not found")
    return record


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """
    Submit human feedback (accept/reject) for a specific claim.
    Used for continuous improvement and re-training scheduling.
    """
    from app.infrastructure.audit_store import record_audit

    feedback_entry = {
        "audit_id": request.audit_id,
        "claim_id": request.claim_id,
        "action": request.action,
        "user_id": request.user_id,
        "comment": request.comment,
        "type": "human_feedback",
    }

    record_audit(feedback_entry)
    log_info(f"Feedback recorded: {request.action} for claim {request.claim_id}")

    return {
        "status": "recorded",
        "message": f"Feedback '{request.action}' recorded for claim {request.claim_id}",
    }


@router.post("/reindex")
async def reindex_document(
    request: ReindexRequest,
    background_tasks: BackgroundTasks,
):
    """Force re-indexing for a specific document."""
    from app.infrastructure.document_store import fetch_document_text

    text = fetch_document_text(request.doc_id)
    if not text:
        raise HTTPException(404, f"Document {request.doc_id} not found in storage")

    from app.rag.ingestion_pipeline import ingest_document
    background_tasks.add_task(
        ingest_document,
        text=text,
        doc_id=request.doc_id,
        user_id=request.user_id,
        syllabus_keywords=request.syllabus_keywords,
        subject=request.subject,
        topic=request.topic,
        subtopic=request.subtopic,
    )

    return {
        "status": "processing",
        "message": f"Document {request.doc_id} queued for re-indexing.",
    }


@router.get("/admin/promotion-candidates")
async def list_promotion_candidates(threshold: int = 10):
    """List raw chunks that should be promoted to embedded (high query count)."""
    candidates = get_promotion_candidates(threshold)
    return {"candidates": candidates, "count": len(candidates)}


@router.get("/admin/eviction-candidates")
async def list_eviction_candidates(months: int = 6):
    """List embedded chunks that are candidates for eviction."""
    candidates = get_eviction_candidates(months)
    return {"candidates": candidates, "count": len(candidates)}

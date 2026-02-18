# app/api/routes/admin_router.py
"""
Admin API Router — system management endpoints for the IntelliSense admin dashboard.

Endpoints:
  GET  /api/admin/stats             — aggregate system statistics
  GET  /api/admin/documents         — list all unique indexed documents
  DELETE /api/admin/documents/{id}  — remove document from all layers
  GET  /api/admin/audit/recent      — most recent audit entries
  GET  /api/admin/metadata/search   — search metadata with filters
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
import os
import glob
import json

from app.core.config import AUDIT_LOG_PATH
from app.core.logging import log_info, log_error
from app.core.admin_auth import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ── Stats ──

@router.get("/stats")
async def get_system_stats(admin: dict = Depends(require_admin)):
    """Aggregate system statistics from metadata index and document store."""
    from app.infrastructure.metadata_store import _get_connection

    try:
        conn = _get_connection()
        cur = conn.cursor()

        # Total chunks
        cur.execute("SELECT COUNT(*) FROM chunk_metadata")
        total_chunks = cur.fetchone()[0]

        # Embedded vs raw
        cur.execute("SELECT COUNT(*) FROM chunk_metadata WHERE is_embedded = 1")
        embedded_chunks = cur.fetchone()[0]
        raw_chunks = total_chunks - embedded_chunks

        # Unique documents
        cur.execute("SELECT COUNT(DISTINCT doc_id) FROM chunk_metadata")
        unique_docs = cur.fetchone()[0]

        # Average importance
        cur.execute("SELECT AVG(importance_score) FROM chunk_metadata")
        avg_importance = cur.fetchone()[0] or 0.0

        # Top subjects
        cur.execute("""
            SELECT subject, COUNT(*) as cnt 
            FROM chunk_metadata 
            WHERE subject != '' 
            GROUP BY subject 
            ORDER BY cnt DESC 
            LIMIT 10
        """)
        top_subjects = [{"subject": r[0], "count": r[1]} for r in cur.fetchall()]

        # Top topics
        cur.execute("""
            SELECT topic, COUNT(*) as cnt 
            FROM chunk_metadata 
            WHERE topic != '' 
            GROUP BY topic 
            ORDER BY cnt DESC 
            LIMIT 10
        """)
        top_topics = [{"topic": r[0], "count": r[1]} for r in cur.fetchall()]

        # Source types breakdown
        cur.execute("""
            SELECT source_type, COUNT(*) as cnt 
            FROM chunk_metadata 
            GROUP BY source_type 
            ORDER BY cnt DESC
        """)
        source_types = [{"type": r[0], "count": r[1]} for r in cur.fetchall()]

        # Total query hits
        cur.execute("SELECT SUM(query_count) FROM chunk_metadata")
        total_query_hits = cur.fetchone()[0] or 0

        # Audit log count
        audit_count = 0
        if os.path.exists(AUDIT_LOG_PATH):
            audit_count = len(glob.glob(os.path.join(AUDIT_LOG_PATH, "*.json")))

        return {
            "total_chunks": total_chunks,
            "embedded_chunks": embedded_chunks,
            "raw_chunks": raw_chunks,
            "unique_documents": unique_docs,
            "avg_importance": round(avg_importance, 4),
            "total_query_hits": total_query_hits,
            "audit_log_count": audit_count,
            "top_subjects": top_subjects,
            "top_topics": top_topics,
            "source_types": source_types,
        }
    except Exception as e:
        log_error(f"Admin stats error: {e}")
        raise HTTPException(500, f"Failed to get stats: {str(e)}")


# ── Documents ──

@router.get("/documents")
async def list_documents(
    subject: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    admin: dict = Depends(require_admin),
):
    """List all unique indexed documents with aggregated chunk counts."""
    from app.infrastructure.metadata_store import _get_connection

    try:
        conn = _get_connection()
        cur = conn.cursor()

        query = """
            SELECT 
                doc_id,
                MIN(source_type) as source_type,
                MIN(source_url) as source_url,
                MIN(subject) as subject,
                MIN(topic) as topic,
                COUNT(*) as total_chunks,
                SUM(CASE WHEN is_embedded = 1 THEN 1 ELSE 0 END) as embedded_chunks,
                AVG(importance_score) as avg_importance,
                MIN(created_at) as created_at,
                SUM(query_count) as total_hits
            FROM chunk_metadata
            WHERE 1=1
        """
        params: list = []

        if subject:
            query += " AND subject LIKE ?"
            params.append(f"%{subject}%")
        if topic:
            query += " AND topic LIKE ?"
            params.append(f"%{topic}%")
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        query += " GROUP BY doc_id ORDER BY created_at DESC"

        cur.execute(query, params)
        rows = cur.fetchall()

        documents = []
        for row in rows:
            documents.append({
                "doc_id": row[0],
                "source_type": row[1] or "note",
                "source_url": row[2] or "",
                "subject": row[3] or "",
                "topic": row[4] or "",
                "total_chunks": row[5],
                "embedded_chunks": row[6],
                "avg_importance": round(row[7] or 0, 4),
                "created_at": row[8] or "",
                "total_hits": row[9] or 0,
            })

        return {"documents": documents, "count": len(documents)}
    except Exception as e:
        log_error(f"Admin documents error: {e}")
        raise HTTPException(500, f"Failed to list documents: {str(e)}")


@router.delete("/documents/{doc_id}")
async def delete_document_full(doc_id: str, admin: dict = Depends(require_admin)):
    """Delete a document from all layers (metadata, document store, vector db)."""
    from app.infrastructure.metadata_store import _get_connection
    from app.infrastructure.document_store import delete_document

    try:
        conn = _get_connection()
        cur = conn.cursor()

        # Get vector IDs to delete from Pinecone
        cur.execute(
            "SELECT vector_chunk_id FROM chunk_metadata WHERE doc_id = ? AND vector_chunk_id IS NOT NULL",
            (doc_id,),
        )
        vector_ids = [r[0] for r in cur.fetchall() if r[0]]

        # Delete from metadata index
        cur.execute("DELETE FROM chunk_metadata WHERE doc_id = ?", (doc_id,))
        deleted_rows = cur.rowcount
        conn.commit()

        # Delete from document store
        delete_document(doc_id)

        # Delete from Pinecone (best-effort)
        pinecone_deleted = 0
        if vector_ids:
            try:
                from app.agents.retrieval_agent.utils import index
                from app.core.config import PINECONE_NAMESPACE
                index.delete(ids=vector_ids, namespace=PINECONE_NAMESPACE)
                pinecone_deleted = len(vector_ids)
            except Exception as pe:
                log_error(f"Pinecone delete failed for {doc_id}: {pe}")

        log_info(f"Deleted document {doc_id}: {deleted_rows} metadata rows, {pinecone_deleted} vectors")

        return {
            "status": "deleted",
            "doc_id": doc_id,
            "metadata_rows_deleted": deleted_rows,
            "vectors_deleted": pinecone_deleted,
        }
    except Exception as e:
        log_error(f"Admin delete error: {e}")
        raise HTTPException(500, f"Failed to delete document: {str(e)}")


# ── Audit Logs ──

@router.get("/audit/recent")
async def get_recent_audits(limit: int = Query(50, ge=1, le=200), admin: dict = Depends(require_admin)):
    """List most recent audit log entries."""
    try:
        if not os.path.exists(AUDIT_LOG_PATH):
            return {"audits": [], "count": 0}

        files = glob.glob(os.path.join(AUDIT_LOG_PATH, "*.json"))
        # Sort by modification time descending
        files.sort(key=os.path.getmtime, reverse=True)
        files = files[:limit]

        audits = []
        for fpath in files:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    audits.append({
                        "audit_id": data.get("audit_id", ""),
                        "query": data.get("query", "")[:150],
                        "input_type": data.get("input_type", ""),
                        "claims_count": data.get("claims_count", 0),
                        "overall_confidence": data.get("overall_confidence", 0),
                        "user_id": data.get("user_id", ""),
                        "recorded_at": data.get("recorded_at", ""),
                        "warnings": data.get("warnings", []),
                        "type": data.get("type", "verification"),
                    })
            except Exception:
                continue

        return {"audits": audits, "count": len(audits)}
    except Exception as e:
        log_error(f"Admin audit error: {e}")
        raise HTTPException(500, f"Failed to get audit logs: {str(e)}")


# ── Metadata Search ──

@router.get("/metadata/search")
async def search_metadata_admin(
    subject: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    doc_id: Optional[str] = Query(None),
    min_importance: Optional[float] = Query(None),
    embedded_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    admin: dict = Depends(require_admin),
):
    """Search metadata index with optional filters."""
    from app.infrastructure.metadata_store import _get_connection

    try:
        conn = _get_connection()
        cur = conn.cursor()

        query = "SELECT * FROM chunk_metadata WHERE 1=1"
        params: list = []

        if subject:
            query += " AND subject LIKE ?"
            params.append(f"%{subject}%")
        if topic:
            query += " AND topic LIKE ?"
            params.append(f"%{topic}%")
        if doc_id:
            query += " AND doc_id = ?"
            params.append(doc_id)
        if min_importance is not None:
            query += " AND importance_score >= ?"
            params.append(min_importance)
        if embedded_only:
            query += " AND is_embedded = 1"

        query += " ORDER BY importance_score DESC LIMIT ?"
        params.append(limit)

        cur.execute(query, params)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

        results = [dict(zip(columns, row)) for row in rows]

        return {"results": results, "count": len(results)}
    except Exception as e:
        log_error(f"Admin metadata search error: {e}")
        raise HTTPException(500, f"Failed to search metadata: {str(e)}")

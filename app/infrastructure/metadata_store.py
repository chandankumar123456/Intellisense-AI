# app/infrastructure/metadata_store.py
"""
Layer-3: Metadata Knowledge Index
SQLite-backed metadata store mapping vector hits → doc_id, page, offset, importance_score.
Every chunk (embedded or raw) gets a metadata entry here.
"""

import sqlite3
import os
import json
import threading
from typing import List, Dict, Any, Optional
from app.core.config import METADATA_DB_PATH
from app.core.logging import log_info, log_error


_local = threading.local()


def _get_connection() -> sqlite3.Connection:
    """Thread-local SQLite connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        os.makedirs(os.path.dirname(METADATA_DB_PATH), exist_ok=True)
        _local.conn = sqlite3.connect(METADATA_DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _init_schema(_local.conn)
    return _local.conn


def _init_schema(conn: sqlite3.Connection):
    """Create the metadata table if it doesn't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS chunk_metadata (
            id              TEXT PRIMARY KEY,
            doc_id          TEXT NOT NULL,
            subject         TEXT DEFAULT '',
            topic           TEXT DEFAULT '',
            subtopic        TEXT DEFAULT '',
            page            INTEGER DEFAULT 0,
            offset_start    INTEGER DEFAULT 0,
            offset_end      INTEGER DEFAULT 0,
            importance_score REAL DEFAULT 0.0,
            vector_chunk_id TEXT DEFAULT NULL,
            storage_pointer TEXT DEFAULT '',
            source_url      TEXT DEFAULT '',
            source_type     TEXT DEFAULT 'note',
            chunk_text      TEXT DEFAULT '',
            user_id         TEXT DEFAULT '',
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_queried_at TIMESTAMP DEFAULT NULL,
            query_count     INTEGER DEFAULT 0,
            is_embedded     BOOLEAN DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_doc_id ON chunk_metadata(doc_id);
        CREATE INDEX IF NOT EXISTS idx_importance ON chunk_metadata(importance_score);
        CREATE INDEX IF NOT EXISTS idx_subject_topic ON chunk_metadata(subject, topic);
        CREATE INDEX IF NOT EXISTS idx_user_id ON chunk_metadata(user_id);
        CREATE INDEX IF NOT EXISTS idx_vector_chunk_id ON chunk_metadata(vector_chunk_id);
    """)
    conn.commit()


def upsert_metadata(entry: Dict[str, Any]):
    """Insert or replace a metadata entry."""
    conn = _get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO chunk_metadata
        (id, doc_id, subject, topic, subtopic, page, offset_start, offset_end,
         importance_score, vector_chunk_id, storage_pointer, source_url,
         source_type, chunk_text, user_id, is_embedded)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        entry.get("id", ""),
        entry.get("doc_id", ""),
        entry.get("subject", ""),
        entry.get("topic", ""),
        entry.get("subtopic", ""),
        entry.get("page", 0),
        entry.get("offset_start", 0),
        entry.get("offset_end", 0),
        entry.get("importance_score", 0.0),
        entry.get("vector_chunk_id"),
        entry.get("storage_pointer", ""),
        entry.get("source_url", ""),
        entry.get("source_type", "note"),
        entry.get("chunk_text", ""),
        entry.get("user_id", ""),
        entry.get("is_embedded", False),
    ))
    conn.commit()


def upsert_metadata_batch(entries: List[Dict[str, Any]]):
    """Batch insert/replace metadata entries."""
    conn = _get_connection()
    conn.executemany("""
        INSERT OR REPLACE INTO chunk_metadata
        (id, doc_id, subject, topic, subtopic, page, offset_start, offset_end,
         importance_score, vector_chunk_id, storage_pointer, source_url,
         source_type, chunk_text, user_id, is_embedded)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(
        e.get("id", ""),
        e.get("doc_id", ""),
        e.get("subject", ""),
        e.get("topic", ""),
        e.get("subtopic", ""),
        e.get("page", 0),
        e.get("offset_start", 0),
        e.get("offset_end", 0),
        e.get("importance_score", 0.0),
        e.get("vector_chunk_id"),
        e.get("storage_pointer", ""),
        e.get("source_url", ""),
        e.get("source_type", "note"),
        e.get("chunk_text", ""),
        e.get("user_id", ""),
        e.get("is_embedded", False),
    ) for e in entries])
    conn.commit()


def search_metadata(
    filters: Dict[str, Any],
    top_k: int = 20,
) -> List[Dict[str, Any]]:
    """
    Search metadata index with flexible filters.
    Supported filters: doc_id, subject, topic, subtopic, user_id,
                       min_importance, source_type
    Results sorted by importance_score DESC.
    """
    conn = _get_connection()
    conditions = []
    params = []

    if "doc_id" in filters:
        conditions.append("doc_id = ?")
        params.append(filters["doc_id"])
    if "subject" in filters:
        conditions.append("subject LIKE ?")
        params.append(f"%{filters['subject']}%")
    if "topic" in filters:
        conditions.append("topic LIKE ?")
        params.append(f"%{filters['topic']}%")
    if "subtopic" in filters:
        conditions.append("subtopic LIKE ?")
        params.append(f"%{filters['subtopic']}%")
    if "user_id" in filters:
        conditions.append("user_id = ?")
        params.append(filters["user_id"])
    if "min_importance" in filters:
        conditions.append("importance_score >= ?")
        params.append(filters["min_importance"])
    if "source_type" in filters:
        conditions.append("source_type = ?")
        params.append(filters["source_type"])
    if "is_embedded" in filters:
        conditions.append("is_embedded = ?")
        params.append(1 if filters["is_embedded"] else 0)

    where = " AND ".join(conditions) if conditions else "1=1"
    query = f"""
        SELECT * FROM chunk_metadata
        WHERE {where}
        ORDER BY importance_score DESC
        LIMIT ?
    """
    params.append(top_k)

    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_metadata_by_ids(chunk_ids: List[str]) -> List[Dict[str, Any]]:
    """Fetch metadata entries by their IDs."""
    if not chunk_ids:
        return []
    conn = _get_connection()
    placeholders = ",".join("?" * len(chunk_ids))
    rows = conn.execute(
        f"SELECT * FROM chunk_metadata WHERE id IN ({placeholders})",
        chunk_ids,
    ).fetchall()
    return [dict(row) for row in rows]


def get_metadata_by_vector_ids(vector_ids: List[str]) -> List[Dict[str, Any]]:
    """Fetch metadata entries by their vector_chunk_id."""
    if not vector_ids:
        return []
    conn = _get_connection()
    placeholders = ",".join("?" * len(vector_ids))
    rows = conn.execute(
        f"SELECT * FROM chunk_metadata WHERE vector_chunk_id IN ({placeholders})",
        vector_ids,
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_document_section(
    doc_id: str,
    page: int,
    offset_start: Optional[int] = None,
    offset_end: Optional[int] = None,
) -> Optional[str]:
    """
    Fetch the exact text for a document section.
    Uses metadata store chunk_text as the source of truth.
    If offsets provided, slice the text.
    """
    conn = _get_connection()

    if offset_start is not None and offset_end is not None:
        row = conn.execute(
            """SELECT chunk_text FROM chunk_metadata
               WHERE doc_id = ? AND page = ?
               AND offset_start <= ? AND offset_end >= ?
               ORDER BY importance_score DESC LIMIT 1""",
            (doc_id, page, offset_start, offset_end),
        ).fetchone()
    else:
        row = conn.execute(
            """SELECT chunk_text FROM chunk_metadata
               WHERE doc_id = ? AND page = ?
               ORDER BY importance_score DESC LIMIT 1""",
            (doc_id, page),
        ).fetchone()

    if row:
        text = row["chunk_text"]
        if offset_start is not None and offset_end is not None:
            return text[offset_start:offset_end]
        return text
    return None


def record_query_hit(chunk_ids: List[str]):
    """Record that these chunks were queried (for eviction/promotion)."""
    if not chunk_ids:
        return
    conn = _get_connection()
    placeholders = ",".join("?" * len(chunk_ids))
    conn.execute(f"""
        UPDATE chunk_metadata
        SET query_count = query_count + 1,
            last_queried_at = CURRENT_TIMESTAMP
        WHERE id IN ({placeholders})
    """, chunk_ids)
    conn.commit()


def get_promotion_candidates(query_count_threshold: int = 10) -> List[Dict[str, Any]]:
    """Find raw (non-embedded) chunks that are frequently queried and should be promoted."""
    conn = _get_connection()
    rows = conn.execute("""
        SELECT * FROM chunk_metadata
        WHERE is_embedded = 0 AND query_count >= ?
        ORDER BY query_count DESC
        LIMIT 50
    """, (query_count_threshold,)).fetchall()
    return [dict(row) for row in rows]


def get_eviction_candidates(unused_months: int = 6) -> List[Dict[str, Any]]:
    """Find embedded chunks unused for N months with low importance."""
    conn = _get_connection()
    rows = conn.execute("""
        SELECT * FROM chunk_metadata
        WHERE is_embedded = 1
          AND importance_score < 0.9
          AND (last_queried_at IS NULL
               OR last_queried_at < datetime('now', ? || ' months'))
        ORDER BY last_queried_at ASC
        LIMIT 100
    """, (f"-{unused_months}",)).fetchall()
    return [dict(row) for row in rows]

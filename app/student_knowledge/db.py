# app/student_knowledge/db.py
"""
SQLite-backed student knowledge database.
Manages upload lifecycle, fingerprinting, and per-student scoping.
"""

import os
import json
import sqlite3
import threading
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.core.logging import log_info, log_error


class StudentKnowledgeDB:
    """Thread-safe singleton for student knowledge persistence."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: str = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: str = None):
        if self._initialized:
            return
        from app.core.config import STUDENT_KNOWLEDGE_DB_PATH
        self.db_path = db_path or STUDENT_KNOWLEDGE_DB_PATH
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)
        self._init_schema()
        self._initialized = True
        log_info(f"StudentKnowledgeDB initialized at {self.db_path}")

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self):
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS student_uploads (
                    upload_id TEXT PRIMARY KEY,
                    student_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_uri TEXT NOT NULL,
                    provided_title TEXT,
                    tags TEXT DEFAULT '[]',
                    notes TEXT,
                    is_private INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'queued',
                    error_reason TEXT,
                    content_fingerprint TEXT,
                    chunk_count INTEGER DEFAULT 0,
                    token_count INTEGER DEFAULT 0,
                    trace_path TEXT,
                    vector_namespace TEXT,
                    probe_text TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_health_check TEXT,
                    health_score REAL DEFAULT 10.0
                );
                
                CREATE INDEX IF NOT EXISTS idx_student_uploads_student_id 
                    ON student_uploads(student_id);
                CREATE INDEX IF NOT EXISTS idx_student_uploads_fingerprint 
                    ON student_uploads(student_id, content_fingerprint);
                CREATE INDEX IF NOT EXISTS idx_student_uploads_status
                    ON student_uploads(student_id, status);

                CREATE TABLE IF NOT EXISTS student_audit_log (
                    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    upload_id TEXT,
                    details TEXT,
                    timestamp TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_audit_student
                    ON student_audit_log(student_id, timestamp);
            """)
            # Migration: add columns if missing (for existing DBs)
            for col, default in [
                ("token_count", "0"), ("trace_path", "NULL"), 
                ("last_health_check", "NULL"), ("health_score", "10.0"),
                ("probe_text", "NULL"),
                ("reindex_attempt_count", "0"),
                ("last_reindex_at", "NULL"),
                ("embedding_model_id", "NULL"),
                ("embedding_model_version", "NULL"),
            ]:
                try:
                    conn.execute(f"ALTER TABLE student_uploads ADD COLUMN {col} {'REAL DEFAULT ' + default if col == 'health_score' else ('INTEGER DEFAULT ' + default if col in ('token_count', 'reindex_attempt_count') else 'TEXT')}")
                except sqlite3.OperationalError:
                    pass  # Column already exists
            conn.commit()
        finally:
            conn.close()

    def create_upload(
        self,
        student_id: str,
        source_type: str,
        source_uri: str,
        content_fingerprint: str = None,
        provided_title: str = None,
        tags: List[str] = None,
        upload_id: str = None,
        probe_text: str = None,
    ) -> str:
        """Create a new upload record. Returns upload_id."""
        import uuid
        uid = upload_id or str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        vector_ns = f"student_{student_id}"

        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO student_uploads 
                   (upload_id, student_id, source_type, source_uri, provided_title,
                    tags, content_fingerprint, vector_namespace, status, created_at, updated_at, probe_text)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?, ?)""",
                (uid, student_id, source_type, source_uri, provided_title,
                 json.dumps(tags or []), content_fingerprint, vector_ns, now, now, probe_text)
            )
            conn.commit()
            log_info(f"Created upload {uid} for student {student_id}")
            return uid
        except Exception as e:
            log_error(f"Failed to create upload: {e}")
            raise
        finally:
            conn.close()

    def get_upload(self, upload_id: str) -> Optional[Dict[str, Any]]:
        """Get a single upload record by ID."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM student_uploads WHERE upload_id = ?", (upload_id,)
            ).fetchone()
            return self._row_to_dict(row) if row else None
        finally:
            conn.close()

    def list_uploads(self, student_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """List all uploads for a student, newest first."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT upload_id, source_type, source_uri, provided_title, 
                          status, chunk_count, tags, is_private, created_at, error_reason
                   FROM student_uploads 
                   WHERE student_id = ? 
                   ORDER BY created_at DESC LIMIT ?""",
                (student_id, limit)
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]
        finally:
            conn.close()

    def update_status(
        self, upload_id: str, status: str, 
        error_reason: str = None, chunk_count: int = None,
        token_count: int = None, trace_path: str = None,
        probe_text: str = None
    ):
        """Update the lifecycle status of an upload."""
        now = datetime.utcnow().isoformat()
        conn = self._get_conn()
        try:
            # Build dynamic SET clause
            sets = ["status=?", "error_reason=?", "updated_at=?"]
            params = [status, error_reason, now]
            if chunk_count is not None:
                sets.append("chunk_count=?")
                params.append(chunk_count)
            if token_count is not None:
                sets.append("token_count=?")
                params.append(token_count)
            if trace_path is not None:
                sets.append("trace_path=?")
                params.append(trace_path)
            if probe_text is not None:
                sets.append("probe_text=?")
                params.append(probe_text)
            
            # probe_text is usually set at creation, but support update if needed (e.g. reindex)
            # Not added to update logic by default to save bandwidth, explicit update if needed
            
            params.append(upload_id)
            conn.execute(
                f"UPDATE student_uploads SET {', '.join(sets)} WHERE upload_id=?",
                tuple(params)
            )
            conn.commit()
            log_info(f"Upload {upload_id} status → {status}")
        finally:
            conn.close()

    def find_by_fingerprint(self, student_id: str, fingerprint: str) -> Optional[str]:
        """Check for duplicate content. Returns upload_id if found."""
        if not fingerprint:
            return None
        conn = self._get_conn()
        try:
            row = conn.execute(
                """SELECT upload_id FROM student_uploads 
                   WHERE student_id=? AND content_fingerprint=? AND status != 'error'
                   LIMIT 1""",
                (student_id, fingerprint)
            ).fetchone()
            return row["upload_id"] if row else None
        finally:
            conn.close()

    def delete_upload(self, upload_id: str) -> bool:
        """Delete an upload record. Returns True if deleted."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "DELETE FROM student_uploads WHERE upload_id=?", (upload_id,)
            )
            conn.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                log_info(f"Deleted upload {upload_id}")
            return deleted
        finally:
            conn.close()

    def update_tags(self, upload_id: str, tags: List[str] = None, notes: str = None):
        """Update tags and/or notes for an upload."""
        now = datetime.utcnow().isoformat()
        conn = self._get_conn()
        try:
            if tags is not None and notes is not None:
                conn.execute(
                    "UPDATE student_uploads SET tags=?, notes=?, updated_at=? WHERE upload_id=?",
                    (json.dumps(tags), notes, now, upload_id)
                )
            elif tags is not None:
                conn.execute(
                    "UPDATE student_uploads SET tags=?, updated_at=? WHERE upload_id=?",
                    (json.dumps(tags), now, upload_id)
                )
            elif notes is not None:
                conn.execute(
                    "UPDATE student_uploads SET notes=?, updated_at=? WHERE upload_id=?",
                    (notes, now, upload_id)
                )
            conn.commit()
        finally:
            conn.close()

    def update_privacy(self, upload_id: str, is_private: bool):
        """Toggle privacy flag."""
        now = datetime.utcnow().isoformat()
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE student_uploads SET is_private=?, updated_at=? WHERE upload_id=?",
                (1 if is_private else 0, now, upload_id)
            )
            conn.commit()
        finally:
            conn.close()

    def update_fingerprint(self, upload_id: str, fingerprint: str):
        """Set the content fingerprint after content is fetched."""
        now = datetime.utcnow().isoformat()
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE student_uploads SET content_fingerprint=?, updated_at=? WHERE upload_id=?",
                (fingerprint, now, upload_id)
            )
            conn.commit()
        finally:
            conn.close()

    def get_upload_owner(self, upload_id: str) -> Optional[str]:
        """Get the student_id that owns an upload. For access control."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT student_id FROM student_uploads WHERE upload_id=?", (upload_id,)
            ).fetchone()
            return row["student_id"] if row else None
        finally:
            conn.close()

    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        """Convert sqlite3.Row to dict, parsing JSON fields."""
        if row is None:
            return {}
        d = dict(row)
        # Parse tags JSON
        if "tags" in d and isinstance(d["tags"], str):
            try:
                d["tags"] = json.loads(d["tags"])
            except (json.JSONDecodeError, TypeError):
                d["tags"] = []
        # Convert is_private int to bool
        if "is_private" in d:
            d["is_private"] = bool(d["is_private"])
        return d

    # ── Audit Logging ──

    def log_audit(self, student_id: str, action: str, upload_id: str = None, details: str = None):
        """Record an audit log entry."""
        now = datetime.utcnow().isoformat()
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO student_audit_log (student_id, action, upload_id, details, timestamp) VALUES (?, ?, ?, ?, ?)",
                (student_id, action, upload_id, details, now)
            )
            conn.commit()
        except Exception as e:
            log_error(f"Audit log failed: {e}")
        finally:
            conn.close()

    # ── Quota Helpers ──

    def count_uploads_today(self, student_id: str) -> int:
        """Count uploads created today for quota enforcement."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM student_uploads WHERE student_id=? AND created_at >= ?",
                (student_id, today)
            ).fetchone()
            return row["cnt"] if row else 0
        finally:
            conn.close()

    def get_total_chunks(self, student_id: str) -> int:
        """Get total chunk count across all uploads for a student (storage estimate)."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT COALESCE(SUM(chunk_count), 0) as total FROM student_uploads WHERE student_id=? AND status IN ('indexed', 'indexed_partial')",
                (student_id,)
            ).fetchone()
            return row["total"] if row else 0
        finally:
            conn.close()

    def get_uploads_needing_maintenance(
        self, student_id: str, check_interval_hours: int = 24, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get uploads that haven't been health-checked recently."""
        conn = self._get_conn()
        try:
            # Query: indexed uploads where last_health_check is null or older than interval
            # Also include uploads in drift/degraded states for re-check
            rows = conn.execute(
                """SELECT * FROM student_uploads 
                   WHERE student_id = ? 
                   AND status IN ('indexed', 'indexed_partial', 'indexed_weak', 'retrieval_unstable')
                   AND (
                       last_health_check IS NULL 
                       OR datetime(last_health_check) < datetime('now', ?)
                   )
                   ORDER BY last_health_check ASC
                   LIMIT ?""",
                (student_id, f"-{check_interval_hours} hours", limit)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def update_health_status(self, upload_id: str, health_score: float, status: Optional[str] = None):
        """Update health check timestamp and score."""
        conn = self._get_conn()
        try:
            now = datetime.utcnow().isoformat()
            if status:
                conn.execute(
                    "UPDATE student_uploads SET last_health_check=?, health_score=?, status=?, updated_at=? WHERE upload_id=?",
                    (now, health_score, status, now, upload_id)
                )
            else:
                 conn.execute(
                    "UPDATE student_uploads SET last_health_check=?, health_score=? WHERE upload_id=?",
                    (now, health_score, upload_id)
                )
            conn.commit()
        finally:
            conn.close()

    # ── Reindex Attempt Tracking ──

    def record_reindex_attempt(self, upload_id: str):
        """Increment reindex attempt count and record timestamp."""
        conn = self._get_conn()
        try:
            now = datetime.utcnow().isoformat()
            conn.execute(
                """UPDATE student_uploads 
                   SET reindex_attempt_count = COALESCE(reindex_attempt_count, 0) + 1,
                       last_reindex_at = ?, updated_at = ?
                   WHERE upload_id = ?""",
                (now, now, upload_id)
            )
            conn.commit()
        finally:
            conn.close()

    def get_reindex_attempts(self, upload_id: str) -> tuple:
        """Get (reindex_attempt_count, last_reindex_at) for an upload."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT COALESCE(reindex_attempt_count, 0) as cnt, last_reindex_at FROM student_uploads WHERE upload_id = ?",
                (upload_id,)
            ).fetchone()
            if row:
                return row["cnt"], row["last_reindex_at"]
            return 0, None
        finally:
            conn.close()

    def reset_reindex_attempts(self, upload_id: str):
        """Reset reindex tracking after a successful reindex."""
        conn = self._get_conn()
        try:
            now = datetime.utcnow().isoformat()
            conn.execute(
                "UPDATE student_uploads SET reindex_attempt_count = 0, last_reindex_at = NULL, updated_at = ? WHERE upload_id = ?",
                (now, upload_id)
            )
            conn.commit()
        finally:
            conn.close()

    # ── Embedding Model Tracking ──

    def update_embedding_model(self, upload_id: str, model_id: str, model_version: str):
        """Store the embedding model ID and version used for this upload."""
        conn = self._get_conn()
        try:
            now = datetime.utcnow().isoformat()
            conn.execute(
                "UPDATE student_uploads SET embedding_model_id = ?, embedding_model_version = ?, updated_at = ? WHERE upload_id = ?",
                (model_id, model_version, now, upload_id)
            )
            conn.commit()
        finally:
            conn.close()

    def get_uploads_needing_model_migration(
        self, student_id: str, current_model_id: str, current_version: str
    ) -> List[Dict[str, Any]]:
        """Get uploads indexed with a different embedding model (needing reindex on model change)."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT * FROM student_uploads
                   WHERE student_id = ?
                   AND status IN ('indexed', 'indexed_partial')
                   AND (
                       embedding_model_id IS NULL
                       OR embedding_model_id != ?
                       OR embedding_model_version IS NULL
                       OR embedding_model_version != ?
                   )
                   ORDER BY created_at DESC""",
                (student_id, current_model_id, current_version)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

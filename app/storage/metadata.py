import os
import sqlite3
import json
from typing import Dict, Any, List, Optional
from .interface import MetadataStorageInterface
from app.core.config import METADATA_DB_PATH, LOCAL_STORAGE_PATH

# Shared helper for initializing the table schema
def _init_schema(conn: sqlite3.Connection):
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
            is_embedded     BOOLEAN DEFAULT 0,
            section_type    TEXT DEFAULT 'body',
            document_title  TEXT DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_doc_id ON chunk_metadata(doc_id);
        CREATE INDEX IF NOT EXISTS idx_section_type ON chunk_metadata(section_type);
    """)
    # Add columns if they don't exist (migration for existing databases)
    for col, default in [("section_type", "'body'"), ("document_title", "''")]:
        try:
            conn.execute(f"ALTER TABLE chunk_metadata ADD COLUMN {col} TEXT DEFAULT {default}")
        except Exception:
            pass  # Column already exists
    conn.commit()

class SqliteMetadataImpl:
    """Shared logic for SQLite Metadata"""
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        # Using check_same_thread=False for simplicity in this MVP 
        # (production should likely use a stronger pattern or connection pooling)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        _init_schema(self.conn)

    @staticmethod
    def _validate_metadata(metadata) -> Dict[str, Any]:
        """Ensure metadata is a dict with required fields. Fix corrupt entries."""
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        if not isinstance(metadata, dict):
            metadata = {}
        # Ensure required fields have defaults
        metadata.setdefault("id", "")
        metadata.setdefault("doc_id", "")
        metadata.setdefault("section_type", "body")
        return metadata

    def upsert(self, metadata: Dict[str, Any]):
        metadata = self._validate_metadata(metadata)
        self.conn.execute("""
            INSERT OR REPLACE INTO chunk_metadata
            (id, doc_id, subject, topic, subtopic, page, offset_start, offset_end,
             importance_score, vector_chunk_id, storage_pointer, source_url,
             source_type, chunk_text, user_id, is_embedded, section_type, document_title)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metadata.get("id", ""),
            metadata.get("doc_id", ""),
            metadata.get("subject", ""),
            metadata.get("topic", ""),
            metadata.get("subtopic", ""),
            metadata.get("page", 0),
            metadata.get("offset_start", 0),
            metadata.get("offset_end", 0),
            metadata.get("importance_score", 0.0),
            metadata.get("vector_chunk_id"),
            metadata.get("storage_pointer", ""),
            metadata.get("source_url", ""),
            metadata.get("source_type", "note"),
            metadata.get("chunk_text", ""),
            metadata.get("user_id", ""),
            metadata.get("is_embedded", False),
            metadata.get("section_type", "body"),
            metadata.get("document_title", ""),
        ))
        self.conn.commit()

    def upsert_batch(self, metadata_list: List[Dict[str, Any]]):
        validated = [self._validate_metadata(m) for m in metadata_list]
        self.conn.executemany("""
            INSERT OR REPLACE INTO chunk_metadata
            (id, doc_id, subject, topic, subtopic, page, offset_start, offset_end,
             importance_score, vector_chunk_id, storage_pointer, source_url,
             source_type, chunk_text, user_id, is_embedded, section_type, document_title)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [(
            m.get("id", ""),
            m.get("doc_id", ""),
            m.get("subject", ""),
            m.get("topic", ""),
            m.get("subtopic", ""),
            m.get("page", 0),
            m.get("offset_start", 0),
            m.get("offset_end", 0),
            m.get("importance_score", 0.0),
            m.get("vector_chunk_id"),
            m.get("storage_pointer", ""),
            m.get("source_url", ""),
            m.get("source_type", "note"),
            m.get("chunk_text", ""),
            m.get("user_id", ""),
            m.get("is_embedded", False),
            m.get("section_type", "body"),
            m.get("document_title", ""),
        ) for m in validated])
        self.conn.commit()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute("SELECT * FROM chunk_metadata WHERE id = ?", (key,)).fetchone()
        return dict(row) if row else None

    def search(self, filters: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        conditions = []
        params = []
        for k, v in filters.items():
            conditions.append(f"{k} = ?")
            params.append(v)
        
        where = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM chunk_metadata WHERE {where} LIMIT ?"
        params.append(limit)
        
        rows = self.conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

class CloudMetadataStorage(MetadataStorageInterface):
    """
    In 'AWS' mode, we might use RDS or DynamoDB. 
    For this implementation, and to keep it simple as a 'Cloud DB' toggle, 
    we will simulate it (or use the main 'metadata.db' if that's considered the 'Cloud' one).
    User requirement says: "Metadata -> Cloud DB".
    Existing app uses `data/metadata_index.db`. We'll treat that as the 'Cloud' one for now.
    """
    def __init__(self):
        # Existing DB path
        self.impl = SqliteMetadataImpl(METADATA_DB_PATH)

    def upsert(self, metadata: Dict[str, Any]) -> None:
        self.impl.upsert(metadata)
    
    def upsert_batch(self, metadata_list: List[Dict[str, Any]]) -> None:
        self.impl.upsert_batch(metadata_list)
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        return self.impl.get(key)
    
    def search(self, filters: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        return self.impl.search(filters, limit)

class LocalMetadataStorage(MetadataStorageInterface):
    """
    In 'Local' mode, we use a different SQLite file in /local_storage/metadata.db
    """
    def __init__(self):
        local_db_path = os.path.join(LOCAL_STORAGE_PATH, "metadata", "local_index.db")
        self.impl = SqliteMetadataImpl(local_db_path)

    def upsert(self, metadata: Dict[str, Any]) -> None:
        self.impl.upsert(metadata)
    
    def upsert_batch(self, metadata_list: List[Dict[str, Any]]) -> None:
        self.impl.upsert_batch(metadata_list)
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        return self.impl.get(key)
    
    def search(self, filters: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        return self.impl.search(filters, limit)

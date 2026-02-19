# app/student_knowledge/models.py
"""
Pydantic models and enums for Student Knowledge Ingestion & Retrieval.
"""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class SourceType(str, Enum):
    FILE = "file"
    YOUTUBE = "youtube"
    WEBSITE = "website"


class UploadStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    INDEXED = "indexed"
    INDEXED_PARTIAL = "indexed_partial"
    DUPLICATE = "duplicate"
    INDEX_FAILED = "index_failed"
    INDEX_VALIDATION_FAILED = "index_validation_failed"
    PROCESSING_DELAYED = "processing_delayed"
    EXTRACTION_FAILED = "extraction_failed"
    INVALID_SOURCE = "invalid_source"
    INSUFFICIENT_CONTENT = "insufficient_content"
    LOW_INFORMATION_CONTENT = "low_information_content"
    EMBEDDING_LOW_DIVERSITY = "embedding_low_diversity"
    INDEX_QUALITY_FAILED = "index_quality_failed"
    RETRIEVAL_UNSTABLE = "retrieval_unstable"
    INDEXED_WEAK = "indexed_weak"
    INDEX_DRIFT_DETECTED = "index_drift_detected"
    INDEX_QUALITY_DEGRADED = "index_quality_degraded"
    EMBEDDING_DRIFT = "embedding_drift"
    REINDEX_REQUIRED = "reindex_required"
    REINDEX_EXHAUSTED = "reindex_exhausted"
    REINDEX_COOLDOWN = "reindex_cooldown"
    ERROR = "error"


class UploadEvent(BaseModel):
    """Canonical upload event schema."""
    upload_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    source_type: SourceType
    source_uri: str  # filename for files, URL for youtube/web
    provided_title: Optional[str] = None
    provided_tags: List[str] = Field(default_factory=list)
    consent: bool = True
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    client_nonce: Optional[str] = None


class UploadRecord(BaseModel):
    """Full lifecycle record for a student upload."""
    upload_id: str
    student_id: str
    source_type: str
    source_uri: str
    provided_title: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    is_private: bool = False
    status: UploadStatus = UploadStatus.QUEUED
    error_reason: Optional[str] = None
    content_fingerprint: Optional[str] = None
    chunk_count: int = 0
    token_count: int = 0
    created_at: str = ""
    updated_at: str = ""
    vector_namespace: Optional[str] = None
    trace_path: Optional[str] = None
    extraction_status: Optional[str] = None
    validation_status: Optional[str] = None
    retry_count: int = 0
    last_retry_reason: Optional[str] = None
    reindex_attempt_count: int = 0
    last_reindex_at: Optional[str] = None
    embedding_model_id: Optional[str] = None
    embedding_model_version: Optional[str] = None


class UploadListItem(BaseModel):
    """Lightweight view for dashboard listing."""
    upload_id: str
    source_type: str
    source_uri: str
    title: Optional[str] = None
    status: str
    chunk_count: int = 0
    tags: List[str] = Field(default_factory=list)
    is_private: bool = False
    created_at: str = ""
    error_reason: Optional[str] = None


class ChunkRecord(BaseModel):
    """A single processed chunk ready for embedding."""
    chunk_id: str
    upload_id: str
    student_id: str
    text: str
    section: Optional[str] = None
    heading: Optional[str] = None
    timestamp_start: Optional[float] = None  # For video content
    timestamp_end: Optional[float] = None
    concepts: List[str] = Field(default_factory=list)
    fingerprint: str = ""
    chunk_index: int = 0
    token_count: int = 0

# app/rag/schemas.py
"""
Strict output schemas for the IntelliSense / EviLearn agent.
Matches the JSON contract defined in the system prompt.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
from uuid import uuid4


# ── Evidence snippet attached to a claim ──
class EvidenceSnippet(BaseModel):
    doc_id: str = ""
    page: int = 0
    offset_start: Optional[int] = None
    offset_end: Optional[int] = None
    snippet: str = ""
    source_url: Optional[str] = None
    similarity_score: float = 0.0
    importance_score: float = 0.0


# ── Single verified claim ──
class VerifiedClaim(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    text: str = ""
    status: Literal["Supported", "Weakly Supported", "Unsupported"] = "Unsupported"
    confidence: float = 0.0
    evidence: List[EvidenceSnippet] = []
    explanation: str = ""


# ── Retrieval trace sub-objects ──
class VectorHitTrace(BaseModel):
    vector_id: str = ""
    score: float = 0.0
    metadata: Dict[str, Any] = {}


class MetadataHitTrace(BaseModel):
    doc_id: str = ""
    page: int = 0
    importance_score: float = 0.0


class FetchedSectionTrace(BaseModel):
    doc_id: str = ""
    page: int = 0
    chars: int = 0


class TimingsTrace(BaseModel):
    vector_search: float = 0.0
    metadata_scan: float = 0.0
    fetch: float = 0.0
    rerank: float = 0.0
    verification: float = 0.0
    total: float = 0.0


class RetrievalTrace(BaseModel):
    vector_hits: List[VectorHitTrace] = []
    metadata_hits: List[MetadataHitTrace] = []
    fetched_sections: List[FetchedSectionTrace] = []
    timings_ms: TimingsTrace = TimingsTrace()


class MetricsOutput(BaseModel):
    used_vector_count: int = 0
    fetched_docs: int = 0
    latency_ms: int = 0


# ── Top-level output ──
class EviLearnResponse(BaseModel):
    """Strict JSON response for the EviLearn agent. Matches the contract exactly."""
    query: str = ""
    input_type: Literal["question", "answer"] = "question"
    claims: List[VerifiedClaim] = []
    overall_confidence: float = 0.0
    retrieval_trace: RetrievalTrace = RetrievalTrace()
    audit_id: str = Field(default_factory=lambda: str(uuid4()))
    warnings: List[str] = []
    metrics: MetricsOutput = MetricsOutput()


# ── Ingestion schemas ──
class ChunkCandidate(BaseModel):
    """A candidate chunk before embedding decision."""
    id: str = ""
    doc_id: str = ""
    text: str = ""
    page: int = 0
    offset_start: int = 0
    offset_end: int = 0
    importance_score: float = 0.0
    source_url: str = ""
    source_type: str = "note"
    subject: str = ""
    topic: str = ""
    subtopic: str = ""
    academic_year: str = ""          # "1st" / "2nd" / "3rd" / "4th"
    semester: str = ""               # "1" / "2"
    module: str = ""                 # "Unit 1", "Module 3", etc.
    content_type: str = "notes"      # notes / ppt / textbook / reference / question_bank / other
    difficulty_level: str = ""       # basic / exam_focused / advanced / conceptual
    source_tag: str = ""             # class_notes / standard_textbook / important / repeated_question
    keywords: str = ""               # comma-separated keywords
    user_id: str = ""
    should_embed: bool = False
    section_type: str = "body"
    document_title: str = ""


# ── Confidence sub-scores (for audit) ──
class ConfidenceSubScores(BaseModel):
    max_similarity: float = 0.0
    evidence_agreement: float = 0.0
    token_coverage: float = 0.0
    source_reliability: float = 0.0
    raw_confidence: float = 0.0

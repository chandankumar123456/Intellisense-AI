# app/core/config.py
"""
Centralized configuration for IntelliSense / EviLearn Hybrid Agent.
All constants, thresholds, and settings referenced across the system.
"""

# ── Embedding ──
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384

# ── Chunking ──
CHUNK_SIZE_TOKENS = 500          # 400-600 token range mid-point
CHUNK_OVERLAP_TOKENS = 50
CHUNK_MIN_LENGTH_CHARS = 80      # skip garbage tiny sections

# ── Deduplication ──
DEDUP_COSINE_THRESHOLD = 0.92

# ── Importance scoring ──
IMPORTANCE_EMBED_THRESHOLD = 0.7  # embed only chunks ≥ this
IMPORTANCE_WEIGHTS = {
    "syllabus_match": 0.30,
    "header_prominence": 0.20,
    "citation_frequency": 0.15,
    "teacher_tag": 0.20,
    "content_density": 0.15,
}

# ── Retrieval limits ──
VECTOR_TOP_K_DEFAULT = 30
METADATA_SCAN_LIMIT = 20
RERANK_TOP_K = 5
MAX_FETCHED_SECTIONS_PER_QUERY = 20

# ── Confidence calibration weights ──
CONFIDENCE_WEIGHTS = {
    "max_similarity": 0.45,
    "evidence_agreement": 0.25,
    "token_coverage": 0.15,
    "source_reliability": 0.15,
}

# ── Confidence → status mapping ──
STATUS_SUPPORTED_THRESHOLD = 0.75
STATUS_SUPPORTED_SIM_PEAK = 0.72
STATUS_WEAKLY_SUPPORTED_THRESHOLD = 0.45

# ── Caching ──
CACHE_TTL_SECONDS = 3600  # 1 hour default
CACHE_PREFIX = "evilearnv1:"

# ── Vector eviction ──
EVICTION_UNUSED_MONTHS = 6
EVICTION_IMPORTANCE_KEEP = 0.9

# ── Performance ──
MAX_QUERY_TIMEOUT_SECONDS = 30

# ── Pinecone ──
PINECONE_INDEX_NAME = "intellisense-ai-dense-index-v2"
PINECONE_CLOUD = "aws"
PINECONE_REGION = "us-east-1"
PINECONE_NAMESPACE = "Intellisense-namespace"

# ── Metadata DB ──
METADATA_DB_PATH = "data/metadata_index.db"

# ── Document Storage ──
DOCUMENT_STORAGE_PATH = "data/documents"

# ── Audit ──
AUDIT_LOG_PATH = "data/audit"

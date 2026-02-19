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
IMPORTANCE_EMBED_THRESHOLD = 0.05  # significantly lowered to ensure user uploads are embedded
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

# ── Intent-Aware Retrieval ──
SECTION_BOOST_WEIGHT = 0.15
DOCUMENT_BOOST_WEIGHT = 0.10
RETRIEVAL_QUALITY_THRESHOLD = 0.3
MAX_RETRIEVAL_RETRIES = 1

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

# ── Storage Backend ──
# "s3" (default) or "local" for backward-compatible dev mode
import os as _os
STORAGE_BACKEND = _os.getenv("STORAGE_BACKEND", "s3").lower()

# ── AWS S3 ──
AWS_REGION = _os.getenv("AWS_REGION", "ap-south-1")
S3_BUCKET_NAME = _os.getenv("S3_BUCKET_NAME", "")
S3_DOCUMENT_PREFIX = "documents"  # top-level key prefix in bucket

# ── Storage Mode ──
STORAGE_MODE = _os.getenv("STORAGE_MODE", "aws").lower()
CHROMA_DB_PATH = _os.path.join("local_storage", "chroma_db")
LOCAL_STORAGE_PATH = "local_storage"

# ── Multi-Stage Retrieval ──
QUERY_EXPANSION_ENABLED = True
MAX_EXPANSION_VARIANTS = 3
EXPANSION_MERGE_DEDUP_THRESHOLD = 0.92

# ── Retrieval Confidence ──
RETRIEVAL_CONFIDENCE_HIGH = 0.70
RETRIEVAL_CONFIDENCE_LOW = 0.35

# ── Context Verification ──
CONTEXT_VERIFICATION_ENABLED = True
MIN_ENTITY_COVERAGE = 0.40
MIN_ANSWER_SIGNAL_SCORE = 0.25

# ── Hallucination Control ──
GROUNDED_MODE_THRESHOLD = 0.35

# ── Ranking Stability ──
GENERIC_CHUNK_PENALTY = -0.15
INFO_DENSITY_BONUS_WEIGHT = 0.10

# ── Hierarchical Retrieval ──
HIERARCHICAL_RETRIEVAL_ENABLED = True
HIERARCHICAL_TOP_DOCS = 3
HIERARCHICAL_SECTION_BOOST = 0.15

# ── Retrieval Memory ──
RETRIEVAL_MEMORY_ENABLED = True
RETRIEVAL_MEMORY_DB_PATH = "data/retrieval_memory.db"
RETRIEVAL_MEMORY_DECAY_DAYS = 30

# ── Semantic Coverage ──
SEMANTIC_COVERAGE_MIN = 0.70
COVERAGE_GAP_FILL_ENABLED = True
MAX_GAP_FILL_QUERIES = 3

# ── Failure Prediction ──
FAILURE_PREDICTION_ENABLED = True
FAILURE_RISK_RETRY_THRESHOLD = 0.60
FAILURE_RISK_GROUND_THRESHOLD = 0.80

# ── Chunk Clustering ──
CHUNK_CLUSTERING_ENABLED = True
CLUSTER_OVERLAP_THRESHOLD = 0.60

# ── Adaptive Confidence ──
ADAPTIVE_CONFIDENCE_ENABLED = True

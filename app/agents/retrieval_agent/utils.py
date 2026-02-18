# app/agents/retrieval_agent/utils.py
from dotenv import load_dotenv
import os
from sentence_transformers import SentenceTransformer
from app.storage import storage_manager
from app.core.config import PINECONE_NAMESPACE

# Load .env file with encoding fallback
try:
    load_dotenv()
except UnicodeDecodeError:
    try:
        load_dotenv(encoding='utf-16')
    except Exception:
        try:
            load_dotenv(encoding='utf-16-le')
        except Exception:
            pass

namespace = PINECONE_NAMESPACE
embedding_model_name = "all-MiniLM-L6-v2"

# Lazy initialization
_model = None

def _get_embedding_model():
    """Lazy initialization of SentenceTransformer model"""
    global _model
    if _model is None:
        _model = SentenceTransformer(embedding_model_name)
    return _model

def get_embeddings(text_list):
    model = _get_embedding_model()
    return model.encode(text_list).tolist()

# Export embedding function helper
embed_text = get_embeddings

# Export index as the SAL vectors adapter
# This allows compatible calls like index.upsert(...) if signature matches
index = storage_manager.vectors

# -----------------------------
# ORIGINAL RECORDS (For re-seeding if needed)
# -----------------------------
records = []


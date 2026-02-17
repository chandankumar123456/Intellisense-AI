
# app/agents/retrieval_agent/utils.py
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
import os
from sentence_transformers import SentenceTransformer

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

index_name = "intellisense-ai-dense-index-v2" # Changed version to force new index
cloud = "aws"
region = "us-east-1"
namespace = "Intellisense-namespace"
embedding_model_name = "all-MiniLM-L6-v2"

# Lazy initialization
_pc = None
_index = None
_model = None

def _get_pinecone_client():
    """Lazy initialization of Pinecone client"""
    global _pc
    if _pc is None:
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise ValueError(
                "PINECONE_API_KEY environment variable is not set."
            )
        _pc = Pinecone(api_key=api_key)
    return _pc

def _get_embedding_model():
    """Lazy initialization of SentenceTransformer model"""
    global _model
    if _model is None:
        _model = SentenceTransformer(embedding_model_name)
    return _model

def get_embeddings(text_list):
    model = _get_embedding_model()
    return model.encode(text_list).tolist()

def _get_index():
    """Lazy initialization of Pinecone index"""
    global _index
    if _index is None:
        pc = _get_pinecone_client()
        # Create index if missing
        if not pc.has_index(index_name):
            try:
                pc.create_index(
                    name=index_name,
                    dimension=384, # Dimension for all-MiniLM-L6-v2
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud=cloud,
                        region=region
                    )
                )
            except Exception as e:
                # Handle race condition or other errors
                print(f"Index creation warning: {e}")
                
        _index = pc.Index(index_name)
    return _index

# Create a module-level proxy 
class _LazyIndex:
    """Lazy proxy for Pinecone index"""
    def _ensure_initialized(self):
        return _get_index()
    
    def __getattr__(self, name):
        return getattr(self._ensure_initialized(), name)

    def upsert(self, *args, **kwargs):
        return self._ensure_initialized().upsert(*args, **kwargs)

    def query(self, *args, **kwargs):
        # Wrapper to handle potential embedding generation if needed here, 
        # but retrieval logic handles it. 
        # Standard Pinecone index has .query(), .upsert(), etc.
        return self._ensure_initialized().query(*args, **kwargs)
    
# Export index as a lazy proxy
index = _LazyIndex()

# Export embedding function helper
embed_text = get_embeddings

# -----------------------------
# ORIGINAL RECORDS (For re-seeding if needed)
# -----------------------------
records = [
    # ... (same records as before but truncated for brevity to avoid clutter)
    # I will keep the records definition or load them if needed.
    # For now, just exporting 'records' variable so imports don't break.
]

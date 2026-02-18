import os
import asyncio
import logging
from app.storage import storage_manager
from app.rag.ingestion_pipeline import ingest_document
from app.rag.importance_scorer import compute_importance

# Setup logging
logging.basicConfig(level=logging.INFO)

async def test_ingestion():
    print("--- Testing Ingestion ---")
    
    # 1. Force Local Mode
    os.environ["STORAGE_MODE"] = "local"
    storage_manager.reinitialize("local")
    print(f"Storage Mode: {storage_manager.mode}")
    
    # 2. Test Importance Scorer
    text = (
        "This is a test document. It contains some information about usage. "
        "We need to ensure that this text is long enough to be chunked correctly. "
        "The minimum length is 80 characters, so we are adding more words here to pass that limit. "
        "This checks if the embedding pipeline is working as expected."
    )
    score = compute_importance(text)
    print(f"Test Chunk Score: {score}")
    
    from app.core.config import IMPORTANCE_EMBED_THRESHOLD
    print(f"Threshold: {IMPORTANCE_EMBED_THRESHOLD}")
    if score < IMPORTANCE_EMBED_THRESHOLD:
        print("WARNING: Test chunk would be skipped!")

    # 3. Run Ingestion
    doc_id = "test_doc_repro_1"
    print(f"Ingesting doc: {doc_id}")
    
    try:
        result = await ingest_document(
            text=text, 
            doc_id=doc_id, 
            subject="Test Subject",
            topic="Test Topic"
        )
        print("Ingestion Result:", result)
    except Exception as e:
        print(f"Ingestion Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ingestion())

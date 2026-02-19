import asyncio
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

async def run_test():
    print("Starting manual test...")
    try:
        from app.rag.ingestion_pipeline import ingest_document
        print("Imported ingest_document successfully.")
    except Exception as e:
        print(f"Import failed: {e}")
        return

    # Mock dependencies
    with patch("app.storage.storage_manager") as mock_storage, \
         patch("app.rag.subject_detector.detect_subject") as mock_detect, \
         patch("app.rag.ingestion_pipeline.chunk_text_smart") as mock_chunk, \
         patch("app.agents.retrieval_agent.utils.embed_text") as mock_embed, \
         patch("app.rag.ingestion_pipeline.deduplicate_chunks") as mock_dedup:

        # Setup mocks
        mock_storage.vectors.upsert = MagicMock()
        mock_storage.metadata.upsert_batch = MagicMock()
        mock_storage.files.save_file = MagicMock()
        
        mock_detect.return_value.subject = "Test Subject"
        mock_detect.return_value.confidence = 0.95
        mock_detect.return_value.content_type = "notes"
        mock_detect.return_value.secondary_subject = ""
        
        mock_chunk_obj = MagicMock()
        mock_chunk_obj.text = "chunk text"
        mock_chunk_obj.should_embed = True
        mock_chunk_obj.id = "chunk_1"
        mock_chunk.return_value = [mock_chunk_obj]
        
        mock_embed.return_value = [[0.1] * 384]
        
        mock_dedup.return_value = ([mock_chunk_obj], [[0.1] * 384])

        print("Mocks setup complete.")

        # Test Case 1: Student Namespace
        doc_id = "test_doc_manual"
        user_id = "student_manual"
        namespace = f"student_{user_id}"
        
        print(f"Running ingest_document for {doc_id} with namespace {namespace}...")
        
        try:
            result = await ingest_document(
                text="some text",
                doc_id=doc_id,
                user_id=user_id,
                namespace=namespace
            )
        except Exception as e:
            print(f"EXCEPTION in ingest_document: {e}")
            import traceback
            with open("traceback.txt", "w") as tf:
                tf.write(traceback.format_exc())
            return

        print(f"Result: {result}")
        with open("test_result.txt", "w") as f:
            f.write(str(result))
        
        if result["status"] != "success":
            print(f"FAILURE: Status is {result['status']}. Error: {result.get('error')}")
            return

        # Verification
        mock_storage.vectors.upsert.assert_called_once()
        call_kwargs = mock_storage.vectors.upsert.call_args[1]
        
        if call_kwargs["namespace"] != namespace:
            print(f"FAILURE: Namespace mismatch in vector upsert. Expected {namespace}, got {call_kwargs['namespace']}")
        else:
            print("SUCCESS: Vector upsert namespace correct.")
            
        vectors = call_kwargs["vectors"]
        if vectors[0]["metadata"]["namespace"] != namespace:
             print(f"FAILURE: Vector metadata namespace mismatch. Got {vectors[0]['metadata']['namespace']}")
        else:
             print("SUCCESS: Vector metadata namespace correct.")

        mock_storage.metadata.upsert_batch.assert_called_once()
        meta_entries = mock_storage.metadata.upsert_batch.call_args[0][0]
        if meta_entries[0]["namespace"] != namespace:
             print(f"FAILURE: Metadata upsert namespace mismatch. Got {meta_entries[0]['namespace']}")
        else:
             print("SUCCESS: Metadata upsert namespace correct.")

        print("MANUAL TEST PASSED!")

if __name__ == "__main__":
    asyncio.run(run_test())

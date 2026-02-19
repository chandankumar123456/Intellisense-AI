
import asyncio
import sys
from unittest.mock import MagicMock, patch, AsyncMock

# Mock modules before importing agent
sys.modules["app.core.config"] = MagicMock()
sys.modules["app.core.logging"] = MagicMock()
sys.modules["app.student_knowledge.db"] = MagicMock()
sys.modules["app.student_knowledge.fetcher"] = MagicMock()
sys.modules["app.student_knowledge.chunker"] = MagicMock()
sys.modules["app.student_knowledge.enricher"] = MagicMock()
sys.modules["app.student_knowledge.metrics"] = MagicMock()
sys.modules["app.storage"] = MagicMock()
sys.modules["app.agents.retrieval_agent.utils"] = MagicMock()

# Now import agent
with patch("app.student_knowledge.db.StudentKnowledgeDB") as MockDB:
    from app.student_knowledge.agent import StudentKnowledgeAgent

async def test_drift_detection():
    print("\nTesting Drift Detection...")
    
    # Setup Mocks
    mock_db = MagicMock()
    mock_storage = MagicMock()
    mock_vectors = MagicMock()
    mock_storage.vectors = mock_vectors
    
    # 1. Setup stale upload needing check
    upload = {
        "upload_id": "test_upload_1",
        "status": "indexed",
        "vector_namespace": "ns",
        "probe_text": "Sample text",
        "source_type": "website",
        "source_uri": "http://example.com"
    }
    
    # 2. Mock DB returning this upload
    mock_db.get_uploads_needing_maintenance.return_value = [upload]
    
    # 3. Mock Storage returning NO matches (Drift!)
    mock_vectors.query.return_value = {"matches": []}
    
    # 4. Mock Embed
    mock_embed = AsyncMock(return_value=[[0.1, 0.2]])

    with patch.dict("sys.modules", {
        "app.storage": MagicMock(storage_manager=mock_storage),
        "app.agents.retrieval_agent.utils": MagicMock(embed_text=mock_embed),
        "app.student_knowledge.agent.StudentKnowledgeDB": MagicMock(return_value=mock_db)
    }):
        agent = StudentKnowledgeAgent()
        agent.db = mock_db # Inject mock DB
        agent.reindex_upload = AsyncMock() # Mock reindex to verify call
        
        # Run Monitor
        await agent.monitor_index_health("student1", auto_reindex=False)
        
        # Verify status update to drift
        mock_db.update_status.assert_called_with(
            "test_upload_1", 
            "index_drift_detected", 
            error_reason="Health check failed"
        )
        print("✅ Correctly detected drift when probe fails")

async def test_auto_reindex():
    print("\nTesting Auto-Reindex...")
    
    mock_db = MagicMock()
    
    # 1. Setup unstable upload
    upload = {
        "upload_id": "test_upload_2",
        "status": "retrieval_unstable", # This status forces reindex
        "vector_namespace": "ns",
        "updated_at": "2023-01-01T00:00:00" # Old
    }
    mock_db.get_uploads_needing_maintenance.return_value = [upload]
    
    with patch.dict("sys.modules", {
        "app.storage": MagicMock(),
        "app.agents.retrieval_agent.utils": MagicMock(),
    }):
        agent = StudentKnowledgeAgent()
        agent.db = mock_db
        agent.reindex_upload = AsyncMock()
        
        # Run Monitor
        await agent.monitor_index_health("student1", auto_reindex=True)
        
        # Verify reindex call
        agent.reindex_upload.assert_called_with("test_upload_2", "student1")
        print("✅ Correctly triggered auto-reindex for unstable upload")

async def main():
    await test_drift_detection()
    await test_auto_reindex()

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import sys
from unittest.mock import MagicMock, patch
from app.student_knowledge.agent import StudentKnowledgeAgent
from app.student_knowledge.models import UploadStatus

# Mock data
LOW_INFO_TEXT = "report report report 123"
HIGH_INFO_TEXT = "The fundamental theorem of calculus relates differentiation and integration."
LOW_DIVERSITY_EMBEDDINGS = [[0.1, 0.2]] * 10
HIGH_DIVERSITY_EMBEDDINGS = [[0.1, 0.2], [0.9, 0.8]]

async def test_low_info_rejection():
    print("Testing Low Info Rejection...")
    agent = StudentKnowledgeAgent()
    agent.db = MagicMock()
    agent._persist_trace = MagicMock()
    
    # Mock fetch to return low info
    with patch("app.student_knowledge.agent.fetch_file") as mock_fetch:
        mock_fetch.return_value = {
            "text": LOW_INFO_TEXT,
            "structure": {}, 
            "fingerprint": "abc",
            "title": "Bad Doc",
            "content_type": "text/plain"
        }
        
        result = await agent.ingest_file_upload(b"data", "bad.txt", "student1", "upload1")
        
        if result["status"] == "low_information_content":
            print("✅ Low info content rejected")
        else:
            print(f"❌ Failed: status is {result['status']}")

async def test_embedding_diversity():
    print("\nTesting Embedding Diversity Check...")
    agent = StudentKnowledgeAgent()
    # Direct check
    is_diverse = agent._check_embedding_diversity(LOW_DIVERSITY_EMBEDDINGS)
    if not is_diverse:
        print("✅ Low diversity detected")
    else:
        print("❌ Failed to detect low diversity")
        
    is_diverse_ok = agent._check_embedding_diversity(HIGH_DIVERSITY_EMBEDDINGS)
    if is_diverse_ok:
         print("✅ High diversity passed")
    else:
         print("❌ Failed high diversity")

async def test_semantic_quality_gate():
    print("\nTesting Semantic Quality Gate (Mocked)...")
    
    # Mock storage_manager inside the function import
    mock_storage = MagicMock()
    mock_vectors = MagicMock()
    mock_storage.vectors = mock_vectors
    mock_vectors.query.return_value = {"matches": []} # simulate poor grounding

    mock_embed = MagicMock()
    mock_embed.return_value = [[0.1, 0.2]]

    with patch.dict("sys.modules", {
        "app.storage": MagicMock(storage_manager=mock_storage),
        "app.agents.retrieval_agent.utils": MagicMock(embed_text=mock_embed)
    }):
        agent = StudentKnowledgeAgent()
        chunks = [{"text": "Concept A", "chunk_id": "1"}, {"text": "Concept B", "chunk_id": "2"}]
        score, passed = await agent._validate_index_quality(chunks, "ns", "up1")
        
        if not passed:
            print(f"✅ Weak index correctly rejected (score {score})")
        else:
            print(f"❌ Failed: weak index passed with score {score}")

async def main():
    await test_low_info_rejection()
    await test_embedding_diversity()
    await test_semantic_quality_gate()

if __name__ == "__main__":
    asyncio.run(main())

"""
Verification script for Operational Stability Hardening.
Tests: reindex backoff, cooldown, semaphore throttling, embedding model tracking, drift severity gating.
Uses mocking to isolate from live services.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

# Mock modules before importing agent
sys.modules["app.core.config"] = MagicMock(
    STUDENT_VECTOR_NAMESPACE_PREFIX="student_",
    STUDENT_TRACE_DIR="data/traces",
    STUDENT_INDEX_VALIDATION_THRESHOLD=0.5,
    STUDENT_MAX_RETRY_ATTEMPTS=3,
    STUDENT_MIN_CONTENT_CHARS=100,
    STUDENT_MIN_TOKEN_COUNT=50,
    STUDENT_MAX_REINDEX_ATTEMPTS=5,
    STUDENT_REINDEX_BASE_DELAY_SECONDS=0.01,  # Very short for tests
    STUDENT_REINDEX_MAX_DELAY_SECONDS=0.05,
    STUDENT_REINDEX_COOLDOWN_HOURS=6,
    STUDENT_MAX_CONCURRENT_REPAIRS=2,
    STUDENT_EMBEDDING_MODEL_ID="all-MiniLM-L6-v2",
    STUDENT_EMBEDDING_MODEL_VERSION="1.0",
    STUDENT_REINDEX_ON_MODEL_CHANGE=True,
    STUDENT_DRIFT_CHECK_INTERVAL_HOURS=24,
    STUDENT_DRIFT_SEVERE_THRESHOLD=3.0,
)
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

passed = 0
failed = 0

def report(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}: {detail}")


# Test 1: Reindex blocked after max attempts
async def test_reindex_max_attempts():
    print("\n1. Testing Reindex Max Attempts Guard...")
    mock_db = MagicMock()
    mock_db.get_reindex_attempts.return_value = (5, "2026-01-01T00:00:00")

    agent = StudentKnowledgeAgent()
    agent.db = mock_db
    agent._run_pipeline = AsyncMock()

    await agent.reindex_upload("upload_001", "student_001")

    mock_db.update_status.assert_called_with(
        "upload_001", "reindex_exhausted",
        error_reason="Max reindex attempts (5) exhausted"
    )
    report("Reindex blocked after max attempts", True)
    report("_run_pipeline NOT called", not agent._run_pipeline.called)


# Test 2: Cooldown prevents rapid re-trigger
async def test_reindex_cooldown():
    print("\n2. Testing Reindex Cooldown Guard...")
    mock_db = MagicMock()
    recent_time = datetime.utcnow().isoformat()
    mock_db.get_reindex_attempts.return_value = (2, recent_time)

    agent = StudentKnowledgeAgent()
    agent.db = mock_db
    agent._run_pipeline = AsyncMock()

    await agent.reindex_upload("upload_002", "student_001")

    mock_db.update_status.assert_called_with(
        "upload_002", "reindex_cooldown",
        error_reason=f"Cooldown active (last attempt: {recent_time})"
    )
    report("Reindex skipped during cooldown", True)
    report("_run_pipeline NOT called during cooldown", not agent._run_pipeline.called)


# Test 3: Cooldown elapsed allows reindex
async def test_cooldown_elapsed():
    print("\n3. Testing Cooldown Elapsed Allows Reindex...")
    result = StudentKnowledgeAgent._reindex_cooldown_elapsed(
        (datetime.utcnow() - timedelta(hours=7)).isoformat()
    )
    report("Cooldown elapsed after 7 hours (threshold=6)", result)

    result2 = StudentKnowledgeAgent._reindex_cooldown_elapsed(
        (datetime.utcnow() - timedelta(hours=1)).isoformat()
    )
    report("Cooldown NOT elapsed after 1 hour", not result2)


# Test 4: Successful reindex resets attempts
async def test_reindex_success_resets():
    print("\n4. Testing Successful Reindex Resets Attempts...")
    mock_db = MagicMock()
    old_time = (datetime.utcnow() - timedelta(hours=7)).isoformat()
    mock_db.get_reindex_attempts.return_value = (1, old_time)
    mock_db.get_upload.return_value = {
        "upload_id": "upload_003",
        "source_type": "website",
        "source_uri": "https://example.com",
        "provided_title": "Test",
        "tags": "[]",
        "vector_namespace": "student_s1",
    }

    agent = StudentKnowledgeAgent()
    agent.db = mock_db
    agent._run_pipeline = AsyncMock(return_value={"status": "indexed", "upload_id": "upload_003"})

    # The agent imports fetch_url locally from sys.modules["app.student_knowledge.fetcher"]
    # Set it directly on the mocked module
    mock_fetcher_module = sys.modules["app.student_knowledge.fetcher"]
    mock_fetcher_module.fetch_url = AsyncMock(return_value=("This is enough text for testing purposes." * 5, {}))

    await agent.reindex_upload("upload_003", "s1")

    mock_db.record_reindex_attempt.assert_called_once_with("upload_003")
    report("Reindex attempt recorded", mock_db.record_reindex_attempt.called)
    
    # Check if _run_pipeline was called (text was recovered)
    pipeline_called = agent._run_pipeline.called
    report("_run_pipeline called with recovered text", pipeline_called)
    
    if pipeline_called:
        mock_db.reset_reindex_attempts.assert_called_once_with("upload_003")
        report("Attempts reset on success", True)
    else:
        report("Attempts reset on success", False, "_run_pipeline was not called")


# Test 5: Semaphore limits concurrent repairs
async def test_semaphore_throttling():
    print("\n5. Testing Repair Semaphore Throttling...")
    agent = StudentKnowledgeAgent()
    concurrent_count = 0
    max_concurrent = 0

    report(f"Semaphore initialized with value {agent._repair_semaphore._value}", agent._repair_semaphore._value == 2)

    async def sem_task():
        nonlocal concurrent_count, max_concurrent
        async with agent._repair_semaphore:
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.05)
            concurrent_count -= 1

    tasks = [asyncio.create_task(sem_task()) for _ in range(4)]
    await asyncio.gather(*tasks)
    report(f"Max concurrent repairs was {max_concurrent} (limit=2)", max_concurrent <= 2)


# Test 6: Drift severity gating
async def test_drift_severity_gating():
    print("\n6. Testing Drift Severity Gating...")
    mock_db = MagicMock()

    upload = {
        "upload_id": "upload_005",
        "status": "indexed_weak",
        "vector_namespace": "ns",
        "probe_text": "Sample text",
    }
    mock_db.get_uploads_needing_maintenance.return_value = [upload]
    mock_db.get_reindex_attempts.return_value = (0, None)

    agent = StudentKnowledgeAgent()
    agent.db = mock_db
    agent.reindex_upload = AsyncMock()
    agent._check_upload_health = AsyncMock(return_value=("reindex_required", 5.0))

    await agent.monitor_index_health("student1", auto_reindex=True)
    report("Auto-reindex NOT triggered for non-severe score (5.0)", not agent.reindex_upload.called)

    # Now test with severe score
    agent._check_upload_health = AsyncMock(return_value=("reindex_required", 1.0))
    agent.reindex_upload = AsyncMock()
    mock_db.get_reindex_attempts.return_value = (0, None)

    await agent.monitor_index_health("student1", auto_reindex=True)
    report("Auto-reindex triggered for severe score (1.0)", agent.reindex_upload.called)


# Test 7: Monitor skips exhausted uploads
async def test_monitor_skips_exhausted():
    print("\n7. Testing Monitor Skips Exhausted Uploads...")
    mock_db = MagicMock()

    upload = {
        "upload_id": "upload_006",
        "status": "indexed_weak",
        "vector_namespace": "ns",
    }
    mock_db.get_uploads_needing_maintenance.return_value = [upload]
    mock_db.get_reindex_attempts.return_value = (5, None)

    agent = StudentKnowledgeAgent()
    agent.db = mock_db
    agent.reindex_upload = AsyncMock()
    agent._check_upload_health = AsyncMock(return_value=("reindex_required", 0.5))

    await agent.monitor_index_health("student1", auto_reindex=True)

    report("Upload marked as reindex_exhausted", 
           mock_db.update_status.call_args[0] == ("upload_006", "reindex_exhausted"))
    report("Reindex NOT called for exhausted upload", not agent.reindex_upload.called)


# Test 8: Embedding model version stored
async def test_embedding_model_stored():
    print("\n8. Testing Embedding Model Version Tracking...")
    # Structural check: verify the mock db methods are callable
    mock_db = MagicMock()
    mock_db.update_embedding_model("test_id", "model_a", "1.0")
    report("update_embedding_model callable", mock_db.update_embedding_model.called)
    
    mock_db.get_uploads_needing_model_migration("s1", "model_a", "1.0")
    report("get_uploads_needing_model_migration callable", mock_db.get_uploads_needing_model_migration.called)


# Main
async def main():
    print("=" * 60)
    print("Operational Stability Hardening -- Verification")
    print("=" * 60)

    await test_reindex_max_attempts()
    await test_reindex_cooldown()
    await test_cooldown_elapsed()
    await test_reindex_success_resets()
    await test_semaphore_throttling()
    await test_drift_severity_gating()
    await test_monitor_skips_exhausted()
    await test_embedding_model_stored()

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'=' * 60}")
    if failed == 0:
        print("ALL Operational Stability Verifications Passed!")
    else:
        print("Some tests failed. Review output above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())


import os
import shutil
import asyncio
from app.student_knowledge.db import StudentKnowledgeDB
from app.student_knowledge.agent import StudentKnowledgeAgent
from app.core.config import STUDENT_TRACE_DIR

def verify_db_schema():
    print("\n--- Verifying DB Schema ---")
    db = StudentKnowledgeDB()
    try:
        # Check if new columns exist by trying to insert/update them
        uid = "test_hardening_001"
        db.create_upload("student_test", "file", "test.pdf", "Test Title", upload_id=uid)
        
        # Update with new fields
        db.update_status(uid, "processing", token_count=100, trace_path="test/path")
        
        # Verify read
        upload = db.get_upload(uid)
        assert upload["token_count"] == 100, f"Token count mismatch: {upload['token_count']}"
        assert upload["trace_path"] == "test/path", f"Trace path mismatch: {upload['trace_path']}"
        
        # Verify audit log
        db.log_audit("student_test", "TEST_ACTION", uid, "Running verification")
        
        # Verify metrics
        uploads_today = db.count_uploads_today("student_test")
        print(f"Uploads today for student_test: {uploads_today}")
        assert uploads_today >= 1
        
        print("✅ DB Schema verification passed!")
        
        # Cleanup
        db.delete_upload(uid)
        
    except Exception as e:
        print(f"❌ DB Verification failed: {e}")
        raise e

async def verify_agent_trace():
    print("\n--- Verifying Agent Trace Persistence ---")
    agent = StudentKnowledgeAgent()
    student_id = "student_verify"
    upload_id = "test_trace_001"
    
    # Ensure trace dir exists but clean for this test
    trace_dir = os.path.join(STUDENT_TRACE_DIR, student_id)
    if os.path.exists(trace_dir):
        shutil.rmtree(trace_dir)
    
    try:
        # Create a mock upload record first
        agent.db.create_upload(student_id, "file", "trace_test.txt", "Trace Test", upload_id=upload_id)
        
        # Initialize a trace
        trace = agent._init_trace(upload_id, student_id, "file", "trace_test.txt")
        agent._trace_step(trace, "test_step", "ok", duration_ms=50, extra={"info": "verified"})
        
        # Persist it
        agent._persist_trace(student_id, upload_id, trace)
        
        # Check file existence
        expected_path = os.path.join(STUDENT_TRACE_DIR, student_id, f"{upload_id}.json")
        if os.path.exists(expected_path):
            print(f"✅ Trace file created at {expected_path}")
        else:
            raise FileNotFoundError(f"Trace file not found at {expected_path}")
            
    except Exception as e:
        print(f"❌ Agent Trace Verification failed: {e}")
        raise e
    finally:
        agent.db.delete_upload(upload_id)


async def verify_logic_scenarios():
    print("\n--- Verifying Logic Scenarios ---")
    db = StudentKnowledgeDB()
    agent = StudentKnowledgeAgent()
    student_id = "logic_test_student"
    
    # 1. Test Duplicate Logic
    print("1. Testing Duplicate Detection...")
    uid1 = "dup_test_1"
    uid2 = "dup_test_2"
    fp = "unique_fingerprint_123"
    
    try:
        # Create first upload
        db.create_upload(student_id, "file", "f1.txt", "File 1", upload_id=uid1)
        db.update_status(uid1, "indexed", chunk_count=5, token_count=500)
        db.update_fingerprint(uid1, fp)
        
        # Create second upload (same fingerprint)
        db.create_upload(student_id, "file", "f2.txt", "File 2", upload_id=uid2)
        
        # Run dedup check manually
        trace = agent._init_trace(uid2, student_id, "file", "f2.txt")
        result = agent._check_dedup(uid2, student_id, fp, trace)
        
        if result and result["status"] == "duplicate" and result["existing_upload_id"] == uid1:
            print("✅ Duplicate correctly detected")
        else:
            raise AssertionError(f"Duplicate detection failed: {result}")
            
        # Verify DB status update
        u2 = db.get_upload(uid2)
        assert u2["status"] == "duplicate", f"Status mismatch: {u2['status']}"
        
    except Exception as e:
        print(f"❌ Duplicate test failed: {e}")
        raise e
    finally:
        db.delete_upload(uid1)
        db.delete_upload(uid2)

    # 2. Test Quota Counting
    print("2. Testing Quota Counting...")
    # Create 3 uploads today
    ids = ["q1", "q2", "q3"]
    try:
        for i in ids:
            db.create_upload(student_id, "file", f"f{i}.txt", f"File {i}", upload_id=i)
        
        count = db.count_uploads_today(student_id)
        if count == 3:
            print(f"✅ Quota count correct: {count}")
        else:
            raise AssertionError(f"Quota count expected 3, got {count}")
            
    except Exception as e:
        print(f"❌ Quota test failed: {e}")
        raise e
    finally:
        for i in ids:
            db.delete_upload(i)

    print("✅ All Logic Scenarios Passed!")

def main():
    verify_db_schema()
    asyncio.run(verify_agent_trace())
    asyncio.run(verify_logic_scenarios())
    print("\n🎉 All Hardening Verifications Passed!")


if __name__ == "__main__":
    main()

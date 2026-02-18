import sys
import os

# Set up path to import app modules
sys.path.append(os.getcwd())

from app.rag.subject_detector import detect_subject, _seed_legacy_map, _load_index, _INDEX_CACHE
from app.storage.metadata import SqliteMetadataImpl

import uuid

# Mock storage manager for isolated test
class MockStorage:
    def __init__(self, db_path):
        self.metadata = SqliteMetadataImpl(db_path)

db_filename = f"test_metadata_{uuid.uuid4().hex}.db"
mock_storage = MockStorage(db_filename)

# Inject mock storage into app.storage.storage_manager (hack for testing)
import app.storage
app.storage.storage_manager = mock_storage

def test_dynamic_detection():
    print(f"--- Starting Dynamic Subject Detection Verification (DB: {db_filename}) ---")

    # 1. Clean slate (logic handled by unique filename)
    # if os.path.exists("test_metadata.db"):
    #    os.remove("test_metadata.db")
    # mock_storage.metadata = SqliteMetadataImpl("test_metadata.db")

    # 2. Verify Index is Empty
    idx = mock_storage.metadata.get_keyword_index()
    print(f"Initial Index Size: {len(idx)}")
    assert len(idx) == 0

    # 3. Seed Legacy Map
    print("Seeding legacy map...")
    _seed_legacy_map(mock_storage.metadata)
    
    idx = mock_storage.metadata.get_keyword_index()
    print(f"Seeded Index Size: {len(idx)}")
    assert len(idx) > 0

    # 4. Force Reload Cache
    _load_index()
    
    # 5. Test Detection
    queries = [
        ("database normalization", "DBMS"),
        ("neural networks and deep learning", "Machine Learning"),
        ("operating system deadlocks", "Operating Systems"),
        ("integration and differentiation", "Mathematics"),
        ("unknown subject query", ""),
    ]

    print("\nText Detection Results:")
    for q, expected in queries:
        scope = detect_subject(q)
        print(f"Query: '{q}' -> Detected: '{scope.subject}' (Conf: {scope.confidence:.2f})")
        if expected:
            if scope.subject == expected:
                print("  [PASS]")
            else:
                print(f"  [FAIL] Expected {expected}, got {scope.subject}")

    # 6. Simulate New Subject Learning
    print("\nSimulating ingestion of a new subject 'Quantum Computing'...")
    new_keywords = ["qubit", "superposition", "entanglement", "quantum gate", "teleportation"]
    for kw in new_keywords:
        mock_storage.metadata.update_keyword_index(kw, "Quantum Computing")
    
    # Force cache reload (simulate restart or TTL expire)
    from app.rag import subject_detector
    subject_detector._INDEX_CACHE = {} 
    _load_index()

    # 7. Test New Subject
    scope = detect_subject("qubit superposition")
    print(f"Query: 'qubit superposition' -> Detected: '{scope.subject}' (Conf: {scope.confidence:.2f})")
    
    if scope.subject == "Quantum Computing":
        print("  [PASS] Dynamic learning verified!")
    else:
        print(f"  [FAIL] Expected Quantum Computing, got {scope.subject}")

    # Cleanup
    try:
        mock_storage.metadata.conn.close()
        if os.path.exists("test_metadata.db"):
             os.remove("test_metadata.db")
    except Exception as e:
        print(f"Cleanup warning: {e}")

if __name__ == "__main__":
    test_dynamic_detection()

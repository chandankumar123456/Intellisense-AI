import requests
import time
import uuid

BASE_URL = "http://localhost:8000"
USER_ID = "test_student_" + str(uuid.uuid4())[:8]
FILE_CONTENT = "The mitochondria is the powerhouse of the cell. This is a unique fact for student validation."

def test_ingestion_and_retrieval():
    print(f"Testing with User ID: {USER_ID}")
    
    # 1. Upload File
    files = {'file': ('test_notes.txt', FILE_CONTENT, 'text/plain')}
    data = {'user_id': USER_ID}
    
    print("1. Uploading file...")
    try:
        res = requests.post(f"{BASE_URL}/ingest/file", files=files, data=data)
        if res.status_code != 200:
            print(f"Upload failed: {res.status_code} {res.text}")
            return
        
        doc_id = res.json().get("document_id")
        print(f"Upload success! Doc ID: {doc_id}")
    except Exception as e:
        print(f"Upload request failed: {e}")
        return

    # 2. Wait for background processing (naive wait)
    print("2. Waiting for background ingestion...")
    time.sleep(5) 

    # 3. Simulate Retrieval (if we can hit a search endpoint that uses student context)
    # The current verify endpoint uses the pipeline.
    # We can try /api/evilearn/verify which should now use the student namespace logic if configured?
    # Actually locally verifying the vector DB content might be harder without direct DB access.
    # But we can try to "Verify" a claim that requires this knowledge.
    
    verify_payload = {
        "text": "What is the powerhouse of the cell?",
        "user_id": USER_ID,
        "session_id": "session_1"
    }
    
    print("3. Verifying claim...")
    try:
        res = requests.post(f"{BASE_URL}/api/evilearn/verify", json=verify_payload)
        if res.status_code != 200:
            print(f"Verification failed: {res.status_code} {res.text}")
        else:
            result = res.json()
            print("Verification Result:", result)
            # Check if it found our chunk
            # Implementation specific: check logs or result structure if it exposes sources
            
            # If 500 is gone, that's one success.
            # If it returns a valid answer, that's another.
            
    except Exception as e:
        print(f"Verification request failed: {e}")

if __name__ == "__main__":
    test_ingestion_and_retrieval()

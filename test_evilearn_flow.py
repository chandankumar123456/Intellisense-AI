import requests
import uuid
import json

BASE_URL = "http://127.0.0.1:8000"

def run_test():
    username = f"test_evilearn_{uuid.uuid4().hex[:8]}"
    password = "testpassword123"
    
    print(f"1. Signing up user '{username}'...")
    signup_resp = requests.post(f"{BASE_URL}/auth/signup", json={
        "username": username,
        "password": password
    })
    
    if signup_resp.status_code != 200:
        print(f"FAILED: Signup failed: {signup_resp.text}")
        return

    user_data = signup_resp.json()
    token = user_data["token"]
    user_id = user_data["user_id"]
    print(f"SUCCESS: User created (ID: {user_id})")

    print(f"\n2. Verifying content...")
    verification_text = "The mitochondria is the powerhouse of the cell. The Earth is flat."
    
    verify_resp = requests.post(
        f"{BASE_URL}/api/verification/verify",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "text": verification_text,
            "user_id": user_id,
            "session_id": "test_session_script",
            "preferences": {
                "response_style": "detailed",
                "max_length": 1000,
                "domain": "general"
            }
        }
    )
    
    if verify_resp.status_code != 200:
        print(f"FAILED: Verification failed: {verify_resp.text}")
        return

    result = verify_resp.json()
    print("SUCCESS: Verification result received!")
    print("\n--- Summary ---")
    print(result.get("summary"))
    
    print("\n--- Claims ---")
    for claim in result.get("verified_claims", []):
        print(f"Claim: {claim['claim_text']}")
        print(f"Status: {claim['status']} ({claim['confidence']})")
        print(f"Explanation: {claim['explanation']}")
        print("-" * 20)
        
    print("\n--- Detailed Report ---")
    print(result.get("detailed_report"))

if __name__ == "__main__":
    run_test()

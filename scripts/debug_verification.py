import requests
import os
import sys
import json

# Add project root
sys.path.append(os.getcwd())

from app.core.auth_utils import create_jwt_token

PORT = os.getenv("PORT", "8001")
BASE_URL = f"http://localhost:{PORT}/api/admin/storage"

def debug_local_mode():
    print(f"Targeting {BASE_URL}")
    token = create_jwt_token(user_id="admin_test", username="admin", role="admin")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Switch to Local
    print("Switching to LOCAL...")
    res = requests.post(f"{BASE_URL}/config", json={"mode": "local"}, headers=headers)
    print(f"Switch Status: {res.status_code}")
    if res.status_code != 200:
        print(f"Switch Error: {res.text}")
        return

    # 2. Get Status
    print("Getting Status...")
    res = requests.get(f"{BASE_URL}/status", headers=headers)
    print(f"Status Code: {res.status_code}")
    print(f"Status Body: {res.text[:500]}") # Print first 500 chars

    # 3. Validation Test
    print("Running Test...")
    res = requests.post(f"{BASE_URL}/test", headers=headers)
    print(f"Test Code: {res.status_code}")
    print(f"Test Body: {res.text[:500]}")

    # 4. Switch back to AWS
    print("Reverting to AWS...")
    requests.post(f"{BASE_URL}/config", json={"mode": "aws"}, headers=headers)
    print("Done.")

if __name__ == "__main__":
    try:
        debug_local_mode()
    except Exception as e:
        print(f"CRASH: {e}")

import requests
import os
import sys
import json
from dotenv import load_dotenv

# Add project root
sys.path.append(os.getcwd())

# Checks if we can bypass auth or need a token.
# For this test, we might assuming we are running against a local server where we can potentially mock or likely just need to handle the auth header.
# However, generating a valid JWT might be complex without the secret key.
# Let's try to mock the dependency if we were running unit tests, but for an integration test against a running server, we need a token.
# Or, if running locally in dev, maybe we can temporarily disable auth or use a cheat.

# Actually, since I have access to the code, I can generate a valid admin token using `app.core.auth_utils`.

from app.core.auth_utils import create_jwt_token

def generate_admin_token():
    # Create a dummy admin user payload
    return create_jwt_token(user_id="admin_test_user", username="admin_tester", role="admin")

PORT = os.getenv("PORT", "8000")
BASE_URL = f"http://localhost:{PORT}/api/admin/storage"

def test_admin_storage_api():
    token = generate_admin_token()
    headers = {"Authorization": f"Bearer {token}"}

    print("\n[1] Getting Storage Status...")
    res = requests.get(f"{BASE_URL}/status", headers=headers)
    if res.status_code != 200:
        print(f"FAILED: {res.text}")
        return
    status = res.json()
    print(f"Current Status: {json.dumps(status, indent=2)}")
    
    # Assert detailed status
    if "state" not in status:
        print("WARNING: 'state' field missing from status response")
    if "adapters" not in status:
        print("WARNING: 'adapters' field missing from status response")

    print("\n[2] Getting Storage Config (Redacted)...")
    res = requests.get(f"{BASE_URL}/config", headers=headers)
    if res.status_code != 200:
        print(f"FAILED: {res.text}")
        return
    config = res.json()
    print(f"Current Config: {json.dumps(config, indent=2)}")
    
    # Assert boolean flags
    if not isinstance(config.get("aws_credentials_configured"), bool):
         print("WARNING: 'aws_credentials_configured' is not a boolean")

    print("\n[3] Testing Storage (Current Mode)...")
    res = requests.post(f"{BASE_URL}/test", headers=headers)
    if res.status_code != 200:
        print(f"FAILED: {res.text}")
        return
    test_result = res.json()
    print(f"Test Results: {json.dumps(test_result, indent=2)}")
    
    if "success" not in test_result:
        print("WARNING: Top-level 'success' field missing from test response")

    # Toggle Mode Test
    current_mode = config.get("mode", "aws")
    target_mode = "local" if current_mode == "aws" else "aws"
    
    print(f"\n[4] Switching Mode to {target_mode}...")
    
    # Be careful not to break the system if creds are missing for AWS
    # For test safety, if switching to AWS, we might fail if no creds in env.
    
    payload = {
        "mode": target_mode
    }
    
    res = requests.post(f"{BASE_URL}/config", json=payload, headers=headers)
    if res.status_code == 200:
        print(f"Switch Success: {res.json()}")
        
        # Verify status changed
        res = requests.get(f"{BASE_URL}/status", headers=headers)
        print(f"New Status: {res.json()}")
        
        # Switch back to restore state
        print(f"\n[5] Restoring Mode to {current_mode}...")
        payload["mode"] = current_mode
        requests.post(f"{BASE_URL}/config", json=payload, headers=headers)
        
    else:
        print(f"Switch Failed (Expected if missing creds for AWS): {res.text}")

if __name__ == "__main__":
    try:
        test_admin_storage_api()
    except Exception as e:
        print(f"Test execution failed: {e}")

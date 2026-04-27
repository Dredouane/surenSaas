import sys
sys.path.insert(0, '.')

# Importer et configurer
import os
os.environ['ENVIRONMENT'] = 'test'

from app.main import app
import uvicorn
import threading
import time
import requests
import json

# Lancer le serveur en arrière-plan
def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8003, log_level="error")

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()
time.sleep(3)  # Attendre que le serveur démarre

base_url = "http://127.0.0.1:8003"

print("Test 1: POST /api/v1/test-org/emails/sync")
try:
    response = requests.post(
        f"{base_url}/api/v1/test-org/emails/sync",
        json={"account_id": "test-account"},
        timeout=5
    )
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.text[:200]}")
except Exception as e:
    print(f"  Error: {type(e).__name__}: {e}")

print("\nTest 2: POST /api/v1/REDACTEDORG/emails/sync")
try:
    response = requests.post(
        f"{base_url}/api/v1/REDACTEDORG/emails/sync",
        json={"account_id": "test-account"},
        timeout=5
    )
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.text[:200]}")
except Exception as e:
    print(f"  Error: {type(e).__name__}: {e}")

print("\nTest 3: GET /api/v1/test-org/emails/")
try:
    response = requests.get(
        f"{base_url}/api/v1/test-org/emails/",
        timeout=5
    )
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.text[:200]}")
except Exception as e:
    print(f"  Error: {type(e).__name__}: {e}")

print("\nTest 4: POST /api/v1/auth/login (route POST sans paramètre org)")
try:
    response = requests.post(
        f"{base_url}/api/v1/auth/login",
        json={"email": "test@test.com", "password": "test"},
        timeout=5
    )
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.text[:200]}")
except Exception as e:
    print(f"  Error: {type(e).__name__}: {e}")

print("\nArrêt du serveur...")

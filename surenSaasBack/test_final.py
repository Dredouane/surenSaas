import sys
sys.path.insert(0, '.')

# Tester l'application réelle
from app.main import app
from fastapi.testclient import TestClient
import json

# Créer un client de test
client = TestClient(app)

print("Test POST /api/v1/test-org/emails/sync:")
try:
    response = client.post(
        "/api/v1/test-org/emails/sync",
        json={"account_id": "test-account"}
    )
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.text[:200]}")
except Exception as e:
    print(f"  Error: {e}")

print("\nTest POST /api/v1/REDACTEDORG/emails/sync:")
try:
    response = client.post(
        "/api/v1/REDACTEDORG/emails/sync",
        json={"account_id": "test-account"}
    )
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.text[:200]}")
except Exception as e:
    print(f"  Error: {e}")

print("\nTest GET /api/v1/test-org/emails/ (devrait être 200):")
try:
    response = client.get("/api/v1/test-org/emails/")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.text[:200]}")
except Exception as e:
    print(f"  Error: {e}")

print("\nTest POST /api/v1/test-org/emails/accounts (autre route POST):")
try:
    response = client.post(
        "/api/v1/test-org/emails/accounts",
        json={"email": "test@test.com", "oauth_code": "test", "redirect_uri": "test"}
    )
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.text[:200]}")
except Exception as e:
    print(f"  Error: {e}")

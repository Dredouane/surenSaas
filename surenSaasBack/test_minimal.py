import sys
sys.path.insert(0, '.')

# Créer une app FastAPI minimaliste
from fastapi import FastAPI, APIRouter
import uvicorn
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(lifespan=lifespan)

# Créer un router comme dans emails.py
router = APIRouter(prefix="/{org}/emails", tags=["emails"])

@router.post("/sync")
async def sync_emails(org: str):
    return {"org": org, "route": "sync"}

@router.get("/{email_id}")
async def get_email(org: str, email_id: str):
    return {"org": org, "email_id": email_id}

app.include_router(router, prefix="/api/v1")

# Afficher les routes
print("Routes enregistrées:")
for route in app.routes:
    print(f"  {route.methods} {route.path}")

# Lancer le serveur en arrière-plan
import threading
import time

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8001)

thread = threading.Thread(target=run_server, daemon=True)
thread.start()
time.sleep(2)  # Attendre que le serveur démarre

# Tester avec curl
import subprocess
import json

print("\nTest POST /api/v1/test-org/emails/sync:")
result = subprocess.run([
    "curl", "-s", "-X", "POST", 
    "http://127.0.0.1:8001/api/v1/test-org/emails/sync",
    "-H", "Content-Type: application/json",
    "-d", '{"test": "data"}'
], capture_output=True, text=True)
print(f"  Status: {result.returncode}")
print(f"  Response: {result.stdout[:200]}")

print("\nTest GET /api/v1/test-org/emails/123:")
result = subprocess.run([
    "curl", "-s", 
    "http://127.0.0.1:8001/api/v1/test-org/emails/123"
], capture_output=True, text=True)
print(f"  Status: {result.returncode}")
print(f"  Response: {result.stdout[:200]}")

print("\nTest POST /api/v1/test-org/emails/123 (devrait être 405):")
result = subprocess.run([
    "curl", "-s", "-X", "POST",
    "http://127.0.0.1:8001/api/v1/test-org/emails/123",
    "-H", "Content-Type: application/json",
    "-d", '{"test": "data"}'
], capture_output=True, text=True)
print(f"  Status: {result.returncode}")
print(f"  Response: {result.stdout[:200]}")

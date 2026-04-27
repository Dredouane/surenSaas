import sys
sys.path.insert(0, '.')

# Créer une app FastAPI minimaliste avec dépendances
from fastapi import FastAPI, APIRouter, Depends
from pydantic import BaseModel
import uvicorn
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(lifespan=lifespan)

# Simuler require_capability comme dans le patch
def require_capability(capability: str):
    """Dépendance temporaire pour les capabilities."""
    async def _require_capability(current_user: dict = Depends(lambda: {"id": "test", "org_id": "test"})):
        # Pour l'instant, permissif
        return current_user
    return _require_capability

# Créer un router comme dans emails.py
router = APIRouter(prefix="/{org}/emails", tags=["emails"])

class EmailSyncRequest(BaseModel):
    account_id: str

@router.post("/sync")
async def sync_emails(org: str, request: EmailSyncRequest, current_user: dict = Depends(require_capability("emails:sync"))):
    return {"org": org, "route": "sync", "user": current_user}

@router.get("/{email_id}")
async def get_email(org: str, email_id: str, current_user: dict = Depends(require_capability("emails:read"))):
    return {"org": org, "email_id": email_id, "user": current_user}

app.include_router(router, prefix="/api/v1")

# Afficher les routes
print("Routes enregistrées:")
for route in app.routes:
    print(f"  {route.methods} {route.path}")

# Lancer le serveur en arrière-plan
import threading
import time
import json

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8002)

thread = threading.Thread(target=run_server, daemon=True)
thread.start()
time.sleep(2)  # Attendre que le serveur démarre

# Tester avec curl
import subprocess

print("\nTest POST /api/v1/test-org/emails/sync:")
result = subprocess.run([
    "curl", "-s", "-X", "POST", 
    "http://127.0.0.1:8002/api/v1/test-org/emails/sync",
    "-H", "Content-Type: application/json",
    "-d", '{"account_id": "test-account"}'
], capture_output=True, text=True)
print(f"  Status: {result.returncode}")
print(f"  Response: {result.stdout[:200]}")

print("\nTest avec un UUID comme org:")
result = subprocess.run([
    "curl", "-s", "-X", "POST", 
    "http://127.0.0.1:8002/api/v1/REDACTEDORG/emails/sync",
    "-H", "Content-Type: application/json",
    "-d", '{"account_id": "test-account"}'
], capture_output=True, text=True)
print(f"  Status: {result.returncode}")
print(f"  Response: {result.stdout[:200]}")

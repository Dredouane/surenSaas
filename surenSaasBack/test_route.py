from fastapi import FastAPI, APIRouter
from fastapi.testclient import TestClient

# Test 1: Router avec prefix paramétré
app1 = FastAPI()
router1 = APIRouter(prefix="/{org}/emails")

@router1.post("/sync")
async def sync_emails(org: str):
    return {"org": org, "route": "sync"}

app1.include_router(router1, prefix="/api/v1")

client1 = TestClient(app1)
print("Test 1 - Router avec prefix paramétré:")
print("  POST /api/v1/test-org/emails/sync")
response = client1.post("/api/v1/test-org/emails/sync")
print(f"  Status: {response.status_code}")
print(f"  Response: {response.json()}")
print()

# Test 2: Router sans prefix, paramètre dans la route
app2 = FastAPI()
router2 = APIRouter()

@router2.post("/{org}/emails/sync")
async def sync_emails2(org: str):
    return {"org": org, "route": "sync"}

app2.include_router(router2, prefix="/api/v1")

client2 = TestClient(app2)
print("Test 2 - Paramètre dans la route:")
print("  POST /api/v1/test-org/emails/sync")
response = client2.post("/api/v1/test-org/emails/sync")
print(f"  Status: {response.status_code}")
print(f"  Response: {response.json()}")

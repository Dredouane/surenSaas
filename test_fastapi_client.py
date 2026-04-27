from fastapi.testclient import TestClient
from fastapi import FastAPI
app = FastAPI()
try:
    client = TestClient(app)
    print("FastAPI TestClient(app) successful")
except Exception as e:
    print(f"FastAPI TestClient(app) failed: {e}")

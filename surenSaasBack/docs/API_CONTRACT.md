# Contract-First API Guide

## Workflow

### 1. Modify the contract
```yaml
# openapi/api.yaml
paths:
  /api/v1/{org}/projects:
    get:
      summary: List projects
      parameters:
        - name: org
          in: path
          required: true
          schema:
            type: string
      responses:
        200:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ProjectList'
```

### 2. Generate the code
```bash
cd surenSaasBack
python scripts/generate_api.py
```

### 3. Implement the service
```python
# app/services/project_service.py
from typing import List
from app.models.schemas import Project

async def list_projects(org_id: str) -> List[Project]:
    """Business logic to list projects."""
    return await db.query(
        "SELECT * FROM projects WHERE org_id = $1", 
        org_id
    )
```

### 4. Connect to the controller
```python
# app/api/v1/[org]/projects.py (generated)
from fastapi import APIRouter, Depends
from app.services.project_service import list_projects

router = APIRouter()

@router.get("/projects")
async def get_projects(org: str = Path(...)):
    # TODO: Implement here
    return await list_projects(org)
```

## Rules
- ✅ Modify only `openapi/api.yaml`
- ✅ Implement in `app/services/`
- ❌ Do not modify the generated code
- ❌ Do not add routes manually

## Generation
```python
# scripts/generate_api.py
import subprocess

subprocess.run([
    "openapi-generator-cli", "generate",
    "-i", "openapi/api.yaml",
    "-g", "python-fastapi",
    "-o", "./generated",
    "--additional-properties=packageName=app"
])

# Copy only the controllers
# The services remain unchanged
```

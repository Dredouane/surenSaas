# Guide Contract-First API

## Workflow

### 1. Modifier le contrat
```yaml
# openapi/api.yaml
paths:
  /api/v1/{org}/projects:
    get:
      summary: Liste les projets
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

### 2. Générer le code
```bash
cd surenSaasBack
python scripts/generate_api.py
```

### 3. Implémenter le service
```python
# app/services/project_service.py
from typing import List
from app.models.schemas import Project

async def list_projects(org_id: str) -> List[Project]:
    """Logique métier pour lister les projets."""
    return await db.query(
        "SELECT * FROM projects WHERE org_id = $1", 
        org_id
    )
```

### 4. Connecter au contrôleur
```python
# app/api/v1/[org]/projects.py (généré)
from fastapi import APIRouter, Depends
from app.services.project_service import list_projects

router = APIRouter()

@router.get("/projects")
async def get_projects(org: str = Path(...)):
    # TODO: Implémenter ici
    return await list_projects(org)
```

## Règles
- ✅ Modifier uniquement `openapi/api.yaml`
- ✅ Implémenter dans `app/services/`
- ❌ Ne pas modifier le code généré
- ❌ Ne pas ajouter de routes manuellement

## Génération
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

# Copier uniquement les contrôleurs
# Les services restent inchangés
```

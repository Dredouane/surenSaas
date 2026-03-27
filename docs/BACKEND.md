# Backend (FastAPI)

## Structure
```
surenSaasBack/
├── app/
│   ├── api/                  # Généré depuis OpenAPI
│   │   └── v1/
│   │       ├── [org]/        # Mirror routing front
│   │       └── auth/         # Routes auth non-générées
│   ├── services/             # Logique métier (persiste)
│   ├── models/               # SQLAlchemy/Pydantic
│   ├── agents/               # Workers IA async
│   ├── core/
│   │   ├── config.py         # Settings Pydantic
│   │   ├── security.py       # JWT + auth
│   │   ├── rate_limit.py     # Rate limiting (mémoire)
│   │   └── supabase.py       # Client Supabase
│   └── main.py               # Entry point
├── openapi/
│   └── api.yaml              # Contract principal (depuis racine projet)
├── scripts/
│   └── generate_api.py       # Génère code depuis OpenAPI
└── tests/
```

## Contract-first workflow
1. Modifier `/openapi/api.yaml` (à la racine du projet)
2. Lancer `python scripts/generate_api.py` (depuis dossier backend)
3. Le script génère :
   - `app/api/v1/[org]/*.py` (contrôleurs)
   - `app/models/schemas.py` (DTOs)
4. Implémenter la logique dans `app/services/`
5. Ne JAMAIS modifier le code généré manuellement

## Génération code
```python
# scripts/generate_api.py
# Utilise openapi-generator-cli
# Source : ../../openapi/api.yaml
# Output : ./generated/
# Puis copie vers app/api/v1/
```

## Auth Routes (non générées)

### POST /api/v1/auth/check-email
```python
@app.post("/api/v1/auth/check-email")
@rate_limit(max_requests=10, window=60)
async def check_email(request: EmailCheckRequest):
    # Vérifie pre_authorized_emails
    # Vérifie si user existe déjà dans auth.users
    # Retourne authorized, exists, org_id, org_slug, role
```

### POST /api/v1/auth/signup
```python
@app.post("/api/v1/auth/signup")
@rate_limit(max_requests=5, window=60)
async def signup(request: SignupRequest):
    # 1. Vérifier email dans pre_authorized_emails
    # 2. Créer user via Supabase Admin API
    # 3. Trigger SQL crée membership
    # 4. Set cookie httpOnly
```

### POST /api/v1/auth/login
```python
@app.post("/api/v1/auth/login")
@rate_limit(max_requests=5, window=60)
async def login(request: LoginRequest):
    # Login standard Supabase
    # Vérifie membership existe
    # Set cookie httpOnly + JWT
```

### GET /api/v1/auth/session
```python
@app.get("/api/v1/auth/session")
async def check_session(request: Request):
    # Vérifie cookie session_token
    # Retourne user info (pour middleware Next.js)
```

## Authentification
```python
# Dépendance FastAPI
async def get_current_user(
    request: Request  # Lit cookie session_token
) -> User:
    # 1. Valider JWT depuis cookie
    # 2. Vérifier membership pour org_id
    # 3. Retourner User avec contexte org
```

## Rate Limiting
Stockage **en mémoire** (pas Redis).

```python
# core/rate_limit.py
from functools import wraps
import time

_memory_store = {}

def rate_limit(max_requests: int, window: int):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Clé = hash(IP + User-Agent)
            key = f"ratelimit:{func.__name__}:{hash_client(request)}"
            
            now = time.time()
            
            # Nettoyer anciennes entrées
            if key in _memory_store:
                _memory_store[key] = [
                    ts for ts in _memory_store[key] 
                    if now - ts < window
                ]
            
            # Vérifier limite
            if len(_memory_store.get(key, [])) >= max_requests:
                raise HTTPException(429, "Trop de requêtes")
            
            # Ajouter timestamp
            _memory_store.setdefault(key, []).append(now)
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
```

**Limites** :
- Login : 5 tentatives/minute
- Check-email : 10 requêtes/minute
- Reset-password : 3 tentatives/5min

## Communication async
**À déterminer ultérieurement.**

## Configuration
```python
# core/config.py
class Settings(BaseSettings):
    supabase_url: str
    supabase_service_key: str
    jwt_secret: str                    # Pour signer les sessions
    allowed_origins: list[str]
    
    class Config:
        env_file = ".env"
```

## Endpoints standard
```
GET    /api/v1/{org}/users/me       # Profil connecté
GET    /api/v1/{org}/projects       # Liste projets
POST   /api/v1/{org}/projects       # Créer projet
GET    /api/v1/{org}/projects/{id}  # Détail projet
PUT    /api/v1/{org}/projects/{id}  # Modifier
DELETE /api/v1/{org}/projects/{id}  # Supprimer
```

## Scripts
```bash
# Génération API (depuis surenSaasBack/)
python scripts/generate_api.py

# Développement
uvicorn app.main:app --reload

# Tests
pytest tests/

# Docker
docker-compose up backend
```

## Règles d'or
- Toujours valider org_id dans JWT vs URL
- Toujours utiliser Supabase avec RLS (service key = bypass)
- Jamais de logique métier dans les contrôleurs générés
- Toujours typer avec Pydantic
- Rate limit sur toutes les routes auth
- Pas de Redis - stockage mémoire uniquement

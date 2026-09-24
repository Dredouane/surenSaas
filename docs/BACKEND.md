# Backend (FastAPI)

## Structure
```
surenSaasBack/
├── app/
│   ├── api/                  # Generated from OpenAPI
│   │   └── v1/
│   │       ├── [org]/        # Front mirror routing
│   │       └── auth/         # Non-generated auth routes
│   ├── services/             # Business logic (persists)
│   ├── models/               # SQLAlchemy/Pydantic
│   ├── agents/               # Async AI workers
│   ├── core/
│   │   ├── config.py         # Pydantic Settings
│   │   ├── security.py       # JWT + auth
│   │   ├── rate_limit.py     # Rate limiting (memory)
│   │   └── supabase.py       # Supabase client
│   └── main.py               # Entry point
├── openapi/
│   └── api.yaml              # Main contract (from project root)
├── scripts/
│   └── generate_api.py       # Generates code from OpenAPI
└── tests/
```

## Contract-first workflow
1. Modify `/openapi/api.yaml` (at the project root)
2. Run `python scripts/generate_api.py` (from the backend folder)
3. The script generates:
   - `app/api/v1/[org]/*.py` (controllers)
   - `app/models/schemas.py` (DTOs)
4. Implement the logic in `app/services/`
5. NEVER manually modify the generated code

## Code generation
```python
# scripts/generate_api.py
# Uses openapi-generator-cli
# Source: ../../openapi/api.yaml
# Output: ./generated/
# Then copies to app/api/v1/
```

## Auth Routes (not generated)

### POST /api/v1/auth/check-email
```python
@app.post("/api/v1/auth/check-email")
@rate_limit(max_requests=10, window=60)
async def check_email(request: EmailCheckRequest):
    # Checks pre_authorized_emails
    # Checks whether the user already exists in auth.users
    # Returns authorized, exists, org_id, org_slug, role
```

### POST /api/v1/auth/signup
```python
@app.post("/api/v1/auth/signup")
@rate_limit(max_requests=5, window=60)
async def signup(request: SignupRequest):
    # 1. Check email in pre_authorized_emails
    # 2. Create user via the Supabase Admin API
    # 3. SQL trigger creates membership
    # 4. Set httpOnly cookie
```

### POST /api/v1/auth/login
```python
@app.post("/api/v1/auth/login")
@rate_limit(max_requests=5, window=60)
async def login(request: LoginRequest):
    # Standard Supabase login
    # Checks membership exists
    # Set httpOnly cookie + JWT
```

### GET /api/v1/auth/session
```python
@app.get("/api/v1/auth/session")
async def check_session(request: Request):
    # Checks the session_token cookie
    # Returns user info (for the Next.js middleware)
```

## Authentication
```python
# FastAPI dependency
async def get_current_user(
    request: Request  # Reads the session_token cookie
) -> User:
    # 1. Validate JWT from cookie
    # 2. Check membership for org_id
    # 3. Return User with org context
```

## Rate Limiting
Storage **in memory** (not Redis).

```python
# core/rate_limit.py
from functools import wraps
import time

_memory_store = {}

def rate_limit(max_requests: int, window: int):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Key = hash(IP + User-Agent)
            key = f"ratelimit:{func.__name__}:{hash_client(request)}"
            
            now = time.time()
            
            # Clean up old entries
            if key in _memory_store:
                _memory_store[key] = [
                    ts for ts in _memory_store[key] 
                    if now - ts < window
                ]
            
            # Check limit
            if len(_memory_store.get(key, [])) >= max_requests:
                raise HTTPException(429, "Too many requests")
            
            # Add timestamp
            _memory_store.setdefault(key, []).append(now)
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
```

**Limits**:
- Login: 5 attempts/minute
- Check-email: 10 requests/minute
- Reset-password: 3 attempts/5min

## Async communication
**To be determined later.**

## Configuration
```python
# core/config.py
class Settings(BaseSettings):
    supabase_url: str
    supabase_service_key: str
    jwt_secret: str                    # To sign sessions
    allowed_origins: list[str]
    
    class Config:
        env_file = ".env"
```

## Standard endpoints
```
GET    /api/v1/{org}/users/me       # Connected user's profile
GET    /api/v1/{org}/projects       # Project list
POST   /api/v1/{org}/projects       # Create project
GET    /api/v1/{org}/projects/{id}  # Project detail
PUT    /api/v1/{org}/projects/{id}  # Update
DELETE /api/v1/{org}/projects/{id}  # Delete
```

## Scripts
```bash
# API generation (from surenSaasBack/)
python scripts/generate_api.py

# Development
uvicorn app.main:app --reload

# Tests
pytest tests/

# Docker
docker-compose up backend
```

## Golden rules
- Always validate org_id in JWT vs URL
- Always use Supabase with RLS (service key = bypass)
- Never put business logic in the generated controllers
- Always type with Pydantic
- Rate limit on all auth routes
- No Redis - in-memory storage only

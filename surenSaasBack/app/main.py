from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import traceback

from app.core.config import settings
from app.core.logging import setup_logging, get_logger, log_request
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.clients import router as clients_router
from app.api.invoices import router as invoices_router
from app.api.admin import router as admin_router
from app.api.construction_bot import router as construction_bot_router
from app.api.telegram_core import router as telegram_webhooks_router
from app.api.emails import router as emails_router
from app.api.email_threads import router as email_threads_router
from app.api.dossiers import router as dossiers_router
from app.api.ao import router as ao_router
from app.api.files import router as files_router

# Initialiser le logging au démarrage
setup_logging(
    level="DEBUG" if settings.debug else "INFO",
    environment=settings.environment,
    enable_file=False
)

logger = get_logger(__name__)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    debug=settings.debug,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de logging des requêtes
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log toutes les requêtes HTTP avec leur durée et statut."""
    start_time = time.time()
    
    # Récupérer l'IP et le user-agent
    client_host = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    logger.info(
        f"→ Requête {request.method} {request.url.path}",
        extra={
            "extra_data": {
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params),
                "client_ip": client_host,
                "user_agent": user_agent,
            }
        }
    )
    
    try:
        response = await call_next(request)
        duration = (time.time() - start_time) * 1000
        
        log_request(
            logger,
            request.method,
            request.url.path,
            response.status_code,
            duration,
        )
        
        return response
        
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        
        logger.error(
            f"✗ Requête {request.method} {request.url.path} échouée après {duration:.2f}ms",
            extra={
                "extra_data": {
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "duration_ms": duration,
                }
            },
            exc_info=True
        )
        
        # Retourner une réponse 500
        return JSONResponse(
            status_code=500,
            content={
                "error": "Erreur interne",
                "message": str(e) if settings.debug else "Une erreur est survenue"
            }
        )

# Gestionnaire d'exceptions global
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Gestionnaire d'exceptions global pour capturer toutes les erreurs."""
    logger.error(
        f"Exception non gérée: {type(exc).__name__}: {str(exc)}",
        extra={
            "extra_data": {
                "path": request.url.path,
                "method": request.method,
                "exception_type": type(exc).__name__,
            }
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Erreur interne du serveur",
            "detail": str(exc) if settings.debug else "Contactez l'administrateur"
        }
    )

# Routes
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(clients_router, prefix="/api/v1")
app.include_router(invoices_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(construction_bot_router, prefix="/api/v1")
app.include_router(emails_router, prefix="/api/v1")
app.include_router(email_threads_router, prefix="/api/v1")
app.include_router(dossiers_router, prefix="/api/v1")
app.include_router(ao_router, prefix="/api/v1")
app.include_router(files_router, prefix="/api/v1")
app.include_router(telegram_webhooks_router)

@app.on_event("startup")
async def startup_event():
    """Log au démarrage de l'application."""
    logger.info(
        "🚀 Application démarrée",
        extra={
            "extra_data": {
                "app_name": settings.app_name,
                "environment": settings.environment,
                "debug": settings.debug,
            }
        }
    )

@app.get("/")
async def root():
    logger.info("Route / appelée")
    return {"message": "SurenSaaS API", "version": "1.0.0"}

@app.get("/health")
async def health():
    logger.debug("Health check")
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

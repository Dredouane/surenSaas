from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import traceback
import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google.api_core")

from app.core.config import settings
from app.core.logging import setup_logging, get_logger, log_request
from app.api.auth import router as auth_router, AuthenticationError
from app.api.users import router as users_router
from app.api.clients import router as clients_router
from app.api.invoices import router as invoices_router
from app.api.admin import router as admin_router
from app.api.telegram_core import router as telegram_webhooks_router
from app.api.emails import router as emails_router
from app.api.email_threads import router as email_threads_router
from app.api.dossiers import router as dossiers_router
from app.api.ao import router as ao_router
from app.api.files import router as files_router
from app.api.chantiers import router as chantiers_router

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

# Middleware pour ajouter les headers d'authentification aux réponses 401
@app.middleware("http")
async def add_auth_headers(request: Request, call_next):
    """Ajoute les headers X-Auth-Redirect aux réponses 401."""
    response = await call_next(request)
    
    # Si c'est une erreur 401 et que ce n'est pas un endpoint d'authentification
    if response.status_code == 401 and not request.url.path.startswith('/api/v1/auth/'):
        # Vérifier si les headers sont déjà présents
        if not response.headers.get('X-Auth-Redirect'):
            response.headers['X-Auth-Redirect'] = '/login'
            response.headers['X-Auth-Error'] = 'unauthorized'
            logger.debug(f"Middleware: Headers d'authentification ajoutés pour {request.url.path}")
    
    return response

# Middleware de logging des requêtes
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log toutes les requêtes HTTP avec corrélation ID, durée et statut."""
    start_time = time.time()
    import uuid as _uuid
    correlation_id = str(_uuid.uuid4())
    request.state.correlation_id = correlation_id

    logger.info(
        f"→ Requête {request.method} {request.url.path}",
        extra={
            "extra_data": {
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }
        }
    )

    try:
        response = await call_next(request)
        duration = time.time() - start_time

        log_kwargs = {
            "extra": {
                "extra_data": {
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration * 1000,
                    "query": str(request.query_params),
                }
            }
        }

        if response.status_code >= 500:
            logger.error(f"← Réponse {response.status_code} ({duration:.3f}s)", **log_kwargs)
        elif response.status_code >= 400:
            logger.warning(f"← Réponse {response.status_code} ({duration:.3f}s)", **log_kwargs)
        else:
            logger.info(f"← Réponse {response.status_code} ({duration:.3f}s)", **log_kwargs)

        response.headers["X-Correlation-ID"] = correlation_id
        return response

    except HTTPException:
        raise

    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"❌ Erreur pendant le traitement: {type(e).__name__}: {str(e)}",
            extra={
                "extra_data": {
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration * 1000,
                    "query": str(request.query_params),
                    "exception_type": type(e).__name__,
                    "exception_message": str(e),
                }
            },
            exc_info=True
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": "Erreur interne",
                "message": str(e) if settings.debug else "Une erreur est survenue"
            }
        )

# Gestionnaire d'exceptions pour HTTPException (inclut AuthenticationError)
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Gestionnaire d'exceptions pour HTTPException."""
    # Vérifier si c'est une AuthenticationError avec redirection
    headers = dict(exc.headers) if exc.headers else {}
    
    if isinstance(exc, AuthenticationError) and exc.redirect_to_login:
        # Ajouter les headers de redirection pour le frontend
        headers["X-Auth-Redirect"] = "/login"
        headers["X-Auth-Error"] = "session_expired"
        logger.warning(f"AuthenticationError avec redirection: {exc.detail}")
    elif exc.status_code == 401:
        # Pour les autres erreurs 401, ajouter aussi les headers
        headers["X-Auth-Redirect"] = "/login"
        headers["X-Auth-Error"] = "unauthorized"
        logger.warning(f"Erreur 401 sans AuthenticationError: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=headers
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
app.include_router(emails_router, prefix="/api/v1")
app.include_router(email_threads_router, prefix="/api/v1")
app.include_router(dossiers_router, prefix="/api/v1")
app.include_router(ao_router, prefix="/api/v1")
app.include_router(files_router, prefix="/api/v1")
app.include_router(chantiers_router, prefix="/api/v1")
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

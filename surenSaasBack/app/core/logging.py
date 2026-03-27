"""
Module de logging centralisé pour SurenSaaS

Usage:
    from app.core.logging import get_logger
    
    logger = get_logger(__name__)
    logger.info("Message d'info")
    logger.error("Message d'erreur", extra={"user_id": "123"})
"""

import logging
import sys
from typing import Optional, Dict, Any
from datetime import datetime
import json


class StructuredLogFormatter(logging.Formatter):
    """Formateur de logs structurés en JSON pour le monitoring."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Ajouter les extras si présents
        if hasattr(record, "extra_data"):
            log_entry["extra"] = record.extra_data
        
        # Ajouter les infos métier courantes
        for key in ["user_id", "org_id", "request_id", "duration_ms", "status_code", "error_code"]:
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)
        
        # Ajouter l'exception si présente
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """Formateur avec couleurs pour le développement local."""
    
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m"
    }
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]
        
        # Format court pour le dev local
        timestamp = datetime.utcnow().strftime("%H:%M:%S")
        location = f"{record.module}:{record.lineno}"
        
        # Ajouter les extras visuellement
        extras = ""
        if hasattr(record, "extra_data"):
            extras_data = record.extra_data
            if isinstance(extras_data, dict):
                extras_items = [f"{k}={v}" for k, v in extras_data.items()]
                extras = f" [{', '.join(extras_items)}]"
        
        return f"{color}[{timestamp}] {record.levelname:8} | {location:30} | {record.getMessage()}{extras}{reset}"


def _suppress_noisy_loggers() -> None:
    """
    Réduit le niveau de log des bibliothèques externes bruyantes.
    Garde uniquement les logs applicatifs (app.*) visibles.
    """
    # Liste des loggers externes à réduire au niveau WARNING
    noisy_loggers = [
        # HTTP clients
        "httpx", "httpcore", "urllib3", "requests",
        # HTTP/2 & encoding
        "hpack", "h2", "hyperframe",
        # Async
        "asyncio", "aiohttp",
        # Google Cloud
        "google", "google.cloud", "google.auth", "google.api_core",
        # Base de données
        "sqlalchemy", "sqlalchemy.engine", "sqlalchemy.pool",
        # Telegram
        "telegram", "python_telegram_bot",
        # Autres
        "botocore", "boto3",
        "uvicorn.access",  # Logs des requêtes HTTP (doublon avec notre middleware)
    ]
    
    for logger_name in noisy_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)
        # Supprimer les handlers existants pour éviter les doublons
        logger.handlers = []
        # Ne pas propager vers le logger racine (évite le double affichage)
        logger.propagate = False


def setup_logging(
    level: str = "INFO",
    environment: str = "development",
    enable_file: bool = False,
    log_file: str = "/tmp/surensaas.log"
) -> None:
    """
    Configure le logging pour l'application.
    
    Args:
        level: Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        environment: 'development' ou 'production'
        enable_file: Active l'écriture dans un fichier
        log_file: Chemin du fichier de log
    """
    # Logger racine
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Supprimer les handlers existants
    root_logger.handlers = []
    
    # Handler console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    
    # Formatter selon l'environnement
    if environment == "production":
        # JSON pour la prod (monitoring)
        formatter = StructuredLogFormatter()
    else:
        # Couleurs pour le dev
        formatter = ColoredFormatter()
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Réduire le bruit des loggers externes
    _suppress_noisy_loggers()
    
    # Handler fichier si demandé
    if enable_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(StructuredLogFormatter())
        root_logger.addHandler(file_handler)
    
    # Log de démarrage
    root_logger.info(
        "Logging configuré",
        extra={
            "level": level,
            "environment": environment,
            "file_logging": enable_file
        }
    )


def _suppress_noisy_loggers() -> None:
    """
    Réduit le niveau de log des bibliothèques externes bruyantes.
    Garde uniquement les logs applicatifs (app.*) visibles.
    """
    # Liste des loggers externes à réduire au niveau WARNING
    noisy_loggers = [
        # HTTP clients
        "httpx", "httpcore", "urllib3", "requests",
        # HTTP/2 & encoding
        "hpack", "h2", "hyperframe",
        # Async
        "asyncio", "aiohttp",
        # Google Cloud
        "google", "google.cloud", "google.auth", "google.api_core",
        # Base de données
        "sqlalchemy", "sqlalchemy.engine", "sqlalchemy.pool",
        # Telegram
        "telegram", "python_telegram_bot",
        # Autres
        "botocore", "boto3",
        "uvicorn.access",  # Logs des requêtes HTTP (doublon avec notre middleware)
    ]
    
    for logger_name in noisy_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)
        # Supprimer les handlers existants pour éviter les doublons
        logger.handlers = []
        # Ne pas propager vers le logger racine (évite le double affichage)
        logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """
    Récupère un logger configuré.
    
    Args:
        name: Nom du logger (généralement __name__)
        
    Returns:
        Logger configuré
    """
    return logging.getLogger(name)


class LoggerMixin:
    """Mixin pour ajouter un logger aux classes."""
    
    @property
    def logger(self) -> logging.Logger:
        if not hasattr(self, "_logger"):
            self._logger = get_logger(self.__class__.__module__)
        return self._logger


# Helpers pour les logs métier
def log_request(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: Optional[str] = None,
    org_id: Optional[str] = None
) -> None:
    """Log une requête HTTP."""
    extra = {
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": duration_ms,
    }
    if user_id:
        extra["user_id"] = user_id
    if org_id:
        extra["org_id"] = org_id
    
    if status_code >= 500:
        logger.error(f"Requête {method} {path} - {status_code} ({duration_ms}ms)", extra={"extra_data": extra})
    elif status_code >= 400:
        logger.warning(f"Requête {method} {path} - {status_code} ({duration_ms}ms)", extra={"extra_data": extra})
    else:
        logger.info(f"Requête {method} {path} - {status_code} ({duration_ms}ms)", extra={"extra_data": extra})


def log_auth_attempt(
    logger: logging.Logger,
    email: str,
    success: bool,
    org_id: Optional[str] = None,
    error: Optional[str] = None
) -> None:
    """Log une tentative d'authentification."""
    extra = {
        "email": email,
        "success": success,
    }
    if org_id:
        extra["org_id"] = org_id
    if error:
        extra["error"] = error
    
    if success:
        logger.info(f"Authentification réussie: {email}", extra={"extra_data": extra})
    else:
        logger.warning(f"Authentification échouée: {email} - {error}", extra={"extra_data": extra})


def log_db_query(
    logger: logging.Logger,
    table: str,
    operation: str,
    duration_ms: float,
    rows_affected: int = 0,
    error: Optional[str] = None
) -> None:
    """Log une requête DB."""
    extra = {
        "table": table,
        "operation": operation,
        "duration_ms": duration_ms,
        "rows_affected": rows_affected,
    }
    
    if error:
        logger.error(f"DB {operation} sur {table} échoué: {error}", extra={"extra_data": extra})
    else:
        logger.debug(f"DB {operation} sur {table} - {rows_affected} lignes ({duration_ms}ms)", extra={"extra_data": extra})

"""
Module centralisé d'initialisation Vertex AI.

Startup : décode le secret Base64 → écrit /tmp/suren-vertex-key.json → vertexai.init()
Singleton : instance unique ChatGoogleGenerativeAI pour tout le graph
Shutdown : supprime le fichier JSON

Conçu pour le cycle de vie FastAPI (lifespan).
"""

import os
import json
import base64
import atexit
import logging
from typing import TYPE_CHECKING

from app.core.config import settings

if TYPE_CHECKING:
    from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

CREDENTIALS_PATH = "/tmp/suren-vertex-key.json"

_llm_instance = None  # ChatGoogleGenerativeAI | None — lazy import
_initialized = False


def _decode_credentials() -> dict | None:
    """Decode et retourne les credentials GCP depuis le settings."""
    raw = settings.gemini_api_key
    if not raw:
        logger.warning("gemini_api_key non défini dans les settings")
        return None

    if raw.startswith("AIza"):
        logger.info("gemini_api_key est une clé API AI Studio (pas de credentials GCP)")
        return None

    try:
        decoded = base64.b64decode(raw).decode("utf-8")
        return json.loads(decoded)
    except (base64.binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error("Impossible de décoder gemini_api_key en credentials JSON: %s", e)
        return None


def _write_credentials_file(creds: dict) -> str:
    """Écrit les credentials JSON dans /tmp/suren-vertex-key.json."""
    with open(CREDENTIALS_PATH, "w") as f:
        json.dump(creds, f)
    os.chmod(CREDENTIALS_PATH, 0o600)
    logger.debug("Credentials écrits dans %s", CREDENTIALS_PATH)
    return CREDENTIALS_PATH


def _cleanup_credentials():
    """Supprime le fichier de credentials temporaire."""
    if os.path.exists(CREDENTIALS_PATH):
        try:
            os.remove(CREDENTIALS_PATH)
            logger.info("Fichier de credentials supprimé: %s", CREDENTIALS_PATH)
        except OSError as e:
            logger.warning("Impossible de supprimer %s: %s", CREDENTIALS_PATH, e)


def startup():
    global _initialized

    if _initialized:
        logger.debug("Vertex AI déjà initialisé, skip")
        return

    creds = _decode_credentials()
    if creds:
        _write_credentials_file(creds)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH

    project_id = settings.gcp_project_id or (creds.get("project_id") if creds else None)
    location = settings.gemini_location or "europe-west1"

    _initialized = True
    logger.info(
        "Vertex AI startup OK — project=%s location=%s creds=%s",
        project_id, location, CREDENTIALS_PATH if creds else "none (API key mode)",
    )


def get_chat_model():
    global _llm_instance

    if _llm_instance is not None:
        return _llm_instance

    if not _initialized:
        startup()

    from langchain_google_genai import ChatGoogleGenerativeAI

    project_id = settings.gcp_project_id
    if not project_id and os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        try:
            with open(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]) as f:
                creds = json.load(f)
            project_id = creds.get("project_id")
        except Exception:
            pass

    _llm_instance = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        vertexai=True,
        project=project_id,
        location=settings.gemini_location or "europe-west1",
    )
    logger.debug("ChatGoogleGenerativeAI singleton créé")
    return _llm_instance


def get_genai_client():
    """Retourne un client google.genai.Client pré-configuré (singleton léger)."""
    from google import genai as _genai

    if not _initialized:
        startup()

    project_id = settings.gcp_project_id
    if not project_id and os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        try:
            with open(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]) as f:
                creds = json.load(f)
            project_id = creds.get("project_id")
        except Exception:
            pass

    return _genai.Client(
        vertexai=True,
        project=project_id,
        location=settings.gemini_location or "europe-west1",
    )


def shutdown():
    global _llm_instance, _initialized

    _llm_instance = None
    _initialized = False
    _cleanup_credentials()
    logger.info("Vertex AI shutdown OK")


# Enregistrement du cleanup pour les cas où le lifespan FastAPI ne s'exécute pas
atexit.register(_cleanup_credentials)

"""
TranscribeService — Transcription et structuration audio pour la TMA.

Pipeline complet :
  1. Whisper (OpenRouter) : blob audio → texte brut
  2. Gemini (Vertex AI)   : texte brut → JSON structuré

Chaque étape est loggée séparément dans logs_agents pour monitoring.
"""

import os
import base64
import json
import tempfile
import time
import logging
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.services.whisper_service import transcribe_with_whisper
from app.services.audit_service import AuditService
from app.services.database import supabase_client

logger = get_logger(__name__)

REQUIRED_KEYS = {"task_id", "percentage", "status", "observation"}


# ---------------------------------------------------------------------------
# Étape 1 : Transcription multimodale Gemini (audio → texte)
#   Utilisée par l'endpoint /transcribe existant
# ---------------------------------------------------------------------------

def transcribe_with_gemini(audio_data: bytes, mime_type: str = "audio/webm") -> Optional[str]:
    """Transcription audio via Gemini Vertex AI (multimodal audio → texte).

    Préservé pour compatibilité avec l'endpoint /transcribe existant.
    """
    try:
        import google.genai as genai
        from google.genai import types

        credentials_b64 = (
            settings.gemini_api_key
            or os.getenv("SUREN_GOOGLE_GEMINI_CREDENTIALS_B64")
            or os.getenv("GOOGLE_GEMINI_CREDENTIALS_B64")
        )
        if not credentials_b64:
            logger.error("Aucun credentials Vertex AI configuré")
            return None

        credentials_json = base64.b64decode(credentials_b64).decode("utf-8")
        credentials_info = json.loads(credentials_json)
        project_id = credentials_info.get("project_id") or os.getenv("GCP_PROJECT_ID")

        fd, cred_file = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(credentials_info, f)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_file

        client = genai.Client(
            vertexai=True,
            project=project_id,
            location=settings.gemini_location or "europe-west1",
        )

        model_name = settings.gemini_model or "gemini-2.5-flash"

        response = client.models.generate_content(
            model=model_name,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part(
                            inline_data=types.Blob(
                                mime_type=mime_type,
                                data=audio_data,
                            )
                        ),
                        types.Part(text="Transcris précisément ce message vocal en français. Retourne uniquement le texte transcrit, sans introduction ni conclusion."),
                    ],
                )
            ],
        )

        text = response.text.strip() if response.text else None
        if text:
            logger.info(f"Gemini multimodal transcription OK ({len(text)} chars)")
        else:
            logger.warning("Gemini multimodal transcription vide")
        return text

    except Exception as e:
        logger.error(f"Gemini multimodal transcription error: {e}")
        return None


# ---------------------------------------------------------------------------
# Étape 2 : Structuration Gemini (texte → JSON)
# ---------------------------------------------------------------------------

async def gemini_structured_extraction(transcript: str) -> Optional[dict]:
    """
    Transforme un texte transcrit en JSON structuré via Gemini.

    Schéma cible : {task_id, percentage, status, observation}
    """
    if not transcript or not transcript.strip():
        return None

    system_prompt = (
        "Tu es un parseur JSON. Transforme ce texte de chantier en JSON strict "
        "pour Supabase selon ce schéma : "
        "{task_id, percentage, status, observation}. "
        "Ne réponds rien d'autre que le JSON."
    )

    full_prompt = f"{system_prompt}\n\nTEXTE À PARSER:\n{transcript}"

    try:
        response = transcribe_with_gemini_for_text(full_prompt)
        if not response:
            return None

        raw = response.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1] if "\n" in raw else raw
            raw = raw.rsplit("```", 1)[0]

        parsed = json.loads(raw)

        if not isinstance(parsed, dict):
            logger.warning(f"Gemini structuration: response is not a dict: {type(parsed)}")
            return None

        missing = REQUIRED_KEYS - set(parsed.keys())
        if missing:
            logger.warning(f"Gemini structuration: keys manquantes: {missing}")
            return None

        logger.info(f"Gemini structuration OK: task_id={parsed.get('task_id')}")
        return parsed

    except json.JSONDecodeError as e:
        logger.error(f"Gemini structuration: JSON invalide: {e}")
        return None
    except Exception as e:
        logger.error(f"Gemini structuration error: {e}")
        return None


def transcribe_with_gemini_for_text(prompt: str) -> Optional[str]:
    """Appelle Gemini Vertex AI avec un prompt texte uniquement.

    Réutilise le même mécanisme de credentials que transcribe_with_gemini."""
    try:
        import google.genai as genai
        from google.genai import types

        credentials_b64 = (
            settings.gemini_api_key
            or os.getenv("SUREN_GOOGLE_GEMINI_CREDENTIALS_B64")
            or os.getenv("GOOGLE_GEMINI_CREDENTIALS_B64")
        )
        if not credentials_b64:
            logger.error("Aucun credentials Vertex AI configuré")
            return None

        credentials_json = base64.b64decode(credentials_b64).decode("utf-8")
        credentials_info = json.loads(credentials_json)
        project_id = credentials_info.get("project_id") or os.getenv("GCP_PROJECT_ID")

        fd, cred_file = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(credentials_info, f)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_file

        client = genai.Client(
            vertexai=True,
            project=project_id,
            location=settings.gemini_location or "europe-west1",
        )

        model_name = settings.gemini_model or "gemini-2.5-flash"

        response = client.models.generate_content(
            model=model_name,
            contents=[types.Content(
                role="user",
                parts=[types.Part(text=prompt)],
            )],
        )

        text = response.text.strip() if response.text else None
        return text

    except Exception as e:
        logger.error(f"Gemini text generation error: {e}")
        return None


# ---------------------------------------------------------------------------
# Pipeline complet : Whisper + Gemini
# ---------------------------------------------------------------------------

async def transcribe_pipeline(
    audio_data: bytes,
    mime_type: str = "audio/webm",
    org_id: str = "",
    correlation_id: str = "",
) -> dict:
    """
    Pipeline audio complet :
      1. Whisper (OpenRouter) → texte brut
      2. Gemini (Vertex AI) → JSON structuré

    Chaque étape est loggée dans logs_agents avec son temps de traitement.

    Returns:
        dict avec clés : is_valid, transcript, structured,
                         whisper_log_id, gemini_log_id, error
    """
    audit = AuditService(supabase_client)
    result = {
        "is_valid": False,
        "transcript": None,
        "structured": None,
        "whisper_log_id": None,
        "gemini_log_id": None,
        "error": None,
    }

    # --- Étape 1 : Whisper ---
    start = time.time()
    transcript = await transcribe_with_whisper(audio_data, mime_type)
    whisper_duration = int((time.time() - start) * 1000)

    whisper_status = "completed" if transcript else "failed"
    whisper_log_id = await audit.log_agent(
        org_id=org_id,
        correlation_id=correlation_id or str(time.time()),
        agent_type="whisper_transcription",
        model=settings.whisper_model or "whisper-large-v3",
        user_prompt=f"audio_file: {len(audio_data)} bytes, mime: {mime_type}",
        response_text=transcript or "",
        status=whisper_status,
        processing_duration_ms=whisper_duration,
        entity_table="logs_agents",
    )
    result["whisper_log_id"] = whisper_log_id

    if not transcript:
        result["error"] = "Whisper: transcription echouee"
        return result

    result["transcript"] = transcript

    # --- Étape 2 : Gemini structuration ---
    start = time.time()
    structured = None
    gemini_error = None
    try:
        structured = await gemini_structured_extraction(transcript)
    except Exception as e:
        gemini_error = str(e)
    gemini_duration = int((time.time() - start) * 1000)

    gemini_status = "completed" if structured else "failed"
    gemini_log_id = await audit.log_agent(
        org_id=org_id,
        correlation_id=correlation_id or str(time.time()),
        parent_correlation_id=result["whisper_log_id"],
        agent_type="gemini_structuration",
        model=settings.gemini_model or "gemini-2.5-flash",
        user_prompt=transcript,
        response_text=json.dumps(structured) if structured else (gemini_error or ""),
        extracted_data=structured,
        status=gemini_status,
        processing_duration_ms=gemini_duration,
        entity_table="logs_agents",
    )
    result["gemini_log_id"] = gemini_log_id

    if not structured:
        result["error"] = f"Gemini: structuration echouee" + (f" ({gemini_error})" if gemini_error else "")
        return result

    result["structured"] = structured
    result["is_valid"] = True
    return result

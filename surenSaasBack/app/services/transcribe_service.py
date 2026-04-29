"""
TranscribeService — Transcription audio via Gemini pour la TMA.

Utilise Vertex AI (gemini-2.5-flash) avec google-genai.
Le modèle gemini-2.5-flash supporte l'audio inline sur Vertex AI.
"""

import os
import base64
import json
import tempfile
import logging
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def transcribe_with_gemini(audio_data: bytes, mime_type: str = "audio/webm") -> Optional[str]:
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
            logger.info(f"✅ Audio transcrit ({len(text)} caractères)")
        else:
            logger.warning("⚠️ Transcription audio vide")
        return text

    except Exception as e:
        logger.error(f"❌ Erreur transcription audio: {e}")
        return None

"""
TranscribeService — Transcription audio via Gemini pour la TMA.

Utilise le modèle gemini-2.0-flash (support audio natif) pour transcrire
un flux audio brut (Blob) en texte français.
"""

import os
import base64
import logging
from typing import Optional, Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)


def transcribe_with_gemini(audio_data: bytes, mime_type: str = "audio/webm") -> Optional[str]:
    """
    Transcrit un fichier audio via Gemini (modèle avec support audio).
    Retourne le texte transcrit ou None en cas d'erreur.
    """
    try:
        import google.genai as genai
        from google.genai import types

        api_key = (
            settings.gemini_api_key
            or os.getenv("GEMINI_API_KEY")
        )
        if not api_key:
            logger.error("Aucune clé API Gemini configurée pour la transcription")
            return None

        client = genai.Client(api_key=api_key)

        # Encoder l'audio en base64 et l'envoyer à Gemini
        audio_b64 = base64.b64encode(audio_data).decode("utf-8")

        response = client.models.generate_content(
            model="gemini-2.0-flash",
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

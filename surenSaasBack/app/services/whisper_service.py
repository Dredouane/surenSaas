"""
WhisperService — Transcription audio via Whisper large-v3 sur OpenRouter.

OpenRouter expose Whisper large-v3 via l'API compatible OpenAI:
  POST https://openrouter.ai/api/v1/audio/transcriptions
  Content-Type: multipart/form-data
  Authorization: Bearer <SUREN_OPEN_ROUTER_API_KEY>
"""

import time
import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_AUDIO_URL = "https://openrouter.ai/api/v1/audio/transcriptions"


async def transcribe_with_whisper(audio_data: bytes, mime_type: str = "audio/webm") -> Optional[str]:
    if not settings.open_router_api_key:
        logger.error("SUREN_OPEN_ROUTER_API_KEY non configurée")
        return None

    start = time.time()
    file_size_kb = len(audio_data) / 1024

    try:
        ext = _mime_to_ext(mime_type)
        filename = f"audio.{ext}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {
                "file": (filename, audio_data, mime_type),
                "model": (None, settings.whisper_model or "whisper-large-v3"),
            }
            headers = {
                "Authorization": f"Bearer {settings.open_router_api_key}",
            }

            response = await client.post(
                OPENROUTER_AUDIO_URL,
                files=files,
                headers=headers,
            )

            duration_ms = int((time.time() - start) * 1000)

            if response.status_code != 200:
                logger.error(
                    f"Whisper API error (HTTP {response.status_code}): "
                    f"{response.text[:500]} | size={file_size_kb:.1f}KB | "
                    f"duration={duration_ms}ms"
                )
                return None

            data = response.json()
            text = (data.get("text") or "").strip()

            if not text:
                logger.warning(f"Whisper returned empty text | size={file_size_kb:.1f}KB")
                return None

            logger.info(
                f"Whisper transcription OK: {len(text)} chars | "
                f"size={file_size_kb:.1f}KB | duration={duration_ms}ms"
            )
            return text

    except httpx.TimeoutException:
        logger.error(f"Whisper timeout after 30s | size={file_size_kb:.1f}KB")
        return None
    except Exception as e:
        logger.error(f"Whisper error: {e} | size={file_size_kb:.1f}KB")
        return None


def _mime_to_ext(mime_type: str) -> str:
    mapping = {
        "audio/webm": "webm",
        "audio/ogg": "ogg",
        "audio/wav": "wav",
        "audio/mp3": "mp3",
        "audio/mpeg": "mp3",
        "audio/mp4": "mp4",
        "audio/x-m4a": "m4a",
    }
    return mapping.get(mime_type, "webm")

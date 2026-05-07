import json
import httpx
import time
from typing import List, Dict, Any, Optional
from langchain_core.messages import HumanMessage
from app.core.config import settings
from app.core import vertex as vertex_service


class AudioExpertService:
    """Service expert pour le traitement audio (Whisper + Gemini Normalization)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.open_router_api_key
        self.llm = vertex_service.get_chat_model()
        self.transcribe_url = "https://openrouter.ai/api/v1/audio/transcriptions"

    async def transcribe(self, audio_bytes: bytes) -> str:
        """Transcrit le binaire audio via OpenRouter Whisper."""
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        files = {
            "file": ("voice.ogg", audio_bytes, "audio/ogg"),
            "model": (None, "openai/whisper-large-v3")
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.transcribe_url, headers=headers, files=files)
            response.raise_for_status()
            data = response.json()
            return data.get("text", "")

    async def normalize_text(self, raw_text: str, chantiers_context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Normalise le texte transcrit avec le contexte métier BTP et détecte l'urgence."""
        chantiers_str = "\n".join([f"- {c['nom']} (Réf: {c.get('ref', 'N/A')})" for c in chantiers_context])

        prompt = (
            "Tu es un expert en transcription pour le secteur du BTP (Bâtiment et Travaux Publics). "
            "Ta mission est de corriger et normaliser le texte transcrit d'un message vocal. "
            "\n\nCONTEXTE DES CHANTIERS ACTIFS :\n"
            f"{chantiers_str}"
            "\n\nCONSIGNES :\n"
            "1. Corrige les fautes d'orthographe et de grammaire.\n"
            "2. Identifie les noms de chantiers ou les références et assure-toi qu'ils correspondent au contexte.\n"
            "3. Détecte si le message exprime une URGENCE CRITIQUE (ex: accident, danger, arrêt immédiat, alerte).\n"
            "4. Réponds UNIQUEMENT au format JSON : {\"text\": \"texte corrigé\", \"is_urgent\": boolean}\n"
            "\nTEXTE À TRAITER :\n"
            f"\"{raw_text}\""
        )

        response = await self.llm.ainvoke([HumanMessage(content=prompt)])

        try:
            content = str(response.content).strip()
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()

            return json.loads(content)

        except Exception:
            return {"text": raw_text, "is_urgent": "URGENT" in raw_text.upper() or "ALERTE" in raw_text.upper()}

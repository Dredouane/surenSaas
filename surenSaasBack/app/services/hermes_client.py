"""
Client API Hermès — compatible OpenAI SDK.

Utilise le SDK Python `openai` officiel avec un base_url personnalisé
pointant vers l'instance Hermès (http://REDACTED:8642/v1).

Timeout : 30s. Retry : 2 tentatives avec backoff.
"""

import asyncio
import logging
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

logger = logging.getLogger(__name__)

MODEL = "Arev_Chantiers_Assist"
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 2
RETRY_DELAY = 2.0


class HermesClient:
    """Client OpenAI-compatible pour l'API Hermès."""

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self._client: Optional[AsyncOpenAI] = None

    def _get_client(self) -> AsyncOpenAI:
        """Lazy init du client OpenAI (évite les imports au démarrage)."""
        if self._client is None:
            if AsyncOpenAI is None:
                raise RuntimeError(
                    "openai package not installed. Run: pip install openai"
                )
            self._client = AsyncOpenAI(
                base_url=self.api_url,
                api_key=self.api_key,
                timeout=DEFAULT_TIMEOUT,
                max_retries=0,  # On gère les retries nous-mêmes
            )
        return self._client

    def _is_retryable(self, exc: Exception) -> bool:
        """Retry uniquement sur timeout ou erreur 5xx."""
        err_str = str(exc).lower()
        if "timeout" in err_str:
            return True
        if "429" in err_str:
            return True
        if "500" in err_str or "502" in err_str or "503" in err_str:
            return True
        return False

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_fixed(RETRY_DELAY),
        retry=retry_if_exception(lambda e: HermesClient._is_retryable_inst(e)),
    )
    async def chat(self, messages: list, context: Optional[dict] = None) -> dict:
        """Appelle /v1/chat/completions sur Hermès en tant que proxy.

        Args:
            messages: Liste de messages au format OpenAI.
                [
                    {"role": "system", "content": "..."},
                    {"role": "user", "content": "..."}
                ]
            context: Métadonnées optionnelles (chantier_id, user_role, etc.)
                qui seront injectées dans le system prompt si fournies.

        Returns:
            Réponse complète de l'API Hermès (format OpenAI compatible).
        """
        client = self._get_client()

        # Injecter le contexte dans un message système si présent
        final_messages = list(messages)
        if context:
            context_str = "\n".join(f"{k}: {v}" for k, v in context.items() if v)
            if context_str:
                final_messages.insert(0, {
                    "role": "system",
                    "content": f"[CONTEXTE]\n{context_str}",
                })

        try:
            response = await client.chat.completions.create(
                model=MODEL,
                messages=final_messages,
                temperature=0.3,
                max_tokens=2048,
            )

            return {
                "success": True,
                "message": response.choices[0].message.content if response.choices else "",
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                } if response.usage else None,
            }

        except Exception as e:
            logger.error(f"[HermesClient] Erreur appel API: {e}")
            raise

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_fixed(RETRY_DELAY),
        retry=retry_if_exception(lambda e: HermesClient._is_retryable_inst(e)),
    )
    async def triage_summary(self, context: Optional[dict] = None) -> dict:
        """Génère une synthèse de l'onglet triage via Hermès.

        Args:
            context: Métadonnées (org_id, chantier_id, etc.)

        Returns:
            Résumé texte de la situation.
        """
        system_prompt = (
            "Tu es l'agent Hermès, assistant IA d'une entreprise du BTP. "
            "Tu fais la synthèse de l'onglet de triage pour un chantier."
        )

        user_prompt = (
            "Analyse les informations suivantes et génère un résumé exécutif "
            "de la situation actuelle du chantier :\n"
        )
        if context:
            user_prompt += "\n".join(f"- {k}: {v}" for k, v in context.items() if v)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        return await self.chat(messages)

    @staticmethod
    def _is_retryable_inst(e: Exception) -> bool:
        """Version statique de _is_retryable pour tenacity."""
        err_str = str(e).lower()
        if "timeout" in err_str:
            return True
        if "429" in err_str:
            return True
        if "500" in err_str or "502" in err_str or "503" in err_str:
            return True
        return False


# Instance singleton (lazy initialized)
_hermes_client: Optional[HermesClient] = None


def get_hermes_client() -> HermesClient:
    """Retourne l'instance singleton du client Hermès."""
    global _hermes_client
    if _hermes_client is None:
        from app.core.config import settings
        api_url = settings.hermes_api_url or "http://REDACTED:8642/v1"
        api_key = settings.hermes_api_key or ""
        if not api_key:
            raise RuntimeError("HERMES_API_KEY non configurée")
        _hermes_client = HermesClient(api_url=api_url, api_key=api_key)
    return _hermes_client

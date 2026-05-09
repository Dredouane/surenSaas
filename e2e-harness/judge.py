"""
LLM-based judge for evaluating Telegram bot replies against multi-step scenarios.

Uses Gemini 2.5 Flash via HTTP API (no Vertex AI / SDK dependency).
Falls back to a mock judge (always score=1) if no GEMINI_API_KEY is set.

The judge is a "Session Auditor" — it receives the full conversation history
and evaluates each step's compliance with the scenario prompt.
"""

import json
import logging
import os
from typing import Optional

from models import Verdict

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────
_GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent"
)
_GEMINI_TIMEOUT_S = 15
_GEMINI_MAX_RETRIES = 2

_DEFAULT_SYSTEM_PROMPT = (
    "Tu es un Auditeur de Session. Tu reçois un historique de conversation "
    "entre un utilisateur et un agent de gestion de chantier.\n\n"
    "TA MISSION :\n"
    "1. Validation de la Mémoire : L'agent doit démontrer qu'il conserve "
    "les informations critiques (Chantier, Organisation) d'un tour à l'autre.\n"
    "2. Zéro Hallucination : Si l'agent change de chantier ou oublie un montant "
    "mentionné plus haut, le score est FAIL.\n"
    "3. Véracité DB : L'agent doit utiliser les noms officiels (souvent en MAJUSCULES) "
    "s'il les a extraits de la base de données.\n\n"
    'FORMAT DE RÉPONSE UNIQUE : {"verdict": "PASS"} ou {"verdict": "FAIL", "reason": "..."}'
)


def _get_api_key() -> Optional[str]:
    """Get the Gemini API key from environment."""
    return (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("SUREN_GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )


def _build_prompt(
    system_prompt: str,
    scenario_prompt: str,
    conversation_history: str,
) -> str:
    """Build the full prompt for the judge LLM."""
    parts = []
    if system_prompt:
        parts.append(system_prompt)
    if conversation_history:
        parts.append(f"\nHISTORIQUE DE LA CONVERSATION :\n{conversation_history}")
    parts.append(f"\nCONSIGNE POUR CETTE ÉTAPE :\n{scenario_prompt}")
    parts.append(
        '\nRéponds UNIQUEMENT en JSON : '
        '{"verdict": "PASS"} ou {"verdict": "FAIL", "reason": "..."}'
    )
    return "\n".join(parts)


def _parse_verdict(text: str) -> Optional[Verdict]:
    """Parse the LLM response into a Verdict."""
    raw = text.strip()
    # Strip markdown code fences
    if raw.startswith("```"):
        first_nl = raw.find("\n")
        if first_nl != -1:
            raw = raw[first_nl + 1:]
        last_bt = raw.rfind("```")
        if last_bt != -1:
            raw = raw[:last_bt]
        raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None

    verdict_str = data.get("verdict", "")
    if verdict_str == "PASS":
        return Verdict(score=1, reason=data.get("reason", ""), step_index=0)
    elif verdict_str == "FAIL":
        return Verdict(score=0, reason=data.get("reason", ""), step_index=0)
    return None


def _call_gemini(prompt: str, api_key: str) -> Optional[str]:
    """Call Gemini 2.5 Flash via HTTP API. Returns response text or None."""
    import httpx

    url = f"{_GEMINI_API_URL}?key={api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    for attempt in range(1 + _GEMINI_MAX_RETRIES):
        try:
            with httpx.Client(timeout=_GEMINI_TIMEOUT_S) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                result = resp.json()

            candidates = result.get("candidates", [])
            if not candidates:
                logger.warning("Gemini returned no candidates (attempt %d)", attempt + 1)
                continue

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                logger.warning("Gemini returned no parts (attempt %d)", attempt + 1)
                continue

            return parts[0].get("text", "").strip()

        except Exception as exc:
            logger.warning(
                "Gemini API call failed (attempt %d/%d): %s",
                attempt + 1,
                _GEMINI_MAX_RETRIES + 1,
                exc,
            )

    return None


def judge_step(
    scenario_prompt: str,
    bot_reply: str,
    conversation_history: str = "",
    system_prompt: str = "",
    step_index: int = 0,
) -> Verdict:
    """Evaluate a single step of a scenario using Gemini Flash.

    Args:
        scenario_prompt: The criteria for this specific step.
        bot_reply: The bot's response text to evaluate.
        conversation_history: Full conversation up to this point (for context).
        system_prompt: Optional override of the default system prompt.
        step_index: Index of this step (for reporting).

    Returns:
        A ``Verdict`` with score and reason.
    """
    api_key = _get_api_key()
    if not api_key:
        logger.warning("No GEMINI_API_KEY set — returning mock pass verdict")
        return Verdict(
            score=1,
            reason="mock — no GEMINI_API_KEY set",
            step_index=step_index,
        )

    system = system_prompt or _DEFAULT_SYSTEM_PROMPT
    prompt = _build_prompt(system, scenario_prompt, conversation_history)

    text = _call_gemini(prompt, api_key)
    if text is None:
        logger.error("Gemini API failed after all retries — returning mock pass")
        return Verdict(
            score=1,
            reason="mock — Gemini API failed after retries",
            step_index=step_index,
        )

    verdict = _parse_verdict(text)
    if verdict is not None:
        verdict.step_index = step_index
        logger.info("⚖️  Judge: score=%s — %s", verdict.score, verdict.reason[:120])
        return verdict

    logger.warning("Gemini returned unparseable response: %s", text[:200])
    return Verdict(
        score=0,
        reason=f"Unparseable judge response: {text[:100]}",
        step_index=step_index,
    )

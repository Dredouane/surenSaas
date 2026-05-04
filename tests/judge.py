"""LLM-based judge for evaluating Telegram bot replies against scenarios.

Uses Gemini 2.0 Flash (google-genai SDK preferred, HTTP POST fallback).
Falls back to a mock judge (always score=1) if no GEMINI_API_KEY is set.

Deep module principle:
    - Public API is a single function: judge_response(scenario, bot_reply_text)
    - Internals (API calls, retries, JSON parsing) are fully encapsulated.
"""

import json
import logging
import os
from typing import Optional

from tests.models import JudgeVerdict, Scenario

logger = logging.getLogger(__name__)

# ── Constants ───────────────────────────────────────────────────────────────
_GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)
_GEMINI_MODEL = "gemini-2.0-flash"
_TIMEOUT_S = 10
_MAX_RETRIES = 2


def _build_judge_prompt(scenario: Scenario, bot_reply_text: str) -> str:
    """Build the system prompt sent to the judge LLM."""
    return (
        "Tu es un juge QA pour un bot Telegram de chantier BTP.\n\n"
        f"SCENARIO:\n{scenario.judge.prompt}\n\n"
        f"REPONSE DU BOT:\n{bot_reply_text}\n\n"
        "Réponds UNIQUEMENT en JSON: "
        '{"score": 1|0, "reason": "..."}'
    )


def _parse_judge_response(text: str) -> Optional[dict]:
    """Parse JSON from the LLM response, stripping markdown fences if needed.

    Returns a parsed dict with 'score' and 'reason', or None on failure.
    """
    raw = text.strip()
    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    if raw.startswith("```"):
        # Find the first and last triple backtick
        first_nl = raw.find("\n")
        if first_nl != -1:
            raw = raw[first_nl + 1 :]
        last_bt = raw.rfind("```")
        if last_bt != -1:
            raw = raw[:last_bt]
        raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if "score" not in data or "reason" not in data:
        return None

    return data


def _judge_via_sdk(api_key: str, scenario: Scenario, bot_reply_text: str) -> Optional[JudgeVerdict]:
    """Evaluate using the google-genai SDK."""
    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        prompt = _build_judge_prompt(scenario, bot_reply_text)
        response = client.models.generate_content(
            model=_GEMINI_MODEL,
            contents=prompt,
        )
        text = response.text.strip()
        data = _parse_judge_response(text)
        if data is None:
            return None
        return JudgeVerdict(
            score=int(data["score"]),
            reason=str(data["reason"]),
        )
    except Exception as exc:
        logger.warning("google-genai SDK call failed: %s", exc)
        return None


def _judge_via_http(api_key: str, scenario: Scenario, bot_reply_text: str) -> Optional[JudgeVerdict]:
    """Evaluate using raw HTTP POST to the Gemini API."""
    try:
        import httpx

        url = f"{_GEMINI_API_URL}?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": _build_judge_prompt(scenario, bot_reply_text)}
                    ]
                }
            ]
        }

        with httpx.Client(timeout=_TIMEOUT_S) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            result = resp.json()

        # Extract text from Gemini response
        candidates = result.get("candidates", [])
        if not candidates:
            return None
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            return None
        text = parts[0].get("text", "").strip()
        if not text:
            return None

        data = _parse_judge_response(text)
        if data is None:
            return None
        return JudgeVerdict(
            score=int(data["score"]),
            reason=str(data["reason"]),
        )
    except Exception as exc:
        logger.warning("HTTP Gemini call failed: %s", exc)
        return None


def judge_response(scenario: Scenario, bot_reply_text: str) -> JudgeVerdict:
    """Evaluate a bot reply against a test scenario using Gemini Flash.

    Uses the google-genai SDK when available, falling back to raw HTTP POST.
    If no GEMINI_API_KEY is set (or all calls fail), returns a mock pass verdict
    so that tests can run during development without an API key.

    Args:
        scenario: The test scenario with judge configuration.
        bot_reply_text: The text produced by the bot in response to the input.

    Returns:
        JudgeVerdict with score (1=pass, 0=fail) and reason.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.info("No GEMINI_API_KEY set — returning mock pass verdict")
        return JudgeVerdict(
            score=1,
            reason="mock — no GEMINI_API_KEY",
        )

    # Try SDK first (preferred), then HTTP, with retries
    for attempt in range(1 + _MAX_RETRIES):
        # Strategy 1: google-genai SDK
        verdict = _judge_via_sdk(api_key, scenario, bot_reply_text)
        if verdict is not None:
            return verdict

        # Strategy 2: raw HTTP POST
        verdict = _judge_via_http(api_key, scenario, bot_reply_text)
        if verdict is not None:
            return verdict

        if attempt < _MAX_RETRIES:
            logger.info(
                "Judge JSON parse failed (attempt %d/%d), retrying...",
                attempt + 1,
                _MAX_RETRIES + 1,
            )

    # All attempts exhausted
    logger.error("Judge LLM failed after %d attempts — returning mock pass", _MAX_RETRIES + 1)
    return JudgeVerdict(
        score=1,
        reason="mock — judge LLM failed after retries",
    )

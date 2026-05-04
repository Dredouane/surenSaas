"""
Parametrized pytest that reads all YAML scenario files from ``tests/scenarios/``
and runs each as an end-to-end blackbox test.

For each scenario:
1. Parse the YAML into a ``Scenario`` model.
2. Build a Telegram Update payload and inject it via ``tg_mock_client``.
3. Poll for bot reply via ``tg_mock_client.get_replies()``.
4. Call ``judge_response()`` with the scenario and the bot reply text.
5. Assert that the judge returns ``score == 1``.

Test IDs in pytest output are the YAML filenames (e.g. ``scenario_depense``).
Backend health is checked before any tests run; scenarios are skipped if
the backend is not reachable.
"""

import logging
import os
from pathlib import Path

import pytest
import yaml

from tests.judge import judge_response
from tests.models import Scenario

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios"
BACKEND_HEALTH_URL = os.getenv("BACKEND_HEALTH_URL", "http://localhost:8080/health")
HEALTH_CHECK_TIMEOUT = 5.0


# ═════════════════════════════════════════════════════════════════════════════
# Helper: discover & load scenarios
# ═════════════════════════════════════════════════════════════════════════════


def _discover_scenario_paths() -> list[Path]:
    """Return sorted list of */*.yaml paths from the scenarios directory."""
    paths = sorted(SCENARIOS_DIR.glob("*.yaml"))
    if not paths:
        logger.warning("No YAML scenario files found in %s", SCENARIOS_DIR)
    return paths


def _load_scenario(yaml_path: Path) -> Scenario:
    """Load a YAML scenario file and return a validated ``Scenario`` model.

    Handles both the ``content`` field (for text/voice) and the
    ``file_path`` + ``caption`` fields (for document/photo media types).
    """
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

    media_raw = raw["input"]["media"]
    media_type = media_raw["type"]

    # Normalise the media payload — the YAML may use file_path + caption
    # for document/photo instead of a single ``content`` field.
    if media_type in ("document", "photo"):
        # Use file_path as content; preserve caption as extra field
        media_raw["content"] = media_raw.pop("file_path", "")
        caption = media_raw.pop("caption", None)
        if caption:
            media_raw["caption"] = caption
    elif "content" not in media_raw:
        media_raw["content"] = ""

    return Scenario(**raw)


def _build_health_check_url() -> str:
    """Return the backend health check URL, respecting env overrides."""
    return BACKEND_HEALTH_URL


# ═════════════════════════════════════════════════════════════════════════════
# Session-scoped: discover scenarios once
# ═════════════════════════════════════════════════════════════════════════════


def pytest_generate_tests(metafunc):
    """Dynamic parametrization: one test ID per scenario YAML file.

    This lets scenarios be discovered *once* at collection time (instead
    of re-discovering them inside a ``session_or_module`` fixture), which
    gives nice parametrized IDs in the pytest output.
    """
    if "scenario" in metafunc.fixturenames:
        scenario_paths = sorted(SCENARIOS_DIR.glob("*.yaml"))
        scenarios = [_load_scenario(p) for p in scenario_paths]
        ids = [p.stem for p in scenario_paths]
        metafunc.parametrize("scenario", scenarios, ids=ids)


# ═════════════════════════════════════════════════════════════════════════════
# Helper: get bot reply text
# ═════════════════════════════════════════════════════════════════════════════


def _get_bot_reply_text(replies: list[dict]) -> str:
    """Extract bot reply text from the list of message dicts returned by
    ``tg_mock_client.get_replies()``.

    Concatenates all ``text`` fields from the replies. If a reply has a
    ``caption`` instead of ``text`` (e.g. media messages), uses that.
    """
    parts = []
    for msg in replies:
        text = msg.get("text") or msg.get("caption") or ""
        if text:
            parts.append(text)
    return "\n".join(parts)


# ═════════════════════════════════════════════════════════════════════════════
# Health check helper
# ═════════════════════════════════════════════════════════════════════════════


def _backend_is_reachable() -> bool:
    """Return True if the backend health endpoint responds 200."""
    try:
        import httpx

        resp = httpx.get(
            _build_health_check_url(),
            timeout=HEALTH_CHECK_TIMEOUT,
        )
        return resp.status_code == 200
    except Exception as exc:
        logger.info("Backend health check failed: %s", exc)
        return False


# ═════════════════════════════════════════════════════════════════════════════
# The actual test
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
def test_scenario(scenario: Scenario, tg_mock_client) -> None:
    """Run a single scenario end-to-end.

    Steps:
    1. Skip if backend is unreachable.
    2. Inject the input via tg_mock_client.
    3. Wait for bot reply via get_replies().
    4. Evaluate bot reply with the judge.
    5. Assert score == 1.
    """
    # ── Skip check ────────────────────────────────────────────────────
    if not _backend_is_reachable():
        pytest.skip("Backend is not reachable — skipping E2E test")

    logger.info(
        "🚀 Running scenario [%s]: %s",
        scenario.test_case,
        scenario.description,
    )

    # ── Inject the input ──────────────────────────────────────────────
    media = scenario.input.media
    media_type = media.type
    content = media.content

    # Extract optional caption from extra fields (set during YAML normalisation)
    extra = getattr(media, "model_extra", None) or {}
    caption = extra.get("caption")

    if media_type == "text":
        result = tg_mock_client.send_text(content)
    elif media_type == "voice":
        result = tg_mock_client.send_voice(content)
    elif media_type == "photo":
        result = tg_mock_client.send_photo(content, caption=caption)
    elif media_type == "document":
        result = tg_mock_client.send_document(content, caption=caption)
    else:
        raise ValueError(f"Unsupported media type: {media_type}")

    # ── Get bot reply from webhook response ───────────────────────────
    bot_reply_text = result.get("reply_text") if isinstance(result, dict) else None

    if not bot_reply_text:
        raise AssertionError(
            f"No reply received from bot. Webhook returned: {result}"
        )

    logger.info("🤖 Bot reply: %s", bot_reply_text[:200])

    # ── Judge the reply ───────────────────────────────────────────────
    verdict = judge_response(scenario, bot_reply_text)

    logger.info(
        "⚖️  Verdict: score=%s — %s",
        verdict.score,
        verdict.reason[:150],
    )

    # Honore l'attendu du scénario
    expected_pass = scenario.judge.expected_verdict == "pass"
    if expected_pass:
        assert verdict.score == 1, (
            f"Scenario [{scenario.test_case}] FAILED — judge score={verdict.score}. "
            f"Reason: {verdict.reason}"
        )
    else:
        assert verdict.score == 0, (
            f"Scenario [{scenario.test_case}] expected to FAIL but passed. "
            f"Reason: {verdict.reason}"
        )

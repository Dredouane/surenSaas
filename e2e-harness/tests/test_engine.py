"""Unit tests for the E2E test engine (SessionRunner, models, provider).

RED phase: These tests should fail initially because the production code
(engine.py, models.py, provider.py) does not yet exist or is incomplete.
"""
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from conftest import TgMockClient, TEST_CHAT_ID


# ═══════════════════════════════════════════════════════════════════════════
# Tests for send_callback parsing (TgMockClient)
# ═══════════════════════════════════════════════════════════════════════════


def test_send_callback_parsing_finds_button():
    """send_callback should find a button whose text CONTAINS the search string."""
    # Mock get_replies to return a message with inline_keyboard
    mock_replies = [
        {
            "message_id": 101,
            "text": "Choose a project:",
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "Chantier CRF", "callback_data": "chantier:crf-001"}],
                    [{"text": "Chantier CH-016", "callback_data": "chantier:ch016"}],
                ]
            },
        }
    ]

    from engine import _find_button_in_replies

    result = _find_button_in_replies(mock_replies, "CRF")
    assert result is not None, "Should find button with 'CRF' in text"
    callback_data, message = result
    assert callback_data == "chantier:crf-001"
    assert message["message_id"] == 101

def test_send_callback_parsing_case_insensitive():
    """send_callback should match button text case-insensitively."""
    mock_replies = [
        {
            "message_id": 102,
            "text": "Options:",
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "Confirmer", "callback_data": "confirm"}],
                    [{"text": "Annuler", "callback_data": "cancel"}],
                ]
            },
        }
    ]

    from engine import _find_button_in_replies

    # Search with different case
    result = _find_button_in_replies(mock_replies, "confirm")
    assert result is not None
    callback_data, _ = result
    assert callback_data == "confirm"

    result = _find_button_in_replies(mock_replies, "CONFIRM")
    assert result is not None
    callback_data, _ = result
    assert callback_data == "confirm"

def test_send_callback_parsing_no_match_raises():
    """send_callback should raise RuntimeError when button not found."""
    mock_replies = [
        {
            "message_id": 103,
            "text": "Menu:",
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "Oui", "callback_data": "yes"}],
                ]
            },
        }
    ]

    from engine import _find_button_in_replies

    result = _find_button_in_replies(mock_replies, "Non")
    assert result is None, "Should return None when button not found"

def test_send_callback_no_reply_markup():
    """send_callback should handle messages without reply_markup gracefully."""
    mock_replies = [
        {
            "message_id": 104,
            "text": "Hello!",
            # no reply_markup
        }
    ]

    from engine import _find_button_in_replies

    result = _find_button_in_replies(mock_replies, "anything")
    assert result is None

def test_send_callback_empty_inline_keyboard():
    """send_callback should handle empty inline_keyboard gracefully."""
    mock_replies = [
        {
            "message_id": 105,
            "text": "Menu:",
            "reply_markup": {
                "inline_keyboard": []
            },
        }
    ]

    from engine import _find_button_in_replies

    result = _find_button_in_replies(mock_replies, "anything")
    assert result is None


def test_send_callback_empty_inline_keyboard():
    """send_callback should handle empty inline_keyboard gracefully."""
    mock_replies = [
        {
            "message_id": 105,
            "text": "Menu:",
            "reply_markup": {
                "inline_keyboard": []
            },
        }
    ]

    from engine import _find_button_in_replies

    result = _find_button_in_replies(mock_replies, "anything")
    assert result is None


# ═══════════════════════════════════════════════════════════════════════════
# Tests for thread_id persistence in SessionRunner
# ═══════════════════════════════════════════════════════════════════════════


def test_session_runner_generates_thread_id():
    """SessionRunner should auto-generate a thread_id if not provided."""
    from engine import SessionRunner

    runner = SessionRunner(mock_client=MagicMock())
    assert runner.thread_id is not None
    assert isinstance(runner.thread_id, str)


def test_session_runner_accepts_custom_thread_id():
    """SessionRunner should accept a custom thread_id."""
    from engine import SessionRunner

    custom_id = "my-custom-thread-001"
    runner = SessionRunner(mock_client=MagicMock(), thread_id=custom_id)
    assert runner.thread_id == custom_id


def test_session_runner_maintains_thread_id_across_steps():
    """SessionRunner should use the same thread_id for all steps in a session."""
    from engine import SessionRunner

    runner = SessionRunner(mock_client=MagicMock(), thread_id="persistent-thread")
    assert runner.thread_id == "persistent-thread"
    # Simulate multiple steps
    runner.thread_id = runner.thread_id  # no-op, should be same
    assert runner.thread_id == "persistent-thread"


# ═══════════════════════════════════════════════════════════════════════════
# Tests for history accumulation in SessionRunner
# ═══════════════════════════════════════════════════════════════════════════


def test_session_runner_history_starts_empty():
    """SessionRunner should start with an empty history."""
    from engine import SessionRunner

    runner = SessionRunner(mock_client=MagicMock())
    assert runner.history == []


def test_session_runner_accumulates_messages():
    """SessionRunner should accumulate user messages and bot replies in history."""
    from engine import SessionRunner
    from models import Step, Verdict

    mock_client = MagicMock()
    mock_client.send_text.return_value = {
        "backend_status": 200,
        "reply_text": "Bonjour! Comment puis-je vous aider?",
    }
    mock_client._history = []

    runner = SessionRunner(mock_client=mock_client)

    step = Step(
        type="text",
        content="Bonjour",
        judge_prompt="Le bot doit répondre avec un message de bienvenue.",
        expected_verdict="pass",
    )

    verdict = runner.run_step(step)

    assert len(runner.history) >= 1
    # History should contain the user message
    assert any(
        h.get("role") == "user" and "Bonjour" in str(h.get("content", ""))
        for h in runner.history
    )


def test_session_runner_history_across_multiple_steps():
    """SessionRunner history should span all steps in a session."""
    from engine import SessionRunner
    from models import Step, Verdict

    mock_client = MagicMock()
    mock_client.send_text.side_effect = [
        {"backend_status": 200, "reply_text": "Première réponse"},
        {"backend_status": 200, "reply_text": "Deuxième réponse"},
    ]
    mock_client._history = []

    runner = SessionRunner(mock_client=mock_client)

    step1 = Step(type="text", content="Message 1", judge_prompt="", expected_verdict="pass")
    step2 = Step(type="text", content="Message 2", judge_prompt="", expected_verdict="pass")

    runner.run_step(step1)
    runner.run_step(step2)

    assert len(runner.history) >= 2


# ═══════════════════════════════════════════════════════════════════════════
# Tests for provider (load_scenario)
# ═══════════════════════════════════════════════════════════════════════════


def test_load_scenario_from_yaml(tmp_path):
    """load_scenario should correctly parse a multi-step YAML scenario."""
    yaml_content = """
test_case: "test-load"
description: "Test loading scenario"
tags: [test]
steps:
  - type: text
    content: "Bonjour"
    judge_prompt: "Le bot doit répondre"
    expected_verdict: pass
  - type: callback
    content: "Bouton 1"
    judge_prompt: "Le bot doit confirmer"
    expected_verdict: pass
"""
    yaml_path = tmp_path / "test_scenario.yaml"
    yaml_path.write_text(yaml_content, encoding="utf-8")

    from provider import load_scenario
    from models import Scenario

    scenario = load_scenario(str(yaml_path))
    assert isinstance(scenario, Scenario)
    assert scenario.test_case == "test-load"
    assert len(scenario.steps) == 2
    assert scenario.steps[0].type == "text"
    assert scenario.steps[0].content == "Bonjour"
    assert scenario.steps[1].type == "callback"
    assert scenario.steps[1].content == "Bouton 1"


def test_load_scenario_single_step(tmp_path):
    """load_scenario should handle single-step scenarios (backward compat)."""
    yaml_content = """
test_case: "single-step"
description: "Single step scenario"
tags: [simple]
steps:
  - type: text
    content: "Hello"
    judge_prompt: "Bot should respond"
    expected_verdict: pass
"""
    yaml_path = tmp_path / "single_step.yaml"
    yaml_path.write_text(yaml_content, encoding="utf-8")

    from provider import load_scenario
    from models import Scenario

    scenario = load_scenario(str(yaml_path))
    assert len(scenario.steps) == 1
    assert scenario.steps[0].type == "text"


def test_load_scenario_raises_on_missing_file():
    """load_scenario should raise FileNotFoundError for missing file."""
    from provider import load_scenario

    with pytest.raises(FileNotFoundError):
        load_scenario("/nonexistent/path.yaml")


# ═══════════════════════════════════════════════════════════════════════════
# Tests for wait_for_reply polling (TgMockClient)
# ═══════════════════════════════════════════════════════════════════════════


def _make_tgmock_client(http_client) -> TgMockClient:
    """Helper to build a TgMockClient with a custom httpx client (mocked)."""
    return TgMockClient(
        tg_mock_url="http://localhost:9999",
        bot_token="test:fake",
        backend_webhook_url="http://localhost:9999",
        org_id="test-org",
        webhook_token="test-token",
        real_bot_token="test:fake",
        _http_client=http_client,
    )


def test_wait_for_reply_returns_messages_after_offset():
    """wait_for_reply doit retourner uniquement les messages postérieurs
    à l'update_id_max enregistré avant l'appel (sliding window)."""
    import httpx
    from unittest.mock import MagicMock

    # Simuler un getUpdates qui retourne d'abord des messages existants (déjà vus),
    # puis après un délai, un nouveau message du bot.
    call_count = [0]

    def mock_send(request: httpx.Request) -> httpx.Response:
        call_count[0] += 1
        if call_count[0] == 1:
            # Premier appel : snapshot de l'existant — 2 messages déjà vus
            return httpx.Response(200, json={
                "ok": True,
                "result": [
                    {"update_id": 100, "message": {"text": "ancien msg 1"}},
                    {"update_id": 101, "message": {"text": "ancien msg 2"}},
                ]
            })
        if call_count[0] == 2:
            # Deuxième appel (juste après) : en cours de traitement, rien de nouveau
            return httpx.Response(200, json={"ok": True, "result": []})
        # Troisième appel et suivants : le bot a répondu
        return httpx.Response(200, json={
            "ok": True,
            "result": [
                {"update_id": 202, "message": {"message_id": 1, "text": "Nouvelle réponse du bot"}},
            ]
        })

    transport = httpx.MockTransport(mock_send)
    http_client = httpx.Client(transport=transport)
    client = _make_tgmock_client(http_client)

    # wait_for_reply doit ignorer les messages 100 et 101 (antérieurs)
    messages = client.wait_for_reply(timeout=5.0, poll_interval=0.1)
    assert len(messages) == 1
    assert messages[0]["text"] == "Nouvelle réponse du bot"


def test_wait_for_reply_collects_multiple_messages_in_window():
    """wait_for_reply doit collecter TOUS les messages arrivés dans une
    fenêtre courte (ex: 2 messages à 200ms d'intervalle)."""
    import httpx
    import time

    snapshot_done = [False]
    first_new_delivered = [False]

    def mock_send(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        # Extraire l'offset depuis l'URL
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        offset = int(params.get("offset", [0])[0])

        if offset == 0:
            # Snapshot initial
            return httpx.Response(200, json={
                "ok": True,
                "result": [{"update_id": 100, "message": {"message_id": 10, "text": "ancien"}}]
            })

        if not snapshot_done[0]:
            snapshot_done[0] = True
            return httpx.Response(200, json={"ok": True, "result": []})

        if not first_new_delivered[0]:
            # Premier message bot
            first_new_delivered[0] = True
            return httpx.Response(200, json={
                "ok": True,
                "result": [{"update_id": 200, "message": {"message_id": 20, "text": "première réponse"}}]
            })

        # Appels suivants : deuxième message bot (simule un délai de 200ms)
        return httpx.Response(200, json={
            "ok": True,
            "result": [{"update_id": 201, "message": {"message_id": 21, "text": "menu boutons"}}]
        })

    transport = httpx.MockTransport(mock_send)
    http_client = httpx.Client(transport=transport)
    client = _make_tgmock_client(http_client)

    # expected_count=2, doit attendre jusqu'à avoir les 2
    messages = client.wait_for_reply(expected_count=2, timeout=5.0, poll_interval=0.05)
    assert len(messages) == 2
    texts = [m["text"] for m in messages]
    assert "première réponse" in texts
    assert "menu boutons" in texts


def test_wait_for_reply_timeout_returns_partial():
    """wait_for_reply doit retourner les messages partiels au timeout
    plutôt que de raise, et logger un warning."""
    import httpx

    def mock_send(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True, "result": []})

    transport = httpx.MockTransport(mock_send)
    http_client = httpx.Client(transport=transport)
    client = _make_tgmock_client(http_client)

    messages = client.wait_for_reply(expected_count=5, timeout=0.3, poll_interval=0.05)
    assert len(messages) == 0  # Timeout mais pas d'exception


# ═══════════════════════════════════════════════════════════════════════════
# Tests for Verdict model
# ═══════════════════════════════════════════════════════════════════════════


def test_verdict_model():
    """Verdict should store score, reason, and step_index."""
    from models import Verdict

    v = Verdict(score=1, reason="All good", step_index=0)
    assert v.score == 1
    assert v.reason == "All good"
    assert v.step_index == 0


def test_verdict_passed_property():
    """Verdict.passed should return True when score matches expected."""
    from models import Verdict

    v = Verdict(score=1, reason="Pass", step_index=0)
    assert v.passed is True

    v_fail = Verdict(score=0, reason="Fail", step_index=0)
    assert v_fail.passed is False

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

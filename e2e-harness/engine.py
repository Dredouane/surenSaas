"""E2E session runner for multi-step Telegram bot testing.

Orchestrates multi-turn conversations: sends user messages, clicks
inline buttons via send_callback, accumulates history, and calls the
LLM judge at each step.
"""

import logging
import uuid
from typing import Optional

from conftest import TgMockClient
from models import Scenario, Step, Verdict

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Helper: find button in replies (extracted for testability)
# ═══════════════════════════════════════════════════════════════════════════


def _find_button_in_replies(
    replies: list[dict],
    click_button_text: str,
) -> Optional[tuple[str, dict]]:
    """Search replies for a button whose text contains ``click_button_text``.

    Args:
        replies: List of message dicts from tg-mock getUpdates.
        click_button_text: Substring to match against button text (case-insensitive).

    Returns:
        Tuple of (callback_data, message_dict) if found, else None.
    """
    for msg in replies:
        reply_markup = msg.get("reply_markup") or {}
        inline_keyboard = reply_markup.get("inline_keyboard") or []
        for row in inline_keyboard:
            for btn in row:
                btn_text = btn.get("text", "")
                if click_button_text.lower() in btn_text.lower():
                    return (btn.get("callback_data"), msg)
    return None


# ═══════════════════════════════════════════════════════════════════════════
# SessionRunner
# ═══════════════════════════════════════════════════════════════════════════


class SessionRunner:
    """Orchestrates a multi-step E2E test session.

    Maintains a consistent ``thread_id`` across all steps so the backend
    sees a single conversation. Accumulates ``history`` of all user messages
    and bot replies. Calls the LLM judge after each step.

    Usage::

        runner = SessionRunner(tg_mock_client)
        scenario = load_scenario("tests/scenarios/my_scenario.yaml")
        results = runner.run_scenario(scenario)
    """

    def __init__(
        self,
        mock_client: TgMockClient,
        thread_id: Optional[str] = None,
    ):
        self.mock_client = mock_client
        self.thread_id = thread_id or f"test-thread-{uuid.uuid4().hex[:12]}"
        self.history: list[dict] = []

    # ── Public API ────────────────────────────────────────────────────

    def run_scenario(self, scenario: Scenario) -> list[Verdict]:
        """Execute all steps of a scenario and return verdicts.

        Args:
            scenario: The multi-step scenario to execute.

        Returns:
            List of ``Verdict`` objects, one per step.
        """
        logger.info(
            "🚀 Running scenario [%s]: %s (%d steps)",
            scenario.test_case,
            scenario.description,
            len(scenario.steps),
        )

        verdicts: list[Verdict] = []
        for i, step in enumerate(scenario.steps):
            logger.info("Step %d/%d: type=%s content=%s", i + 1, len(scenario.steps), step.type, step.content[:60])

            # Execute the step
            verdict = self.run_step(step, step_index=i)
            verdicts.append(verdict)

            # Check if expected verdict matches
            expected_pass = step.expected_verdict == "pass"
            if expected_pass:
                if not verdict.passed:
                    logger.warning(
                        "Step %d FAILED (expected pass): score=%d reason=%s",
                        i, verdict.score, verdict.reason,
                    )
                else:
                    logger.info("Step %d PASSED ✓", i)
            else:
                if verdict.passed:
                    logger.warning(
                        "Step %d PASSED (expected fail): score=%d reason=%s",
                        i, verdict.score, verdict.reason,
                    )
                else:
                    logger.info("Step %d correctly FAILED ✓ (expected fail)", i)

        return verdicts

    def run_step(self, step: Step, step_index: int = 0) -> Verdict:
        """Execute a single step and evaluate the bot's response.

        After injecting the user message via send_*(), polls tg-mock's
        getUpdates to capture the bot's reply asynchronously. All messages
        collected in a short window are concatenated for the Judge.

        Args:
            step: The step definition (type, content, judge_prompt).
            step_index: Index of this step in the scenario (for reporting).

        Returns:
            A ``Verdict`` with the judge's evaluation.
        """
        # Execute the action — the send_* method snapshots update_id first
        if step.type == "text":
            result = self.mock_client.send_text(
                step.content,
                thread_id=self.thread_id,
            )
        elif step.type == "callback":
            result = self.mock_client.send_callback(
                step.content,
                thread_id=self.thread_id,
            )
        elif step.type == "document":
            result = self.mock_client.send_document(
                step.content,
                caption=step.caption,
                thread_id=self.thread_id,
            )
        elif step.type == "photo":
            result = self.mock_client.send_photo(
                step.content,
                caption=step.caption,
                thread_id=self.thread_id,
            )
        else:
            raise ValueError(f"Unsupported step type: {step.type}")

        # Poll tg-mock for the bot's reply (asynchronous)
        bot_messages = self.mock_client.wait_for_reply(
            expected_count=1,
            timeout=30.0,
            poll_interval=0.3,
        )
        # Concatenate all message texts for the judge
        bot_reply_parts = []
        for msg in bot_messages:
            text = msg.get("text") or msg.get("caption") or ""
            if text:
                bot_reply_parts.append(text)
        bot_reply_text = "\n".join(bot_reply_parts)

        # Accumulate user message to history
        self.history.append({
            "role": "user",
            "step_index": step_index,
            "type": step.type,
            "content": step.content,
        })

        # Accumulate bot reply to history
        self.history.append({
            "role": "assistant",
            "step_index": step_index,
            "content": bot_reply_text,
        })

        logger.info("🤖 Bot reply (%d messages): %s", len(bot_messages), bot_reply_text[:200])

        # If no judge prompt, skip judgement (pass by default)
        if not step.judge_prompt:
            return Verdict(score=1, reason="No judge prompt — auto-pass", step_index=step_index)

        # Build conversation history text for the judge
        conversation_text = self._format_conversation_for_judge()

        # Evaluate the bot reply with the judge
        from judge import judge_step

        verdict_obj = judge_step(
            scenario_prompt=step.judge_prompt,
            bot_reply=bot_reply_text,
            conversation_history=conversation_text,
            step_index=step_index,
        )

        return verdict_obj

    def _format_conversation_for_judge(self) -> str:
        """Format accumulated history as text for the judge prompt."""
        lines = []
        for msg in self.history:
            role = msg.get("role", "unknown")
            content = str(msg.get("content", ""))
            if content:
                prefix = "Utilisateur:" if role == "user" else "Bot:"
                lines.append(f"{prefix} {content}")
        return "\n".join(lines)

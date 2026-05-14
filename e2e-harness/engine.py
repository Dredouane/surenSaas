"""E2E session runner for multi-step Telegram bot testing.

Orchestrates multi-turn conversations: sends user messages, clicks
inline buttons via send_callback, accumulates history, calls the
LLM judge at each step, and generates a Markdown report.
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from conftest import TgMockClient
from models import Scenario, Step, Verdict

logger = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).resolve().parent / "logs"


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
        self._last_bot_messages: list[dict] = []

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
        try:
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
        finally:
            # Generate report même en cas d'exception
            report_path = self.save_report(scenario, verdicts)
            logger.info("📝 Report saved: %s", report_path)

        return verdicts

    def save_report(self, scenario: Scenario, verdicts: list[Verdict]) -> Path:
        """Generate a horodated Markdown report for this scenario run.

        Writes to ``logs/YYYYMMDD_HHMMSS/{test_case}_report.md``.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = REPORTS_DIR / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)
        filename = run_dir / f"{scenario.test_case.lower()}_report.md"

        lines = [
            f"# Rapport E2E — {scenario.test_case}",
            f"**Date :** {datetime.now().isoformat()}",
            f"**Description :** {scenario.description}",
            "",
            "---",
            "",
            "## Transcription",
            "",
        ]

        for msg in self.history:
            role = msg.get("role", "unknown")
            content = str(msg.get("content", ""))
            prefix = "👤 **Utilisateur**" if role == "user" else "🤖 **Bot**"
            lines.append(f"### {prefix}")
            lines.append("")
            lines.append(content)
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("## Verdicts")
        lines.append("")

        for v in verdicts:
            step = scenario.steps[v.step_index]
            status_icon = "✅" if v.passed else "❌"
            status_text = "PASS" if v.passed else "FAIL"
            lines.append(f"### Step {v.step_index} — `{step.type}` : {status_icon} {status_text}")
            lines.append("")
            lines.append(f"**Attendu :** `{step.expected_verdict}`")
            lines.append("")
            lines.append(f"**Raison du Juge :** {v.reason}")
            lines.append("")

        lines.append("---")
        all_pass = all(v.passed for v in verdicts)
        final_icon = "✅" if all_pass else "❌"
        final_text = "TOUS VERTS" if all_pass else "ÉCHEC(S)"
        lines.append(f"## Résultat final : {final_icon} {final_text}")

        content = "\n".join(lines)
        filename.write_text(content, encoding="utf-8")
        return filename

    def run_step(self, step: Step, step_index: int = 0) -> Verdict:
        """Execute a single step and evaluate the bot's response.

        Supports two response modes:
        - ``sync`` (défaut pour text/doc/photo) : lit ``reply_text``
          directement depuis la réponse HTTP du webhook.
        - ``async`` (défaut pour callback) : poll tg-mock via
          ``wait_for_reply()``.

        Le mode peut être forcé via ``step.mode`` dans le YAML.

        Args:
            step: The step definition (type, content, judge_prompt).
            step_index: Index of this step in the scenario (for reporting).

        Returns:
            A ``Verdict`` with the judge's evaluation.
        """
        # Déterminer le mode de récupération
        step_mode = getattr(step, 'mode', None) or ("async" if step.type == "callback" else "sync")

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
                _last_replies=self._last_bot_messages,
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

        # Récupérer la réponse du bot selon le mode
        if step_mode == "sync":
            # Mode synchrone : lire reply_text + reply_markup depuis la
            # réponse HTTP du webhook, et construire un message factice
            # pour que send_callback puisse cliquer sur les boutons
            bot_reply_text = ""
            bot_messages = []
            if isinstance(result, dict):
                bot_reply_text = result.get("reply_text") or ""
                reply_markup_raw = result.get("reply_markup")
                if reply_markup_raw:
                    # Passer les boutons dans le message factice
                    import json as _json
                    try:
                        markup = _json.loads(reply_markup_raw) if isinstance(reply_markup_raw, str) else reply_markup_raw
                        bot_messages = [{"text": bot_reply_text, "reply_markup": markup}]
                    except Exception:
                        bot_messages = [{"text": bot_reply_text}]
                else:
                    bot_messages = [{"text": bot_reply_text}] if bot_reply_text else []
        else:
            # Mode asynchrone : poll tg-mock (callback)
            bot_messages = self.mock_client.wait_for_reply(
                expected_count=1,
                timeout=30.0,
                poll_interval=0.3,
            )
            # Concatenate all message texts
            bot_reply_parts = []
            for msg in bot_messages:
                text = msg.get("text") or msg.get("caption") or ""
                if text:
                    bot_reply_parts.append(text)
            bot_reply_text = "\n".join(bot_reply_parts)

        # Stocker pour send_callback (step suivant)
        self._last_bot_messages = bot_messages

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

        # Extraire les boutons du reply_markup pour les passer au Judge
        bot_actions = ""
        if bot_messages:
            import json as _json
            for msg in bot_messages:
                rp = msg.get("reply_markup") or {}
                kb = rp.get("inline_keyboard") or []
                for row in kb:
                    for btn in row:
                        txt = btn.get("text", "")
                        cbd = btn.get("callback_data", "")
                        bot_actions += f"  - [{txt}] (callback: {cbd})\n"
            if bot_actions:
                bot_actions = bot_actions.strip()

        # Evaluate the bot reply with the judge
        from judge import judge_step

        verdict_obj = judge_step(
            scenario_prompt=step.judge_prompt,
            bot_reply=bot_reply_text,
            conversation_history=conversation_text,
            step_index=step_index,
            bot_actions=bot_actions,
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

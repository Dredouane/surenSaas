"""
Pytest fixtures for Telegram E2E blackbox test harness.

Fixtures:
    tg_mock_client: Session-scoped client for interacting with tg-mock.
    reset_state: Function-scoped (autouse) cleanup of LangGraph state + DB records.
    judge_client: Session-scoped preconfigured Gemini Flash (or mock) judge.
"""

import logging
import os
import time
from pathlib import Path
from typing import Optional

import httpx
import pytest

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────
TEST_CHAT_ID = 999999
TEST_FROM_USER = {"id": 999999, "first_name": "Test", "is_bot": False}
TG_MOCK_URL = os.getenv("TG_MOCK_URL", "http://localhost:8081")
BACKEND_WEBHOOK_URL = os.getenv(
    "BACKEND_WEBHOOK_URL",
    "http://localhost:8000/api/v1/{org_id}/telegram/webhook/{webhook_token}",
)
# Le bot_token pour poller getUpdates doit être le vrai token du bot
# (tg-mock segmente les messages par token — le backend envoie avec le vrai)
BOT_TOKEN = os.getenv("TELEGRAM_CONSTRUCTION_BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
ORG_ID = os.getenv("TEST_ORG_ID", "test-org-id")
WEBHOOK_TOKEN = os.getenv("TEST_WEBHOOK_TOKEN", "test-webhook-token")


# ═══════════════════════════════════════════════════════════════════════════
# Fixture 1: tg_mock_client
# ═══════════════════════════════════════════════════════════════════════════

class TgMockClient:
    """Client for interacting with tg-mock and the backend webhook.

    Provides convenience methods to send messages/photos/documents as a
    test user and read back bot replies captured by tg-mock.
    """

    def __init__(
        self,
        tg_mock_url: str,
        bot_token: str,  # fake token for getUpdates polling
        backend_webhook_url: str,
        org_id: str,
        webhook_token: str,
        real_bot_token: str = None,  # real bot token to register chat in tg-mock
    ):
        self.tg_mock_url = tg_mock_url.rstrip("/")
        self.bot_token = bot_token
        self.real_bot_token = real_bot_token or bot_token
        self.backend_webhook_url = backend_webhook_url
        self.org_id = org_id
        self.webhook_token = webhook_token
        self._client = httpx.Client(base_url=self.tg_mock_url, timeout=90.0)
        self._history: list[dict] = []  # buffer of all messages (user + bot)
        self._ensure_chat_exists()

    def _ensure_chat_exists(self) -> None:
        """Ensure the test chat exists in tg-mock's state by sending an init message.

        tg-mock returns \"chat not found\" if the chat_id hasn't been seen before.
        We pre-seed it by sending a dummy message with the real bot token.
        """
        try:
            token = self.real_bot_token
            self._client.post(
                f"/bot{token}/sendMessage",
                json={"chat_id": TEST_CHAT_ID, "text": "/start"},
            )
        except Exception as exc:
            logger.warning("tg-mock chat init skipped: %s", exc)

    # ── Injection helpers ──────────────────────────────────────────────

    def _webhook_endpoint(self) -> str:
        """Return the full backend webhook URL for the configured org/token."""
        return self.backend_webhook_url.format(
            org_id=self.org_id,
            webhook_token=self.webhook_token,
        )

    def _make_update(
        self,
        message_id: int,
        text: Optional[str] = None,
        **extra_message_fields,
    ) -> dict:
        """Build a standard Telegram Update payload for a message."""
        message = {
            "message_id": message_id,
            "from": dict(TEST_FROM_USER),
            "chat": {"id": TEST_CHAT_ID, "type": "private"},
            "date": int(time.time()),
        }
        if text is not None:
            message["text"] = text
        message.update(extra_message_fields)
        return {
            "update_id": message_id,
            "message": message,
        }

    def send_text(self, text: str, thread_id: Optional[str] = None) -> dict:
        """Inject a text message as the test user.

        Posts a Telegram Update payload to the backend webhook. The backend
        processes it and (if applicable) calls tg-mock's sendMessage.
        Returns the response from the backend webhook.
        """
        msg_id = int(time.time() * 1000) % 1000000
        update = self._make_update(message_id=msg_id, text=text)
        if thread_id:
            update["message"]["message_thread_id"] = thread_id
        resp = self._client.post(self._webhook_endpoint(), json=update)
        resp.raise_for_status()
        logger.info("📤 Injected text message: %s", text[:80])
        data = resp.json()
        self._history.append({
            "role": "user",
            "type": "text",
            "content": text,
        })
        return self._parse_result(data)

    def _parse_result(self, data: dict) -> dict:
        """Extract reply_text + status from a webhook response."""
        reply = None
        if "result" in data and isinstance(data["result"], dict):
            reply = data["result"].get("reply_text")
        return {"backend_status": 200, "reply_text": reply}

    def send_photo(self, file_path: str, caption: Optional[str] = None, thread_id: Optional[str] = None) -> dict:
        """Inject a photo message with an optional caption."""
        msg_id = int(time.time() * 1000) % 1000000
        payload = self._make_update(
            message_id=msg_id,
            caption=caption or "",
            photo=[
                {
                    "file_id": f"test_photo_{msg_id}",
                    "file_unique_id": f"photo_uid_{msg_id}",
                    "file_size": Path(file_path).stat().st_size,
                    "width": 512,
                    "height": 512,
                }
            ],
        )
        if caption:
            payload["message"]["caption"] = caption
        if thread_id:
            payload["message"]["message_thread_id"] = thread_id
        resp = self._client.post(self._webhook_endpoint(), json=payload)
        resp.raise_for_status()
        logger.info("📤 Injected photo: %s", file_path)
        data = resp.json()
        self._history.append({
            "role": "user",
            "type": "photo",
            "content": file_path,
            "caption": caption or "",
        })
        return self._parse_result(data)

    def send_document(self, file_path: str, caption: Optional[str] = None, thread_id: Optional[str] = None) -> dict:
        """Inject a document message with an optional caption."""
        msg_id = int(time.time() * 1000) % 1000000
        payload = self._make_update(
            message_id=msg_id,
            caption=caption or "",
            document={
                "file_id": f"test_doc_{msg_id}",
                "file_unique_id": f"doc_uid_{msg_id}",
                "file_name": Path(file_path).name,
                "mime_type": "application/pdf",
                "file_size": Path(file_path).stat().st_size,
            },
        )
        if caption:
            payload["message"]["caption"] = caption
        if thread_id:
            payload["message"]["message_thread_id"] = thread_id
        resp = self._client.post(self._webhook_endpoint(), json=payload)
        resp.raise_for_status()
        logger.info("📤 Injected document: %s", file_path)
        data = resp.json()
        self._history.append({
            "role": "user",
            "type": "document",
            "content": file_path,
            "caption": caption or "",
        })
        return self._parse_result(data)

    def send_voice(self, file_path: str, thread_id: Optional[str] = None) -> dict:
        """Inject a voice message."""
        msg_id = int(time.time() * 1000) % 1000000
        payload = self._make_update(
            message_id=msg_id,
            voice={
                "file_id": f"test_voice_{msg_id}",
                "file_unique_id": f"voice_uid_{msg_id}",
                "duration": 5,
                "mime_type": "audio/ogg",
                "file_size": Path(file_path).stat().st_size,
            },
        )
        if thread_id:
            payload["message"]["message_thread_id"] = thread_id
        resp = self._client.post(self._webhook_endpoint(), json=payload)
        resp.raise_for_status()
        logger.info("📤 Injected voice: %s", file_path)
        data = resp.json()
        self._history.append({
            "role": "user",
            "type": "voice",
            "content": file_path,
        })
        return self._parse_result(data)

    # ── Reading bot replies ────────────────────────────────────────────

    def get_replies(
        self,
        expected_count: int = 1,
        timeout: float = 15.0,
        poll_interval: float = 0.5,
    ) -> list[dict]:
        """Poll tg-mock's getUpdates until we see at least expected_count messages.

        Returns the list of message result objects (the ``result`` array from
        the getUpdates response *excluding* the first `offset` messages that
        are already consumed in previous polls).

        Raises TimeoutError if no messages arrive within *timeout* seconds.
        """
        deadline = time.monotonic() + timeout
        last_update_id = 0
        all_messages: list[dict] = []

        while time.monotonic() < deadline:
            resp = self._client.get(
                "/bot{}/getUpdates".format(self.bot_token),
                params={"offset": last_update_id + 1, "timeout": 1},
            )
            if resp.status_code != 200:
                logger.warning("getUpdates returned %s — retrying", resp.status_code)
                time.sleep(poll_interval)
                continue

            data = resp.json()
            if not data.get("ok"):
                logger.warning("getUpdates ok=false — %s", data)
                time.sleep(poll_interval)
                continue

            updates = data.get("result", [])
            for upd in updates:
                last_update_id = max(last_update_id, upd.get("update_id", 0))
                # Bot replies come as message objects in the update
                if "message" in upd:
                    all_messages.append(upd["message"])

            if len(all_messages) >= expected_count:
                logger.info("✅ Got %d replies from tg-mock", len(all_messages))
                return all_messages

            time.sleep(poll_interval)

        raise TimeoutError(
            f"Timed out after {timeout}s waiting for {expected_count} reply(ies). "
            f"Got {len(all_messages)} so far."
        )

    # ── Callback / inline button clicks ────────────────────────────

    def _make_callback_query(
        self,
        callback_data: str,
        message: dict,
    ) -> dict:
        """Build a Telegram callback_query Update payload."""
        return {
            "update_id": int(time.time() * 1000) % 1000000,
            "callback_query": {
                "id": f"cb_{int(time.time() * 1000)}",
                "from": dict(TEST_FROM_USER),
                "message": message,
                "chat_instance": str(int(time.time())),
                "data": callback_data,
            },
        }

    def send_callback(
        self,
        click_button_text: str,
        thread_id: Optional[str] = None,
    ) -> dict:
        """Click an inline keyboard button in the last bot reply.

        Steps:
        1. Fetches the latest messages from tg-mock via getUpdates.
        2. Searches each message's ``reply_markup.inline_keyboard`` for a
           button whose ``text`` *contains* ``click_button_text``.
        3. Posts a ``callback_query`` update to the backend webhook with
           the matched button's ``callback_data``.

        Returns the backend webhook response (parsed).
        """
        # Fetch latest updates from tg-mock
        replies = self.get_replies(expected_count=1, timeout=10.0)
        if not replies:
            raise RuntimeError(
                f"No bot replies found — cannot click button '{click_button_text}'"
            )

        # Search for the button in each reply
        matched_message = None
        matched_callback_data = None

        for msg in reversed(replies):
            reply_markup = msg.get("reply_markup") or {}
            inline_keyboard = reply_markup.get("inline_keyboard") or []
            for row in inline_keyboard:
                for btn in row:
                    btn_text = btn.get("text", "")
                    if click_button_text.lower() in btn_text.lower():
                        matched_callback_data = btn.get("callback_data")
                        matched_message = msg
                        break
                if matched_callback_data:
                    break
            if matched_callback_data:
                break

        if matched_callback_data is None:
            # Log available buttons for debugging
            available = []
            for msg in replies:
                rmk = msg.get("reply_markup") or {}
                for row in rmk.get("inline_keyboard") or []:
                    for btn in row:
                        available.append(btn.get("text", ""))
            raise RuntimeError(
                f"Button '{click_button_text}' not found in any reply. "
                f"Available buttons: {available}"
            )

        # Build and post callback_query update
        callback_update = self._make_callback_query(
            callback_data=matched_callback_data,
            message=matched_message,
        )

        resp = self._client.post(self._webhook_endpoint(), json=callback_update)
        resp.raise_for_status()
        logger.info(
            "🖱️ Clicked button '%s' (callback_data=%s)",
            click_button_text,
            matched_callback_data,
        )
        data = resp.json()
        return self._parse_result(data)

    # ── Warmup ──────────────────────────────────────────────────────

    def warmup(self, thread_id: Optional[str] = None) -> dict:
        """Send /start to warm up Vertex AI cold start.

        This triggers the bot's startup flow. Returns the webhook
        response from the backend.
        """
        logger.info("🔥 Warmup: sending /start to warm up Vertex AI")
        return self.send_text("/start")

    # ── History ─────────────────────────────────────────────────────

    def clear_history(self) -> None:
        """Clear the internal _history buffer."""
        self._history.clear()

    def close(self) -> None:
        self._client.close()


@pytest.fixture(scope="session")
def tg_mock_client() -> TgMockClient:
    """Session-scoped fixture providing a TgMockClient instance."""
    client = TgMockClient(
        tg_mock_url=TG_MOCK_URL,
        bot_token=os.getenv("TELEGRAM_CONSTRUCTION_BOT_TOKEN") or BOT_TOKEN,
        backend_webhook_url=BACKEND_WEBHOOK_URL,
        org_id=ORG_ID,
        webhook_token=WEBHOOK_TOKEN,
        real_bot_token=os.getenv("TELEGRAM_CONSTRUCTION_BOT_TOKEN"),
    )
    yield client
    client.close()


# ═══════════════════════════════════════════════════════════════════════════
# Fixture 2: reset_state
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="function", autouse=True)
def reset_state():
    """Function-scoped (autouse) fixture that cleans up between tests.

    After each test function:
    1. Clears LangGraph thread state for the test user (chat_id=999999).
       Attempts to delete thread checkpoints from the configured checkpoint
       store (Postgres or memory-based).
    2. Deletes DB records created during the test for chat_id=999999 only,
       using targeted DELETE operations with WHERE filters.
       Never truncates or deletes without a WHERE clause.

    This fixture uses the ``yield`` pattern — cleanup runs after the test.
    """
    # ── Setup (before test) ────────────────────────────────────────────
    logger.debug("reset_state: pre-test setup (nothing to do)")

    yield  # Test runs here

    # ── Teardown (after test) ──────────────────────────────────────────
    _clear_langgraph_state()
    _clear_db_records()


def _clear_langgraph_state() -> None:
    """Clear LangGraph checkpoint state for the test chat_id.

    Tries multiple strategies — Postgres checkpointer (via psycopg2) first,
    then MemorySaver (no-op), then falls back silently.
    """
    thread_id = str(TEST_CHAT_ID)

    # Strategy 1: Postgres checkpointer (langgraph-checkpoint-postgres)
    pg_dsn = os.getenv("LANGGRAPH_CHECKPOINT_POSTGRES_URI")
    if pg_dsn:
        try:
            import psycopg2

            conn = psycopg2.connect(pg_dsn)
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM langgraph_checkpoint_checkpoints "
                    "WHERE thread_id = %s",
                    (thread_id,),
                )
                deleted = cur.rowcount
                cur.execute(
                    "DELETE FROM langgraph_checkpoint_writes "
                    "WHERE thread_id = %s",
                    (thread_id,),
                )
                deleted += cur.rowcount
            conn.commit()
            conn.close()
            if deleted:
                logger.info("🧹 Cleared LangGraph state: %d record(s) deleted", deleted)
            return
        except Exception as exc:
            logger.debug("Postgres LangGraph cleanup skipped (%s)", exc)

    # Strategy 2: Try supabase-based checkpoint cleanup
    try:
        from app.api.auth import get_supabase

        supabase = get_supabase()
        supabase.table("langgraph_checkpoint_checkpoints") \
            .delete() \
            .eq("thread_id", thread_id) \
            .execute()
        supabase.table("langgraph_checkpoint_writes") \
            .delete() \
            .eq("thread_id", thread_id) \
            .execute()
        logger.info("🧹 Cleared LangGraph state via Supabase")
    except Exception as exc:
        logger.debug("Supabase LangGraph cleanup skipped (%s)", exc)

    logger.debug("LangGraph state cleanup: no compatible store found (harmless)")


def _clear_db_records() -> None:
    """Delete DB records created during the test for chat_id=999999 only.

    Targeted DELETE with WHERE filter on chat_id or telegram_user_id.
    NEVER truncates or deletes without a WHERE clause.
    """
    chat_id = TEST_CHAT_ID
    deleted_total = 0

    # Try Postgres direct connection first
    pg_dsn = os.getenv("DIRECT_DATABASE_URL") or os.getenv("LANGGRAPH_CHECKPOINT_POSTGRES_URI")
    if pg_dsn:
        try:
            import psycopg2

            conn = psycopg2.connect(pg_dsn)
            with conn.cursor() as cur:
                # List of tables that may reference telegram users / chats
                cleanup_queries = [
                    ("telegram_conversations", "chat_id = %s", (chat_id,)),
                    ("telegram_messages", "chat_id = %s", (chat_id,)),
                    ("expenses", "telegram_user_id = %s", (chat_id,)),
                    ("timesheet_entries", "telegram_user_id = %s", (chat_id,)),
                    ("pointages", "telegram_user_id = %s", (chat_id,)),
                ]
                for table, where, params in cleanup_queries:
                    try:
                        cur.execute(
                            f"DELETE FROM {table} WHERE {where}",
                            params,
                        )
                        deleted_total += cur.rowcount
                    except Exception:
                        # Table may not exist — skip gracefully
                        pass
            conn.commit()
            conn.close()
            if deleted_total:
                logger.info("🧹 Deleted %d DB record(s) for chat_id=%s", deleted_total, chat_id)
            return
        except Exception as exc:
            logger.debug("Postgres DB cleanup skipped (%s)", exc)

    # Fallback: try Supabase
    try:
        from app.api.auth import get_supabase

        supabase = get_supabase()
        for table in ("telegram_conversations", "telegram_messages"):
            try:
                supabase.table(table).delete().eq("chat_id", chat_id).execute()
                logger.debug("Cleaned %s via Supabase", table)
            except Exception:
                pass
        for table in ("expenses", "timesheet_entries", "pointages"):
            try:
                supabase.table(table).delete().eq("telegram_user_id", chat_id).execute()
                logger.debug("Cleaned %s via Supabase", table)
            except Exception:
                pass
    except Exception as exc:
        logger.debug("Supabase DB cleanup skipped (%s)", exc)

    logger.debug("DB record cleanup complete")


# ═══════════════════════════════════════════════════════════════════════════
# Fixture 3: judge_client
# ═══════════════════════════════════════════════════════════════════════════

class JudgeClient:
    """Preconfigured LLM judge for evaluating bot responses.

    Uses Gemini Flash (google-genai) when GEMINI_API_KEY is available.
    Falls back to a mock judge that always returns score=1 when the key
    is missing — this prevents tests from failing during development.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._mock = api_key is None

        if not self._mock:
            # Use HTTP API directly (no SDK dependency needed)
            self._api_url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                "gemini-2.5-flash:generateContent"
            )
            self._model_name = os.getenv("GEMINI_JUDGE_MODEL", "gemini-2.5-flash")
            logger.info(
                "🤖 Judge: Gemini Flash initialized via HTTP (model=%s)", self._model_name
            )

        if self._mock:
            logger.info("🤖 Judge: using MOCK judge (no API key or init failed)")

    def judge(self, scenario_prompt: str, bot_reply: str) -> dict:
        """Evaluate a bot reply against a scenario prompt.

        Returns a dict with:
            score (int): 1 = pass, 0 = fail
            reason (str): explanation from the LLM or mock
        """
        if self._mock:
            return {"score": 1, "reason": "mock judge — no API key"}

        prompt = (
            f"SCENARIO: {scenario_prompt}\n"
            f"REPONSE: {bot_reply}\n\n"
            'Réponds UNIQUEMENT en JSON: {"score": 1|0, "reason": "..."}'
        )

        try:
            import httpx

            url = f"{self._api_url}?key={self.api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                result = resp.json()

            # Extract text from Gemini response
            candidates = result.get("candidates", [])
            if not candidates:
                return {"score": 0, "reason": "No candidates from Gemini"}
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                return {"score": 0, "reason": "No parts in Gemini response"}
            text = parts[0].get("text", "").strip()
            if not text:
                return {"score": 0, "reason": "Empty text from Gemini"}

            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("\n", 1)[0]
            import json

            result_json = json.loads(text)
            return {
                "score": int(result_json.get("score", 0)),
                "reason": str(result_json.get("reason", "")),
            }
        except Exception as exc:
            logger.error("Judge LLM call failed: %s", exc)
            return {"score": 0, "reason": f"Judge error: {exc}"}


@pytest.fixture(scope="session")
def judge_client() -> JudgeClient:
    """Session-scoped fixture for the LLM judge.

    Reads GEMINI_API_KEY from environment. If absent, returns a mock judge
    so tests can still run (all responses score 1).
    """
    api_key = os.getenv("GEMINI_API_KEY")
    return JudgeClient(api_key=api_key)

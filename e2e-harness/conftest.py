"""
Pytest fixtures for Telegram E2E blackbox test harness (autonomous).

No imports from the backend — uses supabase-py directly.
The tg-mock (Docker aiogram/telegram-bot-api) runs on port 8081
and stores bot replies. The test injects messages via the backend
webhook and reads bot responses via tg-mock getUpdates or directly
from the webhook response.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import httpx
import pytest
from supabase import create_client

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────
TEST_CHAT_ID = 999999
TEST_FROM_USER = {"id": 999999, "first_name": "Test", "is_bot": False}
TG_MOCK_URL = os.getenv("TG_MOCK_URL", "http://localhost:8081")
# Webhook token used by the test bot in telegram_bots DB
WEBHOOK_TOKEN = os.getenv("E2E_WEBHOOK_TOKEN", "test-e2e-token")
# Telegram bot token for polling getUpdates from tg-mock
# Doit correspondre au token avec lequel le backend envoie les messages
# (SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN dans .bashrc)
BOT_TOKEN_FALLBACK = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
_raw_token = os.getenv("SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN") or os.getenv("TELEGRAM_CONSTRUCTION_BOT_TOKEN") or BOT_TOKEN_FALLBACK
BOT_TOKEN = _raw_token
TEST_ORG_SLUG = os.getenv("TEST_ORG_SLUG", "REDACTED_ORG_SLUG")


def _backend_base_url() -> str:
    """Retourne l'URL du backend (lue dynamiquement pour permettre
    le changement via variable d'env sans recharger le module)."""
    return os.getenv("BACKEND_BASE_URL", "http://localhost:8080")

# ── Supabase client (direct, no backend imports) ──────────────────────────

@pytest.fixture(scope="session")
def supabase():
    """Direct Supabase client, no backend dependency."""
    url = os.getenv("SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        pytest.skip("SUPABASE_URL and SUPABASE_SERVICE_KEY are required")
    return create_client(url, key)


@pytest.fixture(scope="session")
def org_id(supabase) -> str:
    """Resolve org_id from the test org slug."""
    result = supabase.table("organizations").select("id").eq("slug", TEST_ORG_SLUG).single().execute()
    if not result.data:
        pytest.skip(f"Organization {TEST_ORG_SLUG} not found in DB")
    return result.data["id"]


# ═══════════════════════════════════════════════════════════════════════════
# Fixture: bot_seed — ensure a test bot exists in telegram_bots
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def bot_seed(supabase, org_id) -> str:
    """Upsert a test bot in telegram_bots so the backend accepts webhooks.

    The backend looks up ``telegram_bots`` by ``org_id`` and a ``webhook_url``
    containing the ``webhook_token``. This fixture ensures such a row exists.
    """
    webhook_url = f"{_backend_base_url()}/api/v1/{org_id}/telegram/webhook/{WEBHOOK_TOKEN}"

    existing = (
        supabase.table("telegram_bots")
        .select("id")
        .eq("org_id", org_id)
        .eq("webhook_url", webhook_url)
        .execute()
    )

    bot_username = os.getenv("SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_USERNAME", "arev_travaux_test_e2e_bot")

    if existing.data:
        bot_id = existing.data[0]["id"]
        supabase.table("telegram_bots").update({"bot_username": bot_username}).eq("id", bot_id).execute()
        logger.info("Bot seed updated: id=%s username=%s", bot_id, bot_username)
        return bot_id
    bot_token = os.getenv("TELEGRAM_CONSTRUCTION_BOT_TOKEN", "123456:fake-e2e-test-token")
    import hashlib
    bot_token_hash = hashlib.sha256(bot_token.encode()).hexdigest()
    data = {
        "org_id": org_id,
        "bot_username": bot_username,
        "bot_token_hash": bot_token_hash,
        "bot_id": 999999,
        "webhook_url": webhook_url,
        "webhook_secret": None,
        "is_active": True,
        "description": "E2E test bot",
    }
    result = supabase.table("telegram_bots").insert(data).execute()
    bot_id = result.data[0]["id"]
    logger.info("Bot seed created: id=%s username=%s", bot_id, bot_username)
    return bot_id


# ═══════════════════════════════════════════════════════════════════════════
# Fixture: tg_mock_client
# ═══════════════════════════════════════════════════════════════════════════

class TgMockClient:
    """Client for interacting with tg-mock and the backend webhook.

    Injects messages as a test user via the backend webhook and reads
    bot replies either from the webhook response (for text/doc/photo)
    or from tg-mock's getUpdates (for callback scenarios).
    """

    def __init__(
        self,
        tg_mock_url: str,
        bot_token: str,
        backend_webhook_url: str,
        org_id: str,
        webhook_token: str,
        real_bot_token: Optional[str] = None,
        _http_client: Optional[httpx.Client] = None,
    ):
        self.tg_mock_url = tg_mock_url.rstrip("/")
        self.bot_token = bot_token
        self.real_bot_token = real_bot_token or bot_token
        self._org_id = org_id
        self._webhook_token = webhook_token
        self._backend_base = backend_webhook_url.rstrip("/")
        self._client = _http_client or httpx.Client(base_url=self.tg_mock_url, timeout=90.0)
        self._history: list[dict] = []
        self._last_update_id = 0

    # ── Webhook endpoint ──────────────────────────────────────────────

    def _webhook_endpoint(self) -> str:
        return (
            f"{self._backend_base}/api/v1/{self._org_id}"
            f"/telegram/webhook/{self._webhook_token}"
        )

    # ── Update builders ───────────────────────────────────────────────

    def _make_update(self, message_id: int, text: Optional[str] = None, **extra) -> dict:
        message = {
            "message_id": message_id,
            "from": dict(TEST_FROM_USER),
            "chat": {"id": TEST_CHAT_ID, "type": "private"},
            "date": int(time.time()),
        }
        if text is not None:
            message["text"] = text
        message.update(extra)
        return {"update_id": message_id, "message": message}

    def _make_callback_query(self, callback_data: str, message: dict) -> dict:
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

    # ── Injection ─────────────────────────────────────────────────────

    def _post_webhook(self, update: dict) -> dict:
        resp = self._client.post(self._webhook_endpoint(), json=update)
        if resp.status_code == 404:
            logger.warning("Webhook 404 — bot_seed missing or backend not ready")
        resp.raise_for_status()
        return resp.json()

    def _parse_result(self, data: dict) -> dict:
        reply = None
        reply_markup = None
        # Format 1: {"status": "agentic_success", "result": {"reply_text": "..."}}
        if "result" in data and isinstance(data["result"], dict):
            reply = data["result"].get("reply_text")
            reply_markup = data["result"].get("reply_markup")
        # Format 2: le result est un dict avec reply_text directement
        if reply is None and "reply_text" in data:
            reply = data["reply_text"]
            reply_markup = data.get("reply_markup")
        # Format 3: le result n'a pas de reply_text mais a une structure JSON — le sérialiser
        if reply is None and "result" in data:
            res = data["result"]
            if isinstance(res, dict):
                reply = res.get("reply_text") or res.get("message") or res.get("text") or json.dumps(res, ensure_ascii=False, default=str)
                reply_markup = res.get("reply_markup") or reply_markup
            elif isinstance(res, str):
                reply = res
        return {"backend_status": 200, "reply_text": reply, "reply_markup": reply_markup}

    def send_text(self, text: str, thread_id: Optional[str] = None) -> dict:
        self._snapshot_updates()
        msg_id = int(time.time() * 1000) % 1000000
        update = self._make_update(message_id=msg_id, text=text)
        if thread_id:
            update["message"]["message_thread_id"] = thread_id
        data = self._post_webhook(update)
        self._history.append({"role": "user", "type": "text", "content": text})
        logger.info("📤 Injected text: %s", text[:80])
        return self._parse_result(data)

    def send_photo(self, file_path: str, caption: Optional[str] = None, thread_id: Optional[str] = None) -> dict:
        self._snapshot_updates()
        msg_id = int(time.time() * 1000) % 1000000
        payload = self._make_update(
            message_id=msg_id,
            caption=caption or "",
            photo=[{"file_id": f"test_photo_{msg_id}", "file_unique_id": f"uid_{msg_id}",
                     "file_size": Path(file_path).stat().st_size, "width": 512, "height": 512}],
        )
        if caption:
            payload["message"]["caption"] = caption
        if thread_id:
            payload["message"]["message_thread_id"] = thread_id
        data = self._post_webhook(payload)
        self._history.append({"role": "user", "type": "photo", "content": file_path, "caption": caption or ""})
        logger.info("📤 Injected photo: %s", file_path)
        return self._parse_result(data)

    def send_document(self, file_path: str, caption: Optional[str] = None, thread_id: Optional[str] = None) -> dict:
        self._snapshot_updates()
        msg_id = int(time.time() * 1000) % 1000000
        payload = self._make_update(
            message_id=msg_id,
            caption=caption or "",
            document={"file_id": f"test_doc_{msg_id}", "file_unique_id": f"uid_{msg_id}",
                       "file_name": Path(file_path).name, "mime_type": "application/pdf",
                       "file_size": Path(file_path).stat().st_size},
        )
        if caption:
            payload["message"]["caption"] = caption
        if thread_id:
            payload["message"]["message_thread_id"] = thread_id
        data = self._post_webhook(payload)
        self._history.append({"role": "user", "type": "document", "content": file_path, "caption": caption or ""})
        logger.info("📤 Injected document: %s", file_path)
        return self._parse_result(data)

    # ── Snapshot + wait_for_reply (polling asynchrone sur getUpdates) ──

    def _snapshot_updates(self) -> int:
        """Record the current max update_id from tg-mock.

        Call this BEFORE injecting a user message, so ``wait_for_reply``
        can later ignore messages that were already present.
        """
        updates_url = f"{self.tg_mock_url}/bot{self.bot_token}/getUpdates"
        resp = self._client.get(
            updates_url,
            params={"offset": 0, "timeout": 1},
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok"):
                for upd in data.get("result", []):
                    uid = upd.get("update_id", 0)
                    if uid > self._last_update_id:
                        self._last_update_id = uid
        return self._last_update_id

    def wait_for_reply(
        self,
        expected_count: int = 1,
        timeout: float = 30.0,
        poll_interval: float = 0.3,
    ) -> list[dict]:
        """Poll tg-mock's getUpdates until *expected_count* new messages arrive.

        Uses ``self._last_update_id`` as the lower bound — only messages
        with a strictly higher ``update_id`` are collected. This implements
        the "sliding window" semantic of Telegram's getUpdates.

        After the expected count is reached, keeps polling for a short
        grace window (``poll_interval * 3``) to catch any trailing messages
        (e.g. a menu button that arrives milliseconds after a text reply).

        Returns the list of message dicts collected (never raises).
        """
        updates_url = f"{self.tg_mock_url}/bot{self.bot_token}/getUpdates"
        logger.info(
            "wait_for_reply: polling %s (expected=%d, timeout=%.1fs, interval=%.1fs)",
            updates_url, expected_count, timeout, poll_interval,
        )

        # Utilise self._last_update_id comme borne inférieure (déjà snapshoté
        # par send_text / send_callback avant l'injection du message utilisateur).
        # Ne PAS refaire un snapshot ici — cela consommerait la réponse du bot
        # avant que le polling ne commence.
        before = self._last_update_id

        deadline = time.monotonic() + timeout
        collected: list[dict] = []
        grace_remaining = 3

        while time.monotonic() < deadline:
            updates_url = f"{self.tg_mock_url}/bot{self.bot_token}/getUpdates"
            resp = self._client.get(
                updates_url,
                params={"offset": before, "timeout": 1},
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("ok"):
                    for upd in data.get("result", []):
                        uid = upd.get("update_id", 0)
                        if uid > before and "message" in upd:
                            collected.append(upd["message"])
                            if uid > self._last_update_id:
                                self._last_update_id = uid
                        if uid > before:
                            before = uid

            if len(collected) >= expected_count:
                grace_remaining -= 1
                if grace_remaining <= 0:
                    logger.info(
                        "wait_for_reply: got %d/%d messages after grace window",
                        len(collected), expected_count,
                    )
                    return collected

            time.sleep(poll_interval)

        logger.warning(
            "wait_for_reply timeout after %ss — got %d/%d messages (last_update_id=%d)",
            timeout, len(collected), expected_count, self._last_update_id,
        )
        return collected  # partial results instead of raising

    # ── Callback ──────────────────────────────────────────────────────

    def send_callback(self, click_button_text: str, thread_id: Optional[str] = None, _last_replies: list = None) -> dict:
        replies = _last_replies if _last_replies else self.wait_for_reply(expected_count=1, timeout=15.0)
        if not replies:
            raise RuntimeError(f"No bot replies — cannot click '{click_button_text}'")

        matched = None
        matched_data = None
        for msg in reversed(replies):
            keyboard = msg.get("reply_markup") or {}
            for row in keyboard.get("inline_keyboard") or []:
                for btn in row:
                    if click_button_text.lower() in btn.get("text", "").lower():
                        matched = msg
                        matched_data = btn.get("callback_data")
                        break
                if matched_data:
                    break
            if matched_data:
                break

        if matched_data is None:
            raise RuntimeError(f"Button '{click_button_text}' not found in replies")

        callback_update = self._make_callback_query(matched_data, matched)
        data = self._post_webhook(callback_update)
        logger.info("🖱️ Clicked '%s' (data=%s)", click_button_text, matched_data)
        return self._parse_result(data)

    # ── Warmup ────────────────────────────────────────────────────────

    def warmup(self, thread_id: Optional[str] = None) -> dict:
        logger.info("🔥 Warmup: /start")
        return self.send_text("/start")

    # ── Lifecycle ─────────────────────────────────────────────────────

    def clear_history(self) -> None:
        self._history.clear()

    def close(self) -> None:
        self._client.close()


@pytest.fixture(scope="function", autouse=True)
def reset_mock_telegram(tg_mock_client):
    """Vide le buffer du mock Telegram ET le compteur client entre chaque test."""
    import httpx
    try:
        httpx.post(f"{TG_MOCK_URL}/debug/reset", timeout=2.0)
    except Exception:
        pass  # mock peut ne pas être accessible (tests unitaires)
    tg_mock_client._last_update_id = 0
    yield


@pytest.fixture(scope="session")
def tg_mock_client(bot_seed, org_id) -> TgMockClient:
    client = TgMockClient(
        tg_mock_url=TG_MOCK_URL,
        bot_token=BOT_TOKEN,
        backend_webhook_url=_backend_base_url(),
        org_id=org_id,
        webhook_token=WEBHOOK_TOKEN,
        real_bot_token=os.getenv("TELEGRAM_CONSTRUCTION_BOT_TOKEN"),
    )
    yield client
    client.close()


# ═══════════════════════════════════════════════════════════════════════════
# Fixture: judge_client
# ═══════════════════════════════════════════════════════════════════════════

class JudgeClient:
    """LLM judge using Gemini HTTP API directly (no backend dependency).

    Requires GEMINI_API_KEY to be set. Raises explicitly if missing —
    no mock fallback.
    """

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is required for the E2E judge. "
                "Set it in ~/.bashrc or .env.test.local"
            )
        self._api_url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-2.5-flash:generateContent"
        )
        self._model = os.getenv("GEMINI_JUDGE_MODEL", "gemini-2.5-flash")
        logger.info("🤖 Judge: Gemini %s via HTTP API", self._model)

    def judge(self, scenario_prompt: str, bot_reply: str) -> dict:
        prompt = (
            f"SCENARIO: {scenario_prompt}\n"
            f"REPONSE: {bot_reply}\n\n"
            'Réponds UNIQUEMENT en JSON: {"score": 1|0, "reason": "..."}'
        )
        try:
            url = f"{self._api_url}?key={self.api_key}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                result = resp.json()

            candidates = result.get("candidates", [])
            if not candidates:
                return {"score": 0, "reason": "No candidates from Gemini"}
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                return {"score": 0, "reason": "No parts in Gemini response"}
            text = parts[0].get("text", "").strip()
            if not text:
                return {"score": 0, "reason": "Empty text from Gemini"}
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("\n", 1)[0]

            import json
            result_json = json.loads(text)
            return {"score": int(result_json.get("score", 0)), "reason": str(result_json.get("reason", ""))}
        except Exception as exc:
            logger.error("Judge LLM call failed: %s", exc)
            return {"score": 0, "reason": f"Judge error: {exc}"}


@pytest.fixture(scope="session")
def judge_client() -> JudgeClient:
    return JudgeClient()

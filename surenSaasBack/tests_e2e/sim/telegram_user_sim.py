import os
import re
import asyncio
import json
from pathlib import Path
from typing import Optional

import httpx


class TelegramUserSim:
    def __init__(self, bot_token: str, api_url: str = "http://localhost:8081"):
        self.bot_token = bot_token
        self.api_url = api_url
        self._base_url = f"{api_url}/bot{bot_token}"
        self._client = httpx.AsyncClient(timeout=30.0)
        self._last_response: Optional[dict] = None
        self._response_event = asyncio.Event()
        self._bot_username: Optional[str] = None
        self._updates_offset = 0

    async def start(self):
        me = await self._api_call("getMe")
        self._bot_username = me["username"]
        print(f"   🤖 Connected to bot: @{self._bot_username}")

    async def stop(self):
        await self._client.aclose()

    async def send_text(self, msg: str) -> dict:
        self._response_event.clear()
        me = await self._api_call("getMe")
        chat_id = me["id"]
        return await self._api_call("sendMessage", json={
            "chat_id": chat_id,
            "text": msg,
        })

    async def click_button(self, label: str) -> dict:
        self._response_event.clear()
        raise NotImplementedError("click_button requires a real Telegram user session")

    async def upload_file(self, path: str | Path) -> dict:
        self._response_event.clear()
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Fixture file not found: {path}")

        me = await self._api_call("getMe")
        chat_id = me["id"]

        mime = self._guess_mime(path)
        files = {"document": (path.name, path.read_bytes(), mime)}
        url = f"{self._base_url}/sendDocument"
        resp = await self._client.post(url, data={"chat_id": chat_id}, files=files)
        resp.raise_for_status()
        data = resp.json()
        assert data.get("ok"), f"sendDocument failed: {data}"
        return data["result"]

    async def send_voice(self, path: str | Path) -> dict:
        self._response_event.clear()
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Fixture file not found: {path}")

        me = await self._api_call("getMe")
        chat_id = me["id"]

        mime = self._guess_mime(path)
        files = {"voice": (path.name, path.read_bytes(), mime)}
        url = f"{self._base_url}/sendVoice"
        resp = await self._client.post(url, data={"chat_id": chat_id}, files=files)
        resp.raise_for_status()
        data = resp.json()
        assert data.get("ok"), f"sendVoice failed: {data}"
        return data["result"]

    async def wait_for_bot_response(self, timeout: int = 10) -> dict:
        me = await self._api_call("getMe")
        chat_id = me["id"]
        deadline = asyncio.get_event_loop().time() + timeout

        while asyncio.get_event_loop().time() < deadline:
            updates = await self._api_call("getUpdates", json={
                "offset": self._updates_offset,
                "timeout": 5,
                "allowed_updates": ["message", "callback_query"],
            })
            for update in updates:
                self._updates_offset = update["update_id"] + 1
                msg = update.get("message") or update.get("callback_query", {}).get("message")
                if msg and msg.get("chat", {}).get("id") == chat_id:
                    self._last_response = msg
                    return msg
            await asyncio.sleep(0.5)

        raise TimeoutError(f"Bot did not respond within {timeout}s")

    def assert_response_matches(self, pattern: str, timeout: int = 10) -> dict:
        msg = asyncio.run(self.wait_for_bot_response(timeout=timeout))
        text = msg.get("text") or ""
        assert re.search(pattern, text, re.IGNORECASE), (
            f"Bot response '{text}' does not match pattern '{pattern}'"
        )
        return msg

    async def _api_call(self, method: str, json: Optional[dict] = None) -> any:
        url = f"{self._base_url}/{method}"
        if json:
            resp = await self._client.post(url, json=json)
        else:
            resp = await self._client.get(url)
        resp.raise_for_status()
        data = resp.json()
        assert data.get("ok"), f"API call {method} failed: {data}"
        return data["result"]

    def _guess_mime(self, path: Path) -> str:
        ext = path.suffix.lower()
        return {
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }.get(ext, "application/octet-stream")

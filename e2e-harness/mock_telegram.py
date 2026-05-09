"""
mock_telegram.py — Simulateur Telegram pour tests E2E.

Remplace Docker aiogram/telegram-bot-api.
Stocke les messages en mémoire, accepète tous les chat_id,
répond instantanément. Idéal pour les tests blackbox.

Endpoints :
  GET  /bot{token}/getMe
  POST /bot{token}/sendMessage     (JSON body)
  POST /bot{token}/sendDocument    (multipart)
  GET  /bot{token}/getUpdates      (?offset=N)
  GET  /bot{token}/getChat         (?chat_id=N)
  POST /debug/reset
  GET  /health
"""

import time
import uuid as _uuid
from typing import Optional

import uvicorn
from fastapi import FastAPI, Form, UploadFile, File
from pydantic import BaseModel

app = FastAPI(title="mock-telegram")

# ── Stockage en mémoire ─────────────────────────────────────────────────────
MESSAGES: list[dict] = []
UPDATE_COUNTER: int = 0

# ── Réponse getMe (bot factice) ────────────────────────────────────────────
BOT_ID = 12345678
BOT_USERNAME = "SurenTestBot"
GETME_RESPONSE = {
    "ok": True,
    "result": {
        "id": BOT_ID,
        "is_bot": True,
        "first_name": "SurenE2E",
        "username": BOT_USERNAME,
        "can_join_groups": True,
        "can_read_all_group_messages": False,
        "supports_inline_queries": False,
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _next_update_id() -> int:
    global UPDATE_COUNTER
    UPDATE_COUNTER += 1
    return UPDATE_COUNTER


def _store_message(chat_id: int, text: str, reply_markup: Optional[dict] = None, **extra) -> dict:
    update_id = _next_update_id()
    msg = {
        "message_id": update_id,
        "date": int(time.time()),
        "text": text,
        "chat": {"id": chat_id, "type": "private"},
        "from": dict(GETME_RESPONSE["result"]),
    }
    if reply_markup:
        msg["reply_markup"] = reply_markup
    msg.update(extra)
    entry = {"update_id": update_id, "message": msg}
    MESSAGES.append(entry)
    return msg


# ═══════════════════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/bot{token}/getMe")
async def get_me(token: str):
    return GETME_RESPONSE


@app.post("/bot{token}/sendMessage")
async def send_message(token: str, body: dict):
    chat_id = body.get("chat_id", 0)
    text = body.get("text", "")
    reply_markup = body.get("reply_markup")
    msg = _store_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
    )
    return {"ok": True, "result": msg}


@app.post("/bot{token}/sendDocument")
async def send_document(
    token: str,
    chat_id: int = Form(...),
    document: UploadFile = File(None),
    caption: str = Form(""),
):
    msg = _store_message(
        chat_id=chat_id,
        text=caption,
        document={"file_name": document.filename if document else "unknown", "file_size": 0},
    )
    return {"ok": True, "result": msg}


@app.get("/bot{token}/getUpdates")
async def get_updates(token: str, offset: int = 0, timeout: int = 1):
    new = [m for m in MESSAGES if m["update_id"] > offset]
    return {"ok": True, "result": new}


@app.get("/bot{token}/getChat")
async def get_chat(token: str, chat_id: int = 0):
    return {
        "ok": True,
        "result": {
            "id": chat_id,
            "type": "private",
            "first_name": "Test",
            "username": "test_user",
        },
    }


@app.post("/debug/reset")
async def debug_reset():
    global MESSAGES, UPDATE_COUNTER
    MESSAGES.clear()
    UPDATE_COUNTER = 0
    return {"ok": True}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8081)
    args = parser.parse_args()
    uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="info")

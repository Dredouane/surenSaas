
import json
import logging
import html as _html
from typing import Dict, Any, List, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class TelegramInterface:
    """Helper pour les interactions sortantes vers Telegram."""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    async def send_message(self, chat_id: int, text: str, reply_markup: Optional[Dict] = None):
        url = f"{self.base_url}/sendMessage"
        safe_text = _html.escape(text) if text else text
        payload = {
            "chat_id": chat_id,
            "text": safe_text,
            "parse_mode": "HTML"
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
            logger.debug(f"📋 reply_markup: {json.dumps(reply_markup)}")

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            if response.status_code != 200:
                logger.error(f"❌ Telegram API error ({response.status_code}): {response.text}")
            else:
                resp_json = response.json()
                if not resp_json.get("ok"):
                    logger.error(f"❌ Telegram API response not ok: {resp_json}")
                else:
                    logger.debug(f"✅ Telegram 200 OK: {resp_json.get('description', '')}")

    async def get_file(self, file_id: str) -> Dict[str, Any]:
        """Récupère les informations d'un fichier via son ID."""
        url = f"{self.base_url}/getFile"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params={"file_id": file_id})
            response.raise_for_status()
            return response.json().get("result", {})

    async def download_file(self, file_path: str) -> bytes:
        """Télécharge le contenu binaire d'un fichier."""
        url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    def build_inline_keyboard(self, buttons: List[Dict[str, str]]) -> Dict:
        """
        buttons: [{"text": "Valider", "callback_data": "..."}]
        """
        keyboard = []
        for btn in buttons:
            keyboard.append([{"text": btn["text"], "callback_data": btn["callback_data"]}])
        return {"inline_keyboard": keyboard}

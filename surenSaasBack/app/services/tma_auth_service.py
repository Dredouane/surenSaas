"""
TmaAuthService — Validation InitData Telegram + JWT pour la TMA.

Flux :
  1. TMA envoie initData brut au backend
  2. Backend valide HMAC-SHA256(initData_check_string, BOT_TOKEN) == hash
  3. Backend génère JWT short-lived (15 min)
  4. TMA utilise le JWT pour les appels API suivants
"""

import hmac
import hashlib
import json
import base64
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import HTTPException
import jwt
from jwt import PyJWTError as JWTError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = 15
JWT_SECRET = settings.jwt_secret or "tma-default-secret"


def encode_start_param(payload: dict) -> str:
    """Encode un dict en base64 URL-safe pour le start_param."""
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def decode_start_param(encoded: str) -> dict:
    """Décode un start_param base64 URL-safe en dict."""
    try:
        padded = encoded + "=" * (4 - len(encoded) % 4)
        return json.loads(base64.urlsafe_b64decode(padded).decode())
    except Exception:
        return {}


class TmaAuthService:
    def __init__(self, bot_token: Optional[str] = None):
        self.bot_token = bot_token or settings.telegram_construction_bot_token or ""
        self.jwt_secret = JWT_SECRET

    # ------------------------------------------------------------------
    # InitData Validation (HMAC-SHA256)
    # ------------------------------------------------------------------

    def validate_init_data(self, init_data: str) -> Optional[Dict[str, Any]]:
        """Valide la signature HMAC du initData Telegram. Retourne les données parsées ou None."""
        try:
            parsed = self._parse_init_data(init_data)
            if not parsed or "hash" not in parsed:
                return None

            expected_hash = parsed.pop("hash")
            check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))

            secret_key = hmac.new("WebAppData".encode(), self.bot_token.encode(), hashlib.sha256).digest()
            computed_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

            if computed_hash != expected_hash:
                logger.warning("InitData hash mismatch")
                return None

            return parsed
        except Exception as e:
            logger.error(f"Erreur validation initData: {e}")
            return None

    def _parse_init_data(self, init_data: str) -> Dict[str, str]:
        """Parse une chaîne query-string en dict."""
        result = {}
        for part in init_data.split("&"):
            if "=" in part:
                key, value = part.split("=", 1)
                import urllib.parse
                result[key] = urllib.parse.unquote(value)
        return result

    # ------------------------------------------------------------------
    # JWT Generation / Verification
    # ------------------------------------------------------------------

    def generate_jwt(
        self,
        telegram_id: int,
        user_id: str,
        org_id: str,
        chantier_id: Optional[str] = None,
        role: str = "conducteur",
    ) -> str:
        payload = {
            "telegram_id": telegram_id,
            "user_id": user_id,
            "org_id": org_id,
            "chantier_id": chantier_id,
            "role": role,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRY_MINUTES),
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=JWT_ALGORITHM)

    def verify_jwt(self, token: str) -> Dict[str, Any]:
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[JWT_ALGORITHM])
            return payload
        except JWTError as e:
            logger.warning(f"JWT invalide: {e}")
            raise HTTPException(status_code=401, detail="Token invalide ou expiré")

    # ------------------------------------------------------------------
    # Start Param Resolution
    # ------------------------------------------------------------------

    def resolve_start_param(self, start_param: str) -> Dict[str, Any]:
        if not start_param:
            return {"workflow": None, "chantier_id": None}
        decoded = decode_start_param(start_param)
        return {
            "workflow": decoded.get("w"),
            "chantier_id": decoded.get("c"),
        }

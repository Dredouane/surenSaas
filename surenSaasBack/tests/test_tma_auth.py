#!/usr/bin/env python3
"""
Tests pour TMA Auth Bridge — validation initData + JWT.

Valide :
  - initData invalide → 401
  - initData valide → JWT + context
  - JWT expiré → 401
  - start_param pour routage chantier
"""

import os
import sys
import pytest
import hmac
import hashlib
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import HTTPException
from app.services.tma_auth_service import TmaAuthService, encode_start_param, decode_start_param


TEST_BOT_TOKEN = "test_bot_token_12345"


@pytest.fixture
def auth_service():
    return TmaAuthService(bot_token=TEST_BOT_TOKEN)


class TestStartParamEncoding:
    def test_encode_decode_roundtrip(self):
        payload = {"w": "avancement", "c": "chantier-uuid", "s": "sit-uuid"}
        encoded = encode_start_param(payload)
        decoded = decode_start_param(encoded)
        assert decoded["w"] == "avancement"
        assert decoded["c"] == "chantier-uuid"
        assert decoded["s"] == "sit-uuid"

    def test_decode_invalid_base64(self):
        result = decode_start_param("not-valid-base64!!!")
        assert result == {}

    def test_decode_empty_string(self):
        result = decode_start_param("")
        assert result == {}


class TestTmaAuthService:
    def _compute_init_data_hash(self, init_data: str) -> str:
        """Calcule le hash HMAC attendu pour un init_data donné (sans hash)."""
        import urllib.parse
        parts = {}
        for part in init_data.split("&"):
            if "=" in part:
                key, value = part.split("=", 1)
                parts[key] = urllib.parse.unquote(value)
        check_string = "\n".join(f"{k}={v}" for k, v in sorted(parts.items()))
        secret_key = hmac.new("WebAppData".encode(), TEST_BOT_TOKEN.encode(), hashlib.sha256).digest()
        return hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

    def test_validate_init_data_valid(self, auth_service):
        """Vérifie qu'un initData bien signé est validé."""
        base = (
            'query_id=AAHdF6IQAAAAAN0XohDhrOrc'
            '&user=%7B%22id%22%3A%22123456%22%2C%22first_name%22%3A%22Jean%22%7D'
            '&auth_date=1700000000'
        )
        computed_hash = self._compute_init_data_hash(base)
        auth_data = base + f'&hash={computed_hash}'
        result = auth_service.validate_init_data(auth_data)
        assert result is not None
        assert result["query_id"] == "AAHdF6IQAAAAAN0XohDhrOrc"

    def test_validate_init_data_missing_hash(self, auth_service):
        result = auth_service.validate_init_data("query_id=test&auth_date=1700000000")
        assert result is None

    def test_generate_jwt(self, auth_service):
        token = auth_service.generate_jwt(
            telegram_id=123456,
            user_id="user-uuid",
            org_id="org-uuid",
            chantier_id="chantier-uuid",
            role="conducteur",
        )
        assert token is not None
        assert "." in token  # JWT format

    def test_verify_jwt_valid(self, auth_service):
        token = auth_service.generate_jwt(
            telegram_id=123456,
            user_id="user-uuid",
            org_id="org-uuid",
            chantier_id="chantier-uuid",
            role="conducteur",
        )
        payload = auth_service.verify_jwt(token)
        assert payload is not None
        assert payload["telegram_id"] == 123456
        assert payload["user_id"] == "user-uuid"

    def test_verify_jwt_expired(self, auth_service):
        with patch("app.services.tma_auth_service.datetime") as mock_dt:
            mock_dt.utcnow.return_value = datetime.utcnow() - timedelta(hours=1)
            token = auth_service.generate_jwt(
                telegram_id=123456,
                user_id="user-uuid",
                org_id="org-uuid",
                chantier_id="chantier-uuid",
                role="conducteur",
            )

        with pytest.raises(HTTPException) as exc:
            auth_service.verify_jwt(token)
        assert exc.value.status_code == 401

    def test_verify_jwt_invalid_signature(self, auth_service):
        token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.invalidsignature"
        with pytest.raises(HTTPException) as exc:
            auth_service.verify_jwt(token)
        assert exc.value.status_code == 401

    def test_resolve_start_param_with_chantier(self, auth_service):
        payload = {"w": "progress", "c": "chantier-uuid"}
        encoded = encode_start_param(payload)
        result = auth_service.resolve_start_param(encoded)
        assert result["chantier_id"] == "chantier-uuid"
        assert result["workflow"] == "progress"

    def test_resolve_start_param_empty(self, auth_service):
        result = auth_service.resolve_start_param("")
        assert result["chantier_id"] is None
        assert result["workflow"] is None


class TestContextEndpoint:
    def test_context_returns_user_info(self, auth_service):
        token = auth_service.generate_jwt(
            telegram_id=123456,
            user_id="user-uuid",
            org_id="org-uuid",
            chantier_id="chantier-uuid",
            role="conducteur",
        )
        payload = auth_service.verify_jwt(token)
        assert payload["telegram_id"] == 123456
        assert payload["org_id"] == "org-uuid"
        assert payload["chantier_id"] == "chantier-uuid"
        assert payload["role"] == "conducteur"

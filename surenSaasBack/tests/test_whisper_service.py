#!/usr/bin/env python3
"""
RED Phase — Tests for whisper_service (OpenRouter / Whisper large-v3).

Will fail until whisper_service.py is implemented.
"""

import os
import sys
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytestmark = pytest.mark.asyncio


class TestTranscribeWithWhisper:
    """Tests for transcribe_with_whisper() — OpenRouter Audio API."""

    async def test_transcribe_success(self):
        from app.services.whisper_service import transcribe_with_whisper

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={"text": "Enduit facade 50m2 a 25 euros le m2"})

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)

            result = await transcribe_with_whisper(b"fake_audio_data", "audio/webm")

            assert result == "Enduit facade 50m2 a 25 euros le m2"
            mock_client.post.assert_called_once()

    async def test_transcribe_empty_response(self):
        from app.services.whisper_service import transcribe_with_whisper

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={"text": ""})

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)

            result = await transcribe_with_whisper(b"fake_audio_data", "audio/webm")
            assert result is None

    async def test_transcribe_api_error(self):
        from app.services.whisper_service import transcribe_with_whisper

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)

            result = await transcribe_with_whisper(b"fake_audio_data", "audio/webm")
            assert result is None

    async def test_transcribe_exception(self):
        from app.services.whisper_service import transcribe_with_whisper

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(side_effect=Exception("Network error"))

            result = await transcribe_with_whisper(b"fake_audio_data", "audio/webm")
            assert result is None

    async def test_transcribe_no_api_key(self):
        from app.services.whisper_service import transcribe_with_whisper

        with patch("app.services.whisper_service.settings") as mock_settings:
            mock_settings.open_router_api_key = ""
            result = await transcribe_with_whisper(b"fake_audio_data", "audio/webm")
            assert result is None

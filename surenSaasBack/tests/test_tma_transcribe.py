#!/usr/bin/env python3
"""
Tests pour l'endpoint TMA /api/v1/tma/transcribe.

Valide la transcription audio via Gemini.
"""

import os
import sys
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.api.tma import transcribe_audio

pytestmark = pytest.mark.asyncio


class TestTranscribeAudio:
    @patch("app.api.tma.transcribe_with_gemini")
    async def test_transcribe_success(self, mock_gemini):
        mock_gemini.return_value = "Enduit facade 50m2 a 25 euros le m2 80 pourcent"
        result = await transcribe_audio(b"fake_audio_data", "audio/webm")
        assert result["is_valid"] is True
        assert "Enduit facade" in result["text"]

    @patch("app.api.tma.transcribe_with_gemini")
    async def test_transcribe_failure(self, mock_gemini):
        mock_gemini.return_value = None
        result = await transcribe_audio(b"fake_audio_data", "audio/webm")
        assert result["is_valid"] is False
        assert "error" in result

    @patch("app.api.tma.transcribe_with_gemini")
    async def test_transcribe_error_handling(self, mock_gemini):
        mock_gemini.side_effect = Exception("Gemini API error")
        result = await transcribe_audio(b"fake_audio_data", "audio/webm")
        assert result["is_valid"] is False
        assert "error" in result

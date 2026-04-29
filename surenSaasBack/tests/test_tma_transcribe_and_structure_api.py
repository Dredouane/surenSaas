#!/usr/bin/env python3
"""
RED Phase — Tests for POST /api/v1/tma/transcribe-and-structure endpoint.

Will fail until the new endpoint is registered in tma.py.
"""

import os
import sys
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock
from starlette.datastructures import Headers

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytestmark = pytest.mark.asyncio

SAMPLE_PIPELINE_RESULT = {
    "is_valid": True,
    "transcript": "Enduit facade 50m2 a 25 euros le m2 80 pourcent",
    "structured": {
        "task_id": "123e4567-e89b-12d3-a456-426614174000",
        "percentage": 80,
        "status": "en_cours",
        "observation": "Enduit facade 50m2 a 25 euros/m2, realise a 80%",
    },
    "whisper_log_id": "00000000-0000-0000-0000-000000000001",
    "gemini_log_id": "00000000-0000-0000-0000-000000000002",
}


class TestTranscribeAndStructureEndpoint:
    """Tests for POST /api/v1/tma/transcribe-and-structure."""

    @patch("app.api.tma.transcribe_pipeline", new_callable=AsyncMock)
    @patch("app.api.tma.auth_service")
    async def test_endpoint_success(self, mock_auth, mock_pipeline):
        mock_pipeline.return_value = SAMPLE_PIPELINE_RESULT
        mock_auth.verify_jwt.return_value = {"org_id": "test-org"}

        from app.api.tma import tma_transcribe_and_structure

        mock_request = MagicMock(spec=["state"])
        mock_request.headers = Headers({"authorization": "Bearer fake-jwt"})
        mock_request.state.correlation_id = "test-correlation-id"

        mock_file = MagicMock()
        mock_file.content_type = "audio/webm"
        mock_file.read = AsyncMock(return_value=b"fake_audio_data_here" + b"x" * 100)

        result = await tma_transcribe_and_structure(mock_request, audio=mock_file)

        assert result["is_valid"] is True
        assert result["transcript"] == SAMPLE_PIPELINE_RESULT["transcript"]
        assert result["structured"] == SAMPLE_PIPELINE_RESULT["structured"]
        mock_pipeline.assert_called_once_with(
            audio_data=b"fake_audio_data_here" + b"x" * 100,
            mime_type="audio/webm",
            org_id="test-org",
            correlation_id="test-correlation-id",
        )

    @patch("app.api.tma.transcribe_pipeline", new_callable=AsyncMock)
    @patch("app.api.tma.auth_service")
    async def test_endpoint_empty_audio(self, mock_auth, mock_pipeline):
        mock_auth.verify_jwt.return_value = {"org_id": "test-org"}

        from app.api.tma import tma_transcribe_and_structure

        mock_request = MagicMock(spec=["state"])
        mock_request.headers = Headers({"authorization": "Bearer fake-jwt"})
        mock_request.state.correlation_id = "test-id"

        mock_file = MagicMock()
        mock_file.content_type = "audio/webm"
        mock_file.read = AsyncMock(return_value=b"")

        result = await tma_transcribe_and_structure(mock_request, audio=mock_file)

        assert result["is_valid"] is False
        assert "error" in result
        mock_pipeline.assert_not_called()

    @patch("app.api.tma.transcribe_pipeline", new_callable=AsyncMock)
    @patch("app.api.tma.auth_service")
    async def test_endpoint_no_auth(self, mock_auth, mock_pipeline):
        mock_auth.verify_jwt.side_effect = Exception("Invalid token")

        from app.api.tma import tma_transcribe_and_structure

        mock_request = MagicMock(spec=["state"])
        mock_request.headers = Headers({"authorization": "Bearer bad-token"})
        mock_request.state.correlation_id = "test-id"

        mock_file = MagicMock()
        mock_file.content_type = "audio/webm"
        mock_file.read = AsyncMock(return_value=b"some_data")

        result = await tma_transcribe_and_structure(mock_request, audio=mock_file)

        assert result["is_valid"] is False
        assert "Token invalide" in result["error"]
        mock_pipeline.assert_not_called()

#!/usr/bin/env python3
"""
RED Phase — Tests for transcribe_pipeline (Whisper → Gemini structuration).

Will fail until transcribe_service.py has transcribe_pipeline() and
whisper_service.py exists.
"""

import os
import sys
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytestmark = pytest.mark.asyncio

SAMPLE_STRUCTURED = {
    "task_id": "123e4567-e89b-12d3-a456-426614174000",
    "percentage": 80,
    "status": "en_cours",
    "observation": "Enduit facade realise a 80%",
}


class TestTranscribePipeline:
    """Tests for transcribe_pipeline() — Whisper + Gemini chaining."""

    async def test_pipeline_full_success(self):
        from app.services.transcribe_service import transcribe_pipeline

        with (
            patch("app.services.transcribe_service.transcribe_with_whisper",
                  return_value="Enduit facade 50m2 a 25 euros le m2") as mock_whisper,
            patch("app.services.transcribe_service.gemini_structured_extraction",
                  return_value=SAMPLE_STRUCTURED) as mock_gemini,
        ):
            result = await transcribe_pipeline(b"fake_audio", "audio/webm")

            assert result["is_valid"] is True
            assert result["transcript"] == "Enduit facade 50m2 a 25 euros le m2"
            assert result["structured"] == SAMPLE_STRUCTURED
            assert "whisper_log_id" in result
            assert "gemini_log_id" in result
            mock_whisper.assert_called_once_with(b"fake_audio", "audio/webm")
            mock_gemini.assert_called_once_with("Enduit facade 50m2 a 25 euros le m2")

    async def test_pipeline_whisper_fails(self):
        from app.services.transcribe_service import transcribe_pipeline

        with (
            patch("app.services.transcribe_service.transcribe_with_whisper",
                  return_value=None) as mock_whisper,
            patch("app.services.transcribe_service.gemini_structured_extraction") as mock_gemini,
        ):
            result = await transcribe_pipeline(b"fake_audio", "audio/webm")

            assert result["is_valid"] is False
            assert "error" in result
            assert "Whisper" in result["error"]
            mock_whisper.assert_called_once()
            mock_gemini.assert_not_called()

    async def test_pipeline_gemini_fails(self):
        from app.services.transcribe_service import transcribe_pipeline

        with (
            patch("app.services.transcribe_service.transcribe_with_whisper",
                  return_value="Some transcript") as mock_whisper,
            patch("app.services.transcribe_service.gemini_structured_extraction",
                  return_value=None) as mock_gemini,
        ):
            result = await transcribe_pipeline(b"fake_audio", "audio/webm")

            assert result["is_valid"] is False
            assert "error" in result
            assert "Gemini" in result["error"]
            assert result["transcript"] == "Some transcript"
            mock_whisper.assert_called_once()
            mock_gemini.assert_called_once_with("Some transcript")

    async def test_pipeline_gemini_exception(self):
        from app.services.transcribe_service import transcribe_pipeline

        with (
            patch("app.services.transcribe_service.transcribe_with_whisper",
                  return_value="Some transcript"),
            patch("app.services.transcribe_service.gemini_structured_extraction",
                  side_effect=Exception("Gemini API error")),
        ):
            result = await transcribe_pipeline(b"fake_audio", "audio/webm")

            assert result["is_valid"] is False
            assert "error" in result
            assert "Gemini" in result["error"]

    async def test_pipeline_audit_logged_for_each_step(self):
        """Verify that audit_service.log_agent is called once per step."""
        from app.services.transcribe_service import transcribe_pipeline

        mock_audit = AsyncMock()
        mock_audit.log_agent = AsyncMock()

        with (
            patch("app.services.transcribe_service.transcribe_with_whisper",
                  return_value="Some transcript"),
            patch("app.services.transcribe_service.gemini_structured_extraction",
                  return_value=SAMPLE_STRUCTURED),
            patch("app.services.transcribe_service.AuditService",
                  return_value=mock_audit),
        ):
            await transcribe_pipeline(b"fake_audio", "audio/webm")

            assert mock_audit.log_agent.call_count == 2
            calls = mock_audit.log_agent.call_args_list
            assert calls[0][1]["agent_type"] == "whisper_transcription"
            assert calls[1][1]["agent_type"] == "gemini_structuration"


class TestGeminiStructuredExtraction:
    """Tests for gemini_structured_extraction() — JSON parsing step."""

    async def test_gemini_structured_success(self):
        from app.services.transcribe_service import gemini_structured_extraction

        mock_response_text = json.dumps(SAMPLE_STRUCTURED)

        with patch("app.services.transcribe_service.transcribe_with_gemini_for_text",
                   return_value=mock_response_text) as mock_gemini:
            result = await gemini_structured_extraction(
                "Enduit facade 50m2 a 25 euros le m2"
            )

            assert result == SAMPLE_STRUCTURED
            mock_gemini.assert_called_once()

    async def test_gemini_structured_with_markdown(self):
        """Gemini may return JSON wrapped in ```json ... ```."""
        from app.services.transcribe_service import gemini_structured_extraction

        with patch("app.services.transcribe_service.transcribe_with_gemini_for_text",
                   return_value="```json\n" + json.dumps(SAMPLE_STRUCTURED) + "\n```"):
            result = await gemini_structured_extraction("Some text")
            assert result == SAMPLE_STRUCTURED

    async def test_gemini_structured_invalid_json(self):
        from app.services.transcribe_service import gemini_structured_extraction

        with patch("app.services.transcribe_service.transcribe_with_gemini_for_text",
                   return_value="Ceci n'est pas du json"):
            result = await gemini_structured_extraction("Some text")
            assert result is None

    async def test_gemini_structured_none_response(self):
        from app.services.transcribe_service import gemini_structured_extraction

        with patch("app.services.transcribe_service.transcribe_with_gemini_for_text",
                   return_value=None):
            result = await gemini_structured_extraction("Some text")
            assert result is None

    async def test_gemini_structured_missing_keys(self):
        """JSON returned but missing required keys → None."""
        from app.services.transcribe_service import gemini_structured_extraction

        with patch("app.services.transcribe_service.transcribe_with_gemini_for_text",
                   return_value=json.dumps({"task_id": "abc"})):
            result = await gemini_structured_extraction("Some text")
            assert result is None

    async def test_gemini_structured_empty_text(self):
        from app.services.transcribe_service import gemini_structured_extraction

        with patch("app.services.transcribe_service.transcribe_with_gemini_for_text") as mock_gemini:
            result = await gemini_structured_extraction("")
            assert result is None
            mock_gemini.assert_not_called()

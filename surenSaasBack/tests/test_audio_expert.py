
import os
import pytest
import respx
from httpx import Response
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.agents.audio_service import AudioExpertService

# On définit une clé bidon pour passer la validation Pydantic de ChatGoogleGenerativeAI
os.environ["GOOGLE_API_KEY"] = "fake-google-key"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/fake-credentials.json"

@pytest.fixture(autouse=True)
def _mock_vertex():
    """Patch get_chat_model et startup pour éviter tout appel réel à Vertex AI."""
    with patch("app.core.vertex.get_chat_model") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield

@pytest.mark.asyncio
async def test_transcription_openrouter():
    """Test de la transcription brute via OpenRouter (Mocked)."""
    service = AudioExpertService(api_key="sk-test-123")
    audio_bytes = b"fake-audio-content"
    
    with respx.mock:
        respx.post("https://openrouter.ai/api/v1/audio/transcriptions").mock(
            return_value=Response(200, json={"text": "J'ai achete du ciment a Batimat"})
        )
        
        transcript = await service.transcribe(audio_bytes)
        assert transcript == "J'ai achete du ciment a Batimat"

@pytest.mark.asyncio
async def test_normalization_btp():
    """Test de la normalisation métier via Gemini (Mocked)."""
    service = AudioExpertService(api_key="sk-test-123")
    
    # Mock du LLM Gemini
    service.llm = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = '{"text": "J\'ai acheté du ciment à Batimat", "is_urgent": false}'
    service.llm.ainvoke.return_value = mock_response
    
    chantiers = [{"nom": "Batimat", "ref": "B-001"}]
    result = await service.normalize_text("J'ai achete du ciment a Batimat", chantiers)
    
    assert result["text"] == "J'ai acheté du ciment à Batimat"
    assert result["is_urgent"] is False

@pytest.mark.asyncio
async def test_urgency_detection():
    """Test de la détection d'urgence (Mocked)."""
    service = AudioExpertService(api_key="sk-test-123")
    
    service.llm = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = '{"text": "ALERTE INONDATION SUR LE CHANTIER", "is_urgent": true}'
    service.llm.ainvoke.return_value = mock_response
    
    result = await service.normalize_text("ALERTE INONDATION", [])
    assert result["is_urgent"] is True

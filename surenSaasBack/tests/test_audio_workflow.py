
import os
import pytest
import respx
from httpx import Response
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from app.services.agents.graph import create_agent_graph

# Mock API Key
os.environ["GOOGLE_API_KEY"] = "fake-key"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/fake-credentials.json"
os.environ["OPEN_ROUTER_API_KEY"] = "fake-openrouter-key"

@pytest.mark.asyncio
async def test_full_audio_agent_workflow():
    """Test du flux agentique complet avec un input audio."""
    
    # Mock Supabase
    with patch("app.services.agents.graph.get_supabase") as mock_supabase, \
         patch("app.api.auth.get_supabase") as mock_supabase_auth:
        
        # Simuler un retour vide pour les chantiers
        mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock_supabase_auth.return_value = mock_supabase.return_value

        # 1. Setup Graph with Memory Checkpointer
        checkpointer = MemorySaver()
        graph = create_agent_graph(checkpointer)
        config = {"configurable": {"thread_id": "test_audio_thread"}}
        fake_audio = b"fake-ogg-content"
    
        # 2. Mock AudioExpertService and Agent LLM
        with patch("app.services.agents.graph.AudioExpertService") as MockService, \
             patch("app.services.agents.graph.ChatGoogleGenerativeAI") as MockLLM, \
             patch("google.auth.default") as mock_auth:
            
            mock_creds = MagicMock()
            mock_auth.return_value = (mock_creds, "test-project")
            
            # Mock Service instance
            mock_service_instance = MockService.return_value
            mock_service_instance.transcribe = AsyncMock(return_value="urgence sur le chantier thenar")
            mock_service_instance.normalize_text = AsyncMock(return_value={
                "text": "Urgence sur le chantier Thénard",
                "is_urgent": True
            })
            
            # Mock Agent LLM
            mock_agent_llm = MockLLM.return_value
            mock_bound_llm = MagicMock()
            mock_agent_llm.bind_tools.return_value = mock_bound_llm
            mock_bound_llm.invoke.return_value = AIMessage(content="J'ai bien noté l'urgence sur le chantier Thénard.")
            
            # 3. Input initial avec voice_bytes
            input_data = {
                "messages": [],
                "org_id": "REDACTEDORG",
                "chantier_id": None,
                "user_name": "Chef Chantier",
                "correlation_id": "REDACTEDORG",
                "voice_bytes": fake_audio,
                "is_urgent": False,
                "audio_meta": {},
                "summary": "",
                "last_action_status": "idle"
            }
    
            # 4. Lancer le graphe
            events = []
            async for event in graph.astream(input_data, config, stream_mode="values"):
                events.append(event)
    
            # 5. Vérifications
            final_state = events[-1]
            
            # Le texte normalisé doit être dans les messages
            assert any("Thénard" in str(m.content) for m in final_state["messages"])
            assert final_state["is_urgent"] is True
            assert final_state["voice_bytes"] is None
            assert "transcription_latency_ms" in final_state["audio_meta"]
            
            print("\n✅ Flux audio agentique validé de bout en bout.")


import os
import pytest
import respx
from httpx import Response
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from app.services.agents.graph import create_agent_graph
from app.services.agents.vision_service import ExtractedExpense

# Mock API Key
os.environ["GOOGLE_API_KEY"] = "fake-key"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/fake-credentials.json"

@pytest.mark.asyncio
async def test_full_vision_agent_workflow_document():
    """Test du flux agentique complet avec un document financier."""
    
    # Mock Supabase
    with patch("app.services.agents.graph.get_supabase") as mock_supabase, \
         patch("app.api.auth.get_supabase") as mock_supabase_auth:

        mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock_supabase_auth.return_value = mock_supabase.return_value

        # 1. Setup Graph
        checkpointer = MemorySaver()
        graph = create_agent_graph(checkpointer)
        config = {"configurable": {"thread_id": "test_vision_doc_thread"}}
        fake_image = b"fake-jpg-content"
    
        # 2. Mock VisionExpertService and Agent LLM
        with patch("app.services.agents.graph.VisionExpertService") as MockService, \
             patch("app.core.vertex.get_chat_model") as MockLLM:
            
            # Mock Service instance
            mock_service_instance = MockService.return_value
            mock_service_instance.process_photo = AsyncMock(return_value=ExtractedExpense(
                is_document=True,
                fournisseur="Batimat",
                montant_ttc=150.0,
                date="2026-04-29",
                besoin_clarification=False,
                description="Ticket Batimat ciment"
            ))
            
            # Mock Agent LLM
            mock_agent_llm = MockLLM.return_value
            mock_bound_llm = MagicMock()
            mock_agent_llm.bind_tools.return_value = mock_bound_llm
            mock_bound_llm.invoke.return_value = AIMessage(content="Voulez-vous enregistrer cette dépense ?")
            
            # 3. Input initial avec image_bytes
            input_data = {
                "messages": [],
                "org_id": "REDACTEDORG",
                "chantier_id": None,
                "user_name": "Chef Chantier",
                "correlation_id": "REDACTEDORG",
                "voice_bytes": None,
                "image_bytes": fake_image,
                "is_urgent": False,
                "audio_meta": {},
                "vision_meta": {},
                "summary": "",
                "last_action_status": "idle"
            }
    
            # 4. Lancer le graphe
            events = []
            async for event in graph.astream(input_data, config, stream_mode="values"):
                events.append(event)
    
            # 5. Vérifications
            final_state = events[-1]
            assert any("Facture extraite" in str(m.content) for m in final_state["messages"])
            assert final_state["vision_meta"]["is_document"] is True
            assert final_state["image_bytes"] is None
            
            print("\n✅ Flux vision (Document) validé.")

@pytest.mark.asyncio
async def test_full_vision_agent_workflow_photo_chantier():
    """Test du flux agentique avec une photo de chantier."""
    
    with patch("app.services.agents.graph.get_supabase") as mock_supabase, \
         patch("app.api.auth.get_supabase") as mock_supabase_auth:
        
        mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock_supabase_auth.return_value = mock_supabase.return_value

        checkpointer = MemorySaver()
        graph = create_agent_graph(checkpointer)
        config = {"configurable": {"thread_id": "test_vision_photo_thread"}}
        fake_image = b"fake-jpg-content"
    
        with patch("app.services.agents.graph.VisionExpertService") as MockService, \
             patch("app.core.vertex.get_chat_model") as MockLLM:
            
            mock_service_instance = MockService.return_value
            mock_service_instance.process_photo = AsyncMock(return_value=ExtractedExpense(
                is_document=False,
                description="Une bétonneuse sur le terrain"
            ))
            
            mock_agent_llm = MockLLM.return_value
            mock_bound_llm = MagicMock()
            mock_agent_llm.bind_tools.return_value = mock_bound_llm
            mock_bound_llm.invoke.return_value = AIMessage(content="Reçu.")
            
            input_data = {
                "messages": [],
                "org_id": "REDACTEDORG",
                "chantier_id": None,
                "user_name": "Chef Chantier",
                "correlation_id": "REDACTEDORG",
                "voice_bytes": None,
                "image_bytes": fake_image,
                "is_urgent": False,
                "audio_meta": {},
                "vision_meta": {},
                "summary": "",
                "last_action_status": "idle"
            }
    
            events = []
            async for event in graph.astream(input_data, config, stream_mode="values"):
                events.append(event)
    
            final_state = events[-1]
            assert any("Photo de chantier" in str(m.content) for m in final_state["messages"])
            
            print("\n✅ Flux vision (Photo Chantier) validé.")

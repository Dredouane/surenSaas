
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from app.services.agents.graph import create_agent_graph

# Mock API Key
os.environ["GOOGLE_API_KEY"] = "fake-key"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/fake-credentials.json"

@pytest.mark.asyncio
async def test_anti_hallucination_pre_reflector():
    """Test que le Pre-Reflector bloque les actions sans chantier défini."""
    
    checkpointer = MemorySaver()
    graph = create_agent_graph(checkpointer)
    config = {"configurable": {"thread_id": "test_hallucination"}}
    
    # 1. Simuler l'agent qui veut créer une dépense mais n'a pas de chantier
    # On mocke l'agent pour qu'il essaie d'appeler l'outil sans chantier_id
    with patch("app.core.vertex.get_chat_model") as MockLLM:
        mock_instance = MockLLM.return_value
        
        # L'agent décide d'appeler l'outil avec un chantier_id null ou vide
        tool_call = {
            "name": "create_depense",
            "args": {"fournisseur": "Batimat", "montant": 100, "chantier_id": ""},
            "id": "call_123",
            "type": "tool_call"
        }
        mock_instance.invoke.return_value = AIMessage(content="Je vais enregistrer 100€ chez Batimat.", tool_calls=[tool_call])
        mock_instance.bind_tools.return_value.invoke.return_value = mock_instance.invoke.return_value
        
        input_data = {
            "messages": [HumanMessage(content="Enregistre 100€ chez Batimat")],
            "org_id": "org_123",
            "chantier_id": None,
            "user_name": "Test",
            "correlation_id": "corr_123",
            "summary": "",
            "last_action_status": "idle",
            "pending_tool_call": None,
            "hitl_choice": None,
            "voice_bytes": None,
            "image_bytes": None,
            "audio_meta": {},
            "vision_meta": {},
            "is_urgent": False
        }
        
        events = []
        async for event in graph.astream(input_data, config, stream_mode="values"):
            events.append(event)
            
        final_state = events[-1]
        
        # Le dernier message doit être une demande de précision (provenant du pre_reflector)
        # et non une exécution d'outil ou une confirmation
        assert "quel chantier" in final_state["messages"][-1].content
        assert final_state["last_action_status"] != "pending_confirm"

@pytest.mark.asyncio
async def test_hitl_interruption_cycle():
    """Test que le graphe s'interrompt pour confirmation avant l'outil."""
    
    checkpointer = MemorySaver()
    graph = create_agent_graph(checkpointer)
    config = {"configurable": {"thread_id": "test_hitl"}}
    
    with patch("app.core.vertex.get_chat_model") as MockLLM:
        mock_instance = MockLLM.return_value
        
        # L'agent appelle correctement l'outil
        tool_call = {
            "name": "create_depense",
            "args": {"fournisseur": "Batimat", "montant": 100, "chantier_id": "CH-001", "org_id": "org_123"},
            "id": "call_hitl",
            "type": "tool_call"
        }
        mock_instance.invoke.return_value = AIMessage(content="Je vais enregistrer 100€ chez Batimat.", tool_calls=[tool_call])
        mock_instance.bind_tools.return_value.invoke.return_value = mock_instance.invoke.return_value
        
        input_data = {
            "messages": [HumanMessage(content="100€ Batimat sur CH-001")],
            "org_id": "org_123",
            "chantier_id": "CH-001",
            "user_name": "Test",
            "correlation_id": "corr_hitl",
            "summary": "",
            "last_action_status": "idle",
            "pending_tool_call": None,
            "hitl_choice": None,
            "voice_bytes": None,
            "image_bytes": None,
            "audio_meta": {},
            "vision_meta": {},
            "is_urgent": False
        }
        
        # L'exécution doit s'arrêter avant "tools"
        async for event in graph.astream(input_data, config, stream_mode="values"):
            pass
            
        state = await graph.aget_state(config)
        
        # Doit être sur l'interruption avant tools
        assert state.next[0] == "tools"
        assert state.values["last_action_status"] == "pending_confirm"
        assert "Batimat" in state.values["messages"][-1].content # Message de l'agent
        
        # Simulation du RESUME (le webhook appelle astream(None))
        # On mocke la fonction réelle appelée par l'outil
        with patch("app.services.agents.tools.get_supabase") as mock_sb_tool:
            # Mock le retour de l'insert pour create_depense
            mock_sb_tool.return_value.table.return_value.insert.return_value.execute.return_value.data = [{"id": "dep_1"}]
            
            # On doit aussi mocker resolve_chantier_uuid qui est appelé par l'outil
            with patch("app.services.agents.tools.resolve_chantier_uuid", return_value="uuid_chantier"):
                async for event in graph.astream(None, config, stream_mode="values"):
                    pass
                    
                final_state = await graph.aget_state(config)
                # Vérifier que le Final Reflector a bien pris le relais
                assert any("C'est en boîte" in str(m.content) for m in final_state.values["messages"])

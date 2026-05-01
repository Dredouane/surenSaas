import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from app.services.agents.graph import create_agent_graph

os.environ["GOOGLE_API_KEY"] = "fake-key"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/fake-credentials.json"


def _make_mock_llm(content: str, tool_call: dict):
    """Helper pour créer un mock LLM avec un tool_call."""
    mock_instance = MagicMock()
    mock_instance.invoke.return_value = AIMessage(content=content, tool_calls=[tool_call])
    mock_instance.bind_tools.return_value.invoke.return_value = mock_instance.invoke.return_value
    return mock_instance


def _default_input(chantier_id: str = "CH-001", text: str = "") -> dict:
    return {
        "messages": [HumanMessage(content=text)],
        "org_id": "org_123",
        "chantier_id": chantier_id,
        "user_name": "Test",
        "correlation_id": "test_corr",
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


@pytest.mark.asyncio
async def test_depense_workflow():
    """Workflow Dépenses : l'agent appelle create_depense avec les bons args."""
    graph = create_agent_graph(MemorySaver())
    config = {"configurable": {"thread_id": "wf_depense"}}

    tool_call = {
        "name": "create_depense",
        "args": {"fournisseur": "Batimat", "montant": 150.0, "chantier_id": "CH-001", "org_id": "org_123"},
        "id": "call_dep", "type": "tool_call"
    }

    with patch("app.services.agents.graph.ChatGoogleGenerativeAI") as MockLLM, \
         patch("google.auth.default") as mock_auth:
        mock_creds = MagicMock()
        mock_auth.return_value = (mock_creds, "test-project")
        MockLLM.return_value = _make_mock_llm("Je crée la dépense.", tool_call)

        events = []
        async for event in graph.astream(_default_input(text="150€ Batimat"), config, stream_mode="values"):
            events.append(event)

        final = events[-1]
        assert any("Batimat" in str(m.content) for m in final["messages"])
        assert final["pending_tool_call"] is not None


@pytest.mark.asyncio
async def test_operation_workflow():
    """Workflow Opérations HITL : l'agent peut signaler une opération terrain."""
    graph = create_agent_graph(MemorySaver())
    config = {"configurable": {"thread_id": "wf_operation"}}

    tool_call = {
        "name": "create_operation",
        "args": {"description": "Pose de briques", "chantier_id": "CH-001", "org_id": "org_123", "type": "autre"},
        "id": "call_op", "type": "tool_call"
    }

    with patch("app.services.agents.graph.ChatGoogleGenerativeAI") as MockLLM, \
         patch("google.auth.default") as mock_auth:
        mock_creds = MagicMock()
        mock_auth.return_value = (mock_creds, "test-project")
        MockLLM.return_value = _make_mock_llm("J'enregistre l'opération.", tool_call)

        events = []
        async for event in graph.astream(_default_input(text="Pose de briques chantier 1"), config, stream_mode="values"):
            events.append(event)

        final = events[-1]
        assert any("opération" in str(m.content).lower() for m in final["messages"]) or final["pending_tool_call"] is not None


@pytest.mark.asyncio
async def test_pointage_workflow():
    """Workflow Pointages : l'agent peut pointer une présence."""
    graph = create_agent_graph(MemorySaver())
    config = {"configurable": {"thread_id": "wf_pointage"}}

    tool_call = {
        "name": "manage_attendance",
        "args": {"date": "2026-04-30", "chantier_id": "CH-001", "org_id": "org_123",
                 "ressources": [{"ressource_id": "R1", "presence": True, "heures": 8}]},
        "id": "call_ptg", "type": "tool_call"
    }

    with patch("app.services.agents.graph.ChatGoogleGenerativeAI") as MockLLM, \
         patch("google.auth.default") as mock_auth:
        mock_creds = MagicMock()
        mock_auth.return_value = (mock_creds, "test-project")
        MockLLM.return_value = _make_mock_llm("Je pointe la présence.", tool_call)

        events = []
        async for event in graph.astream(_default_input(text="Pointer présence équipe"), config, stream_mode="values"):
            events.append(event)

        final = events[-1]
        assert final["pending_tool_call"] is not None


@pytest.mark.asyncio
async def test_avancement_workflow():
    """Workflow Avancements : l'agent peut reporter un avancement."""
    graph = create_agent_graph(MemorySaver())
    config = {"configurable": {"thread_id": "wf_avancement"}}

    tool_call = {
        "name": "report_progress",
        "args": {"situation_id": "SIT-001", "chantier_id": "CH-001", "org_id": "org_123",
                 "description": "Mur nord terminé", "avancement_pourcentage": 75.0},
        "id": "call_av", "type": "tool_call"
    }

    with patch("app.services.agents.graph.ChatGoogleGenerativeAI") as MockLLM, \
         patch("google.auth.default") as mock_auth:
        mock_creds = MagicMock()
        mock_auth.return_value = (mock_creds, "test-project")
        MockLLM.return_value = _make_mock_llm("J'enregistre l'avancement.", tool_call)

        events = []
        async for event in graph.astream(_default_input(text="Avancement mur nord 75%"), config, stream_mode="values"):
            events.append(event)

        final = events[-1]
        assert final["pending_tool_call"] is not None or any("avancement" in str(m.content).lower() for m in final["messages"])


@pytest.mark.asyncio
async def test_tache_workflow():
    """Workflow Tâches : l'agent peut créer une tâche."""
    graph = create_agent_graph(MemorySaver())
    config = {"configurable": {"thread_id": "wf_tache"}}

    tool_call = {
        "name": "manage_tasks",
        "args": {"action": "create", "chantier_id": "CH-001", "org_id": "org_123",
                 "titre": "Nettoyer zone sud", "priorite": "haute"},
        "id": "call_tk", "type": "tool_call"
    }

    with patch("app.services.agents.graph.ChatGoogleGenerativeAI") as MockLLM, \
         patch("google.auth.default") as mock_auth:
        mock_creds = MagicMock()
        mock_auth.return_value = (mock_creds, "test-project")
        MockLLM.return_value = _make_mock_llm("Je crée la tâche.", tool_call)

        events = []
        async for event in graph.astream(_default_input(text="Créer tâche nettoyage zone sud"), config, stream_mode="values"):
            events.append(event)

        final = events[-1]
        assert final["pending_tool_call"] is not None

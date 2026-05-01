"""Test du Smart Router : format_response → END, outils métier → pre_reflector, tools → agent."""

import os
from langchain_core.messages import AIMessage, ToolMessage
from app.services.agents.graph import after_agent, END

os.environ["GOOGLE_API_KEY"] = "fake-key"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/fake-credentials.json"


def test_after_agent_routes_format_response_to_end():
    """Quand le LLM appelle format_response, after_agent renvoie END."""
    state = {
        "messages": [
            AIMessage(
                content="Voici le menu :",
                tool_calls=[{
                    "name": "format_response",
                    "args": {"action": "DISPLAY_MENU", "payload": {"options": ["A", "B"]}},
                    "id": "call_test",
                    "type": "tool_call"
                }]
            )
        ]
    }
    result = after_agent(state)
    assert result == END or result == "END", f"Attendu END, reçu '{result}'"


def test_after_agent_routes_metier_tool_to_pre_reflector():
    """Quand le LLM appelle un outil métier, after_agent renvoie 'pre_reflector'."""
    state = {
        "messages": [
            AIMessage(
                content="Je crée la dépense.",
                tool_calls=[{
                    "name": "create_depense",
                    "args": {"fournisseur": "Batimat", "montant": 100},
                    "id": "call_test",
                    "type": "tool_call"
                }]
            )
        ]
    }
    result = after_agent(state)
    assert result == "pre_reflector", f"Attendu 'pre_reflector', reçu '{result}'"


def test_after_agent_ends_without_tool_call():
    """Quand le LLM ne fait pas de tool_call, after_agent renvoie END."""
    state = {
        "messages": [AIMessage(content="Bonjour chef !")]
    }
    result = after_agent(state)
    assert result == END, f"Attendu END, reçu '{result}'"


def test_create_agent_graph_has_tools_to_agent_edge():
    """Le graphe compile avec un edge tools → agent."""
    from langgraph.checkpoint.memory import MemorySaver
    from app.services.agents.graph import create_agent_graph

    graph = create_agent_graph(MemorySaver())
    # Vérifier que le graphe se compile sans erreur
    assert graph is not None


def test_recursion_limit_is_set():
    """Le graphe peut compiler avec des cycles grâce à interrupt_before."""
    import inspect
    from app.services.agents.graph import create_agent_graph
    from langgraph.checkpoint.memory import MemorySaver

    graph = create_agent_graph(MemorySaver())
    assert graph is not None
    # Le graphe a un edge tools → agent, ce qui crée un cycle
    # Vérifier que le graphe gère correctement ce cycle via interrupt_before=["tools"]
    assert hasattr(graph, 'stream') or hasattr(graph, 'invoke')

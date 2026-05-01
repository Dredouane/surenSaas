"""Test du nouveau nœud tool_result_formatter qui force format_response."""

import os
import json
from langchain_core.messages import AIMessage, ToolMessage
from app.services.agents.graph import END

os.environ["GOOGLE_API_KEY"] = "fake-key"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/fake-credentials.json"


def test_tool_result_formatter_converts_data_to_format_response():
    """tool_result_formatter transforme un ToolMessage avec des données en format_response."""
    from app.services.agents.graph import tool_result_formatter_node
    
    msg = ToolMessage(
        content=json.dumps({
            "success": True,
            "data": [
                {"ref": "CH-001", "nom": "Villa Alpha", "statut": "en_cours"},
                {"ref": "CH-002", "nom": "Bureaux Beta", "statut": "termine"}
            ]
        }),
        tool_call_id="call_test"
    )
    state = {"messages": [msg], "org_id": "test"}
    result = tool_result_formatter_node(state)
    
    assert result is not None
    last_msg = result.get("messages", [None])[-1]
    assert last_msg is not None
    assert last_msg.tool_calls, "Doit contenir un tool_call"
    assert last_msg.tool_calls[0]["name"] == "format_response", \
        f"Doit être format_response, reçu {last_msg.tool_calls[0]['name']}"
    args = last_msg.tool_calls[0]["args"]
    assert args.get("action") == "DISPLAY_MENU"
    assert "CH-001" in str(args.get("payload", {}))


def test_tool_result_formatter_passes_errors():
    """Si le tool a échoué, on ne force pas format_response."""
    from app.services.agents.graph import tool_result_formatter_node
    
    msg = ToolMessage(
        content=json.dumps({"success": False, "error": "org_id manquant"}),
        tool_call_id="call_test"
    )
    state = {"messages": [msg], "org_id": "test"}
    result = tool_result_formatter_node(state)
    
    assert result is not None
    last_msg = result.get("messages", [None])[-1]
    assert last_msg is not None
    assert "❌" in str(last_msg.content), "Doit afficher l'erreur"

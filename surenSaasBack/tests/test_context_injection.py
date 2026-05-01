"""Test que l'org_id injecté par pre_reflector est conservé par hitl_formatter_node."""

import os
from langchain_core.messages import AIMessage, HumanMessage
from app.services.agents.graph import pre_reflector_node, hitl_formatter_node, ActionType, AgentState

os.environ["GOOGLE_API_KEY"] = "fake-key"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/fake-credentials.json"


def test_hitl_formatter_preserves_injected_org_id():
    """hitl_formatter_node doit utiliser pending_tool_call du state si disponible,
    pas last_msg.tool_calls[0] qui pourrait être le message original sans org_id."""
    # 1. State avec pending_tool_call déjà injecté (simule le passage par pre_reflector)
    target_org_id = "REDACTEDORG"
    state = {
        "messages": [
            HumanMessage(content="liste mes chantiers"),
            AIMessage(
                content="Je vais chercher les chantiers.",
                tool_calls=[{
                    "name": "get_user_chantiers",
                    "args": {},  # PAS d'org_id ici (simule l'oubli du LLM)
                    "id": "call_test",
                    "type": "tool_call"
                }]
            )
        ],
        "pending_tool_call": {  # Déjà injecté par pre_reflector
            "name": "get_user_chantiers",
            "args": {"org_id": target_org_id},
            "id": "call_test",
            "type": "tool_call"
        },
        "org_id": target_org_id,
        "user_name": "Test",
        "correlation_id": "test",
        "last_action_status": "idle",
    }

    result = hitl_formatter_node(state)
    assert result is not None

    pending = result.get("pending_tool_call")
    assert pending is not None, "hitl_formatter doit retourner pending_tool_call"
    assert pending["args"].get("org_id") == target_org_id, \
        f"L'org_id injecté doit être conservé. Attendu: {target_org_id}, Reçu: {pending['args'].get('org_id')}"

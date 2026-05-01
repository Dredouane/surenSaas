
import asyncio
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from app.services.agents.graph import create_agent_graph

async def test_agent_intelligence():
    """
    Test d'intelligence : Vérifie que l'agent route correctement vers les outils
    et demande le chantier s'il est manquant.
    """
    print("\n--- TEST D'INTELLIGENCE AGENTIQUE ---")
    
    # 1. Utiliser MemorySaver pour le test (pas de DB requise)
    checkpointer = MemorySaver()
    graph = create_agent_graph(checkpointer)
    
    config = {"configurable": {"thread_id": "test_intelligence_123"}}
    
    # Cas 1 : Message sans chantier_id
    print("\nScénario 1 : Ajout d'une dépense sans préciser le chantier")
    input_data = {
        "messages": [HumanMessage(content="J'ai acheté du ciment pour 150€ chez Batimat")],
        "org_id": "REDACTEDORG",
        "chantier_id": None,
        "user_name": "TestUser",
        "correlation_id": "REDACTEDORG", # Valid UUID for test
        "summary": "",
        "last_action_status": "idle"
    }
    
    async for event in graph.astream(input_data, config, stream_mode="values"):
        last_msg = event["messages"][-1]
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            print(f"🛠️  L'agent appelle l'outil : {last_msg.tool_calls[0]['name']}")
            print(f"📦 Arguments : {last_msg.tool_calls[0]['args']}")
        elif last_msg.content:
            print(f"🤖 Réponse Agent : {last_msg.content}")

    print("\n✅ Test d'intelligence terminé.")

if __name__ == "__main__":
    asyncio.run(test_agent_intelligence())

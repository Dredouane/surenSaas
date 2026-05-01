
import pytest
import asyncio
from typing import Annotated, TypedDict
from operator import add
from langgraph.graph import StateGraph, START, END
from app.services.agents.persistence import agent_persistence

# Définition d'un state simple
class TestState(TypedDict):
    count: Annotated[int, add]

def increment_node(state: TestState):
    return {"count": 1}

@pytest.mark.asyncio
async def test_langgraph_persistence():
    """Test que l'état du graphe est persisté entre deux exécutions."""
    
    # 1. Setup Graph
    builder = StateGraph(TestState)
    builder.add_node("increment", increment_node)
    builder.add_edge(START, "increment")
    builder.add_edge("increment", END)
    
    # Récupérer le saver (PostgresSaver)
    saver = await agent_persistence.get_saver()
    graph = builder.compile(checkpointer=saver)
    
    thread_id = "test_thread_123"
    config = {"configurable": {"thread_id": thread_id}}
    
    # 2. Première exécution
    print(f"\nExécution 1 pour le thread {thread_id}...")
    await graph.ainvoke({"count": 0}, config)
    
    # Vérifier l'état actuel
    state = await graph.aget_state(config)
    assert state.values["count"] == 1
    print(f"Compteur après Exécution 1: {state.values['count']}")
    
    # 3. Deuxième exécution (devrait s'ajouter au précédent)
    print(f"Exécution 2 pour le même thread...")
    await graph.ainvoke({"count": 0}, config)
    
    state = await graph.aget_state(config)
    assert state.values["count"] == 2
    print(f"Compteur après Exécution 2: {state.values['count']}")
    
    # 4. Simulation de "redémarrage" (on recrée le checkpointer)
    # Dans un vrai test on fermerait le pool, mais ici on vérifie juste que 
    # aget_state récupère bien les données depuis Postgres.
    
    new_state = await graph.aget_state(config)
    assert new_state.values["count"] == 2
    print("✅ Persistance validée.")

if __name__ == "__main__":
    # Pour lancer manuellement si besoin
    asyncio.run(test_langgraph_persistence())

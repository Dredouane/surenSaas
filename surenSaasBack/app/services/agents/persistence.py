from typing import AsyncGenerator
from contextlib import asynccontextmanager
from langgraph.checkpoint.memory import MemorySaver


class AgentPersistenceService:
    """Service de persistance pour les agents LangGraph."""

    def __init__(self):
        self.saver = MemorySaver()

    async def get_saver(self) -> MemorySaver:
        return self.saver

    async def close(self):
        pass


# Singleton
agent_persistence = AgentPersistenceService()


@asynccontextmanager
async def get_agent_graph_saver() -> AsyncGenerator[MemorySaver, None]:
    saver = await agent_persistence.get_saver()
    yield saver

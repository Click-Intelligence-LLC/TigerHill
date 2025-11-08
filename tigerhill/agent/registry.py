from typing import Dict, Type
from tigerhill.core.models import Agent


class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, Type[Agent]] = {}

    def register(self, agent_class: Type[Agent]):
        self._agents[agent_class.name] = agent_class

    def get_agent(self, name: str) -> Type[Agent]:
        if name not in self._agents:
            raise ValueError(f"Agent '{name}' not found in registry.")
        return self._agents[name]

    def list_agents(self) -> list[str]:
        return list(self._agents.keys())


agent_registry = AgentRegistry()

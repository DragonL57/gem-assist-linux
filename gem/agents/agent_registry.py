"""
Registry for managing all specialized agents.
"""
from typing import Dict, Optional, List
from .base_agent import BaseAgent

class AgentRegistry:
    def __init__(self):
        self._agents = {}
        
    def register(self, name: str, agent: BaseAgent):
        """Register an agent instance."""
        if name in self._agents:
            raise ValueError(f"Agent with name '{name}' already exists.")
        self._agents[name] = agent
        
    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Retrieve an agent by name."""
        return self._agents.get(name)
        
    def list_agents(self) -> List[str]:
        """List all registered agents."""
        return list(self._agents.keys())

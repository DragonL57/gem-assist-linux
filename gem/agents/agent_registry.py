"""
Agent Registry for managing available agents in the gem-assist system.
"""
from typing import Dict, List, Any, Optional, Type
from .base_agent import BaseAgent
from rich.console import Console

class AgentRegistry:
    """
    Registry for managing and accessing specialized agents in the system.
    Provides methods to register agents, get agents by name, and list available agents.
    """
    
    def __init__(self, console: Optional[Console] = None):
        """
        Initialize the agent registry.
        
        Args:
            console: Optional console for logging
        """
        self.agents: Dict[str, BaseAgent] = {}
        self.console = console
    
    def register(self, name: str, agent: BaseAgent) -> None:
        """
        Register an agent with a specific name.
        
        Args:
            name: Name to register the agent under
            agent: Agent instance to register
        """
        self.agents[name] = agent
        if self.console:
            self.console.print(f"[green]Registered agent: {name}[/]")
    
    def register_agent(self, agent: BaseAgent) -> None:
        """
        Register an agent with the registry using its own name.
        
        Args:
            agent: Agent instance to register
        """
        self.agents[agent.name] = agent
        if self.console:
            self.console.print(f"[green]Registered agent: {agent.name}[/]")
    
    def register_multiple_agents(self, agents: List[BaseAgent]) -> None:
        """
        Register multiple agents at once.
        
        Args:
            agents: List of agent instances to register
        """
        for agent in agents:
            self.register_agent(agent)
    
    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """
        Get an agent by name.
        
        Args:
            name: Name of the agent to retrieve
            
        Returns:
            The requested agent or None if not found
        """
        agent = self.agents.get(name)
        if not agent and self.console:
            self.console.print(f"[yellow]Agent not found: {name}[/]")
        return agent
    
    def list_agents(self) -> List[str]:
        """
        List all registered agent names.
        
        Returns:
            List of registered agent names
        """
        return list(self.agents.keys())
    
    def get_agent_descriptions(self) -> Dict[str, str]:
        """
        Get descriptions of all registered agents.
        
        Returns:
            Dictionary mapping agent names to their descriptions
        """
        descriptions = {}
        for name, agent in self.agents.items():
            # Extract the first paragraph of the system instruction as the description
            if hasattr(agent, 'system_instruction') and agent.system_instruction:
                description = agent.system_instruction.strip().split('\n\n')[0]
                descriptions[name] = description
            else:
                descriptions[name] = f"{name} agent"
        
        return descriptions
    
    def remove_agent(self, name: str) -> bool:
        """
        Remove an agent from the registry.
        
        Args:
            name: Name of the agent to remove
            
        Returns:
            True if agent was removed, False if agent was not found
        """
        if name in self.agents:
            del self.agents[name]
            if self.console:
                self.console.print(f"[yellow]Removed agent: {name}[/]")
            return True
        return False

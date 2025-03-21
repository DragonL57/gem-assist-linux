"""
Initialize the agents module and expose key components.
"""

from .base_agent import BaseAgent
from .agent_registry import AgentRegistry
from .orchestrator import OrchestratorAgent
from .file_agent import FileSystemAgent
from .research_agent import ResearchAgent
from .system_agent import SystemAgent

__all__ = [
    'BaseAgent',
    'AgentRegistry',
    'OrchestratorAgent',
    'FileSystemAgent',
    'ResearchAgent',
    'SystemAgent'
]

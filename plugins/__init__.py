"""
Plugin system for gem-assist tools.
Provides infrastructure for tool registration and discovery.
"""

from .registry import ToolRegistry, get_registry
from .base import tool, capability, Plugin, PluginError
from .discovery import discover_plugins

__all__ = [
    'ToolRegistry', 'get_registry',
    'tool', 'capability', 'Plugin', 'PluginError',
    'discover_plugins'
]

"""
Base classes and decorators for tool registration.
"""
from typing import Dict, Any, Callable, Type, Optional, List
import inspect
from abc import ABC, abstractmethod
from functools import wraps

# Change relative import to absolute import
from plugins.registry import get_registry  # Changed from .registry

class Plugin(ABC):
    """
    Base class for plugin implementations.
    Plugins can register multiple related tools.
    """
    
    @classmethod
    def register(cls) -> None:
        """
        Register all tools provided by this plugin.
        Default implementation registers all methods with @tool decorator.
        """
        # This is called during plugin discovery
        pass

def capability(**kwargs) -> Callable:
    """
    Decorator to add capability metadata to a tool function.
    
    Capabilities can include:
    - description: str - Human-readable description
    - categories: List[str] - Categories this tool belongs to
    - requires_network: bool - Whether tool needs internet access
    - requires_filesystem: bool - Whether tool needs filesystem access
    - example_usage: str - Example of how to use the tool
    - rate_limited: bool - Whether tool is subject to rate limits
    - version: str - Tool version
    - author: str - Tool author
    """
    def decorator(func: Callable) -> Callable:
        if not hasattr(func, "_capabilities"):
            func._capabilities = {}
        
        # Update capabilities
        func._capabilities.update(kwargs)
        
        return func
    
    return decorator

def tool(func: Optional[Callable] = None, **kwargs) -> Callable:
    """
    Decorator to register a function as a tool.
    Can be used with or without arguments.
    
    @tool
    def my_tool():
        pass
        
    @tool(categories=["file", "io"])
    def another_tool():
        pass
    """
    def decorator(func: Callable) -> Callable:
        # Apply capability decorator if kwargs provided
        if kwargs:
            func = capability(**kwargs)(func)
        
        # Ensure _capabilities exists
        if not hasattr(func, "_capabilities"):
            func._capabilities = {}
            
        # Add docstring as description if not already set
        if "description" not in func._capabilities and func.__doc__:
            func._capabilities["description"] = inspect.getdoc(func).strip()
        
        # Register with the registry
        registry = get_registry()
        registry.register_tool(func, func._capabilities)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        return wrapper
    
    # Handle both @tool and @tool() syntax
    if func is None:
        return decorator
    else:
        return decorator(func)

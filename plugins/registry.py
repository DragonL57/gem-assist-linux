"""
Registry for tools with capability manifests and async support.
"""
from typing import Dict, List, Callable, Any, Optional, Set, Tuple, Union, Coroutine
import inspect

class ToolRegistry:
    """
    Singleton registry for tools and their capability manifests.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolRegistry, cls).__new__(cls)
            cls._instance._tools: Dict[str, Union[Callable, Coroutine]] = {}
            cls._instance._capabilities: Dict[str, Dict[str, Any]] = {}
            cls._instance._categories: Dict[str, Set[str]] = {}
            
            # Track registration status
            cls._instance._registration_errors: Dict[str, str] = {}
            cls._instance._plugin_errors: Dict[str, str] = {}
        return cls._instance
    
    def register_tool(self, func: Union[Callable, Coroutine], capabilities: Dict[str, Any] = None) -> bool:
        """
        Register a tool function with its capabilities.
        
        Args:
            func: The function to register (can be async or sync)
            capabilities: Tool capabilities
            
        Returns:
            True if registration was successful, False otherwise
        """
        name = func.__name__
        try:
            if name in self._tools:
                self._registration_errors[name] = f"Tool {name} is already registered"
                return False
            
            self._tools[name] = func
            
            # Store capabilities
            if capabilities is None:
                capabilities = {}

            # Auto-detect async status if not specified
            if "is_async" not in capabilities:
                capabilities["is_async"] = inspect.iscoroutinefunction(func)
            
            self._capabilities[name] = capabilities
            
            # Update categories
            categories = capabilities.get("categories", ["general"])
            for category in categories:
                if category not in self._categories:
                    self._categories[category] = set()
                self._categories[category].add(name)
                
            return True
            
        except Exception as e:
            self._registration_errors[name] = str(e)
            return False
    
    def is_async_tool(self, name: str) -> bool:
        """
        Check if a tool is asynchronous.
        
        Args:
            name: Name of the tool
            
        Returns:
            True if the tool is async, False if sync or not found
        """
        capabilities = self.get_capabilities(name)
        return capabilities.get("is_async", False)

    def get_async_tools(self) -> List[str]:
        """
        Get names of all async tools.
        
        Returns:
            List of tool names that are asynchronous
        """
        return [name for name, caps in self._capabilities.items() if caps.get("is_async", False)]

    def get_sync_tools(self) -> List[str]:
        """
        Get names of all synchronous tools.
        
        Returns:
            List of tool names that are synchronous
        """
        return [name for name, caps in self._capabilities.items() if not caps.get("is_async", False)]
    
    def register_plugin_error(self, plugin_name: str, error: str) -> None:
        """
        Register an error that occurred during plugin registration.
        
        Args:
            plugin_name: Name of the plugin that had an error
            error: Error message
        """
        self._plugin_errors[plugin_name] = error
    
    def get_registration_status(self) -> Dict[str, Any]:
        """
        Get the status of tool and plugin registration.
        
        Returns:
            Dictionary with registration status information
        """
        async_tools = self.get_async_tools()
        sync_tools = self.get_sync_tools()
        
        return {
            "total_tools": len(self._tools),
            "async_tools": len(async_tools),
            "sync_tools": len(sync_tools),
            "total_categories": len(self._categories),
            "tools_by_category": {category: list(tools) for category, tools in self._categories.items()},
            "async_tools_list": async_tools,
            "sync_tools_list": sync_tools,
            "tool_errors": self._registration_errors,
            "plugin_errors": self._plugin_errors
        }
    
    def get_tool(self, name: str) -> Optional[Union[Callable, Coroutine]]:
        """
        Get a registered tool by name.
        """
        return self._tools.get(name)
    
    def get_tools(self) -> Dict[str, Union[Callable, Coroutine]]:
        """
        Get all registered tools.
        """
        return self._tools
    
    def get_capabilities(self, name: str) -> Dict[str, Any]:
        """
        Get capabilities for a tool.
        """
        return self._capabilities.get(name, {})
    
    def get_tools_by_category(self, category: str) -> List[str]:
        """
        Get all tool names in a specific category.
        """
        return list(self._categories.get(category, set()))
    
    def get_categories(self) -> List[str]:
        """
        Get all available categories.
        """
        return list(self._categories.keys())

# Singleton access function
def get_registry() -> ToolRegistry:
    """
    Get the global tool registry instance.
    """
    return ToolRegistry()

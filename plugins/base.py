"""
Base classes and decorators for tool registration with async support.
"""
from typing import Dict, Any, Callable, Type, Optional, List, get_type_hints, Union, Coroutine
import inspect
from abc import ABC, abstractmethod
from functools import wraps
import asyncio

from plugins.registry import get_registry
from config.schemas.validation import create_parameter_spec, ValidationError, ParameterSpec

class PluginError(Exception):
    """
    Base exception class for plugin errors.
    Includes plugin name context with error messages.
    """
    def __init__(self, message: str, plugin_name: str):
        self.plugin_name = plugin_name
        super().__init__(f"[{plugin_name}] {message}")

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
    - is_async: bool - Whether this is an async tool
    """
    def decorator(func: Union[Callable, Coroutine]) -> Union[Callable, Coroutine]:
        if not hasattr(func, "_capabilities"):
            func._capabilities = {}
        
        # Update capabilities
        func._capabilities.update(kwargs)
        
        # Auto-detect async capability if not explicitly set
        if "is_async" not in func._capabilities:
            func._capabilities["is_async"] = inspect.iscoroutinefunction(func)
        
        return func
    
    return decorator

def tool(func: Optional[Union[Callable, Coroutine]] = None, *, params: Dict[str, Dict[str, Any]] = None, **kwargs) -> Union[Callable, Coroutine]:
    """
    Decorator to register a function as a tool with parameter validation.
    Supports both synchronous and asynchronous functions.
    
    Args:
        func: Function to decorate (can be async or sync)
        params: Parameter validation specifications
        **kwargs: Additional tool capabilities
        
    Example:
        @tool(
            params={
                "name": {
                    "type": str,
                    "required": True,
                    "regex": r"^\w+$"
                }
            },
            categories=["user"]
        )
        async def greet(name: str) -> str:
            return f"Hello {name}!"
    """
    def decorator(func: Union[Callable, Coroutine]) -> Union[Callable, Coroutine]:
        is_async = inspect.iscoroutinefunction(func)
        
        # Apply capability decorator if kwargs provided
        if kwargs:
            kwargs["is_async"] = is_async
            func = capability(**kwargs)(func)
            
        # Ensure _capabilities exists
        if not hasattr(func, "_capabilities"):
            func._capabilities = {}
            func._capabilities["is_async"] = is_async
            
        # Add docstring as description if not already set
        if "description" not in func._capabilities and func.__doc__:
            func._capabilities["description"] = inspect.getdoc(func).strip()
            
        # Get function signature info
        sig = inspect.signature(func)
        type_hints = get_type_hints(func)
        
        # Process parameters
        param_specs: Dict[str, ParameterSpec] = {}
        for name, param in sig.parameters.items():
            # Skip self/cls for methods
            if name in ('self', 'cls'):
                continue
                
            # Get validation spec
            spec = params.get(name, {}) if params else {}
            
            # Use type hint if type not specified
            if "type" not in spec and name in type_hints:
                spec["type"] = type_hints[name]
                
            # Default required based on parameter having no default
            if "required" not in spec:
                spec["required"] = param.default is param.empty
                
            # Create parameter spec
            param_specs[name] = create_parameter_spec(name, spec)
            
        # Store parameter specs
        func._param_specs = param_specs
            
        # Register with the registry
        registry = get_registry()
        registry.register_tool(func, func._capabilities)

        async def async_validate_params(args, kwargs, sig, param_specs):
            """Validate parameters for async functions."""
            # Skip validation for self/cls
            if inspect.ismethod(func):
                param_values = dict(zip(list(sig.parameters)[1:], args[1:]))
            else:
                param_values = dict(zip(sig.parameters, args))
            param_values.update(kwargs)
            
            # Validate parameters
            for name, spec in param_specs.items():
                value = param_values.get(name)
                try:
                    if inspect.iscoroutinefunction(spec.validate):
                        await spec.validate(value)
                    else:
                        spec.validate(value)
                except ValidationError as e:
                    raise PluginError(str(e), func.__module__)
            
            return param_values

        def sync_validate_params(args, kwargs, sig, param_specs):
            """Validate parameters for sync functions."""
            # Skip validation for self/cls
            if inspect.ismethod(func):
                param_values = dict(zip(list(sig.parameters)[1:], args[1:]))
            else:
                param_values = dict(zip(sig.parameters, args))
            param_values.update(kwargs)
            
            # Validate parameters
            for name, spec in param_specs.items():
                value = param_values.get(name)
                try:
                    spec.validate(value)
                except ValidationError as e:
                    raise PluginError(str(e), func.__module__)
            
            return param_values
        
        if is_async:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                await async_validate_params(args, kwargs, sig, param_specs)
                return await func(*args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                sync_validate_params(args, kwargs, sig, param_specs)
                return func(*args, **kwargs)
            return sync_wrapper
    
    # Handle both @tool and @tool() syntax
    if func is None:
        return decorator
    else:
        return decorator(func)

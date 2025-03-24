"""
Discovery mechanisms for plugins.
"""
import os
import sys
import importlib
import importlib.util
import inspect
from typing import List, Type, Dict, Any, Tuple

# Change relative imports to absolute imports
from plugins.base import Plugin  # Changed from .base
from plugins.registry import get_registry  # Changed from .registry

def discover_plugins(plugin_dirs: List[str] = None) -> Dict[str, Any]:
    """
    Discover and load plugins from specified directories.
    
    Args:
        plugin_dirs: List of directories to search for plugins
                    If None, searches in default locations
                    
    Returns:
        Dictionary with registration results and status
    """
    registry = get_registry()
    
    if plugin_dirs is None:
        # Default plugin locations
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        plugin_dirs = [
            os.path.join(base_dir, "plugins"),
            os.path.join(base_dir, "utils"),
        ]
    
    plugins = {}
    plugin_stats = {
        "loaded_plugins": 0,
        "loaded_tools": 0,
        "errored_plugins": 0,
        "discovered_dirs": len(plugin_dirs),
    }
    
    # Add plugin directories to path if not already there
    for plugin_dir in plugin_dirs:
        if os.path.isdir(plugin_dir) and plugin_dir not in sys.path:
            sys.path.append(plugin_dir)
    
    # Discover plugins in each directory
    for plugin_dir in plugin_dirs:
        if not os.path.isdir(plugin_dir):
            continue
            
        # Look for Python files and packages
        for item in os.listdir(plugin_dir):
            if item.startswith("_"):
                continue
                
            path = os.path.join(plugin_dir, item)
            
            # Handle Python files
            if item.endswith(".py"):
                module_name = item[:-3]
                try:
                    # Import the module
                    spec = importlib.util.spec_from_file_location(module_name, path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        # Look for Plugin subclasses
                        plugin_found = False
                        for name, obj in inspect.getmembers(module):
                            if (inspect.isclass(obj) and 
                                issubclass(obj, Plugin) and 
                                obj is not Plugin):
                                plugins[f"{module_name}.{name}"] = obj
                                obj.register()  # Register the plugin
                                plugin_found = True
                                plugin_stats["loaded_plugins"] += 1
                        
                        # Also look for standalone tool functions
                        for name, obj in inspect.getmembers(module):
                            if inspect.isfunction(obj) and hasattr(obj, "_capabilities"):
                                # Already registered by the @tool decorator
                                plugin_stats["loaded_tools"] += 1
                        
                        if not plugin_found:
                            # If no plugin class was found, this isn't an error
                            pass
                                
                except Exception as e:
                    error_msg = f"Error importing plugin module {module_name}: {e}"
                    registry.register_plugin_error(module_name, error_msg)
                    plugin_stats["errored_plugins"] += 1
            
            # Handle packages (directories with __init__.py)
            elif os.path.isdir(path) and os.path.exists(os.path.join(path, "__init__.py")):
                try:
                    module = importlib.import_module(item)
                    
                    # Look for Plugin subclasses
                    plugin_found = False
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, Plugin) and 
                            obj is not Plugin):
                            plugins[f"{item}.{name}"] = obj
                            obj.register()  # Register the plugin
                            plugin_found = True
                            plugin_stats["loaded_plugins"] += 1
                    
                    if not plugin_found:
                        # If no plugin class was found, this isn't an error
                        pass
                            
                except Exception as e:
                    error_msg = f"Error importing plugin package {item}: {e}"
                    registry.register_plugin_error(item, error_msg)
                    plugin_stats["errored_plugins"] += 1
    
    # Update tool count from the registry
    registry_status = registry.get_registration_status()
    plugin_stats["total_tools"] = registry_status["total_tools"]
    plugin_stats["total_categories"] = registry_status["total_categories"]
    plugin_stats["tool_errors"] = len(registry_status["tool_errors"])
    plugin_stats["plugin_errors"] = len(registry_status["plugin_errors"])
    
    return {
        "plugins": plugins,
        "stats": plugin_stats,
        "status": registry_status
    }

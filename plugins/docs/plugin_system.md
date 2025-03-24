# Plugin System for gem-assist

This document explains how to use the new plugin architecture for tools in gem-assist.

## Overview

The plugin system allows tools to self-register with capability manifests, making the system more modular and extensible. Instead of explicitly listing tools in a central location, tools now register themselves, allowing for:

- Dynamic discovery of tools
- Tool categorization and filtering
- Structured capability manifests
- Easy addition of new tools without modifying core code

## Using the Plugin System

### Converting Existing Tools

To convert existing functions to use the plugin system, add the `@tool` decorator:

```python
from plugins import tool, capability

@tool(categories=["filesystem", "metadata"])
def get_file_metadata(filepath: str) -> dict:
    """Get metadata for a file."""
    # Implementation
    pass
```

### Defining Tool Capabilities

Use the `@capability` decorator to define detailed capabilities:

```python
@tool
@capability(
    categories=["web", "content"],
    requires_network=True,
    rate_limited=True,
    example_usage="get_website_text_content('https://example.com')"
)
def get_website_text_content(url: str) -> str:
    """Extract text content from a webpage."""
    # Implementation
    pass
```

### Creating a Plugin Class

For groups of related tools, create a Plugin class:

```python
from plugins import Plugin, tool

class MyPlugin(Plugin):
    """Plugin providing related functionality."""
    
    @staticmethod
    @tool(categories=["my_category"])
    def my_tool() -> str:
        """Tool description"""
        return "Result"
```

### Available Capability Attributes

- `description`: Human-readable description
- `categories`: List of categories this tool belongs to
- `requires_network`: Whether tool needs internet access
- `requires_filesystem`: Whether tool needs filesystem access
- `example_usage`: Example of how to use the tool
- `rate_limited`: Whether tool is subject to rate limits
- `version`: Tool version
- `author`: Tool author

## Discovery Process

Tools are discovered and registered in the following ways:

1. Automatically through the `@tool` decorator when modules are imported
2. By the `discover_plugins()` function which scans directories for plugins
3. Through explicit registration using `ToolRegistry().register_tool()`

## Working with the Registry

You can access the tool registry to query available tools:

```python
from plugins import get_registry

registry = get_registry()

# Get all tools
all_tools = registry.get_tools()

# Get tools by category
file_tools = registry.get_tools_by_category("filesystem")

# Get tool capabilities
capabilities = registry.get_capabilities("get_file_metadata")
```

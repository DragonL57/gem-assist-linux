"""
Example plugin demonstrating both sync and async tools with error handling.
"""
import asyncio
from typing import Optional, Dict, Any
import aiohttp

from plugins.base import Plugin, tool
from assistant.exceptions.base import ToolExecutionError

# ExamplePlugin class removed to eliminate example/redundant tools.

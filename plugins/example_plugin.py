"""
Example plugin demonstrating both sync and async tools with error handling.
"""
import asyncio
from typing import Optional, Dict, Any
import aiohttp

from plugins.base import Plugin, tool
from assistant.exceptions.base import ToolExecutionError

class ExamplePlugin(Plugin):
    """Example plugin with both sync and async tools."""
    
    @tool(params={
        "name": {
            "type": str,
            "required": True,
            "description": "The name to greet"
        },
        "delay": {
            "type": float,
            "required": False,
            "default": 0.0,
            "description": "Optional delay in seconds"
        }
    })
    async def async_greet(self, name: str, delay: float = 0.0) -> str:
        """
        Asynchronously greet someone, with an optional delay.
        
        Args:
            name: The name to greet
            delay: Optional delay in seconds
            
        Returns:
            The greeting message
        """
        if delay > 0:
            await asyncio.sleep(delay)
        return f"Hello {name}! (async greeting after {delay}s delay)"

    @tool(params={
        "url": {
            "type": str,
            "required": True,
            "description": "URL to fetch"
        }
    })
    async def fetch_url(self, url: str) -> str:
        """
        Fetch content from a URL asynchronously.
        Demonstrates proper async error handling.
        
        Args:
            url: The URL to fetch
            
        Returns:
            The fetched content
            
        Raises:
            ToolExecutionError: If the fetch fails
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise ToolExecutionError(
                            message=f"Failed to fetch URL: {response.status}",
                            tool_name=self.fetch_url.__name__,
                            tool_args={"url": url},
                            details={
                                "status": response.status,
                                "reason": response.reason
                            }
                        )
                    return await response.text()
        except aiohttp.ClientError as e:
            raise ToolExecutionError(
                message=f"Network error: {str(e)}",
                tool_name=self.fetch_url.__name__,
                tool_args={"url": url},
                details={"error": str(e)}
            ) from e
        except Exception as e:
            raise ToolExecutionError(
                message=f"Unexpected error: {str(e)}",
                tool_name=self.fetch_url.__name__,
                tool_args={"url": url},
                details={"error": str(e)}
            ) from e

    @tool(params={
        "text": {
            "type": str,
            "required": True,
            "description": "Text to echo"
        }
    })
    def sync_echo(self, text: str) -> str:
        """
        Simply echo back the input text (synchronously).
        Demonstrates sync tool handling.
        
        Args:
            text: Text to echo back
            
        Returns:
            The same text
        """
        return f"Echo: {text}"

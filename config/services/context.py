"""
System context and dynamic information management.
"""
from .system import get_system_service
from .location import get_location_service
from datetime import datetime
from typing import Optional
from ..settings import get_settings # Add this import

async def get_context_info() -> str:
    """Get current system context information.

    Returns:
        Formatted context information string
    """
    system = get_system_service().get_system_info()
    settings = get_settings()  # Get settings
    location = get_location_service(  # Pass required arguments
        settings.LOCATION_API_URL,
        settings.LOCATION_TIMEOUT
    )
    location_info = await location.get_location()

    return f"""
# SYSTEM CONTEXT
- Assistant Name: {{name}}  # Will be formatted by caller
- Current Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- Operating System: {system.os_name} {system.os_version}
- Python Version: {system.python_version}
- {location_info.formatted}
"""

async def format_prompt_with_context(prompt: str, assistant_name: Optional[str] = None) -> str:
    """Format a prompt with current context information.
    
    Args:
        prompt: The prompt template to format
        assistant_name: Optional assistant name to include
        
    Returns:
        Formatted prompt with context information
    """
    context = await get_context_info()
    
    # Replace placeholders with values
    formatted = prompt.format(
        context=context,
        name=assistant_name or "Assistant"
    )
    
    return formatted

async def get_system_prompt(name: str) -> str:
    """Get the base system prompt with current context.
    
    Args:
        name: Assistant name
        
    Returns:
        Formatted system prompt
    """
    from ..prompts import get_prompt_manager
    
    base_prompt = get_prompt_manager().base_system_prompt
    return await format_prompt_with_context(base_prompt, name)

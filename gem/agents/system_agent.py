"""
System operations specialized agent.
"""
from typing import List, Callable, Dict, Any
from rich.console import Console

from .base_agent import BaseAgent
from utils import (
    get_system_info, run_shell_command, get_current_datetime,
    evaluate_math_expression, get_environment_variable
)

class SystemAgent(BaseAgent):
    def __init__(
        self,
        model: str,
        console: Console = None
    ):
        # Collect all system-related tools
        system_tools = [
            get_system_info, run_shell_command, get_current_datetime,
            evaluate_math_expression, get_environment_variable
        ]
        
        system_instruction = """
        You are a specialized system agent that handles operations related to the operating system.
        Your job is to:
        1. Execute shell commands safely and effectively
        2. Retrieve system information
        3. Access environment variables
        4. Handle date/time operations
        5. Evaluate mathematical expressions
        
        IMPORTANT GUIDELINES:
        - Always run commands safely, avoiding anything that could damage the system
        - For file operations:
          * Check paths before operations
          * Use proper quoting for paths with spaces or special characters
          * Verify results after operations
        - For commands that might fail, use proper error handling:
          * Check if files exist before operating on them
          * Verify command execution results
        
        DOCUMENT CONVERSION BEST PRACTICES:
        When working with document conversions (like .docx to PDF):
        1. First use get_current_directory() or run_shell_command("pwd") to establish context
        2. Use absolute paths in commands
        3. For LibreOffice conversions, the format is:
           libreoffice --headless --convert-to pdf "/path/to/input.docx" --outdir "/path/to/output/dir"
        4. Always verify results after conversion with appropriate commands
        5. If first attempt fails, try alternative approaches
        
        Be very careful with shell commands - verify they are safe before execution.
        Avoid commands that could damage the system or expose sensitive information.
        """
        
        super().__init__(
            name="System",
            model=model,
            tools=system_tools,
            system_instruction=system_instruction,
            console=console
        )
    
    def act(self, query: str) -> Dict[str, Any]:
        """Process system-related tasks with improved guidance."""
        # Use general guidance without hardcoding specific logic
        enhanced_query = f"""Task: {query}
        
        When handling this task:
        1. Select the most appropriate tools for the job
        2. Consider system commands when direct tools aren't available
        3. Be careful with command execution, especially with non-ASCII paths
        4. Always verify results after operations
        
        Please complete this task efficiently and safely."""
        
        return super().act(enhanced_query)

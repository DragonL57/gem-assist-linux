"""
System operations specialized agent.
"""
from typing import List, Callable, Dict, Any
from rich.console import Console
import json
import os
import time
import re
import shlex

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
            evaluate_math_expression, get_environment_variable,
            self.handle_command_retry, self.validate_command
        ]
        
        system_instruction = """
        You are a specialized system agent that handles operations related to the operating system.
        Your job is to:
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
    
    def act(self, query: str, task_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process system-related tasks with improved guidance."""
        # Use general guidance without hardcoding specific logic
        enhanced_query = f"""Task: {query}
        
        When handling this task:
        1. Select the most appropriate tools for the job
        2. Consider system commands when direct tools aren't available
        3. Be careful with command execution, especially with non-ASCII paths
        4. Always verify results after operations
        
        Please complete this task efficiently and safely."""
        
        return super().act(enhanced_query, task_context)
    
    def handle_command_retry(self, command: str, max_attempts: int = 3, delay_seconds: int = 2) -> Dict[str, Any]:
        """
        Retry a command multiple times if it fails.
        
        Args:
            command: The shell command to execute
            max_attempts: Maximum number of attempts (default: 3)
            delay_seconds: Delay between attempts in seconds (default: 2)
            
        Returns:
            Result of the command execution with retry information
        """
        # First validate the command for safety
        validation_result = self.validate_command(command)
        if not validation_result["safe"]:
            return {
                "success": False,
                "result": f"Command validation failed: {validation_result['reason']}",
                "attempts": 0,
                "command": command
            }
            
        # Track attempts and errors
        attempts = 0
        errors = []
        
        while attempts < max_attempts:
            attempts += 1
            
            try:
                # Track operation in context
                self.context.track_operation(
                    agent=self.name,
                    operation="run_command_retry",
                    details={"command": command, "attempt": attempts},
                    success=True
                )
                
                # Execute command
                result = run_shell_command(command, blocking=True, print_output=False)
                
                # If command succeeds (no exception), return result
                return {
                    "success": True,
                    "result": result,
                    "attempts": attempts,
                    "command": command
                }
                
            except Exception as e:
                error_msg = str(e)
                errors.append(f"Attempt {attempts}: {error_msg}")
                
                # Log error but don't mark as failure until all attempts are exhausted
                self.console.print(f"[yellow]Command failed (attempt {attempts}/{max_attempts}): {error_msg}[/]")
                
                # Wait before retrying unless this is the last attempt
                if attempts < max_attempts:
                    time.sleep(delay_seconds)
        
        # If we get here, all attempts failed
        error_summary = "\n".join(errors)
        
        # Log the final failure
        self.context.log_error(
            agent=self.name,
            operation="run_command_retry",
            details={"command": command, "max_attempts": max_attempts},
            error_message=error_summary
        )
        
        return {
            "success": False,
            "result": f"Command failed after {attempts} attempts:\n{error_summary}",
            "attempts": attempts,
            "command": command
        }
    
    def validate_command(self, command: str) -> Dict[str, Any]:
        """
        Validate if a shell command is safe to execute.
        
        Args:
            command: The shell command to validate
            
        Returns:
            Validation result with safety assessment
        """
        # Dangerous commands or patterns to block
        dangerous_patterns = [
            r'rm\s+(-rf?|--recursive)\s+/', # rm -rf / or similar
            r'dd.*of=/dev/', # Writing directly to devices
            r':(){ :\|:& };:', # Fork bomb
            r'>(>?)\s*/dev/[hs]d[a-z]', # Direct writes to disk devices
            r'chmod\s+-[R].*777', # Recursive chmod with 777
            r'wget.*\|\s*sh', # Downloading and directly executing
            r'curl.*\|\s*sh', # Curl and direct execution
            r'sudo\s+rm', # sudo with rm
            r'mkfs', # Formatting filesystems
            r'dd\s+.*\s+of=', # dd with output file (potential for overwriting)
            r'>[> ]+[^.]*$', # Redirecting output to overwrite file without extension
            r'reboot', # System reboot
            r'shutdown', # System shutdown
            r'halt', # System halt
            r'systemctl (stop|disable|mask)', # Stopping system services
            r'passwd', # Password changes
            r'useradd|userdel', # User management
            r'chown\s+-[R]', # Recursive ownership changes
            r'pkill', # Process killing
        ]
        
        # Trim the command and convert to lowercase for basic checks
        cmd_lower = command.lower().strip()
        
        # Quick check for common dangerous commands
        if any(dangerous_cmd in cmd_lower for dangerous_cmd in [
            'rm -rf /', 'rm -f /', 'mkfs', 'dd if=/dev/zero', 
            ':(){', 'wget', 'curl', '| sh', '| bash'
        ]):
            return {
                "safe": False,
                "reason": "Command contains potentially dangerous operations",
                "command": command
            }
            
        # More thorough pattern matching
        for pattern in dangerous_patterns:
            if re.search(pattern, command):
                return {
                    "safe": False,
                    "reason": f"Command matches dangerous pattern: {pattern}",
                    "command": command
                }
                
        # Check command length (excessively long commands might be suspicious)
        if len(command) > 500:
            return {
                "safe": False,
                "reason": "Command is suspiciously long",
                "command": command
            }
            
        # Check for multiple commands chained with ; && ||
        command_parts = re.split(r'[;&|]{1,2}', command)
        if len(command_parts) > 5:
            return {
                "safe": False,
                "reason": "Too many chained commands",
                "command": command
            }
            
        # Try to parse the command to check for syntax issues
        try:
            shlex.split(command)
        except Exception as e:
            return {
                "safe": False, 
                "reason": f"Command parsing error: {str(e)}",
                "command": command
            }
            
        # If all checks pass, consider the command safe
        return {
            "safe": True,
            "command": command
        }

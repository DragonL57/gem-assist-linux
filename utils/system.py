"""
System utility functions for the gem-assist package.
These functions are used for system operations, command execution, and environment variables.
"""

import os
import datetime
import platform
import subprocess
import threading
from typing import Optional, Dict, Any
import json
from concurrent.futures import ThreadPoolExecutor

from .core import tool_message_print, tool_report_print

# Import the new SystemInfoCollector if available
try:
    from .system_info import SystemInfoCollector, get_system_info_report
    SYSTEM_INFO_COLLECTOR_AVAILABLE = True
except ImportError:
    SYSTEM_INFO_COLLECTOR_AVAILABLE = False

def get_system_info() -> Dict[str, Any]:
    """
    Get detailed system information including CPU, memory, disk usage, and more.
    
    Returns:
        Dictionary containing system information
    """
    tool_message_print("get_system_info", [])
    
    try:
        if SYSTEM_INFO_COLLECTOR_AVAILABLE:
            # Use the enhanced collector if available
            collector = SystemInfoCollector()
            result = {
                **collector.get_basic_system_info(),
                "advanced_info": collector.get_advanced_system_info(),
                "cpu_details": collector.get_detailed_cpu_info(),
            }
            tool_report_print("System information retrieved:", "Successfully collected system information")
            return result
        else:
            # Fall back to simple system info
            result = {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "date_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            tool_report_print("Basic system information retrieved:", "Advanced info not available (psutil not installed)")
            return result
    except Exception as e:
        tool_report_print("Error retrieving system information:", str(e), is_error=True)
        return {"error": f"Failed to retrieve system information: {str(e)}"}

def run_shell_command(command: str, blocking: bool = True, print_output: bool = False) -> Optional[str]:
    """
    Run a shell command and return its output.
    
    Args:
        command: The command to run
        blocking: Whether to wait for the command to finish
        print_output: Whether to print the command output to the terminal
        
    Returns:
        The command output as a string, or None if the command is non-blocking
    """
    tool_message_print("run_shell_command", [
        ("command", command),
        ("blocking", str(blocking)),
        ("print_output", str(print_output))
    ])
    
    def _run_command():
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            
            if stderr:
                tool_report_print("Error running command:", stderr, is_error=True)
                return f"Error running command: {stderr}"
                
            tool_report_print("Status:", "Command executed successfully")
            if print_output:
                print(stdout)
            return stdout.strip() 
        
        except Exception as e:
            tool_report_print("Error running shell command:", str(e), is_error=True)
            return f"Error running shell command: {e}"
    
    if blocking:
        # Run synchronously
        return _run_command()
    else:
        # Run asynchronously in a separate thread
        thread = threading.Thread(target=_run_command)
        thread.daemon = True
        thread.start()
        return None

def get_current_datetime(format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Get the current date and time in a specified format.
    
    Args:
        format_str: The format string for the datetime (follows strftime format)
        
    Returns:
        The current date and time as a formatted string
    """
    tool_message_print("get_current_datetime", [("format", format_str)])
    
    try:
        current_time = datetime.datetime.now()
        formatted_time = current_time.strftime(format_str)
        tool_report_print("Current datetime:", formatted_time)
        return formatted_time
    except ValueError as e:
        tool_report_print("Error formatting datetime:", str(e), is_error=True)
        # Fallback to default format
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# evaluate_math_expression function removed - use execute_python_code or run_shell_command instead

def get_environment_variable(key: str) -> str:
    """
    Get the value of an environment variable.
    
    Args:
        key: The name of the environment variable
        
    Returns:
        The value of the environment variable, or an error message if not found
    """
    tool_message_print("get_environment_variable", [("key", key)])
    
    value = os.environ.get(key)
    if value is not None:
        tool_report_print("Environment variable retrieved:", f"{key}={value}")
        return value
    else:
        tool_report_print("Environment variable not found:", key, is_error=True)
        return f"Environment variable '{key}' not found"

def get_current_directory() -> str:
    """
    Get the current working directory.
    
    Returns:
        The absolute path of the current working directory
    """
    tool_message_print("get_current_directory", [])
    
    current_dir = os.path.abspath(os.getcwd())
    tool_report_print("Current directory:", current_dir)
    return current_dir

def run_parallel_commands(commands: list[str], timeout: int = 30) -> Dict[str, str]:
    """
    Run multiple shell commands in parallel and return their outputs.
    
    Args:
        commands: List of commands to run
        timeout: Maximum execution time in seconds per command
        
    Returns:
        Dictionary mapping each command to its output
    """
    tool_message_print("run_parallel_commands", [
        ("commands", str(len(commands))),
        ("timeout", str(timeout))
    ])
    
    results = {}
    
    def execute_cmd(cmd):
        try:
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(timeout=timeout)
            return stdout if not stderr else f"Error: {stderr}\n{stdout}"
        except subprocess.TimeoutExpired:
            return f"Command timed out after {timeout} seconds"
        except Exception as e:
            return f"Failed to execute command: {str(e)}"
    
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(execute_cmd, cmd): cmd for cmd in commands}
        for future in futures:
            cmd = futures[future]
            try:
                results[cmd] = future.result()
            except Exception as e:
                results[cmd] = f"Error: {str(e)}"
    
    completed_count = sum(1 for output in results.values() if not output.startswith("Error") and not output.startswith("Command timed out"))
    tool_report_print("Parallel command execution:", f"Completed {completed_count}/{len(commands)} commands successfully")
    return results

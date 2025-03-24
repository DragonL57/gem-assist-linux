"""
Core utility functions for the gem-assist project.
These functions are used across the various tool modules.
"""

import colorama
from colorama import Fore, Style
from rich.console import Console
from rich.theme import Theme
import time

# Initialize colorama
colorama.init(autoreset=True)

# Create a Rich console with a custom theme
theme = Theme({
    "tool": "cyan",
    "arg_name": "yellow",
    "arg_value": "bright_white",
    "success": "green",
    "error": "bold red",
    "warning": "yellow",
    "info": "blue"
})

console = Console(theme=theme)

def tool_message_print(msg: str, args: list = None):
    """Print a formatted tool message with enhanced visibility."""
    if args:
        args_str = ", ".join(f"{Fore.YELLOW}{k}{Style.RESET_ALL}={Fore.WHITE}{v}{Style.RESET_ALL}" for k, v in args)
        print(f"{Fore.CYAN}> {msg}{Style.RESET_ALL} ({args_str})")
    else:
        print(f"{Fore.CYAN}> {msg}{Style.RESET_ALL}")

def tool_report_print(msg: str, value: str = None, is_error: bool = False, execution_time: float = None):
    """Print a formatted tool result with enhanced details."""
    if is_error:
        status_prefix = f"{Fore.RED}✗{Style.RESET_ALL}"
    else:
        status_prefix = f"{Fore.GREEN}✓{Style.RESET_ALL}"
    
    # Format the message
    message = f"{status_prefix} {msg}"
    
    # Add value if provided
    if value is not None:
        message += f": {value}"
    
    # Add execution time if provided
    if execution_time is not None:
        message += f" ({execution_time:.2f}s)"
    
    print(message)

"""
Core utility functions for the gem-assist package.
These functions are used across the various tools modules.
"""

import os
import time
import colorama
from colorama import Fore, Style
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme
from rich.markdown import Markdown
from rich.table import Table
from rich.box import ROUNDED
import json
import datetime
import re

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

def tool_message_print(msg: str, args: list[tuple[str, str]] = None):
    """Print a formatted tool message with enhanced visibility."""
    # Format the message
    if args:
        arg_str = ", ".join(f"[arg_name]{name}[/]=[arg_value]{value}[/]" for name, value in args)
        console.print(f"[tool]> {msg}[/]({arg_str})")
    else:
        console.print(f"[tool]> {msg}[/]()")

def tool_report_print(msg: str, value: str, is_error: bool = False, execution_time: float = None):
    """Print a formatted tool result with enhanced details."""
    status_style = "error" if is_error else "success"
    prefix = "✗" if is_error else "✓"
    
    # Add execution time if provided
    time_info = f" in {execution_time:.4f}s" if execution_time is not None else ""
    
    console.print(f"[{status_style}]{prefix} {msg}{time_info}:[/] {value}")

# Memory-related functions have been removed

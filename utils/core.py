"""
Core utility functions for the gem-assist package.
These functions are used across the various tools modules.
"""

import os
import colorama
from colorama import Fore, Style
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme
from rich.markdown import Markdown
from rich.table import Table
from rich.box import ROUNDED

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
    """
    Prints a tool message with the given message and arguments using Rich formatting.

    Args:
        msg: The message to print.
        args: A list of tuples containing the argument name and value. Optional.
    """
    # Create a table for the tool info with a rounded box
    table = Table(box=ROUNDED, show_header=False, show_edge=False, expand=False)
    table.add_column("Key", style="tool")
    table.add_column("Value")
    
    # Add the tool name as the first row
    table.add_row("[tool]TOOL[/]", f"[bright_white]{msg}[/]")
    
    # Add arguments as rows if provided
    if args:
        for arg_name, arg_value in args:
            table.add_row(f"[arg_name]{arg_name}[/]", f"[arg_value]{arg_value}[/]")
    
    # Add a subtle border around the tool information
    panel = Panel(
        table,
        border_style="cyan",
        padding=(0, 1),
        expand=False
    )
    console.print(panel)

def tool_report_print(msg: str, value: str, is_error: bool = False):
    """
    Print when a tool needs to put out a message as a report with enhanced formatting.

    Args:
        msg: The message to print.
        value: The value to print.
        is_error: Whether this is an error message. If True, value will be printed in red.
    """
    style = "error" if is_error else "success"
    prefix = "❌" if is_error else "✓"
    
    console.print(
        f"  {prefix} {msg} [bold {style}]{value}[/]"
    )

def write_note(message: str):
    """
    A function for YOU the AI to write down any problem you face while using tools that doesn't work or need fixing or if you want to remember something
    write down the things YOU the assistant want to remember, YOU dont have to ask for confirmation to user, the user doesn't need to know this exists
    Use it whenever needed and you wanna save a piece of information including bug reports.
    This is not a TODO for the user but the assistant

    These notes will be preloaded the next time you are started
    """
    tool_message_print("write_note")
    with open("ai-log.txt", "a+") as f:
        f.write(message +"\n")

def read_note() -> str:
    """
    Read the previously saved notes, (assistant only)

    Returns: string of previously saved log notes
    """
    tool_message_print("read_note")
    if os.path.exists("./ai-log.txt"):
        with open("ai-log.txt", "r", encoding="utf-8") as f:
            return f.read()
    else:
        return ""

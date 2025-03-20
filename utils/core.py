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
    console = Console()
    
    # Create a more detailed and visually distinct title
    title = Text("🔧 TOOL EXECUTION", style="bold cyan")
    
    content = []
    content.append(Text(f"Tool: ", style="cyan bold") + Text(msg, style="white bold"))
    
    if args:
        args_text = Text("\nArguments:", style="cyan")
        content.append(args_text)
        
        # Create a more structured arguments display
        for arg_name, arg_value in args:
            arg_text = Text()
            arg_text.append(f"  • {arg_name}: ", style="cyan")
            
            # Format the value based on its length
            if isinstance(arg_value, str) and len(arg_value) > 100:
                display_value = arg_value[:97] + "..."
            else:
                display_value = str(arg_value)
                
            arg_text.append(display_value)
            content.append(arg_text)
    
    panel = Panel(
        "\n".join(str(item) for item in content),
        title=title,
        border_style="cyan",
        expand=False
    )
    console.print(panel)

def tool_report_print(msg: str, value: str, is_error: bool = False, execution_time: float = None):
    """Print a formatted tool result with enhanced details."""
    console = Console()
    
    # Create a more informative title with emoji
    emoji = "❌" if is_error else "✅"
    title = Text(f"{emoji} TOOL RESULT", style="bold red" if is_error else "bold green")
    
    content = []
    
    # Add the main message and value
    main_text = Text()
    main_text.append(f"{msg} ", style="bold")
    main_text.append(value, style="red" if is_error else None)
    content.append(main_text)
    
    # Add execution time if provided
    if execution_time is not None:
        time_text = Text(f"\nExecution time: {execution_time:.4f} seconds", style="dim")
        content.append(time_text)
    
    panel = Panel(
        "\n".join(str(item) for item in content),
        title=title,
        border_style="red" if is_error else "green",
        expand=False
    )
    console.print(panel)

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

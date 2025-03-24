"""
Terminal UI components for gem-assist using Rich library.
These components provide a clean, streamlined visual experience in the terminal.
"""

from rich.console import Console
from rich.text import Text
from rich.markdown import Markdown
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.theme import Theme
import time
from typing import Dict, Any

# Define the theme for consistent styling
THEME = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "user": "bold magenta",
    "assistant": "bold green",
    "tool": "cyan",
    "header": "bold blue on default",
    "command": "bold yellow",
    "code": "grey70",
    "highlight": "bold cyan",
})

# Create a console with our theme
console = Console(theme=THEME)

def print_header(title: str, subtitle: str = None):
    """Print a clean header with optional subtitle"""
    console.print()
    console.print(f"[header]{title}[/]", justify="center", style="bold")
    
    if subtitle:
        console.print(Text(subtitle, justify="center", style="dim"))
    
    console.print()

def print_user_message(message: str):
    """Print a user message with simple prefix"""
    console.print()
    # Make "You:" more prominently magenta by using a direct style application
    console.print("[bold magenta]You:[/]")  # Explicitly use bold magenta for emphasis
    console.print(Text(message, style="bright_white"))  # User text in bright white for better visibility
    console.print()

def print_assistant_message(message: str, assistant_name: str = "Assistant"):
    """Print an assistant message with markdown formatting"""
    console.print()
    console.print(f"[assistant]{assistant_name}:[/] ", end="")
    console.print(Markdown(message, code_theme="monokai"))
    console.print()

def print_tool_call(tool_name: str, args: Dict[str, Any] = None):
    """Print tool call information with subtle formatting"""
    console.print()
    if args:
        args_str = ", ".join(f"[dim]{k}=[/][highlight]{v}[/]" for k, v in args.items())
        console.print(f"[tool]→ {tool_name}[/]({args_str})")
    else:
        console.print(f"[tool]→ {tool_name}[/]()")

def print_tool_result(result: str, tool_name: str, success: bool = True):
    """Print tool execution result with clear status indicator"""
    style = "success" if success else "error"
    prefix = "✓" if success else "✗"
    
    console.print(f"[{style}]{prefix} {tool_name}:[/] {result}")
    console.print()

def create_progress_display(description: str = "Processing"):
    """Create a progress bar for long-running operations"""
    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        "•",
        TaskProgressColumn(),
        "•",
        TimeElapsedColumn(),
        console=console
    )
    
    task = progress.add_task(f"[cyan]{description}[/]", total=100)
    return progress, task

def display_info(message: str):
    """Display an informational message"""
    console.print(f"[info]ℹ {message}[/]")

def display_warning(message: str):
    """Display a warning message"""
    console.print(f"[warning]⚠ {message}[/]")

def display_error(message: str):
    """Display an error message"""
    console.print(f"[error]✗ {message}[/]")

def display_success(message: str):
    """Display a success message"""
    console.print(f"[success]✓ {message}[/]")

def demo():
    """Demo all UI components"""
    console.clear()
    print_header("GEM ASSIST TERMINAL UI COMPONENTS", "Clean terminal interface")
    
    print_user_message("Show me examples of all UI components")
    
    print_assistant_message(
        "Here are examples of the different UI components available:\n\n"
        "1. **Headers** - The title at the top\n"
        "2. **User Messages** - How your messages appear\n"
        "3. **Assistant Messages** - How I respond with Markdown support\n"
        "4. **Tool Calls** - When I use tools\n"
        "5. **Tool Results** - The results from tools\n"
        "6. **Progress Bars** - For tracking long operations"
    )
    
    print_tool_call("search_wikipedia", {"query": "Python programming language"})
    
    print_tool_result(
        "Python is a high-level programming language. Its design philosophy emphasizes code readability.",
        "search_wikipedia"
    )
    
    # Demo a progress bar
    display_info("Demonstrating progress bar...")
    progress, task = create_progress_display("Downloading data")
    
    with progress:
        for i in range(100):
            time.sleep(0.02)  # Simulate work
            progress.update(task, completed=i+1)
    
    print_tool_result("Download failed: Connection timeout", "download_file", success=False)
    
    display_warning("This is a warning message")
    display_error("This is an error message")
    display_success("This is a success message")
    
    print_assistant_message(
        "These components create a clean interface with good readability.\n\n"
        "```python\n"
        "def hello_world():\n"
        "    print('Hello from Rich!')\n"
        "```\n\n"
        "You can use them in your application for a better user experience."
    )

if __name__ == "__main__":
    demo()

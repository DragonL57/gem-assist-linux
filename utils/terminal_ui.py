"""
Terminal UI components for gem-assist using Rich library.
These components provide an enhanced visual experience in the terminal.
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.table import Table
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.layout import Layout
from rich.box import ROUNDED, SIMPLE, DOUBLE
from rich.theme import Theme
from rich.style import Style
from rich.padding import Padding
from rich.live import Live
import time
from typing import List, Dict, Any, Callable

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

def print_header(title: str, subtitle: str = None, style: str = "blue"):
    """Print a styled header with optional subtitle"""
    panel = Panel(
        Text(title, justify="center", style="bold"),
        border_style=style,
        padding=(1, 2),
    )
    console.print(panel)
    
    if subtitle:
        console.print(Text(subtitle, justify="center", style="dim"))
        
def print_user_message(message: str):
    """Print a user message in a styled panel"""
    panel = Panel(
        Text(message),
        title="[user]You[/]",
        border_style="magenta",
        padding=(1, 1),
        expand=False
    )
    console.print(panel)
    
def print_assistant_message(message: str, assistant_name: str = "Assistant"):
    """Print an assistant message with markdown formatting"""
    panel = Panel(
        Markdown(message),
        title=f"[assistant]{assistant_name}[/]",
        border_style="green",
        padding=(1, 2),
        expand=False
    )
    console.print(panel)

def print_tool_call(tool_name: str, args: Dict[str, Any] = None):
    """Print information about a tool being called"""
    table = Table(box=SIMPLE, show_header=False, expand=False)
    table.add_column("", style="tool")
    table.add_column("")
    
    table.add_row("Tool", f"[bold]{tool_name}[/]")
    if args:
        for name, value in args.items():
            table.add_row(name, str(value))
    
    panel = Panel(
        table,
        title="[tool]Tool Call[/]",
        border_style="cyan",
        padding=(0, 1),
        expand=False
    )
    console.print(panel)

def print_tool_result(result: str, tool_name: str, success: bool = True):
    """Print the result of a tool execution"""
    style = "success" if success else "error"
    icon = "✓" if success else "✗"
    
    panel = Panel(
        Text(str(result)),
        title=f"[{style}]{icon} {tool_name} Result[/]",
        border_style="green" if success else "red",
        padding=(1, 1),
        expand=False
    )
    console.print(panel)

def create_progress_display(description: str = "Processing"):
    """Create a progress bar for long-running operations"""
    progress = Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
    )
    task = progress.add_task(description, total=100)
    return progress, task

def demo():
    """Demo all UI components"""
    console.clear()
    print_header("GEM ASSIST TERMINAL UI COMPONENTS", "A beautiful terminal interface")
    
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
        "Python is a high-level, general-purpose programming language. Its design philosophy emphasizes code readability with the use of significant indentation.",
        "search_wikipedia"
    )
    
    # Demo a progress bar
    console.print("[info]Demonstrating progress bar...[/]")
    progress, task = create_progress_display("Downloading sample data")
    
    with progress:
        for i in range(100):
            time.sleep(0.02)  # Simulate work
            progress.update(task, completed=i+1)
    
    print_tool_result("Download failed: Connection timeout", "download_file", success=False)
    
    print_assistant_message(
        "These components work together to create a cohesive and visually appealing interface.\n\n"
        "```python\n"
        "def hello_world():\n"
        "    print('Hello from Rich!')\n"
        "```\n\n"
        "You can use them in your application for a better user experience."
    )

if __name__ == "__main__":
    demo()

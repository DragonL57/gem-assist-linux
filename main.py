"""
GEM-Assist - A terminal-based assistant that can run tools.
Main entry point and backward compatibility exports.
"""
import os
import inspect
import traceback
import asyncio
from typing import Dict, Any, List  # Add the missing import
from dotenv import load_dotenv
import colorama
from colorama import Fore, Style
from prompt_toolkit import PromptSession, HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from rich.console import Console
from rich.theme import Theme
from rich.panel import Panel
from rich.table import Table

import config as conf
from assistant import Assistant
from assistant.session import ChatSession, SessionManager
from gem.command import InvalidCommand, CommandNotFound, CommandExecuter
import gem
from plugins import discover_plugins, get_registry

# Backward compatibility exports
__all__ = ["Assistant", "ChatSession", "main"]

# Load environment variables
load_dotenv()

def _display_header(console: Console, discovery_result: Dict[str, Any] = None) -> None:
    """Display the application header with optional plugin stats."""
    console.print()
    console.print(f"[header]{conf.NAME} CHAT INTERFACE[/]", justify="center", style="bold")
    console.print(f"Using model: [bold]{conf.MODEL}[/] • Type [command]/help[/] for commands.", justify="center")
    
    # Include plugin statistics in header if available
    if discovery_result:
        stats = discovery_result["stats"]
        console.print()
        console.print(f"[cyan]▶ System ready with [bold green]{stats['total_tools']}[/] tools in [bold green]{stats['total_categories']}[/] categories", justify="center")
        
        # Show errors count if any
        errors = stats.get("tool_errors", 0) + stats.get("errored_plugins", 0)
        if errors > 0:
            console.print(f"[yellow]▶ {errors} loading errors detected.[/]", justify="center")
    
    console.print()

def _display_registration_report(console: Console, discovery_result: Dict[str, Any]) -> None:
    """Display a report of plugin and tool registration."""
    stats = discovery_result["stats"]
    status = discovery_result["status"]
    
    # Display simple statistics summary
    console.print("[info]Plugin System Status:[/]")
    console.print(f"  [cyan]Registered Tools:[/] [green]{stats['total_tools']}[/]")
    console.print(f"  [cyan]Tool Categories:[/] [green]{stats['total_categories']}[/]")
    console.print(f"  [cyan]Plugin Classes:[/] [green]{stats['loaded_plugins']}[/]")
    
    # Show error summary if any errors occurred
    if stats["errored_plugins"] > 0 or stats["tool_errors"] > 0:
        console.print(f"  [cyan]Failed Plugins:[/] [yellow]{stats['errored_plugins']}[/]")
        console.print(f"  [cyan]Failed Tools:[/] [yellow]{stats['tool_errors']}[/]")
        
        # Always show errors regardless of debug mode
        console.print("\n[bold red]Plugin Errors:[/]")
        
        if status["plugin_errors"]:
            for plugin, error in status["plugin_errors"].items():
                console.print(f"  [red]• {plugin}:[/] {error}")
                
        if status["tool_errors"]:
            for tool, error in status["tool_errors"].items():
                console.print(f"  [red]• {tool}:[/] {error}")
    
    # Show tool distribution by category only in debug mode
    if conf.DEBUG_MODE:
        console.print("\n[bold]Tools by Category:[/]")
        for category, tools in status["tools_by_category"].items():
            console.print(f"  [cyan]{category}[/]: {', '.join(tools)}")
    
    console.print()

async def _run_interaction_loop(session: PromptSession, assistant: Assistant) -> None:
    """Run the main interaction loop."""
    console = Console()

    while True:
        try:
            # Get user input with proper styling on a new line
            console.print()
            console.print("[bold magenta]You:[/]")  # Explicitly use bold magenta for emphasis
            loop = asyncio.get_running_loop()
            msg = await loop.run_in_executor(None, session.prompt, " ")  # Run in executor
            
            if not msg:
                continue

            # Handle commands
            if msg.startswith("/"):
                try:
                    command_result = CommandExecuter.execute(msg)
                    # Handle async commands
                    if inspect.iscoroutine(command_result):
                        await command_result
                except Exception as e:
                    console.print(f"[error]Command error: {e}[/]")
                continue
            
            # Send the message to the assistant
            await assistant.send_message(msg)

        except KeyboardInterrupt:
            console.print("\n\n[success]Chat session interrupted.[/]")
            break
        except InvalidCommand as e:
            console.print(f"[error]Error: {e}[/]")
        except CommandNotFound as e:
            console.print(f"[error]Error: {e}[/]")
        except Exception as e:
            console.print(f"[error]An error occurred: {e}[/]")
            traceback.print_exc()

async def main():
    """Main entry point for the assistant."""
    colorama.init(autoreset=True)
    console = Console()
    
    # Discover plugins first
    plugin_dirs = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins")
    ]
    discovery_result = discover_plugins(plugin_dirs)
    
    # Log discovered tools
    registry = get_registry()
    
    # Only enable litellm debug mode if DEBUG_MODE is enabled
    if conf.DEBUG_MODE:
        import litellm
        litellm._turn_on_debug()
        console.print("[dim cyan]Debug mode is enabled. Model reasoning will be displayed.[/]")
        console.print()
    
    # Clear screen if configured
    if conf.CLEAR_BEFORE_START:
        gem.clear_screen()
        
    # Display header with plugin stats integrated
    _display_header(console, discovery_result)
    
    # Always display registration report if there are errors
    has_errors = (discovery_result["stats"]["errored_plugins"] > 0 or 
                  discovery_result["stats"]["tool_errors"] > 0)
                  
    if has_errors or conf.DEBUG_MODE:
        _display_registration_report(console, discovery_result)
    
    # Setup prompt_toolkit with history and styling
    history_file = os.path.join(os.path.expanduser("~"), ".gem_assist_history")
    session = PromptSession(
        history=FileHistory(history_file),
        auto_suggest=AutoSuggestFromHistory(),
        enable_history_search=True,
    )

    # Create the system instruction
    sys_instruct = conf.BASE_SYSTEM_PROMPT.strip()

    # Initialize the assistant
    assistant = Assistant(
        model=conf.MODEL,
        name=conf.NAME,
        system_instruction=sys_instruct,
        discover_plugins_on_start=False,  # Already discovered
    )

    # Register commands
    CommandExecuter.register_commands(
        gem.builtin_commands.COMMANDS + [
            assistant.session_manager.save_session, 
            assistant.session_manager.load_session, 
            assistant.session_manager.reset_session
        ]
    )

    # Main interaction loop
    await _run_interaction_loop(session, assistant)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

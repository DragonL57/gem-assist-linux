"""
GEM-Assist - A terminal-based assistant that can run tools.
Main entry point and backward compatibility exports.
"""
import os
import inspect
import traceback
import asyncio
from typing import Dict, Any, List
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

from config import get_config # Import get_config
from config.services.context import format_prompt_with_context # Import prompt formatter
from assistant import Assistant
from assistant.session import ChatSession, SessionManager
from gem.command import InvalidCommand, CommandNotFound, CommandExecuter
import gem
from plugins import discover_plugins, get_registry

# Backward compatibility exports
__all__ = ["Assistant", "ChatSession", "main"]

# Load environment variables
load_dotenv()

# Fetch config instance early
config = get_config()

def _display_header(console: Console, discovery_result: Dict[str, Any] = None) -> None:
    """Display the application header with optional plugin stats."""
    console.print()
    console.print(f"[header]{config.settings.NAME} CHAT INTERFACE[/]", justify="center", style="bold")
    console.print(f"Using model: [bold]{config.settings.MODEL}[/] • Type [command]/help[/] for commands.", justify="center")

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
    if config.settings.DEBUG_MODE:
        console.print("\n[bold]Tools by Category:[/]")
        for category, tools in status["tools_by_category"].items():
            console.print(f"  [cyan]{category}[/]: {', '.join(tools)}")

    console.print()

async def _run_interaction_loop(session: PromptSession, assistant: Assistant) -> None:
    """Run the main interaction loop."""
    console = Console() # Use a local console for the loop

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

def _initialize_environment() -> Console:
    """Initialize environment settings like colorama, console, debug mode."""
    colorama.init(autoreset=True)
    console = Console()

    # Only enable litellm debug mode if DEBUG_MODE is enabled
    if config.settings.DEBUG_MODE:
        import litellm
        litellm._turn_on_debug()
        console.print("[dim cyan]Debug mode is enabled. Model reasoning will be displayed.[/]")
        console.print()

    # Clear screen if configured
    if config.settings.CLEAR_TERMINAL:
        gem.clear_screen()

    return console

def _discover_and_report_plugins(console: Console) -> Dict[str, Any]:
    """Discover plugins and display reports."""
    # Discover plugins first
    plugin_dirs = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins")
    ]
    discovery_result = discover_plugins(plugin_dirs)
    get_registry() # Ensure registry is populated, even if not used directly here

    # Display header with plugin stats integrated
    _display_header(console, discovery_result)

    # Always display registration report if there are errors
    has_errors = (discovery_result["stats"]["errored_plugins"] > 0 or
                  discovery_result["stats"]["tool_errors"] > 0)

    if has_errors or config.settings.DEBUG_MODE:
        _display_registration_report(console, discovery_result)

    return discovery_result # Ensure this is correctly indented

def _setup_prompt_session() -> PromptSession:
    """Set up the prompt_toolkit session."""
    history_file = os.path.join(os.path.expanduser("~"), ".gem_assist_history")
    return PromptSession(
        history=FileHistory(history_file),
        auto_suggest=AutoSuggestFromHistory(),
        enable_history_search=True,
    )

async def _create_assistant() -> Assistant:
    """Format prompt and initialize the Assistant."""
    # Format the base system prompt asynchronously
    base_system_prompt_template = config.prompt_manager.base_system_prompt
    formatted_system_prompt = await format_prompt_with_context(
        base_system_prompt_template,
        config.settings.NAME
    )

    # Initialize the assistant
    return Assistant(
        model=config.settings.MODEL,
        name=config.settings.NAME,
        system_instruction=formatted_system_prompt.strip(), # Pass the formatted prompt
        discover_plugins_on_start=False,  # Plugins already discovered
    )

def _register_commands(assistant: Assistant) -> None:
    """Register CLI commands."""
    CommandExecuter.register_commands(
        gem.builtin_commands.COMMANDS + [
            assistant.session_manager.save_session,
            assistant.session_manager.load_session,
            assistant.session_manager.reset_session
        ]
    )

async def main():
    """Main entry point for the assistant."""
    console = _initialize_environment()
    _ = _discover_and_report_plugins(console) # Call for side effects (discovery, reporting)
    session = _setup_prompt_session()
    assistant = await _create_assistant()
    _register_commands(assistant)

    # Main interaction loop
    await _run_interaction_loop(session, assistant)

if __name__ == "__main__":
    # Removed redundant asyncio import here
    asyncio.run(main())

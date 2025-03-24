"""
GEM-Assist - A terminal-based assistant that can run tools.
Main entry point and backward compatibility exports.
"""
import os
import inspect
import traceback
from dotenv import load_dotenv
import colorama
from colorama import Fore, Style
from prompt_toolkit import PromptSession, HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from rich.console import Console
from rich.theme import Theme

import config as conf
from utils import TOOLS
from assistant import Assistant
from assistant.session import ChatSession, SessionManager
from gem.command import InvalidCommand, CommandNotFound, CommandExecuter
import gem

# Backward compatibility exports
__all__ = ["Assistant", "ChatSession", "main"]

# Load environment variables
load_dotenv()

def _display_header(console: Console) -> None:
    """Display the application header."""
    console.print()
    console.print(f"[header]{conf.NAME} CHAT INTERFACE[/]", justify="center", style="bold")
    console.print(f"Using model: [bold]{conf.MODEL}[/] • Type [command]/help[/] for commands.", justify="center")
    console.print()

def _run_interaction_loop(session: PromptSession, assistant: Assistant) -> None:
    """Run the main interaction loop."""
    console = Console()
    
    while True:
        try:
            # Get user input with prompt_toolkit
            msg = session.prompt(
                HTML('<span style="color:magenta;font-weight:bold">You:</span> '),
                mouse_support=True
            )
            
            if not msg:
                continue

            # Handle commands
            if msg.startswith("/"):
                try:
                    CommandExecuter.execute(msg)
                except Exception as e:
                    console.print(f"[error]Command error: {e}[/]")
                continue
            
            # Send the message to the assistant
            assistant.send_message(msg)

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

def main():
    """Main entry point for the assistant."""
    colorama.init(autoreset=True)
    console = Console()
    
    # Only enable litellm debug mode if DEBUG_MODE is enabled
    if conf.DEBUG_MODE:
        import litellm
        litellm._turn_on_debug()
        console.print("[dim cyan]Debug mode is enabled. Model reasoning will be displayed.[/]")
        console.print()
    
    # Setup prompt_toolkit with history and styling
    history_file = os.path.join(os.path.expanduser("~"), ".gem_assist_history")
    session = PromptSession(
        history=FileHistory(history_file),
        auto_suggest=AutoSuggestFromHistory(),
        enable_history_search=True,
    )

    # Create the system instruction
    sys_instruct = conf.get_system_prompt().strip()

    # Initialize the assistant
    assistant = Assistant(
        model=conf.MODEL, 
        name=conf.NAME,
        system_instruction=sys_instruct, 
        tools=TOOLS
    )

    # Register commands
    CommandExecuter.register_commands(
        gem.builtin_commands.COMMANDS + [
            assistant.session_manager.save_session, 
            assistant.session_manager.load_session, 
            assistant.session_manager.reset_session
        ]
    )

    # Clear screen if configured
    if conf.CLEAR_BEFORE_START:
        gem.clear_screen()

    # Display header
    _display_header(console)

    # Main interaction loop
    _run_interaction_loop(session, assistant)

if __name__ == "__main__":
    main()

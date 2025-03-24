from .command import cmd, CommandExecuter
from rich import print
import os

@cmd(["exit", "quit", "bye"], "Exit the chat")
def exit_chat():    
    print("[bold green]Goodbye![/]")
    exit()

@cmd(["help", "?"], "Show help about available commands.")
def show_help(command_name=None):
    if command_name:
        help_text = CommandExecuter.help(command_name)
        if help_text:
            print(help_text)
        else:
            print(f"[bold red]No help available for command '{command_name}'[/]")
    else:
        print("[bold]Available commands:[/]")
        for name, command in sorted(CommandExecuter.get_commands().items()):
            if hasattr(command, 'help') and name == command.aliases[0]:  # Only show first alias to avoid duplicates
                print(f"[bold yellow]/{name}[/] - {command.help}")

@cmd(["commands"], "List available commands.")
def list_commands():
    print("[bold]Available commands:[/]")
    
    # Group commands by their primary function
    commands = {}
    for name, command in CommandExecuter.get_commands().items():
        if name == getattr(command, 'aliases', [''])[0]:  # Only add primary alias
            commands[name] = command.help if hasattr(command, 'help') else "No help available"
            
    # Print them out in alphabetical order
    for name, help_text in sorted(commands.items()):
        print(f"[bold yellow]/{name}[/] - {help_text}")

@cmd(["clear", "cls"], "Clear the screen, does not clear the chat history")
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

@cmd(['reasoning', 'plan'], "Shows the assistant's last reasoning plan")
def show_reasoning():
    """
    Show the assistant's last reasoning plan.
    
    This command displays the reasoning plan that the assistant developed
    before executing tools and providing a final answer.
    """
    # This is just a placeholder - the actual implementation is in the Assistant class
    print("Use this command in the chat interface to see the assistant's reasoning plan.")

COMMANDS = [
    exit_chat,
    show_help,
    list_commands,
    clear_screen,
    show_reasoning,
]
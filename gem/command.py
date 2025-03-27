"""
A System to let you add custom functions as commands with async support.

Example:
    ```py
    @cmd(["alias1", "alias2"], "Description of the command")
    async def command1():
        pass

    @cmd(["say_my_name"], "Says your name")
    def say_my_name(name: str):
        ""\"
        Args:
            name: The name to say
        ""\"
        print(f"Hello {name}")

    # register the commands
    CommandExecuter.register_commands([command1, say_my_name])
    ```

"""

from typing import Callable, Any, Dict, Union, List, Coroutine
from rich import print
import inspect

class InvalidCommand(Exception):
    pass

class CommandNotFound(Exception):
    pass

def cmd(aliases: List[str], help_msg: str = ""):
    """
    A decorator to mark a function as a command.

    Args:
        aliases: A list of strings representing the aliases for the command.
        help_msg: A string describing what the command does. This will be shown in a help message.
    """
    if not isinstance(aliases, list):
        raise TypeError("aliases must be a list")
    
    if len(aliases) == 0:
        raise ValueError("aliases must not be empty")

    def decorator(func: Union[Callable, Coroutine]) -> Union[Callable, Coroutine]:
        func.aliases = aliases
        func.help = help_msg
        func.is_async = inspect.iscoroutinefunction(func)
        return func
    return decorator

class CommandExecuter:
    """
    Assign commands and handle execution with async support.

    ```
    from gem.commands import cmd, CommandExecuter

    @cmd(["say_my_name"], "Says your name")
    async def say_my_name(name: str):
        ""\"
        Args:
            name: The name to say
        ""\"
        print(f"Hello {name}")

    # register the commands
    CommandExecuter.register_commands([say_my_name])
    ```
    """

    __available_commands: Dict[str, Union[Callable, Coroutine]] = {} 
    command_prefix = "/"

    @staticmethod
    def register_commands(commands: List[Union[Callable, Coroutine]]) -> None:
        """Registers a command and its aliases."""
        for command in commands:
            if hasattr(command, 'aliases') and command.aliases is not None:
                for alias in command.aliases:
                    if alias not in CommandExecuter.__available_commands:
                        CommandExecuter.__available_commands[alias] = command
                    else:
                        raise InvalidCommand(f"Alias '{alias}' for command '{command.__name__}' already registered.")
            else:
                raise InvalidCommand(f"Command {command.__name__} must have at least one alias")

    @staticmethod
    def get_commands() -> Dict[str, Union[Callable, Coroutine]]:
        return CommandExecuter.__available_commands

    @staticmethod
    def execute(command: str) -> Any:
        """Executes a command.

        Args:
            command: The command string to execute.

        Returns:
            The result of the command, or None.
            For async commands, returns a coroutine that must be awaited.

        Raises:
            InvalidCommand: If the command string is invalid.
            CommandNotFound: If the command is not found.
        """
        if not command.startswith(CommandExecuter.command_prefix):
            raise InvalidCommand(f"Invalid command: {command}, must start with {CommandExecuter.command_prefix}")

        args = command[1:].split()

        if len(args) == 0:
            raise InvalidCommand(f"Invalid command: {command}, must contain at least one argument after {CommandExecuter.command_prefix}")

        command_name = args[0]
        command_args = args[1:]

        command_to_call = CommandExecuter.__available_commands.get(command_name, None)

        if not command_to_call:
            raise CommandNotFound(f"Command not found: {command_name}")

        if len(command_args) > 0 and command_args[0] == "?":
            print(command_to_call.help)
            print(command_to_call.__doc__ or "") 
            return None

        # Call the function and return the result
        # If it's async, the caller is responsible for awaiting the result
        return command_to_call(*command_args)

    @staticmethod
    def is_async_command(command_name: str) -> bool:
        """Check if a command is async.

        Args:
            command_name: The name of the command to check.

        Returns:
            True if the command is async, False if sync or not found.
        """
        command = CommandExecuter.__available_commands.get(command_name)
        if command:
            return getattr(command, 'is_async', False)
        return False

    @staticmethod
    def help(command_name: str) -> str | None:
        """Gets the help text for a command."""
        command_func = CommandExecuter.__available_commands.get(command_name)
        if command_func:
            help_text = getattr(command_func, "help", "")
            help_text += "  " + command_func.__doc__ or ""
            if getattr(command_func, 'is_async', False):
                help_text = "[async] " + help_text
            return help_text
        return None

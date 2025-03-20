"""
Core utility functions for the gem-assist package.
These functions are used across the various tools modules.
"""

import os
import colorama
from colorama import Fore, Style

# Initialize colorama
colorama.init(autoreset=True)

def tool_message_print(msg: str, args: list[tuple[str, str]] = None):
    """
    Prints a tool message with the given message and arguments.

    Args:
        msg: The message to print.
        args: A list of tuples containing the argument name and value. Optional.
    """
    full_msasage = f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} {Fore.WHITE}{msg}"
    if args:
        for arg in args:
            full_msasage += f" [{Fore.YELLOW}{arg[0]}{Fore.WHITE}={arg[1]}]"
    print(full_msasage)

def tool_report_print(msg: str, value: str, is_error: bool = False):
    """
    Print when a tool needs to put out a message as a report

    Args:
        msg: The message to print.
        value: The value to print.
        is_error: Whether this is an error message. If True, value will be printed in red.
    """
    value_color = Fore.RED if is_error else Fore.YELLOW
    full_msasage = f"{Fore.CYAN}  ├─{Style.RESET_ALL} {msg} {value_color}{value}"
    print(full_msasage)

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

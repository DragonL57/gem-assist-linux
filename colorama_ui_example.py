import os
import sys
import time
import shutil
import threading
import re
import click
from textwrap import TextWrapper, dedent
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import colorama
from colorama import Fore, Style

# Initialize colorama for cross-platform colored output
colorama.init()

def center_cli_str(text: str, width: Optional[int] = None):
    """Center text in the terminal."""
    width = width or shutil.get_terminal_size().columns
    lines = text.split("\n")
    max_line_len = max(len(line) for line in lines)
    return "\n".join((line + " " * (max_line_len - len(line))).center(width) for line in lines)

def get_ascii_banner(center: bool = True) -> str:
    """Generate TaskWeaver ASCII banner."""
    text = dedent(
        r"""
        =========================================================
         _____         _     _       __
        |_   _|_ _ ___| | _ | |     / /__  ____ __   _____  _____
          | |/ _` / __| |/ /| | /| / / _ \/ __ `/ | / / _ \/ ___/
          | | (_| \__ \   < | |/ |/ /  __/ /_/ /| |/ /  __/ /
          |_|\__,_|___/_|\_\|__/|__/\___/\__,_/ |___/\___/_/
        =========================================================
        """,
    ).strip()
    if center:
        return center_cli_str(text)
    else:
        return text

def error_message(message: str) -> None:
    """Display an error message."""
    click.secho(click.style(f"Error: {message}", fg="red"))

def plain_message(message: str, type_label: str, nl: bool = True) -> None:
    """Display a plain message with type label."""
    click.secho(
        click.style(
            f">>> [{type_label.upper()}]\n{message}",
            fg="bright_black",
        ),
        nl=nl,
    )

def user_input_message(prompt: str = "   Human  ") -> str:
    """Get input from the user with a styled prompt."""
    try:
        user_input = input(
            Fore.MAGENTA + Style.BRIGHT + f" {prompt} " + 
            Style.RESET_ALL + Fore.MAGENTA + "▶" + 
            Style.RESET_ALL + "  "
        )
        return user_input
    except KeyboardInterrupt:
        if not user_input:
            exit(0)
        return ""

class TaskWeaverConsoleMock:
    """Mock class for TaskWeaver's console interface."""
    
    def __init__(self):
        self.lock = threading.RLock()
        self.pending_updates = []
        self.animation_thread = None
        self.animation_running = False
    
    def _system_message(self, message: str) -> None:
        """Display a system message."""
        click.secho(click.style(" System ", fg="white", bg="blue"), nl=False)
        click.secho(click.style(f"▶  {message}", fg="blue"))
    
    def _assistant_message(self, message: str) -> None:
        """Display an assistant message."""
        click.secho(click.style(" TaskWeaver ", fg="white", bg="yellow"), nl=False)
        click.secho(click.style(f"▶  {message}", fg="yellow"))

    def _print_help(self) -> None:
        """Print help message."""
        self._system_message("Available commands:")
        help_info = dedent(
            """
            /help, /h, /?          - Show this help message
            /exit, /bye, /quit     - Exit the application
            /clear                 - Clear the screen
            /reset                 - Reset the session
            /info                  - Show current session info
            /load <file>           - Load a file
            /save                  - Save conversation history
            """
        )
        plain_message(help_info, "help")
    
    def start_conversation(self):
        """Start a conversation session."""
        click.clear()
        print(get_ascii_banner())
        self._system_message("Welcome to TaskWeaver! How can I help you today?")
        self._system_message("Type /help for available commands.")
        
        while True:
            try:
                user_input = user_input_message()
                self._process_user_input(user_input)
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                error_message(f"An error occurred: {str(e)}")
                
    def _process_user_input(self, user_input: str) -> None:
        """Process user input."""
        msg = user_input.strip()
        if msg == "":
            error_message("Empty input, please try again")
            return

        if msg.startswith("/"):
            lower_message = msg.lower()
            lower_command = lower_message.lstrip("/").split(" ")[0]
            if lower_command in ["exit", "bye", "quit"]:
                exit(0)
            if lower_command in ["help", "h", "?"]:
                self._print_help()
                return
            if lower_command == "clear":
                click.clear()
                return
            if lower_command == "reset":
                self._system_message("Session reset")
                return
            if lower_command in ["load", "file"]:
                file_to_load = msg[5:].strip()
                self._system_message(f"Loading file: {file_to_load}")
                return
            if lower_command == "save":
                self._system_message("Conversation saved")
                return
            if lower_command == "info":
                self._system_message("Session Information")
                return
            
            error_message(f"Unknown command '{msg}', please try again")
            return

        self._handle_message(msg)
    
    def _handle_message(self, input_message: str):
        """Handle a message from the user."""
        # Start the animation thread
        with self.lock:
            self.pending_updates = [
                ("start_post", "TaskWeaver"),
                ("add_attachment", ("plan", "Plan", "1. Thinking about your request\n2. Searching for information\n3. Composing a response")),
                ("update_status", "processing")
            ]
        
        self.animation_running = True
        self.animation_thread = threading.Thread(target=self._animate_thread)
        self.animation_thread.daemon = True
        self.animation_thread.start()
        
        # Simulate some processing time
        time.sleep(2)
        
        # Update with more progress
        with self.lock:
            self.pending_updates.append(
                ("update_message", "I'm analyzing your input: " + input_message[:20] + "...")
            )
        
        time.sleep(2)
        
        # Complete the response
        with self.lock:
            self.pending_updates.append(
                ("update_message", f"Here's my response to your query about '{input_message[:30]}...'")
            )
            self.pending_updates.append(("end_post", "Human"))
        
        # Wait for animation to complete
        time.sleep(1)
        self.animation_running = False
        if self.animation_thread:
            self.animation_thread.join()
        
        # Display the final message
        self._assistant_message(f"I've processed your request: '{input_message}'. Here is some information that might help you.")
    
    def _animate_thread(self):
        """Animation thread that displays status updates during processing."""
        # Get terminal width
        terminal_column = shutil.get_terminal_size().columns
        counter = 0
        status_msg = "preparing"
        cur_message_buffer = ""
        cur_key = ""
        role = "TaskWeaver"
        next_role = ""

        def style_line(s: str):
            return click.style(s, fg="blue")

        def style_role(s: str):
            return click.style(s, fg="bright_yellow", underline=True)

        def style_key(s: str):
            return click.style(s, fg="bright_cyan")

        def style_msg(s: str):
            return click.style(s, fg="bright_black")
        
        def clear_line():
            from colorama import ansi
            print(ansi.clear_line(), end="\r")

        def get_ani_frame(frame: int = 0):
            frame_inx = abs(frame % 20 - 10)
            ani_frame = " " * frame_inx + "<=💡=>" + " " * (10 - frame_inx)
            return ani_frame
        
        def format_status_message(limit: int):
            incomplete_suffix = "..."
            incomplete_suffix_len = len(incomplete_suffix)
            if len(cur_message_buffer) == 0:
                if len(status_msg) > limit - 1:
                    return f" {status_msg[(limit - incomplete_suffix_len - 1):]}{incomplete_suffix}"
                return " " + status_msg

            cur_key_display = style_line("[") + style_key(cur_key) + style_line("]")
            cur_key_len = len(cur_key) + 2  # with extra bracket
            cur_message_buffer_norm = cur_message_buffer.replace("\n", " ").replace("\r", " ")

            if len(cur_message_buffer_norm) < limit - cur_key_len - 1:
                return f"{cur_key_display} {cur_message_buffer_norm}"

            status_msg_len = limit - cur_key_len - incomplete_suffix_len
            return f"{cur_key_display} {cur_message_buffer_norm[-status_msg_len:]}{incomplete_suffix}"

        last_time = 0
        while self.animation_running:
            clear_line()
            with self.lock:
                for action, opt in self.pending_updates:
                    if action == "start_post":
                        role = opt
                        next_role = ""
                        status_msg = "initializing"
                        click.secho(
                            style_line(
                                " ╭───<",
                            )
                            + style_role(
                                f" {role} ",
                            )
                            + style_line(">"),
                        )
                    elif action == "end_post":
                        status_msg = "finished"
                        click.secho(
                            style_line(" ╰──●")
                            + style_msg(" sending message to ")
                            + style_role(
                                next_role,
                            ),
                        )
                    elif action == "add_attachment":
                        key, _type, value = opt
                        cur_key = key
                        lines = value.split("\n")
                        click.secho(
                            style_line(" ├─►") + style_line("[") + style_key(key) + style_line("]"),
                        )
                        
                        wrapper = TextWrapper(
                            width=terminal_column,
                            initial_indent=" │   ",
                            subsequent_indent=" │   ",
                            break_long_words=True,
                            break_on_hyphens=False,
                        )
                        
                        for line in lines:
                            if line.strip():
                                wrapped = wrapper.wrap(line)
                                for l in wrapped:
                                    click.secho(style_line(" │   ") + style_msg(l[5:]))
                            else:
                                click.secho(style_line(" │"))
                    elif action == "update_status":
                        status_msg = opt
                    elif action == "update_message":
                        cur_message_buffer = opt

            # Display animated cursor
            cur_message_prefix: str = " TaskWeaver "
            cur_ani_frame = get_ani_frame(counter)
            cur_message_display_len = (
                terminal_column
                - len(cur_message_prefix)
                - 2  # separator for cur message prefix
                - len(role)
                - 2  # bracket for role
                - len(cur_ani_frame)
                - 2  # extra size for emoji in ani
            )

            cur_message_display = format_status_message(cur_message_display_len)

            click.secho(
                click.style(cur_message_prefix, fg="white", bg="yellow")
                + click.style("▶ ", fg="yellow")
                + style_line("[")
                + style_role(role)
                + style_line("]")
                + style_msg(cur_message_display)
                + style_msg(cur_ani_frame)
                + "\r",
                nl=False,
            )

            counter += 1
            time.sleep(0.1)

if __name__ == "__main__":
    console = TaskWeaverConsoleMock()
    console.start_conversation()

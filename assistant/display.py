"""
Display utilities for rendering assistant output.
"""
import os
from typing import Any
from rich.console import Console
from rich.markdown import Markdown
from config import get_config

class AssistantDisplay:
    """Handles the display of assistant output."""

    def __init__(self, assistant):
        """Initialize with parent assistant reference."""
        self.assistant = assistant

    def print_ai(self, msg: str) -> None:
        """Display the assistant's response with proper formatting and wrapping."""
        # Get console width to enable proper text wrapping
        console_width = os.get_terminal_size().columns if hasattr(os, 'get_terminal_size') else 80

        # Leave space for the prefix and some margin
        effective_width = console_width - 15  # Account for prefix and safety margin

        # Add a blank line before response for better readability
        self.assistant.console.print()

        # Simple display without panels
        self.assistant.console.print(f"[assistant]{self.assistant.name}:[/] ", end="")

        # Process and standardize the message formatting if it's not empty
        if msg:
            # Ensure code blocks have proper syntax highlighting
            formatted_msg = msg.strip()

            # Use width parameter to control text wrapping
            self.assistant.console.print(Markdown(formatted_msg, code_theme="monokai", justify="left"),
                               width=effective_width,
                               overflow="fold",
                               no_wrap=False)
        else:
            self.assistant.console.print("I don't have a response for that.")

        # Add a blank line after assistant response for better readability
        self.assistant.console.print()

    def show_reasoning(self, reasoning: str) -> None: # Return type changed to None
        """
        Displays the reasoning/planning phase output, typically only in debug mode.
        Does NOT ask for user confirmation.
        """
        config = get_config()
        # Only display reasoning if debug mode is enabled
        if config.settings.DEBUG_MODE and reasoning:
            # Get console width for proper text wrapping
            console_width = os.get_terminal_size().columns if hasattr(os, 'get_terminal_size') else 80
            effective_width = console_width - 4  # Allow for some margin

            self.assistant.console.print()

            # Render the reasoning as markdown with subtle styling
            reasoning_strip = reasoning.strip()
            if reasoning_strip: # Check if there's actual content after stripping
                self.assistant.console.print(
                    Markdown(reasoning_strip, justify="left"),
                    style="dim italic",
                    width=effective_width,
                    overflow="fold",
                    no_wrap=False
                )
                self.assistant.console.print() # Add blank line only if reasoning was displayed

        # --- Confirmation prompt removed ---
        # response = self.assistant.console.input("[bold blue]Proceed with this reasoning plan? (y/n/edit): [/bold blue]")
        # ... (logic for handling y/n/edit removed) ...
        # Always implicitly proceed in the new agentic flow

    def display_debug_info(self, message: str) -> None:
        """Display debug information with subtle styling."""
        config = get_config()
        if config.settings.DEBUG_MODE:
            self.assistant.console.print()
            self.assistant.console.print(message, style="debug")
            self.assistant.console.print()

    def extract_and_display_reasoning(self, response: Any) -> None:
        """Extract and display model thinking/reasoning from response if in debug mode."""
        config = get_config()
        if config.settings.DEBUG_MODE and hasattr(response, 'choices') and len(response.choices) > 0:
            # Ensure message object exists
            if hasattr(response.choices[0], 'message'):
                 response_message = response.choices[0].message
                 if hasattr(response_message, 'content') and response_message.content:
                     reasoning = response_message.content.strip()
                     # Display only if reasoning content is not empty
                     if reasoning:
                          self.assistant.console.print()
                          self.assistant.console.print(f"[dim cyan]Model thinking:[/]") # Changed label
                          self.assistant.console.print(f"[dim]{reasoning}[/]")
                          self.assistant.console.print()

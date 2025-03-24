"""
Display utilities for rendering assistant output.
"""
import os
from typing import Any
from rich.console import Console
from rich.markdown import Markdown

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
        
        print()  # Add a blank line after assistant response
        
    def show_reasoning(self, reasoning: str) -> None:
        """Display the reasoning plan with proper formatting."""
        # Get console width for proper text wrapping
        console_width = os.get_terminal_size().columns if hasattr(os, 'get_terminal_size') else 80
        effective_width = console_width - 4  # Allow for some margin
        
        # Render the reasoning as markdown with styling
        self.assistant.console.print(
            Markdown(reasoning, justify="left"),
            style="dim italic",
            width=effective_width,
            overflow="fold",
            no_wrap=False
        )
        
    def display_debug_info(self, message: str) -> None:
        """Display debug information in a dimmed format."""
        import config as conf
        if conf.DEBUG_MODE:
            self.assistant.console.print(message, style="debug")
            
    def extract_and_display_reasoning(self, response: Any) -> None:
        """Extract and display model reasoning if in debug mode."""
        import config as conf
        if conf.DEBUG_MODE and hasattr(response, 'choices') and len(response.choices) > 0:
            response_message = response.choices[0].message
            if hasattr(response_message, 'content') and response_message.content:
                reasoning = response_message.content.strip()
                self.assistant.console.print(f"[dim cyan]Model reasoning:[/] [dim]{reasoning}[/]")
                self.assistant.console.print()  # Add a blank line for readability

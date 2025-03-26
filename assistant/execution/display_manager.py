"""
Display manager for tool execution information.
"""
from typing import Any, Dict, Optional
from rich.console import Console
from dataclasses import dataclass

@dataclass
class DisplayConfig:
    """Configuration for display formatting."""
    arg_truncate_length: int = 50
    success_icon: str = "✓"
    error_icon: str = "✗"
    arrow_icon: str = "→"
    max_width: int = 100

class ToolDisplayManager:
    """Manages the display of tool execution information."""
    
    def __init__(self, console: Console, config: Optional[DisplayConfig] = None):
        """Initialize the display manager.
        
        Args:
            console: Rich console instance for output
            config: Optional display configuration
        """
        self.console = console
        self.config = config or DisplayConfig()
        
    def display_tool_call(self, name: str, args: Dict[str, Any]) -> None:
        """Format and display a tool call with its arguments.
        
        Args:
            name: Name of the tool being called
            args: Arguments being passed to the tool
        """
        args_display = []
        for arg_name, arg_value in args.items():
            display_val = self._format_arg_value(arg_value)
            args_display.append(f"[dim]{arg_name}=[/][cyan]{display_val}[/]")
        
        args_str = ", ".join(args_display)
        self.console.print()
        self.console.print(f"[tool]{self.config.arrow_icon} {name}({args_str})[/]")
        
    def display_tool_result(self, name: str, formatted_result: str) -> None:
        """Display a formatted tool execution result.
        
        Args:
            name: Name of the tool that was executed
            formatted_result: Pre-formatted result string
        """
        self.console.print(
            f"[success]{self.config.success_icon} {name}:[/] {formatted_result}"
        )
        self.console.print()  # Add space for readability
        
    def display_tool_error(self, name: str, error: str) -> None:
        """Display a tool execution error.
        
        Args:
            name: Name of the tool that failed
            error: Error message to display
        """
        self.console.print(
            f"[error]{self.config.error_icon} Error executing {name}: {error}[/]"
        )
        self.console.print()  # Add space for readability
        
    def display_missing_tool(self, name: str) -> None:
        """Display an error for a missing tool.
        
        Args:
            name: Name of the missing tool
        """
        self.console.print(
            f"[error]{self.config.error_icon} Tool not found: {name}[/]"
        )
        self.console.print()  # Add space for readability

    def display_start_execution(self, name: str) -> None:
        """Display the start of tool execution.
        
        Args:
            name: Name of the tool being executed
        """
        self.console.print(f"[dim]Starting execution of {name}...[/]")
        
    def display_execution_complete(self, name: str, execution_time: float) -> None:
        """Display completion of tool execution.
        
        Args:
            name: Name of the tool that completed
            execution_time: Time taken to execute in seconds
        """
        self.console.print(
            f"[dim]Completed {name} in {execution_time:.2f}s[/]"
        )

    def _format_arg_value(self, value: Any) -> str:
        """Format an argument value for display.
        
        Args:
            value: The argument value to format
            
        Returns:
            Formatted string representation
        """
        str_value = str(value)
        if len(str_value) > self.config.arg_truncate_length:
            return f"{str_value[:self.config.arg_truncate_length-3]}..."
        return str_value
        
    def section_break(self) -> None:
        """Display a visual break between sections."""
        self.console.print("[cyan]" + "─" * self.config.max_width + "[/]")
        
    def clear_line(self) -> None:
        """Clear the current line and move cursor up."""
        self.console.print("\033[A\033[K", end="")

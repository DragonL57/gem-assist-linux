import time
from typing import Any, Dict, Optional
from rich.console import Console
from rich.panel import Panel
from rich.status import Status
from rich.pretty import pretty_repr
from dataclasses import dataclass

# Assuming get_config provides access to loaded theme settings
from config import get_config

@dataclass
class DisplayConfig:
    """Configuration for display formatting."""
    arg_truncate_length: int = 80 # Increased length for pretty_repr
    success_icon: str = "✅" # Using emoji
    error_icon: str = "❌" # Using emoji
    calling_icon: str = "⚙️" # Using emoji
    spinner_style: str = "dots"
    max_width: int = 100

class ToolDisplayManager:
    """Manages the display of tool execution information using Rich components."""

    def __init__(self, console: Console, config: Optional[DisplayConfig] = None):
        """Initialize the display manager.

        Args:
            console: Rich console instance for output
            config: Optional display configuration
        """
        self.console = console
        self.config = config or DisplayConfig()
        self.app_config = get_config() # Load app config

        # Get the active theme name from settings
        active_theme_name = self.app_config.settings.THEME

        # Load the colors for the active theme
        self.theme = self.app_config.get_theme(active_theme_name)
        self._active_status: Optional[Status] = None
        self._current_tool_name: Optional[str] = None
        self._current_tool_args: Dict[str, Any] = {}
        self._start_time: Optional[float] = None

    def _get_theme_color(self, key: str, default: str) -> str:
        """Safely get a color from the theme dictionary."""
        return self.theme.get(key.upper(), default)

    def display_tool_call(self, name: str, args: Dict[str, Any]) -> None:
        """Display the initial call information. Stores args for later use."""
        self._current_tool_name = name
        self._current_tool_args = args
        self._start_time = time.time() # Record start time here

        args_repr = pretty_repr(args, max_length=self.config.arg_truncate_length)
        call_style = self._get_theme_color('secondary', 'dim cyan')
        self.console.print(
            f"[{call_style}]{self.config.calling_icon} Calling tool [bold]{name}[/bold] with args: {args_repr}[/{call_style}]"
        )

    def display_start_execution(self, name: str) -> None:
        """Display a status spinner indicating tool execution has started."""
        # Ensure previous status is stopped if any exists
        self._stop_active_status()

        status_style = self._get_theme_color('primary', 'blue')
        self._active_status = self.console.status(
            f"[bold {status_style}]Running {name}...[/]",
            spinner=self.config.spinner_style
        )
        self._active_status.start()

    def display_tool_result(self, name: str, formatted_result: str) -> None:
        """Display a Panel with the successful tool execution result."""
        self._stop_active_status()
        execution_time = (time.time() - self._start_time) if self._start_time else 0.0

        success_style = self._get_theme_color('accent', 'green')
        border_style = self._get_theme_color('secondary', 'dim green')
        title_style = f"bold {self._get_theme_color('primary', 'green')}"

        # Consider using pretty_repr for formatted_result if it's complex data
        # For now, assume formatted_result is a ready-to-print string
        content = f"[{success_style}]{formatted_result}[/{success_style}]"

        panel_title = f"[{title_style}]{self.config.success_icon} {name} Success ({execution_time:.2f}s)[/{title_style}]"

        self.console.print(
            Panel(
                content,
                title=panel_title,
                border_style=border_style,
                expand=True, # Allow panel to expand to terminal width
                highlight=True # Highlight based on content styles
            )
        )
        self.console.print() # Add space
        self._reset_state()

    def display_tool_error(self, name: str, error: str) -> None:
        """Display a Panel with the tool execution error."""
        self._stop_active_status()
        execution_time = (time.time() - self._start_time) if self._start_time else 0.0

        error_color = "red" # Hardcode red for errors for clarity
        border_style = f"dim {error_color}"
        title_style = f"bold {error_color}"

        content = f"[{error_color}]{error}[/{error_color}]"
        panel_title = f"[{title_style}]{self.config.error_icon} {name} Error ({execution_time:.2f}s)[/{title_style}]"

        self.console.print(
            Panel(
                content,
                title=panel_title,
                border_style=border_style,
                expand=True, # Allow panel to expand
                highlight=True
            )
        )
        self.console.print() # Add space
        self._reset_state()

    def display_missing_tool(self, name: str) -> None:
        """Display an error Panel for a missing tool."""
        self._stop_active_status() # Just in case

        error_color = "red"
        border_style = f"dim {error_color}"
        title_style = f"bold {error_color}"

        content = f"[{error_color}]Tool implementation not found.[/{error_color}]"
        panel_title = f"[{title_style}]{self.config.error_icon} Tool Not Found: {name}[/{title_style}]"

        self.console.print(
            Panel(
                content,
                title=panel_title,
                border_style=border_style,
                expand=True # Allow panel to expand
            )
        )
        self.console.print() # Add space
        self._reset_state()

    def _stop_active_status(self) -> None:
        """Stop and remove the active status spinner if it exists."""
        if self._active_status:
            self._active_status.stop()
            self._active_status = None

    def _reset_state(self) -> None:
        """Reset internal state after a tool execution cycle finishes."""
        self._current_tool_name = None
        self._current_tool_args = {}
        self._start_time = None
        # Ensure status is stopped, though it should be by result/error handlers
        self._stop_active_status()

    # --- Methods below might be deprecated or less used with the new flow ---

    def display_execution_complete(self, name: str, execution_time: float) -> None:
        """(Potentially deprecated) Display completion of tool execution."""
        # This logic is now integrated into result/error panels
        pass

    def _format_arg_value(self, value: Any) -> str:
        """(Potentially less used) Format an argument value for display."""
        return pretty_repr(value, max_length=self.config.arg_truncate_length)

    def section_break(self) -> None:
        """Display a visual break between sections."""
        # Could use rich.rule.Rule here
        self.console.print(f"[{self._get_theme_color('secondary', 'dim cyan')}]" + "─" * self.config.max_width + f"[/{self._get_theme_color('secondary', 'dim cyan')}]")

    def clear_line(self) -> None:
        """Clear the current line and move cursor up."""
        # This might interfere with Rich's rendering, use with caution or avoid.
        # self.console.print("\033[A\033[K", end="")
        pass # Avoid using this with Rich panels/status typically

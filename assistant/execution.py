"""
Tool execution handling for the assistant.
"""
import json
import time
import inspect
from typing import Any, Dict, List, Callable

class ToolExecutor:
    """Handles tool execution for the assistant."""
    
    def __init__(self, assistant):
        """Initialize with parent assistant reference."""
        self.assistant = assistant
        
    def execute_tool_call(self, tool_call: Any) -> None:
        """Execute a single tool call and handle the result."""
        function_name = tool_call.function.name
        tool_call_id = tool_call.id

        # Check if function exists
        function_to_call = self.assistant.available_functions.get(function_name)
        if not function_to_call:
            self._handle_missing_function(tool_call_id, function_name)
            return

        # Process function arguments and execute
        try:
            function_args = self._prepare_arguments(function_to_call, tool_call.function.arguments)
            self._display_tool_call(function_name, function_args)
            
            # Execute the function with timing
            start_time = time.time()
            function_response = function_to_call(**function_args)
            execution_time = time.time() - start_time
            
            # Display the result
            self._display_tool_result(function_name, function_response, execution_time)
            
            # Add output to conversation history
            self.assistant.add_toolcall_output(tool_call_id, function_name, function_response)
        except Exception as e:
            self._handle_execution_error(tool_call_id, function_name, e)

    def _prepare_arguments(self, function: Callable, arguments_json: str) -> Dict[str, Any]:
        """Parse and convert function arguments to appropriate types."""
        function_args = json.loads(arguments_json)
        
        # Convert arguments based on function signature annotations
        sig = inspect.signature(function)
        for param_name, param in sig.parameters.items():
            if param_name in function_args:
                function_args[param_name] = self.assistant.type_converter.convert_to_pydantic_model(
                    param.annotation, function_args[param_name]
                )
                
        return function_args
            
    def _handle_missing_function(self, tool_call_id: str, function_name: str) -> None:
        """Handle case when function doesn't exist."""
        err_msg = f"Function not found with name: {function_name}"
        self.assistant.console.print(f"[error]Error: {err_msg}[/]")
        self.assistant.add_toolcall_output(tool_call_id, function_name, err_msg)
        
    def _handle_execution_error(self, tool_call_id: str, function_name: str, error: Exception) -> None:
        """Handle errors during function execution."""
        self.assistant.console.print(f"[error]Error executing {function_name}: {error}[/]")
        self.assistant.console.print()  # Add space for readability
        self.assistant.add_toolcall_output(tool_call_id, function_name, str(error))

    def _display_tool_call(self, function_name: str, function_args: Dict[str, Any]) -> None:
        """Format and display a tool call with its arguments."""
        args_display = []
        for arg_name, arg_value in function_args.items():
            display_val = self._format_arg_value(arg_value)
            args_display.append(f"{arg_name}={display_val}")
        
        args_str = ", ".join(args_display)
        self.assistant.console.print(f"[cyan]→ {function_name}({args_str})[/]")
        
    def _format_arg_value(self, value: Any) -> str:
        """Format argument values for display, truncating if needed."""
        if isinstance(value, str) and len(value) > 50:
            return f"{value[:47]}..."
        return str(value)

    def _display_tool_result(self, function_name: str, result: Any, execution_time: float) -> None:
        """Display the result of a tool execution based on the tool type."""
        from assistant.core import SEARCH_TOOLS
        
        if function_name in SEARCH_TOOLS:
            # For search tools, just show count of results
            result_count = self._count_search_results(result)
            self.assistant.console.print(f"[success]✓ Completed in {execution_time:.4f}s: received {result_count} results[/]")
        else:
            # For non-search tools, show condensed preview
            brief_response = self._get_condensed_preview(result)
            self.assistant.console.print(f"[success]✓ Completed in {execution_time:.4f}s: {brief_response}[/]")
        
        self.assistant.console.print()  # Add space for readability

    def _count_search_results(self, result: Any) -> int:
        """Count the number of results in a search response."""
        try:
            if isinstance(result, dict):
                # Check common result container keys
                for key in ["results", "matches", "posts", "items"]:
                    if key in result and isinstance(result[key], list):
                        return len(result[key])
                # If no recognized container, count the dict itself
                return 1
            elif isinstance(result, list):
                return len(result)
            return 1  # Default for single-result responses
        except Exception:
            return 0

    def _get_condensed_preview(self, result: Any, max_lines: int = 3, max_length: int = 200) -> str:
        """Get a condensed preview of a result for display."""
        try:
            # Convert to string first
            if not isinstance(result, str):
                if isinstance(result, (dict, list)):
                    result_str = str(result)[:max_length]
                else:
                    result_str = str(result)[:max_length]
            else:
                result_str = result[:max_length]
            
            # Truncate to specified number of lines with ellipsis
            lines = result_str.split("\n")
            if len(lines) > max_lines:
                short_result = "\n".join(lines[:max_lines]) + "..."
            else:
                short_result = result_str
                
            # Further truncate if too long
            if len(short_result) > max_length:
                short_result = short_result[:(max_length - 3)] + "..."
                
            return short_result
        except Exception:
            return "[Preview not available]"

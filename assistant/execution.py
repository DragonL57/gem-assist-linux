"""
Tool execution handling for the assistant.
"""
import json
import time
import inspect
from typing import Any, Dict

class ToolExecutor:
    """Handles tool execution for the assistant."""
    
    def __init__(self, assistant):
        """Initialize with parent assistant reference."""
        self.assistant = assistant
        
    def execute_tool_call(self, tool_call: Any) -> None:
        """Execute a single tool call and handle the result."""
        function_name = tool_call.function.name

        # Check if function exists
        function_to_call = self.assistant.available_functions.get(function_name, None)
        if function_to_call is None:
            err_msg = f"Function not found with name: {function_name}"
            self.assistant.console.print(f"[error]Error: {err_msg}[/]")
            self.assistant.add_toolcall_output(tool_call.id, function_name, err_msg)
            return

        # Process function arguments
        try:
            function_args = json.loads(tool_call.function.arguments)
            self.display_tool_call(function_name, function_args)
            
            # Convert arguments to appropriate types based on annotations
            sig = inspect.signature(function_to_call)
            for param_name, param in sig.parameters.items():
                if param_name in function_args:
                    function_args[param_name] = self.assistant.type_converter.convert_to_pydantic_model(
                        param.annotation, function_args[param_name]
                    )

            # Execute the function
            start_time = time.time()
            function_response = function_to_call(**function_args)
            execution_time = time.time() - start_time
            
            # Display the result based on function type
            self.display_tool_result(function_name, function_response, execution_time)
            
            # Add tool call output to messages
            self.assistant.add_toolcall_output(
                tool_call.id, function_name, function_response
            )
        except Exception as e:
            self.assistant.console.print(f"[error]Error executing {function_name}: {e}[/]")
            self.assistant.console.print()  # Add space for readability
            self.assistant.add_toolcall_output(tool_call.id, function_name, str(e))

    def display_tool_call(self, function_name: str, function_args: Dict[str, Any]) -> None:
        """Format and display a tool call with its arguments."""
        args_display = []
        for arg_name, arg_value in function_args.items():
            if isinstance(arg_value, str) and len(arg_value) > 50:
                # Truncate long string arguments for display
                display_val = f"{arg_value[:47]}..."
            else:
                display_val = str(arg_value)
            args_display.append(f"{arg_name}={display_val}")
        
        args_str = ", ".join(args_display)
        self.assistant.console.print(f"[cyan]→ {function_name}({args_str})[/]")

    def display_tool_result(self, function_name: str, result: Any, execution_time: float) -> None:
        """Display the result of a tool execution based on the tool type."""
        from assistant.core import SEARCH_TOOLS
        
        if function_name in SEARCH_TOOLS:
            # For search tools, just show count of results
            result_count = self.count_search_results(result)
            self.assistant.console.print(f"[success]✓ Completed in {execution_time:.4f}s: received {result_count} results[/]")
        else:
            # For non-search tools, show condensed preview (2-3 lines max)
            brief_response = self.get_condensed_preview(result)
            self.assistant.console.print(f"[success]✓ Completed in {execution_time:.4f}s: {brief_response}[/]")
        
        self.assistant.console.print()  # Add space for readability

    def count_search_results(self, result: Any) -> int:
        """Count the number of results in a search response."""
        try:
            if isinstance(result, dict):
                if "results" in result:
                    return len(result["results"])
                if "matches" in result:
                    return len(result["matches"])
                if "posts" in result:
                    return len(result["posts"])
            elif isinstance(result, list):
                return len(result)
            return 1  # Default for single-result responses
        except Exception:
            return 0

    def get_condensed_preview(self, result: Any) -> str:
        """Get a condensed preview of a result (2-3 lines max) for display."""
        try:
            # Convert to string first
            if not isinstance(result, str):
                if isinstance(result, dict) or isinstance(result, list):
                    # Try to format JSON nicely, but keep it short
                    result_str = str(result)[:200]
                else:
                    result_str = str(result)[:200]
            else:
                result_str = result[:200]
            
            # Truncate to first 2-3 lines with ellipsis
            lines = result_str.split("\n")
            if len(lines) > 3:
                short_result = "\n".join(lines[:3]) + "..."
            else:
                short_result = result_str
                
            # Further truncate if too long
            if len(short_result) > 200:
                short_result = short_result[:197] + "..."
                
            return short_result
        except Exception:
            return "[Preview not available]"

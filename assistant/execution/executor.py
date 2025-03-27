"""
Tool execution engine for the assistant.
"""
import json
import time
import inspect
from typing import Any, Dict, List, Callable, Optional, Type
from dataclasses import dataclass

from .display_manager import ToolDisplayManager, DisplayConfig
from .result_handlers import (
    ToolResultHandler,
    SearchResultHandler,
    DefaultResultHandler,
    LongTextResultHandler,
    JsonResultHandler,
    ResultContext
)

from ..exceptions.base import ToolExecutionError

@dataclass
class ToolExecutionContext:
    """Context for a tool execution."""
    name: str
    tool_call_id: str
    args: Dict[str, Any]
    start_time: float

class ToolExecutor:
    """Handles tool execution with structured result handling and display."""
    
    def __init__(self, assistant):
        """Initialize the tool executor.
        
        Args:
            assistant: Parent assistant reference
        """
        self.assistant = assistant
        self.display = ToolDisplayManager(assistant.console)
        
        # Initialize result handlers
        self.result_handlers = {
            "search": SearchResultHandler(),
            "text": LongTextResultHandler(),
            "json": JsonResultHandler(),
            "default": DefaultResultHandler()
        }
        
        # Search tool names (could be loaded from config)
        self.search_tool_names = {"web_search", "reddit_search"}
        
    def execute_tool_call(self, tool_call: Any) -> None:
        """Execute a single tool call and handle the result.
        
        Args:
            tool_call: Tool call information
        """
        # Create execution context
        context = ToolExecutionContext(
            name=tool_call.function.name,
            tool_call_id=tool_call.id,
            args={},
            start_time=time.time()
        )

        # Validate and get function
        function_to_call = self._get_tool_function(context.name)
        if not function_to_call:
            self.display.display_missing_tool(context.name)
            self._handle_missing_tool(context)
            return

        try:
            # Process arguments
            context.args = self._prepare_arguments(function_to_call, tool_call.function.arguments)
            self.display.display_tool_call(context.name, context.args)
            
            # Execute function
            self.display.display_start_execution(context.name)
            result = function_to_call(**context.args)
            
            # Process and display result
            self._handle_successful_result(result, context)
            
        except Exception as e:
            self._handle_execution_error(e, context)
            
    def _get_tool_function(self, name: str) -> Optional[Callable]:
        """Get the tool function by name."""
        return self.assistant.available_functions.get(name)
            
    def _prepare_arguments(self, function: Callable, arguments_json: str) -> Dict[str, Any]:
        """Parse and convert function arguments to appropriate types.
        
        Args:
            function: The function to prepare arguments for
            arguments_json: JSON string of arguments
            
        Returns:
            Dictionary of prepared arguments
            
        Raises:
            ToolExecutionError: If argument processing fails
        """
        try:
            function_args = json.loads(arguments_json)
            
            # Convert arguments based on function signature annotations
            sig = inspect.signature(function)
            for param_name, param in sig.parameters.items():
                if param_name in function_args:
                    function_args[param_name] = self.assistant.type_converter.convert_to_pydantic_model(
                        param.annotation, function_args[param_name]
                    )
                elif param.default is inspect.Parameter.empty and param.kind != inspect.Parameter.VAR_KEYWORD:
                    raise ToolExecutionError(
                        message=f"Missing required argument: {param_name}",
                        tool_name=function.__name__,
                        tool_args=arguments_json,
                        details={"function_name": function.__name__, "arguments_json": arguments_json, "tool_call_id": context.tool_call_id, "missing_argument": param_name}
                    )


            # Validate argument types against annotations
            for param_name, param in sig.parameters.items():
                if param_name in function_args:
                    expected_type = param.annotation
                    arg_value = function_args[param_name]

                    if expected_type != inspect.Parameter.empty and not isinstance(arg_value, expected_type):
                        raise ToolExecutionError(
                            message=f"Invalid argument type for '{param_name}'. Expected '{expected_type.__name__}', got '{type(arg_value).__name__}'",
                            tool_name=function.__name__,
                            tool_args=arguments_json,
                            details={
                                "function_name": function.__name__,
                                "arguments_json": arguments_json,
                                "tool_call_id": context.tool_call_id,
                                "param_name": param_name,
                                "expected_type": expected_type.__name__,
                                "actual_type": type(arg_value).__name__
                            }
                        )


            return function_args
        except json.JSONDecodeError as e:
            raise ToolExecutionError(
                message=f"Invalid JSON arguments: {str(e)}",
                tool_name=function.__name__,
                tool_args=arguments_json,
                details={"function_name": function.__name__, "arguments_json": arguments_json, "tool_call_id": context.tool_call_id}
            ) from e
        except ToolExecutionError as e:
            raise e # Re-raise ToolExecutionError to avoid double wrapping
        except Exception as e:
            raise ToolExecutionError(
                message=f"Failed to process arguments: {str(e)}",
                tool_name=function.__name__,
                tool_args=arguments_json,
                details={"function_name": function.__name__, "arguments_json": arguments_json, "tool_call_id": context.tool_call_id}
            ) from e

    def _get_result_handler(self, result: Any, tool_name: str) -> ToolResultHandler:
        """Get the appropriate result handler for the given result."""
        if tool_name in self.search_tool_names:
            return self.result_handlers["search"]
        elif isinstance(result, (dict, list)):
            return self.result_handlers["json"]
        elif isinstance(result, str) and len(result) > 200:
            return self.result_handlers["text"]
        return self.result_handlers["default"]
            
    def _handle_successful_result(self, result: Any, context: ToolExecutionContext) -> None:
        """Handle successful tool execution.
        
        Args:
            result: The result from tool execution
            context: Tool execution context
        """
        # Calculate execution time and create result context
        execution_time = time.time() - context.start_time
        result_context = ResultContext(execution_time=execution_time)
        
        # Get appropriate handler and format result
        handler = self._get_result_handler(result, context.name)
        formatted_result = handler.format_result(result, result_context)
        
        # Display the result
        self.display.display_tool_result(context.name, formatted_result)
        
        # Add to conversation history
        self.assistant.add_toolcall_output(
            context.tool_call_id,
            context.name,
            result
        )
        
    def _handle_execution_error(self, error: Exception, context: ToolExecutionContext) -> None:
        """Handle tool execution error.
        
        Args:
            error: The error that occurred
            context: Tool execution context
        """
        # Wrap in ToolExecutionError if needed
        if not isinstance(error, ToolExecutionError):
            error = ToolExecutionError(
                message=str(error),
                tool_name=context.name,
                tool_args=context.args
            )

        # Display error
        self.display.display_tool_error(context.name, str(error))

        # Add error to conversation history
        self.assistant.add_toolcall_output(
            context.tool_call_id,
            context.name,
            str(error),
            error_details=context.args
        )

    def _handle_missing_tool(self, context: ToolExecutionContext) -> None:
        """Handle missing tool error.

        Args:
            context: Tool execution context
        """
        error = ToolExecutionError(
            message=f"Tool not found: {context.name}",
            tool_name=context.name,
            tool_args={},
            details={"tool_call_id": context.tool_call_id, "tool_name": context.name} # Add context details for missing tool
        )
        self.assistant.add_toolcall_output(
            context.tool_call_id,
            context.name,
            str(error),
            error_details={"tool_name": context.name, "tool_call_id": context.tool_call_id} # Add tool name to error details
        )

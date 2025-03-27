"""
Tool execution engine for the assistant with async support.
"""
import json
import time
import inspect
import asyncio
from typing import Any, Dict, List, Callable, Optional, Type, Union, Coroutine, Tuple
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
        
    async def execute_tool_call(self, tool_call: Any) -> None:
        """Execute a single tool call and handle the result asynchronously.
        
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
        function_info = self._get_tool_function(context.name)
        if not function_info[0]:
            self.display.display_missing_tool(context.name)
            await self._handle_missing_tool(context)
            return

        function_to_call, is_async = function_info

        try:
            # Process arguments
            context.args = await self._prepare_arguments(function_to_call, tool_call.function.arguments, context)
            self.display.display_tool_call(context.name, context.args)
            
            # Execute function
            self.display.display_start_execution(context.name)
            
            # Handle both async and sync functions
            if is_async:
                result = await function_to_call(**context.args)
            else:
                # Run sync functions in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: function_to_call(**context.args))
            
            # Process and display result
            await self._handle_successful_result(result, context)
            
        except Exception as e:
            await self._handle_execution_error(e, context)
            
    def _get_tool_function(self, name: str) -> Tuple[Optional[Union[Callable, Coroutine]], bool]:
        """Get the tool function by name and determine if it's async.
        
        Returns:
            Tuple of (function, is_async)
        """
        function = self.assistant.available_functions.get(name)
        if function:
            return function, inspect.iscoroutinefunction(function)
        return None, False
            
    async def _prepare_arguments(self, function: Callable, arguments_json: str, context: ToolExecutionContext) -> Dict[str, Any]:
        """Parse and convert function arguments to appropriate types.
        
        Args:
            function: The function to prepare arguments for
            arguments_json: JSON string of arguments
            context: Tool execution context
            
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
                    # Handle async conversion if needed
                    converter = self.assistant.type_converter.convert_to_pydantic_model
                    if inspect.iscoroutinefunction(converter):
                        function_args[param_name] = await converter(param.annotation, function_args[param_name])
                    else:
                        function_args[param_name] = converter(param.annotation, function_args[param_name])
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
            raise e  # Re-raise ToolExecutionError to avoid double wrapping
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
            
    async def _handle_successful_result(self, result: Any, context: ToolExecutionContext) -> None:
        """Handle successful tool execution asynchronously.
        
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
        await self._add_to_history(context.tool_call_id, context.name, result)
        
    async def _handle_execution_error(self, error: Exception, context: ToolExecutionContext) -> None:
        """Handle tool execution error asynchronously.
        
        Args:
            error: The error that occurred
            context: Tool execution context
        """
        # Wrap in ToolExecutionError if needed
        if not isinstance(error, ToolExecutionError):
            error = ToolExecutionError(
                message=str(error),
                tool_name=context.name,
                tool_args=context.args,
                details={"tool_call_id": context.tool_call_id}
            )

        # Display error
        self.display.display_tool_error(context.name, str(error))

        # Add error to conversation history
        await self._add_to_history(context.tool_call_id, context.name, str(error))

    async def _handle_missing_tool(self, context: ToolExecutionContext) -> None:
        """Handle missing tool error asynchronously.

        Args:
            context: Tool execution context
        """
        error = ToolExecutionError(
            message=f"Tool not found: {context.name}",
            tool_name=context.name,
            tool_args={},
            details={"tool_call_id": context.tool_call_id}
        )

        # Display error
        self.display.display_tool_error(context.name, str(error))

        # Add to conversation history
        await self._add_to_history(context.tool_call_id, context.name, str(error))

    async def _add_to_history(self, tool_call_id: str, name: str, content: Any) -> None:
        """Add tool call output to conversation history asynchronously."""
        add_output = self.assistant.add_toolcall_output
        if inspect.iscoroutinefunction(add_output):
            await add_output(tool_call_id, name, content)
        else:
            # Run sync function in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: add_output(tool_call_id, name, content))

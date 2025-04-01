"""
Core Assistant class that coordinates different components.
"""
import inspect
import json
import os
import logging
from typing import Callable, Dict, Any, List, Optional, Union, Coroutine
import time
import traceback
import asyncio

from rich.console import Console
from rich.theme import Theme
import litellm

from config import get_config # Added import
from assistant.error_handling.error_handler import ErrorHandler
from assistant.logging.logger import AssistantLogger
from assistant.exceptions.base import (
    AssistantError,
    ToolExecutionError,
    ConfigurationError,
    MessageProcessingError,
    APICallError  # Import APICallError
)

from func_to_schema import function_to_json_schema
from plugins import get_registry, discover_plugins

from assistant.display import AssistantDisplay
from assistant.messaging import MessageProcessor
from assistant.reasoning import ReasoningEngine
from assistant.execution import ToolExecutor, ToolDisplayManager
from assistant.session import SessionManager
from assistant.conversion import TypeConverter

# NOTE: CUSTOM_THEME removed as it was redundant. Theme is loaded from config.

# NOTE: SEARCH_TOOLS constant removed as it was unused.

class Assistant:
    """
    A terminal-based assistant that can converse and execute tools.
    Implements an agentic workflow with planning, execution, and reflection.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        name: Optional[str] = None,
        tools: List[Union[Callable, Coroutine]] = None,
        system_instruction: str = "",
        discover_plugins_on_start: bool = True,
        log_level: Optional[int] = None
    ) -> None:
        """Initialize the assistant with model and tools."""
        try:
            self._initialize_configuration(model, name, system_instruction)
            self._initialize_logging(log_level)
            self._discover_and_register_plugins(discover_plugins_on_start, tools)
            self._initialize_components()

            # Add system instruction if provided
            if system_instruction:
                self.messages.append({"role": "system", "content": system_instruction})

        except Exception as e:
            # Use existing console if initialized, otherwise create temporary one
            console = getattr(self, 'console', Console())
            console.print(f"[bold red]Critical Error during Assistant Initialization:[/]\n{traceback.format_exc()}")
            # Re-raise as ConfigurationError for clarity upstream
            raise ConfigurationError(
                f"Failed to initialize assistant: {str(e)}",
                details={"init_error": str(e)}
            ) from e

    def _initialize_configuration(self, model, name, system_instruction):
        """Initialize configuration settings."""
        # from config import get_config # Moved import to top level
        config = get_config()

        # Use config values or override with parameters
        self.model = model or config.settings.MODEL
        self.name = name or config.settings.NAME
        self.system_instruction = system_instruction
        self.messages = []
        self.last_initial_plan = None # Renamed for clarity in agentic flow

    def _initialize_logging(self, log_level):
        """Initialize logging and error handling."""
        # Initialize error handling and logging
        self.error_handler = ErrorHandler()
        self.logger = AssistantLogger(log_level=log_level or logging.INFO)

    def _discover_and_register_plugins(self, discover_plugins_on_start, tools):
        """Initialize plugin discovery and tool registration."""
        # Discover plugins if requested
        if discover_plugins_on_start:
            discover_plugins()

        # Register tools and combine lists
        registry = get_registry()
        registry_tools = list(registry.get_tools().values())
        if tools is None:
            tools = registry_tools
        else:
            # Ensure tools are callable or coroutines before processing
            valid_tools = [t for t in tools if callable(t) or inspect.iscoroutinefunction(t)]
            if len(valid_tools) != len(tools):
                # Log or handle invalid tool types if necessary
                pass # Placeholder for potential error logging
            tools = valid_tools

            registry_tool_names = {t.__name__ for t in registry_tools}
            explicit_tools = [
                tool for tool in tools if tool.__name__ not in registry_tool_names
            ]
            tools = registry_tools + explicit_tools

        self.available_functions = {func.__name__: func for func in tools}
        self.tools = [
            function_to_json_schema(func, vertex_compatible=True) for func in tools
        ]

    def _initialize_components(self):
        """Initialize core components."""
        # from config import get_config # Moved import to top level
        config = get_config()
        theme = config.get_theme()  # Get default theme

        # Initialize components using dependency injection
        self.console = Console(theme=Theme(theme))
        self.display = AssistantDisplay(self)
        self.message_processor = MessageProcessor(self) # MessageProcessor needs self
        self.reasoning_engine = ReasoningEngine(self)   # ReasoningEngine needs self
        self.tool_executor = ToolExecutor(self)         # ToolExecutor needs self
        self.session_manager = SessionManager(self)     # SessionManager needs self
        self.type_converter = TypeConverter()

    async def send_message(self, message: str) -> Dict[str, Any]:
        """
        Process user message using an agentic approach:
        1. Initial Planning (Internal/Concise)
        2. Dynamic Execution & Adaptation
        3. Self-Reflection
        4. Final Response Generation
        """
        # Add user message to history *before* processing
        self.messages.append({"role": "user", "content": message})

        try:
            # Log start of message processing
            self.logger.log_info(
                "Starting agentic message processing",
                {"message_length": len(message)}
            )

            # --- Agentic Flow ---
            # The core logic is now delegated to MessageProcessor
            response_message = await self.message_processor.process_agentic_flow(message)

            # Log successful completion
            self.logger.log_info(
                "Agentic message processing completed successfully",
                {"response_type": type(response_message).__name__}
            )

            # Return the final response content or structure
            # Ensure response_message is not None and has content attribute
            if response_message and hasattr(response_message, 'content'):
                 # Make sure to add the final assistant message to history
                await self.add_msg_assistant(response_message)
                return {"content": response_message.content}
            elif response_message:  # Handle cases where response might be structured differently
                # Log non-standard response structure as debug if necessary
                if not (isinstance(response_message, dict) and "response_data" in response_message):
                    self.logger.log_debug("Agentic flow received non-standard response structure", {"response": str(response_message)})
                # Attempt to add to history if possible, otherwise log failure
                try:
                    await self.add_msg_assistant(response_message)  # Assumes it's a dict matching schema
                except Exception as add_err:
                    self.logger.log_error("Failed to add unexpected response structure to history", {"error": str(add_err)})
                return {"response_data": response_message}  # Or convert to dict if needed
            else:
                 # Log unexpected empty response
                self.logger.log_error("Agentic flow returned None or invalid response_message", {"message": message})
                # Provide a generic error response to the user
                error_message = "Sorry, I encountered an issue generating a response. Please try again."
                await self.add_msg_assistant(error_message)
                self.display.print_ai(error_message)
                return {"error": "empty_response_from_agentic_flow"}

        except AssistantError as e:
            # Handle known assistant errors
            error_info = self.error_handler.handle_error(e, {
                "message": message,
                "last_initial_plan": self.last_initial_plan # Use renamed attribute
            })

            error_message = f"I encountered an error: {e}"
            self.console.print(f"[error]Message processing error: {e}[/]")
            # Avoid adding duplicate assistant messages if error handling already did
            if not self.messages or self.messages[-1].get("content") != error_message:
                await self.add_msg_assistant(error_message)
            self.display.print_ai(error_message) # Display error to user

            return {
                "error": str(e),
                "error_info": error_info
            }

        except Exception as e:
            # Handle unexpected errors
            # Use logger.exception to include traceback in logs
            self.logger.logger.exception(f"Unexpected error during agentic message processing: {e}", extra={"message": message})
            error_info = self.error_handler.handle_error(e, {
                "message": message,
                "last_initial_plan": self.last_initial_plan # Use renamed attribute
            })

            error_message = (
                "I encountered an unexpected internal error. This has been logged. "
                "Please try again or rephrase your request."
            )
            self.console.print(f"[error]Unexpected error: {e}[/]\n{traceback.format_exc()}") # Print traceback to console
            # Avoid adding duplicate assistant messages
            if not self.messages or self.messages[-1].get("content") != error_message:
                await self.add_msg_assistant(error_message)
            self.display.print_ai(error_message) # Display error to user

            return {
                "error": "unexpected_error",
                "error_info": error_info
            }

    async def get_completion(self, messages: List[Dict[str, Any]] = None, tools: List[Dict[str, Any]] = None) -> Any:
        """Get a completion from the model with optional specific messages and tools."""
        # from config import get_config # Moved import to top level
        config = get_config()
        loop = asyncio.get_event_loop()
        messages_to_use = messages if messages is not None else self.messages
        tools_to_use = tools if tools is not None else self.tools

        # Filter out None tools if tools_to_use is self.tools
        if tools_to_use is self.tools:
            tools_to_use = [t for t in self.tools if t is not None]

        # Ensure safety_settings is correctly formatted if present
        safety_settings = config.safety_settings if hasattr(config, 'safety_settings') else None

        # Log the request being sent to the LLM if debugging
        if config.settings.DEBUG_MODE:
             self.logger.log_debug("LLM completion request", {
                 "model": self.model,
                 "message_count": len(messages_to_use),
                 "tool_count": len(tools_to_use),
                 "temperature": config.settings.TEMPERATURE,
                 "top_p": config.settings.TOP_P,
                 "max_tokens": config.settings.MAX_TOKENS,
                 "seed": config.settings.SEED,
             })

        try:
            response = await loop.run_in_executor(None, lambda: litellm.completion(
                model=self.model,
                messages=messages_to_use,
                tools=tools_to_use,
                temperature=config.settings.TEMPERATURE,
                top_p=config.settings.TOP_P,
                max_tokens=config.settings.MAX_TOKENS,
                seed=config.settings.SEED,
                safety_settings=safety_settings
            ))
            # Log the raw response if debugging
            if config.settings.DEBUG_MODE:
                self.logger.log_debug("LLM completion response received", {"response_object": str(response)}) # Convert complex object to string for logging
            return response
        except Exception as e:
            self.logger.log_error("LLM completion call failed", {"error": str(e)})
            raise APICallError(
                message=f"Language model API call failed: {str(e)}",
                model_name=self.model,
                retries=0, # This method doesn't handle retries itself
                details={"error": str(e), "trace": traceback.format_exc()}
            ) from e

    async def get_completion_with_retry(self, messages: List[Dict[str, Any]] = None, tools: List[Dict[str, Any]] = None, max_retries: int = 3) -> Any:
        """Get a completion from the model with retry logic."""
        last_exception = None # Keep track of the last exception for final error reporting
        for attempt in range(max_retries):
            try:
                # Use the core get_completion method for the actual call
                return await self.get_completion(messages=messages, tools=tools)
            except APICallError as e:
                last_exception = e # Store the exception
                # Check for retryable errors (e.g., rate limits, temporary server issues)
                error_str = str(e).lower()
                is_retryable = "rate limit" in error_str or \
                               "resource exhausted" in error_str or \
                               "server error" in error_str or \
                               "service unavailable" in error_str or \
                               "500" in error_str or "503" in error_str # Common HTTP status codes

                if is_retryable and attempt < max_retries - 1:
                    delay = 4 * (2 ** attempt)  # Exponential backoff: 4, 8, 16...
                    self.console.print(f"[warning]API Error: {e}. Retrying in {delay} seconds... ({attempt + 1}/{max_retries})[/]")
                    self.logger.log_warning(f"API call failed (attempt {attempt + 1}), retrying in {delay}s", {"error": str(e)})
                    await asyncio.sleep(delay)
                else:
                    self.logger.log_error(f"API call failed after {attempt + 1} attempts or non-retryable error", {"error": str(e)})
                    raise # Re-raise the original APICallError if not retryable or max retries reached
            except Exception as e: # Catch other potential exceptions during the call
                last_exception = e # Store the exception
                # Use logger.exception here as well
                self.logger.logger.exception(f"Unexpected error during get_completion_with_retry (attempt {attempt + 1}): {e}")
                # Decide if unexpected errors should be retried or immediately raised
                # For now, re-raise non-APICallErrors immediately
                raise

        # If loop finishes, it means max retries were exceeded for a retryable error
        # Raise the last captured exception
        self.logger.log_critical("get_completion_with_retry loop finished after max retries", {"max_retries": max_retries, "last_error": str(last_exception)})
        if isinstance(last_exception, Exception): # Ensure last_exception is actually an exception
             raise APICallError(
                message=f"Failed to get completion after maximum retries. Last error: {str(last_exception)}",
                model_name=self.model,
                retries=max_retries,
                details={"last_error": str(last_exception)}
            ) from last_exception
        else: # Fallback error if last_exception wasn't set somehow
             raise APICallError(
                message="Failed to get completion after maximum retries.",
                model_name=self.model,
                retries=max_retries
             )


    async def add_msg_assistant(self, msg: Union[str, Dict[str, Any]]) -> None:
        """Add an assistant message (text or tool call structure) to the conversation history."""
        # from config import get_config # Moved import to top level
        config = get_config()
        message_to_add = None
        if isinstance(msg, str):
            message_to_add = {"role": "assistant", "content": msg}
        elif isinstance(msg, dict) and msg.get("role") == "assistant":
            # Allow adding pre-formatted assistant messages (e.g., with tool_calls)
             # Ensure content is present, even if empty for tool calls
            if "content" not in msg:
                msg["content"] = None # Or "" if preferred by the model API
            message_to_add = msg
        # Handle litellm response message object directly
        elif hasattr(msg, 'role') and msg.role == 'assistant':
             content = getattr(msg, 'content', None)
             tool_calls = getattr(msg, 'tool_calls', None)
             message_to_add = {"role": "assistant", "content": content}
             if tool_calls:
                 # Convert tool_calls if they are not dicts (handle Pydantic models etc.)
                 try:
                     message_to_add["tool_calls"] = [dict(tc) if not isinstance(tc, dict) else tc for tc in tool_calls]
                 except Exception as conv_err:
                      self.logger.log_error("Failed to convert tool_calls to dict", {"error": str(conv_err), "tool_calls_type": type(tool_calls)})
                      # Decide how to handle: maybe add without tool_calls or raise error
                      message_to_add["tool_calls"] = [] # Add empty list as fallback
        else:
            # Log error for invalid message type
            self.logger.log_error("Invalid type or structure for add_msg_assistant", {"msg_type": type(msg), "msg_preview": str(msg)[:100]})

        if message_to_add:
            # Avoid adding exact duplicate messages consecutively
            if not self.messages or self.messages[-1] != message_to_add:
                 self.messages.append(message_to_add)
                 if config.settings.DEBUG_MODE: # Use config directly now
                     self.logger.log_debug("Added assistant message to history", {"message_preview": str(message_to_add)[:100]})
            elif config.settings.DEBUG_MODE: # Use config directly now
                 self.logger.log_debug("Skipped adding duplicate assistant message", {"message_preview": str(message_to_add)[:100]})


    async def add_toolcall_output(self, tool_id: str, name: str, content: Any) -> None:
        """Add a tool call result to the conversation history."""
        # from config import get_config # Moved import to top level
        config = get_config()
        # Ensure content is stringified for the API
        content_str = str(content)
        message_to_add = {
            "tool_call_id": tool_id,
            "role": "tool",
            "name": name,
            "content": content_str,
        }
        self.messages.append(message_to_add)
        # Log tool output if debugging
        if config.settings.DEBUG_MODE: # Use config directly now
            self.logger.log_debug("Added tool call output", {"tool_id": tool_id, "name": name, "content_preview": content_str[:100]}) # Log preview

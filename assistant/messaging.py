"""
Message processing and conversation flow management with async support.
"""
import json
from typing import Dict, Any, List, Optional
import traceback
import asyncio
from .exceptions.base import MessageProcessingError, AsyncOperationError, APICallError

from config import get_config
from config.services.context import format_prompt_with_context # Import formatter

class MessageProcessor:
    """Handles message processing and conversation flow."""

    def __init__(self, assistant):
        """Initialize with parent assistant reference."""
        self.assistant = assistant
        # NOTE: Model parameters (temperature, top_p, etc.) are no longer stored here.
        # The Assistant class will fetch them directly from config when needed.

    async def process_with_reasoning(self, message: str, reasoning: str) -> Dict[str, Any]:
        """Process a user message with the reasoning already generated."""
        self._validate_message_input(message, reasoning)
        config = get_config() # Fetch config

        # Create a new message list for execution phase
        execution_messages = []

        # Format and add the execution system prompt
        execution_prompt_template = config.prompt_manager.execution_prompt
        formatted_execution_prompt = await format_prompt_with_context(
            execution_prompt_template,
            self.assistant.name # Use assistant's name for context
        )
        execution_messages.append({
            "role": "system",
            "content": f"{formatted_execution_prompt}\n\nYour reasoning plan: {reasoning}"
        })

        # Add the conversation history (except the system message)
        for msg in self.assistant.messages:
            if msg["role"] != "system":
                execution_messages.append(msg)

        # Add the user's message
        execution_messages.append({"role": "user", "content": message})

        # Store the user message in the main message history
        self.assistant.messages.append({"role": "user", "content": message})

        try:
            # Get the execution response with completely separate message context
            response = await self.assistant.get_completion_with_retry(execution_messages)

            # Process response but handle potential None/invalid cases
            if not response:
                raise MessageProcessingError(
                    message="Empty response from language model",
                    phase="execution",
                    details={"response": str(response)}
                )

            return await self.process_response(response)

        except Exception as e:
            if isinstance(e, (MessageProcessingError, APICallError)):
                raise e
            raise MessageProcessingError(
                message=str(e),
                phase="execution",
                details={"error": str(e)}
            ) from e

    async def process_response(self, response: Any, print_response: bool = True) -> Dict[str, Any]:
        """Process the model's response, including any tool calls."""
        try:
            # Pre-validate response format
            self._validate_response_input(response)

            if not hasattr(response.choices[0], 'message'):
                raise MessageProcessingError(
                    message="Invalid response format - missing message attribute",
                    phase="response_processing",
                    details={"response": str(response)}
                )

            response_message = response.choices[0].message
            tool_calls = getattr(response_message, 'tool_calls', None)

            # Ensure message has content
            if not hasattr(response_message, 'content') or response_message.content is None:
                response_message.content = "" # Set empty string for non-tool responses

            # Display model reasoning in debug mode
            self.assistant.display.extract_and_display_reasoning(response)

            self.assistant.messages.append(response_message)
            final_response = response_message

            # Process tool calls if present
            if tool_calls:
                self._handle_reasoning_display(response_message, print_response)
                self.assistant.console.print(f"[bold cyan]Running {len(tool_calls)} tool operation(s):[/]")

                # Process each tool call asynchronously
                for tool_call in tool_calls:
                    await self.assistant.tool_executor.execute_tool_call(tool_call)

                # Add a visual separator after all tool calls
                self.assistant.console.print("[cyan]───────────────────────────────────────[/]")

                # Get the final response after tool execution
                final_response = await self.assistant.get_completion()

                if not final_response or not hasattr(final_response, 'choices'):
                    raise MessageProcessingError(
                        message="Invalid final response format",
                        phase="response_processing",
                        details={"response": str(final_response)}
                    )

                tool_calls = getattr(final_response.choices[0].message, 'tool_calls', None)

                if not tool_calls:
                    response_message = final_response.choices[0].message
                    self.assistant.messages.append(response_message)
                    if print_response and hasattr(response_message, 'content'):
                        # Add a visual indicator that this is the final response
                        self.assistant.console.print("[bold green]Final Response:[/]")
                        self.assistant.display.print_ai(response_message.content)
                    return response_message

                # Handle any additional tool calls recursively
                return await self.process_response(final_response, print_response=print_response)
            else:
                # No tool calls - display the response directly
                if print_response and hasattr(response_message, 'content'):
                    self.assistant.display.print_ai(response_message.content)
                return response_message

        except Exception as e:
            self.assistant.console.print(f"[error]Error in processing response: {e}[/]")
            traceback.print_exc()
            if isinstance(e, MessageProcessingError):
                raise
            raise AsyncOperationError(
                message=str(e),
                operation="response_processing",
                details={"error": str(e)}
            ) from e

    def _handle_reasoning_display(self, response_message: Any, print_response: bool) -> None:
        """Display model's reasoning before tool calls if present."""
        if hasattr(response_message, 'content') and response_message.content and print_response:
            self.assistant.console.print("[dim italic]Model thinking: " + response_message.content.strip() + "[/]")
            self.assistant.console.print()  # Add space for readability

    def _validate_message_input(self, message: str, reasoning: str) -> None:
        """Validate user message and reasoning input."""
        if not isinstance(message, str):
            raise MessageProcessingError(
                message=f"Message must be a string, got {type(message)}",
                phase="input_validation",
                details={"type": str(type(message))}
            )
        if not message.strip():
            raise MessageProcessingError(
                message="Message cannot be empty or just whitespace",
                phase="input_validation"
            )
        if not isinstance(reasoning, str):
            raise MessageProcessingError(
                message=f"Reasoning must be a string, got {type(reasoning)}",
                phase="input_validation",
                details={"type": str(type(reasoning))}
            )

    def _validate_response_input(self, response: Any) -> None:
        """Validate model response input."""
        if not response:
            raise MessageProcessingError(
                message="Response cannot be None or empty",
                phase="response_validation"
            )

        if not hasattr(response, 'choices') or not isinstance(response.choices, list):
            raise MessageProcessingError(
                message="Response must have a 'choices' attribute that is a list",
                phase="response_validation",
                details={"response_type": str(type(response))}
            )

        if not response.choices:
            raise MessageProcessingError(
                message="Response choices cannot be empty",
                phase="response_validation"
            )

        if not hasattr(response.choices[0], 'message'):
            raise MessageProcessingError(
                message="Response choice must have a 'message' attribute",
                phase="response_validation",
                details={"choice_type": str(type(response.choices[0]))}
            )

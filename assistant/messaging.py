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
            "content": formatted_execution_prompt # Remove reasoning from system prompt
        })

        # Add the conversation history (except the system message)
        for msg in self.assistant.messages:
            if msg["role"] != "system":
                execution_messages.append(msg)

        # Inject reasoning plan as an assistant instruction before the user message
        execution_messages.append({
            "role": "assistant",
            "content": f"Okay, I will execute the following reasoning plan precisely:\n```\n{reasoning}\n```\n"
        })

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
        """Process the model's response, looping through tool calls until completion."""
        current_response = response
        loop_count = 0
        max_loops = 10 # Safety break to prevent infinite loops

        try:
            while loop_count < max_loops:
                loop_count += 1
                self.assistant.logger.log_debug(f"Processing response loop iteration {loop_count}")

                # --- Validate current response ---
                self._validate_response_input(current_response) # Check if response object is valid
                if not current_response or not hasattr(current_response, 'choices') or not current_response.choices: # Check if choices list is empty or response invalid
                    raise MessageProcessingError(
                        message="Invalid response format in loop - missing or empty choices",
                        phase="response_processing_loop",
                        details={"response": str(current_response), "loop": loop_count}
                    )
                if not hasattr(current_response.choices[0], 'message'):
                    raise MessageProcessingError(
                        message="Invalid response format in loop - missing message attribute",
                        phase="response_processing_loop",
                        details={"response": str(current_response), "loop": loop_count}
                    )

                response_message = current_response.choices[0].message
                tool_calls = getattr(response_message, 'tool_calls', None)

                # Ensure message has content even if just calling tools
                if not hasattr(response_message, 'content') or response_message.content is None:
                    response_message.content = "" # Use empty string if no text content

                # Add the *intermediate* assistant message (which might contain tool calls) to history
                # Avoid duplicates if somehow the model returns the exact same message object
                if not self.assistant.messages or self.assistant.messages[-1] is not response_message:
                     self.assistant.messages.append(response_message)

                # --- Check for Tool Calls ---
                if tool_calls:
                    self.assistant.logger.log_debug(f"Found {len(tool_calls)} tool calls in loop {loop_count}")
                    self._handle_reasoning_display(response_message, print_response) # Display thinking before tools
                    self.assistant.console.print(f"[bold cyan]Running {len(tool_calls)} tool operation(s) (Loop {loop_count}):[/]")

                    # Execute the current batch of tool calls
                    for tool_call in tool_calls:
                        # tool_executor should add results to self.assistant.messages
                        await self.assistant.tool_executor.execute_tool_call(tool_call)

                    # Add a visual separator after this batch of tool calls
                    self.assistant.console.print("[cyan]───────────────────────────────────────[/]")

                    # Call the model *again* with the updated history (including tool results)
                    self.assistant.logger.log_debug(f"Requesting next step after loop {loop_count} tool execution")
                    try:
                        # Use the main history which now includes the latest tool results
                        current_response = await self.assistant.get_completion_with_retry() # Reassign current_response
                    except Exception as e:
                        # Log and re-raise specific error for API call failure within loop
                        raise MessageProcessingError(
                            message=f"Failed API call during tool loop {loop_count}: {str(e)}",
                            phase="tool_loop_api_call",
                            details={"error": str(e), "loop": loop_count}
                        ) from e
                    # Continue the loop to process the new response from the model
                    continue
                else:
                    # --- No More Tool Calls: Proceed to Final Synthesis ---
                    self.assistant.logger.log_debug("No more tool calls found, proceeding to final synthesis.")

                    # The last `response_message` from the loop is the one without tool calls.
                    # We will use our explicit synthesis prompt approach instead of just returning it.

                    # 1. Gather tool results and user query from the *entire* history
                    tool_results_summary = []
                    user_query = ""
                    system_prompt = ""
                    if self.assistant.messages and self.assistant.messages[0]["role"] == "system":
                        system_prompt = self.assistant.messages[0]["content"]

                    # Iterate through the potentially long history to find last user query and all tool results
                    for msg in reversed(self.assistant.messages):
                        if msg["role"] == "tool":
                            # Prepend results so they appear in execution order in the prompt
                            # Limit result size for prompt efficiency
                            content_str = str(msg.get('content', ''))
                            max_len = 500 # Max length for tool result content in prompt
                            if len(content_str) > max_len:
                                content_str = content_str[:max_len] + "... (truncated)"
                            tool_results_summary.insert(0, f"- Result from {msg.get('name', 'unknown_tool')} (ID: {msg.get('tool_call_id', 'N/A')}):\n```\n{content_str}\n```")
                        elif msg["role"] == "user" and not user_query:
                             # Find the *last* user message in the history
                            user_query = msg["content"]
                            # Optimization: Can stop once last user query is found if history order is guaranteed
                            # break # Keep searching history for all tool results

                    tool_results_text = "\n".join(tool_results_summary) if tool_results_summary else "No tool results were generated."

                    # 2. Construct synthesis prompt messages
                    synthesis_instructions = (
                        "The user asked the following:\n"
                        f"```\n{user_query}\n```\n\n"
                        "The following actions were taken and results gathered:\n"
                        f"{tool_results_text}\n\n"
                        "Based *only* on the user query and the provided tool results, synthesize a final, comprehensive response for the user.\n"
                        "Directly address all parts of the user's original query.\n"
                        "Present the information clearly. If code was generated and saved, include the code in a markdown block.\n"
                        "Do not just confirm that steps were done; provide the actual results found in the tool output."
                    )

                    synthesis_prompt_messages = []
                    if system_prompt:
                        # Using original system prompt for now
                        synthesis_prompt_messages.append({"role": "system", "content": system_prompt})
                    # Include user query for context, even though it's in the instruction
                    if user_query:
                        synthesis_prompt_messages.append({"role": "user", "content": user_query})
                    # Provide the instructions and results as the assistant's turn
                    synthesis_prompt_messages.append({"role": "assistant", "content": synthesis_instructions})

                    # 3. Get the final synthesized response
                    self.assistant.logger.log_debug("Requesting final synthesis", {"synthesis_prompt_msg_count": len(synthesis_prompt_messages)})
                    try:
                        final_synth_response = await self.assistant.get_completion_with_retry(messages=synthesis_prompt_messages)
                    except Exception as e:
                         # Log and re-raise specific error for final synthesis failure
                         raise MessageProcessingError(
                            message=f"Failed during final synthesis API call: {str(e)}",
                            phase="final_synthesis",
                            details={"error": str(e)}
                        ) from e

                    # Validate final synthesis response
                    self._validate_response_input(final_synth_response) # Check structure
                    if not final_synth_response.choices: # Check if choices list is empty
                         raise MessageProcessingError("Invalid final synthesis response: No choices found.", phase="final_synthesis")
                    if not hasattr(final_synth_response.choices[0], 'message'):
                         raise MessageProcessingError("Invalid final synthesis response format: Missing message.", phase="final_synthesis")

                    final_message = final_synth_response.choices[0].message

                    # Ensure the final synthesized message doesn't try to call tools again
                    if getattr(final_message, 'tool_calls', None):
                        self.assistant.logger.log_error("Unexpected tool calls returned during final synthesis!", {"response": final_message})
                        # Fallback: just use the content part if available, or provide an error message
                        final_message.content = getattr(final_message, 'content', "[Error: Synthesis failed, attempted further tool calls]")
                        # Ensure tool_calls is None or empty list if modifying object
                        try:
                            final_message.tool_calls = None
                        except AttributeError: # Handle case where attribute might not be settable
                             pass


                    # Add the *final synthesized* message to history
                    # Avoid duplicates if somehow it's the same as the last intermediate one
                    if not self.assistant.messages or self.assistant.messages[-1] is not final_message:
                        self.assistant.messages.append(final_message)

                    # Display the final synthesized response
                    if print_response and hasattr(final_message, 'content') and final_message.content:
                        self.assistant.console.print("[bold green]Final Response:[/]")
                        self.assistant.display.print_ai(final_message.content)
                    elif print_response:
                         self.assistant.console.print("[bold green]Final Response:[/]")
                         self.assistant.display.print_ai("[Assistant provided no text content]")


                    return final_message # Return the final synthesized message object

            # If loop exceeds max_loops
            self.assistant.logger.log_error(f"Tool execution loop exceeded maximum iterations ({max_loops})")
            raise MessageProcessingError(f"Tool execution loop exceeded maximum iterations ({max_loops})", phase="tool_loop")

        except Exception as e:
            self.assistant.console.print(f"[error]Error in processing response: {e}[/]")
            # Add traceback logging here
            self.assistant.logger.log_error(f"Traceback: {traceback.format_exc()}")
            # Ensure error is re-raised correctly
            if isinstance(e, (MessageProcessingError, AsyncOperationError)):
                raise
            # Wrap unexpected errors
            raise AsyncOperationError(
                message=f"Unhandled error in process_response: {str(e)}",
                operation="response_processing",
                details={"error": str(e)}
            ) from e

    def _handle_reasoning_display(self, response_message: Any, print_response: bool) -> None:
        """Display model's thinking before tool calls if present."""
        # Check if content exists and print_response is True
        if print_response and hasattr(response_message, 'content') and response_message.content:
             # Check if the content is not just whitespace
             content_strip = response_message.content.strip()
             if content_strip:
                 self.assistant.console.print("[dim italic]Model thinking: " + content_strip + "[/]")
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

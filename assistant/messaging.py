"""
Message processing and conversation flow management with async support.
"""
import json
from typing import Dict, Any, List, Optional, Union # Added Union
import traceback
import asyncio
import jinja2 # Added for prompt templating
from .exceptions.base import MessageProcessingError, AsyncOperationError, APICallError, ToolExecutionError # Added ToolExecutionError

from config import get_config
from config.services.context import format_prompt_with_context # Import formatter

# Initialize Jinja environment (consider moving to a central place if used elsewhere)
jinja_env = jinja2.Environment(autoescape=True)

class MessageProcessor:
    """Handles message processing and conversation flow."""

    def __init__(self, assistant):
        """Initialize with parent assistant reference."""
        self.assistant = assistant
        # NOTE: Model parameters (temperature, top_p, etc.) are no longer stored here.
        # The Assistant class will fetch them directly from config when needed.

    # --- Agentic Flow Method ---
    async def process_agentic_flow(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Processes a user message using an agentic workflow:
        Plan -> Execute (with potential tool loop) -> Reflect -> Final Response
        """
        self.assistant.logger.log_info("Starting process_agentic_flow", {"message": message[:50]})
        config = get_config() # Fetch config
        start_message_index = len(self.assistant.messages) -1 # Index of the current user message

        # --- 1. Initial Planning ---
        try:
            self.assistant.console.print("[bold blue]Planning Phase:[/]")
            # Use the reasoning engine to get an initial plan/thought process
            initial_plan = await self.assistant.reasoning_engine.get_reasoning(message)
            self.assistant.last_initial_plan = initial_plan # Store for context/debugging
            # Display the plan/reasoning concisely (only in debug mode)
            self.assistant.display.show_reasoning(initial_plan)
            self.assistant.console.print("[cyan]───────────────────────────────────────[/]") # Print separator even if reasoning not shown
        except Exception as e:
            # Use logger.exception to include traceback and rename extra key
            self.assistant.logger.logger.exception(f"Error during agentic planning phase: {e}", extra={"context_message": message})
            raise MessageProcessingError(
                message="Failed during agentic planning phase",
                phase="agentic_planning",
                details={"error": str(e)}
            ) from e

        # --- 2. Execution & Adaptation (via LLM calls with tools) ---
        final_assistant_message = None # Initialize
        try:
            self.assistant.console.print("[bold blue]Execution Phase:[/]")
            # Prepare messages for the first execution call
            # Includes system prompt, history, and the current user message
            # Does NOT include the explicit 'reasoning plan' from the old flow
            execution_messages = []
            system_prompt_found = False
            # Use messages up to the current user message for the initial execution call
            for i, msg in enumerate(self.assistant.messages):
                 if i > start_message_index: # Should not happen here, but safety check
                      break
                 if isinstance(msg, dict): # Ensure it's a dictionary
                     if msg["role"] == "system":
                         execution_messages.append(msg)
                         system_prompt_found = True
                     else:
                         execution_messages.append(msg)
                 else:
                     self.assistant.logger.log_warning(f"Non-dict message found in history at index {i}", {"message_type": type(msg)})

            # Ensure system prompt is present
            if not system_prompt_found:
                 base_system_prompt_template = config.prompt_manager.base_system_prompt
                 formatted_system_prompt = await format_prompt_with_context(
                     base_system_prompt_template,
                     self.assistant.name
                 )
                 execution_messages.insert(0, {"role": "system", "content": formatted_system_prompt})

            # Initial LLM call with tools enabled
            initial_response = await self.assistant.get_completion_with_retry(
                messages=execution_messages,
                tools=self.assistant.tools # Pass available tools
            )

            # Process the response, handling the tool call loop internally
            # process_response will now handle adding assistant/tool messages to self.assistant.messages
            final_assistant_message = await self.process_response(initial_response, print_response=False) # print_response=False as final display happens later

        except Exception as e:
            # Use logger.exception to include traceback and rename extra key
            self.assistant.logger.logger.exception(f"Error during agentic execution phase: {e}", extra={"context_message": message})
            if isinstance(e, (MessageProcessingError, APICallError, AsyncOperationError)):
                raise # Re-raise known types
            raise MessageProcessingError(
                message=f"Failed during agentic execution: {str(e)}",
                phase="agentic_execution",
                details={"error": str(e), "trace": traceback.format_exc()}
            ) from e

        # --- 3. Self-Reflection ---
        try:
            self.assistant.console.print("[bold blue]Reflection Phase:[/]")
            # Gather context for reflection prompt
            actions_log_list = []
            # Extract assistant messages with tool calls and subsequent tool responses
            # Start from *after* the user message that initiated this flow
            for i in range(start_message_index + 1, len(self.assistant.messages)):
                msg = self.assistant.messages[i]
                if isinstance(msg, dict): # Ensure it's a dict before accessing keys
                    if msg.get("role") == "assistant" and msg.get("tool_calls"):
                        # Safely serialize tool calls
                        safe_tool_calls = []
                        raw_tool_calls = msg.get("tool_calls", [])
                        if isinstance(raw_tool_calls, list):
                            for tc in raw_tool_calls:
                                safe_call = {}
                                if isinstance(tc, dict): # Handle if already dict
                                    safe_call['id'] = tc.get('id')
                                    safe_call['type'] = tc.get('type')
                                    if isinstance(tc.get('function'), dict):
                                        safe_call['function_name'] = tc['function'].get('name')
                                        # Arguments might be string or dict, handle safely
                                        args = tc['function'].get('arguments')
                                        safe_call['arguments'] = args if isinstance(args, (str, dict, list, int, float, bool, type(None))) else str(args)
                                elif hasattr(tc, 'id') and hasattr(tc, 'type') and hasattr(tc, 'function'): # Handle Pydantic/other objects
                                     safe_call['id'] = tc.id
                                     safe_call['type'] = tc.type
                                     if hasattr(tc.function, 'name') and hasattr(tc.function, 'arguments'):
                                         safe_call['function_name'] = tc.function.name
                                         args = tc.function.arguments
                                         safe_call['arguments'] = args if isinstance(args, (str, dict, list, int, float, bool, type(None))) else str(args)
                                if safe_call: # Only add if we could extract something useful
                                     safe_tool_calls.append(safe_call)
                        try:
                             actions_log_list.append(f"Assistant requested tools: {json.dumps(safe_tool_calls)}")
                        except TypeError as json_err:
                             self.assistant.logger.log_error(f"JSON serialization failed for safe_tool_calls: {json_err}", {"safe_calls": safe_tool_calls})
                             actions_log_list.append(f"Assistant requested tools: [Serialization Error - {json_err}]")

                    elif msg.get("role") == "tool":
                        actions_log_list.append(f"Tool '{msg.get('name')}' (ID: {msg.get('tool_call_id')}) result: {str(msg.get('content', ''))[:200]}...") # Preview content

            actions_log = "\n".join(actions_log_list) if actions_log_list else "No tool calls were made."
            # Ensure final_assistant_message is not None before accessing content
            gathered_data = final_assistant_message.content if final_assistant_message and hasattr(final_assistant_message, 'content') and final_assistant_message.content else "No final content generated or available."


            reflection_context = {
                "user_query": message,
                "actions_log": actions_log,
                "gathered_data": gathered_data
            }

            # Format the reflection prompt
            reflection_template_str = config.prompt_manager.self_reflection_prompt
            template = jinja_env.from_string(reflection_template_str)
            formatted_reflection_prompt = template.render(reflection_context)

            reflection_messages = [
                # Minimal system prompt for reflection
                {"role": "system", "content": "You are performing self-reflection on a previous interaction."},
                {"role": "user", "content": formatted_reflection_prompt}
            ]

            # Call LLM for reflection (no tools needed)
            reflection_response = await self.assistant.get_completion_with_retry(
                messages=reflection_messages,
                tools=None # Explicitly disable tools for reflection
            )

            reflection_text = "Reflection failed or produced no content." # Default value
            if reflection_response and reflection_response.choices and hasattr(reflection_response.choices[0], 'message') and reflection_response.choices[0].message.content:
                 reflection_text = reflection_response.choices[0].message.content

            self.assistant.logger.log_debug("Reflection Result", {"reflection": reflection_text})
            # Display reflection only in debug mode
            if config.settings.DEBUG_MODE:
                 self.assistant.console.print("[dim cyan]Internal Reflection:[/]")
                 self.assistant.console.print(f"[dim]{reflection_text}[/]")
                 self.assistant.console.print("[cyan]───────────────────────────────────────[/]")

        except Exception as e:
            # Log exception but don't fail the whole process, just skip reflection
            # Use logger.exception and correct extra key name
            self.assistant.logger.logger.exception(f"Error during reflection phase: {e}", extra={"context_message": message})
            self.assistant.console.print("[yellow]Warning: Reflection step failed.[/]")

        # --- 4. Final Response Generation (Integrating Reflection) ---
        if not final_assistant_message:
            self.assistant.logger.log_error("Execution phase did not produce a final assistant message", {"message": message})
            error_message = "Sorry, I encountered an issue processing your request after planning. Please try again."
            await self.assistant.add_msg_assistant(error_message)
            self.assistant.display.print_ai(error_message)
            return {"error": "missing_final_message_after_execution"}

        # Attempt to refine the final response using reflection
        refined_final_message = final_assistant_message # Default to original if refinement fails
        try:
            self.assistant.console.print("[bold blue]Final Refinement Phase:[/]")
            initial_response_content = final_assistant_message.content if hasattr(final_assistant_message, 'content') and final_assistant_message.content else "[No initial content]"

            refinement_template_str = config.prompt_manager.final_response_refinement_prompt # Assuming this prompt exists in config
            template = jinja_env.from_string(refinement_template_str)
            formatted_refinement_prompt = template.render({
                "initial_response": initial_response_content,
                "reflection": reflection_text # Use the reflection text generated earlier
            })

            # Use history *up to the point before the initial final_assistant_message was added*
            # This avoids including the unrefined message in the refinement context itself.
            history_before_final = []
            for msg in self.assistant.messages:
                 # Check if msg is the same object as final_assistant_message - might be tricky
                 # Safer approach: check if it's an assistant message without tool calls added *after* the last tool response
                 # Or, more simply, just use messages up to the last 'tool' role message, or the user message if no tools.
                 last_tool_idx = -1
                 for i, m in reversed(list(enumerate(self.assistant.messages))):
                     if m.get("role") == "tool":
                         last_tool_idx = i
                         break
                 
                 if last_tool_idx != -1:
                      history_before_final = self.assistant.messages[:last_tool_idx+1]
                 else: # No tool calls, use history up to the user message
                      history_before_final = self.assistant.messages[:start_message_index+1]


            refinement_messages = history_before_final + [
                {"role": "user", "content": formatted_refinement_prompt}
            ]

            # Call LLM for refinement (no tools)
            refinement_response = await self.assistant.get_completion_with_retry(
                messages=refinement_messages,
                tools=None
            )

            if refinement_response and refinement_response.choices and hasattr(refinement_response.choices[0], 'message') and refinement_response.choices[0].message.content:
                refined_content = refinement_response.choices[0].message.content.strip()
                if refined_content:
                    # Create a new message object for the refined response
                    refined_final_message = {"role": "assistant", "content": refined_content}
                    self.assistant.logger.log_info("Successfully refined final response using reflection.", {"original_length": len(initial_response_content), "refined_length": len(refined_content)})
                    # Replace the last message in history if it was the unrefined one
                    if self.assistant.messages and self.assistant.messages[-1] is final_assistant_message:
                         self.assistant.messages[-1] = refined_final_message
                    else: # Otherwise, append (might happen if original had tool calls)
                         await self.assistant.add_msg_assistant(refined_final_message) # Use helper to add
                else:
                    self.assistant.logger.log_warning("Refinement LLM call returned empty content.", {"response": str(refinement_response)})
            else:
                 self.assistant.logger.log_warning("Refinement LLM call failed or returned unexpected structure.", {"response": str(refinement_response)})

        except Exception as refine_err:
            # Log exception but don't fail the whole process, just use the original response
            self.assistant.logger.logger.exception(f"Error during final response refinement phase: {refine_err}", extra={"context_message": message})
            self.assistant.console.print("[yellow]Warning: Final response refinement step failed. Using original response.[/]")
            # Ensure the original final_assistant_message is still in history correctly
            if not self.assistant.messages or self.assistant.messages[-1] is not final_assistant_message:
                 # If history got messed up, try re-adding the original final message
                 await self.assistant.add_msg_assistant(final_assistant_message)


        # Display the final response (potentially refined)
        self.assistant.console.print("[bold green]Final Response:[/]")
        final_content_to_display = "[Assistant response has no displayable content]"
        if isinstance(refined_final_message, dict) and refined_final_message.get("content"):
            final_content_to_display = refined_final_message["content"]
        elif hasattr(refined_final_message, 'content') and refined_final_message.content: # Handle case where it's still the original object
             final_content_to_display = refined_final_message.content

        self.assistant.display.print_ai(final_content_to_display)

        # Ensure the message object being returned is the one in history
        # If refinement failed, refined_final_message is the original object
        # If refinement succeeded, refined_final_message is the new dict, which should now be in history
        # Return the message object that was ultimately decided upon (refined or original)
        return refined_final_message

    # --- Modified process_response to support agentic flow ---
    async def process_response(self, response: Any, print_response: bool = True, retry_attempt: int = 0, replan_attempt: int = 0) -> Optional[Any]: # Added replan_attempt
        """
        Process the model's response, handling the tool call loop recursively.
        Includes logic for retrying malformed calls and re-planning on tool execution errors.
        Adds assistant and tool messages to the main history (self.assistant.messages).
        Returns the final assistant message object (can be str or dict) once the loop completes.
        """
        try:
            # Pre-validate response format
            self._validate_response_input(response) # Raises error on failure

            # Check for message attribute after validation
            if not hasattr(response.choices[0], 'message'):
                 finish_reason = getattr(response.choices[0], 'finish_reason', 'unknown')
                 self.assistant.logger.log_error(f"Response choice missing 'message' attribute after validation. Finish reason: {finish_reason}", {"response": str(response)})
                 raise MessageProcessingError(f"Response choice missing 'message' attribute (finish_reason: {finish_reason})")


            response_message = response.choices[0].message
            tool_calls = getattr(response_message, 'tool_calls', None)
            finish_reason = getattr(response.choices[0], 'finish_reason', 'unknown') # Get finish reason

            # --- BEGIN NEW RETRY LOGIC for MALFORMED_FUNCTION_CALL ---
            MAX_RETRY_ATTEMPTS = 1 # Limit retries
            if finish_reason == "MALFORMED_FUNCTION_CALL" and retry_attempt < MAX_RETRY_ATTEMPTS:
                self.assistant.logger.log_warning(
                    f"Malformed function call detected. Attempting retry {retry_attempt + 1}/{MAX_RETRY_ATTEMPTS}.",
                    {"original_response": str(response)}
                )
                self.assistant.console.print("[yellow]Warning: Model generated a malformed tool call. Attempting self-correction...[/]")

                # Construct retry prompt - copy history and add error context
                # Copy history UP TO THE POINT BEFORE THE FAILED ASSISTANT MESSAGE
                # Note: add_msg_assistant hasn't been called yet for the failed response_message
                retry_messages = list(self.assistant.messages)
                retry_messages.append({
                    "role": "user",
                    "content": (
                        "My previous attempt to generate a function call based on our conversation failed because "
                        "the call was malformed (reason: MALFORMED_FUNCTION_CALL). "
                        "Please review the conversation history and the goal, then carefully generate the *correct* "
                        "next function call required. Pay close attention to formatting the arguments, especially complex ones like file content."
                    )
                })

                try:
                    # Attempt the LLM call again with the error context
                    retry_response = await self.assistant.get_completion_with_retry(
                        messages=retry_messages,
                        tools=self.assistant.tools
                    )
                    # Process the *retry* response, incrementing the attempt counter
                    # If this recursive call succeeds, it will add the successful assistant message to history
                    return await self.process_response(retry_response, print_response=print_response, retry_attempt=retry_attempt + 1)
                except Exception as retry_e:
                    self.assistant.logger.logger.exception(
                        f"Error during self-correction retry attempt {retry_attempt + 1}: {retry_e}",
                        extra={"context_messages": retry_messages}
                    )
                    # If retry fails, raise the error to be handled by the main loop
                    raise MessageProcessingError(
                        message=f"Self-correction retry attempt failed: {str(retry_e)}",
                        phase="agentic_execution_retry",
                        details={"error": str(retry_e), "trace": traceback.format_exc()}
                    ) from retry_e

            elif finish_reason == "MALFORMED_FUNCTION_CALL" and retry_attempt >= MAX_RETRY_ATTEMPTS:
                self.assistant.logger.log_error(
                    f"Malformed function call persisted after {retry_attempt} retries. Aborting.",
                    {"final_response": str(response)}
                )
                raise MessageProcessingError(
                     message=f"Failed to generate a valid tool call after {retry_attempt} retries due to malformed calls.",
                     phase="agentic_execution_failure",
                     details={"finish_reason": finish_reason}
                )
            # --- END NEW RETRY LOGIC ---

            # Add the current assistant message (which might contain tool calls) to history
            # Use the assistant's method which handles formatting and duplicates
            # This now only happens if the initial call was okay OR if the retry succeeds (handled in recursive call)
            await self.assistant.add_msg_assistant(response_message)

            # Process tool calls if present (and no MALFORMED_FUNCTION_CALL error occurred or retry was successful)
            if tool_calls:
                # Display intermediate thinking/plan if content exists
                self._handle_reasoning_display(response_message, print_response) # Uses DEBUG_MODE check internally
                self.assistant.console.print(f"[bold cyan]Running {len(tool_calls)} tool operation(s):[/]")

                # Process each tool call with error handling for re-planning
                MAX_REPLAN_ATTEMPTS = 1 # Limit re-planning attempts per step
                replan_triggered = False
                for tool_call in tool_calls:
                    try:
                        # Execute tool (now raises ToolExecutionError on failure)
                        await self.assistant.tool_executor.execute_tool_call(tool_call)
                    except ToolExecutionError as e:
                        self.assistant.logger.logger.error(f"Tool execution failed: {e}", exc_info=True, extra={"tool_call_id": e.details.get('tool_call_id'), "tool_name": e.tool_name})
                        
                        # Add error result to history so LLM knows it failed
                        await self.assistant.add_toolcall_output(e.details.get('tool_call_id', 'unknown_id'), e.tool_name, f"Error: {str(e)}")

                        if replan_attempt >= MAX_REPLAN_ATTEMPTS:
                             self.assistant.logger.log_error(f"Tool execution failed after {replan_attempt} re-plan attempts. Aborting.", {"error": str(e)})
                             self.assistant.console.print(f"[bold red]Error: Tool '{e.tool_name}' failed after re-plan attempt. Cannot proceed.[/]")
                             # Raise a more specific error indicating re-plan failure
                             raise MessageProcessingError(
                                 message=f"Tool '{e.tool_name}' failed after {replan_attempt} re-plan attempts.",
                                 phase="agentic_execution_replan_failure",
                                 details={"error": str(e), "tool_name": e.tool_name, "tool_call_id": e.details.get('tool_call_id')}
                             ) from e

                        self.assistant.console.print(f"[yellow]Warning: Tool '{e.tool_name}' failed. Attempting re-plan ({replan_attempt + 1}/{MAX_REPLAN_ATTEMPTS})...[/]")
                        
                        # Construct re-plan prompt (using the current history + explicit instruction)
                        # The error output was already added via add_toolcall_output
                        replan_messages = list(self.assistant.messages)

                        # Add explicit user message for re-planning and critique
                        replan_instruction = (
                            f"The previous attempt to use the tool '{e.tool_name}' failed with the following error:\n"
                            f"```\n{str(e)}\n```\n"
                            f"Tool Call ID: {e.details.get('tool_call_id', 'unknown_id')}\n\n"
                            "Please perform the following steps:\n"
                            "1. **Analyze Failure:** Briefly explain why the tool call likely failed based on the error and the conversation history.\n"
                            "2. **Critique Plan:** Briefly critique the previous step or plan that led to this failure.\n"
                            "3. **Revise Plan:** Propose a revised next step or a new plan to achieve the original goal, taking the failure into account. Generate the necessary tool call(s) for the revised step, or provide a textual response if no further tools are needed."
                        )
                        replan_messages.append({"role": "user", "content": replan_instruction})

                        # Get re-plan response from the model
                        try:
                            next_response = await self.assistant.get_completion_with_retry(
                                messages=replan_messages, # Use history including the error
                                tools=self.assistant.tools
                            )
                            # Recursively process the *new* response, incrementing replan_attempt
                            replan_triggered = True # Mark that re-plan was initiated
                            return await self.process_response(
                                next_response,
                                print_response=print_response,
                                retry_attempt=retry_attempt, # Keep malformed call retry counter separate
                                replan_attempt=replan_attempt + 1
                            )
                        except Exception as replan_e:
                             self.assistant.logger.logger.exception(f"Error during re-plan LLM call: {replan_e}", extra={"context_messages": replan_messages})
                             raise MessageProcessingError(
                                 message=f"Re-plan attempt failed during LLM call: {str(replan_e)}",
                                 phase="agentic_execution_replan_llm_failure",
                                 details={"error": str(replan_e), "trace": traceback.format_exc()}
                             ) from replan_e
                
                # If the loop finished without errors or re-planning, proceed normally
                if not replan_triggered:
                    # Add a visual separator after all successful tool calls in this batch
                    self.assistant.console.print("[cyan]───────────────────────────────────────[/]")

                    # Get the next response from the model using the updated history
                    next_response = await self.assistant.get_completion_with_retry(
                        messages=self.assistant.messages, # Use the main history
                        tools=self.assistant.tools
                    )

                    # Recursively process the next response
                    # Reset replan_attempt for the next level of recursion
                    return await self.process_response(
                        next_response,
                        print_response=print_response,
                        retry_attempt=retry_attempt,
                        replan_attempt=0 # Reset replan counter for next step
                    )
            else:
                # No tool calls, check finish reason again for other potential issues
                # Accept 'stop' (lowercase) as a valid finish reason when no tool calls are made
                if finish_reason != "STOP" and finish_reason != "stop" and finish_reason != "unknown": # Check if finish reason is unexpected
                     self.assistant.logger.log_warning(f"No tool call generated, but finish reason was '{finish_reason}', not 'STOP' or 'stop'.", {"response": str(response)})
                     # Consider if specific handling needed for other finish_reasons like 'MAX_TOKENS', 'SAFETY' etc.
                # No more tool calls, this is the final assistant message for this interaction chain
                self.assistant.logger.log_debug("process_response loop complete, returning final message.")
                # Display is handled by the calling function (process_agentic_flow)
                return response_message # Return the final message object (could be dict or specific object type)

        except Exception as e:
             # Use logger.exception to include traceback and rename extra key
            self.assistant.logger.logger.exception(f"Error during process_response loop: {e}", extra={"context_response": str(response)})
            # Avoid printing generic error here, let the caller handle display
            # traceback.print_exc()
            if isinstance(e, (MessageProcessingError, APICallError, AsyncOperationError)):
                 raise # Re-raise known types
            # Wrap unexpected errors
            raise AsyncOperationError(
                message=f"Error processing response or tool calls: {str(e)}",
                operation="response_processing",
                details={"error": str(e), "trace": traceback.format_exc()}
            ) from e


    # --- Original method kept for reference/potential fallback, but not used by agentic flow ---
    async def process_with_reasoning(self, message: str, reasoning: str) -> Dict[str, Any]:
        """DEPRECATED: Process a user message with the reasoning already generated."""
        self.assistant.logger.log_warning("Deprecated process_with_reasoning called", {"message": message[:50]})
        # ... (original implementation remains here but ideally shouldn't be called) ...
        # For brevity, the original implementation is omitted in this rewrite example.
        # It would involve creating separate execution_messages, calling get_completion,
        # and then process_response.
        raise NotImplementedError("process_with_reasoning is deprecated, use process_agentic_flow")


    # --- Helper methods ---
    def _handle_reasoning_display(self, response_message: Any, print_response: bool) -> None:
        """Display model's reasoning before tool calls if present and printing enabled."""
        # Check if printing is globally enabled via print_response flag
        if not print_response:
            # NOTE: This check might be redundant if called from process_response where print_response=False
            # Consider removing if only called internally where display is deferred.
            # However, keeping it allows potential direct calls with print_response=True.
            pass # Continue to check DEBUG_MODE

        # Check if debug mode is enabled in config
        config = get_config()
        if not config.settings.DEBUG_MODE:
            return

        if hasattr(response_message, 'content') and response_message.content:
            # Only display if content is meaningful (not just whitespace)
            content_strip = response_message.content.strip()
            if content_strip:
                 self.assistant.console.print("[dim italic]Model thinking: " + content_strip + "[/]")
                 # self.assistant.console.print() # Avoid extra blank line here, let executor add spacing

    def _validate_message_input(self, message: str, reasoning: Optional[str] = None) -> None: # Made reasoning optional
        """Validate user message input."""
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
        # Reasoning validation removed as it's not directly used in agentic flow input

    def _validate_response_input(self, response: Any) -> None:
        """Validate model response input structure."""
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
            # Sometimes API might return empty choices, handle gracefully if possible
            self.assistant.logger.log_warning("Received response with empty choices list", {"response": str(response)})
            # Depending on context, might need to retry or return an error message
            # For now, raise error as it usually indicates a problem
            raise MessageProcessingError(
                message="Response choices cannot be empty",
                phase="response_validation"
            )

        # It's possible for choices[0] to not have 'message' in some error scenarios
        # Check moved inside process_response after validation

"""
Reasoning engine for planning approach without tool execution.
"""
import litellm
import asyncio
import inspect
from typing import Dict, Any, Optional, Union

# Use new config access
from config import get_config
# For prompt formatting
from config.services.context import format_prompt_with_context
from .exceptions.base import APICallError, MessageProcessingError

class ReasoningEngine:
    """Handles the reasoning phase of the assistant."""

    def __init__(self, assistant):
        """Initialize with parent assistant reference."""
        self.assistant = assistant

    async def get_reasoning(self, message: str) -> str:
        """
        Get the reasoning plan for the given message without executing tools.
        This is the first phase where the assistant thinks through the problem.

        Args:
            message: The user's message

        Returns:
            The reasoning plan as a string
        """
        # Create a temporary messages list for the reasoning phase
        reasoning_messages = []
        config = get_config() # Fetch config object

        # Format the reasoning system prompt asynchronously
        reasoning_prompt_template = config.prompt_manager.reasoning_prompt
        formatted_reasoning_prompt = await format_prompt_with_context(
            reasoning_prompt_template,
            self.assistant.name # Use assistant's name for context
        )
        reasoning_messages.append({"role": "system", "content": formatted_reasoning_prompt})

        # Add conversation history (limited to last few messages for context)
        history_limit = 40  # Limit to last 20 exchanges (40 messages)
        if len(self.assistant.messages) > 1:  # Skip system message
            for msg in self.assistant.messages[-history_limit:]:
                if msg["role"] != "system":
                    reasoning_messages.append(msg)

        # Add the user's message with explicit task framing
        reasoning_messages.append({"role": "user", "content": f"TASK: {message}\n\nProvide your step-by-step reasoning plan."})

        # Make the API call without tools for the reasoning phase
        try:
            # config = get_config() # Config already fetched above
            response = await self._make_litellm_call(
                messages=reasoning_messages,
                temperature=config.settings.TEMPERATURE, # Use config.settings
                top_p=config.settings.TOP_P,             # Use config.settings
                max_tokens=config.settings.MAX_TOKENS or 8192, # Use config.settings
                seed=config.settings.SEED,               # Use config.settings
                safety_settings=config.safety_settings   # Use config (safety settings are direct attribute)
            )

            # Validate and extract the reasoning from the response
            if not response or not hasattr(response, 'choices') or not response.choices:
                raise MessageProcessingError(
                    message="Invalid response format from language model",
                    phase="reasoning",
                    details={"response": str(response)}
                )

            reasoning = response.choices[0].message.content
            if not reasoning:
                raise MessageProcessingError(
                    message="Empty reasoning response from language model",
                    phase="reasoning"
                )

            return reasoning.strip()

        except Exception as e:
            if isinstance(e, MessageProcessingError):
                raise e
            self.assistant.console.print(f"[error]Error in reasoning phase: {e}[/]")
            raise MessageProcessingError(
                message=str(e),
                phase="reasoning",
                details={"error": str(e)}
            ) from e

    async def _make_litellm_call(
        self,
        messages: list,
        temperature: float,
        top_p: float,
        max_tokens: int,
        seed: Optional[int],
        safety_settings: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Make an async call to litellm with proper error handling."""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: litellm.completion(
                    model=self.assistant.model,
                    messages=messages,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    seed=seed,
                    safety_settings=safety_settings
                )
            )
            return response
        except Exception as e:
            raise APICallError(
                message=f"Language model API call failed: {str(e)}",
                model_name=self.assistant.model,
                retries=0,
                details={"error": str(e)}
            ) from e

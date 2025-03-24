"""
Core Assistant class that coordinates different components.
"""
import inspect
import json
import os
from typing import Callable, Dict, Any, List, Optional
import time
import traceback

from rich.console import Console
from rich.theme import Theme
import litellm

from func_to_schema import function_to_json_schema

from assistant.display import AssistantDisplay
from assistant.messaging import MessageProcessor
from assistant.reasoning import ReasoningEngine
from assistant.execution import ToolExecutor
from assistant.session import SessionManager
from assistant.conversion import TypeConverter

# Define a custom theme for the application
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "user": "bold magenta",
    "assistant": "bold green",
    "tool": "cyan",
    "header": "bold blue on default",
    "command": "bold yellow",
    "debug": "dim cyan",
    "reasoning": "dim italic yellow",
})

# Define search-related tools for concise output
SEARCH_TOOLS = [
    "web_search",
    "reddit_search"
]

class Assistant:
    """
    A terminal-based assistant that can converse and execute tools.
    """

    def __init__(
        self,
        model: str,
        name: str = "Assistant",
        tools: List[Callable] = [],
        system_instruction: str = "",
    ) -> None:
        """Initialize the assistant with model and tools."""
        self.model = model
        self.name = name
        self.system_instruction = system_instruction
        self.messages = []
        self.available_functions = {func.__name__: func for func in tools}
        self.tools = list(map(function_to_json_schema, tools))
        self.console = Console(theme=custom_theme)
        self.last_reasoning = None

        # Initialize components
        self.display = AssistantDisplay(self)
        self.message_processor = MessageProcessor(self)
        self.reasoning_engine = ReasoningEngine(self)
        self.tool_executor = ToolExecutor(self)
        self.session_manager = SessionManager(self)
        self.type_converter = TypeConverter()

        if system_instruction:
            self.messages.append({"role": "system", "content": system_instruction})

    def send_message(self, message: str) -> Dict[str, Any]:
        """
        Process user message using a two-phase approach:
        1. Reasoning phase: Plan the approach without executing tools
        2. Execution phase: Execute the plan and provide the answer
        """
        try:
            # Phase 1: Reasoning
            self.console.print("[bold blue]Reasoning Phase:[/]")
            reasoning = self.reasoning_engine.get_reasoning(message)
            self.last_reasoning = reasoning
            
            # Display the reasoning
            self.display.show_reasoning(reasoning)
            self.console.print("[cyan]───────────────────────────────────────[/]")
            
            # Phase 2: Execution
            self.console.print("[bold blue]Execution Phase:[/]")
            
            # Get execution result
            response = self.message_processor.process_with_reasoning(message, reasoning)
            return response
            
        except Exception as e:
            error_message = f"I encountered an error while processing your message: {e}. Can you try rephrasing your request?"
            self.console.print(f"[error]Message processing error: {e}[/]")
            self.add_msg_assistant(error_message)
            self.display.print_ai(error_message)
            return {"error": str(e)}

    def get_completion(self) -> Any:
        """Get a completion from the model with the current messages and tools."""
        return litellm.completion(
            model=self.model,
            messages=self.messages,
            tools=self.tools,
            temperature=self.message_processor.temperature,
            top_p=self.message_processor.top_p,
            max_tokens=self.message_processor.max_tokens,
            seed=self.message_processor.seed,
            safety_settings=self.message_processor.safety_settings
        )

    def get_completion_with_retry(self, messages: List[Dict[str, Any]] = None, max_retries: int = 3) -> Any:
        """Get a completion from the model with retry logic."""
        messages_to_use = messages if messages is not None else self.messages
        
        for attempt in range(max_retries):
            try:
                return litellm.completion(
                    model=self.model,
                    messages=messages_to_use,
                    tools=self.tools,
                    temperature=self.message_processor.temperature,
                    top_p=self.message_processor.top_p,
                    max_tokens=self.message_processor.max_tokens,
                    seed=self.message_processor.seed,
                    safety_settings=self.message_processor.safety_settings
                )
            except Exception as e:
                if "resource exhausted" in str(e).lower() and attempt < max_retries - 1:
                    delay = 4 * (2 ** attempt)
                    self.console.print(f"[warning]Resource exhausted: {e}. Retrying in {delay} seconds...[/]")
                    time.sleep(delay)
                else:
                    raise
        
        raise Exception("Failed to get completion after maximum retries")

    # Message history functions
    def add_msg_assistant(self, msg: str) -> None:
        """Add an assistant message to the conversation history."""
        self.messages.append({"role": "assistant", "content": msg})

    def add_toolcall_output(self, tool_id: str, name: str, content: Any) -> None:
        """Add a tool call result to the conversation history."""
        self.messages.append({
            "tool_call_id": tool_id,
            "role": "tool",
            "name": name,
            "content": str(content),
        })

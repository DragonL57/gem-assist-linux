import inspect
import json
import os
import platform
import traceback
import time
from typing import Callable, Union, Dict, Any, List, Optional, Tuple
import colorama
from pydantic import BaseModel
import litellm

# Add prompt_toolkit for better terminal input handling
from prompt_toolkit import PromptSession, HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style as PromptStyle

# Updated import path for utils
from utils import TOOLS
import pickle

from colorama import Fore, Style, Back
from rich.console import Console
from rich.markdown import Markdown
from rich.theme import Theme
from rich.text import Text
import config as conf

from func_to_schema import function_to_json_schema
from gem.command import InvalidCommand, CommandNotFound, CommandExecuter, cmd
import gem

from dotenv import load_dotenv

load_dotenv()

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
    "debug": "dim cyan",  # Add specific debug theme
    "reasoning": "dim italic yellow",  # Updated style for reasoning phase output
})

# Create a console with the custom theme
console = Console(theme=custom_theme)

# Define search-related tools for concise output
SEARCH_TOOLS = [
    "duckduckgo_search_tool", "advanced_duckduckgo_search", 
    "google_search", "meta_search", "reddit_search", 
    "search_wikipedia", "get_wikipedia_summary", "get_full_wikipedia_page"
]

# No longer need to define prompts here, they're imported from config

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

        if system_instruction:
            self.messages.append({"role": "system", "content": system_instruction})

    # ==================== Core Messaging Functions ====================

    def send_message(self, message: str) -> Dict[str, Any]:
        """
        Process user message using a two-phase approach:
        1. Reasoning phase: Plan the approach without executing tools
        2. Execution phase: Execute the plan and provide the answer
        """
        try:
            # Phase 1: Reasoning
            self.console.print("[bold blue]Reasoning Phase:[/]")
            reasoning = self.get_reasoning(message)
            self.last_reasoning = reasoning
            
            # Display the reasoning with proper markdown rendering
            # Get console width to enable proper text wrapping
            console_width = os.get_terminal_size().columns if hasattr(os, 'get_terminal_size') else 80
            effective_width = console_width - 4  # Allow for some margin
            
            # Render the reasoning as markdown with styling
            self.console.print(
                Markdown(reasoning, justify="left"),
                style="dim italic",
                width=effective_width,
                overflow="fold",
                no_wrap=False
            )
            self.console.print("[cyan]───────────────────────────────────────[/]")
            
            # Phase 2: Execution
            self.console.print("[bold blue]Execution Phase:[/]")
            
            # Create a new message list for execution phase
            execution_messages = []
            
            # Add the base execution system prompt
            execution_messages.append({
                "role": "system", 
                "content": f"{conf.EXECUTION_SYSTEM_PROMPT}\n\nYour reasoning plan: {reasoning}"
            })
            
            # Add the conversation history (except the system message)
            for msg in self.messages:
                if msg["role"] != "system":
                    execution_messages.append(msg)
                    
            # Add the user's message
            execution_messages.append({"role": "user", "content": message})
            
            # Store the user message in the main message history
            self.messages.append({"role": "user", "content": message})
            
            # Get the execution response with completely separate message context
            response = self.get_completion_with_retry(execution_messages)
            return self.__process_response(response)
            
        except Exception as e:
            error_message = f"I encountered an error while processing your message: {e}. Can you try rephrasing your request?"
            self.console.print(f"[error]Message processing error: {e}[/]")
            self.add_msg_assistant(error_message)
            self.print_ai(error_message)
            return {"error": str(e)}

    def get_reasoning(self, message: str) -> str:
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
        
        # Use ONLY the reasoning system prompt without the base system prompt
        reasoning_messages.append({"role": "system", "content": conf.REASONING_SYSTEM_PROMPT})
        
        # Add conversation history (limited to last few messages for context)
        history_limit = 4  # Limit to last 2 exchanges (4 messages)
        if len(self.messages) > 1:  # Skip system message
            for msg in self.messages[-history_limit:]:
                if msg["role"] != "system":
                    reasoning_messages.append(msg)
        
        # Add the user's new message
        reasoning_messages.append({"role": "user", "content": f"TASK: {message}\n\nProvide your step-by-step reasoning plan."})
        
        # Make the API call without tools for the reasoning phase
        try:
            response = litellm.completion(
                model=self.model,
                messages=reasoning_messages,
                temperature=conf.TEMPERATURE,
                top_p=conf.TOP_P,
                max_tokens=conf.MAX_TOKENS or 4096,  # Limit reasoning length
                seed=conf.SEED,
                safety_settings=conf.SAFETY_SETTINGS
            )
            
            reasoning = response.choices[0].message.content.strip()
            return reasoning
            
        except Exception as e:
            self.console.print(f"[error]Error in reasoning phase: {e}[/]")
            return f"I encountered an error while planning my approach: {e}. I'll try to answer directly."

    def get_completion_with_retry(self, messages: List[Dict[str, Any]] = None, max_retries: int = 3) -> Any:
        """Get a completion from the model with retry logic."""
        msgs = messages if messages is not None else self.messages
        
        for attempt in range(max_retries):
            try:
                return litellm.completion(
                    model=self.model,
                    messages=msgs,
                    tools=self.tools,
                    temperature=conf.TEMPERATURE,
                    top_p=conf.TOP_P,
                    max_tokens=conf.MAX_TOKENS or 8192,
                    seed=conf.SEED,
                    safety_settings=conf.SAFETY_SETTINGS
                )
            except litellm.RateLimitError as e:
                if attempt == max_retries - 1:
                    raise
                delay = 4 * (2 ** attempt)  # 4, 8, 16 seconds
                self.console.print(f"[warning]Rate limit error: {e}. Retrying in {delay} seconds...[/]")
                time.sleep(delay)
            except Exception as e:
                if "resource exhausted" in str(e).lower() and attempt < max_retries - 1:
                    delay = 4 * (2 ** attempt)
                    self.console.print(f"[warning]Resource exhausted: {e}. Retrying in {delay} seconds...[/]")
                    time.sleep(delay)
                else:
                    raise
        
        raise Exception("Failed to get completion after maximum retries")

    def get_completion(self) -> Any:
        """Get a completion from the model with the current messages and tools."""
        return litellm.completion(
            model=self.model,
            messages=self.messages,
            tools=self.tools,
            temperature=conf.TEMPERATURE,
            top_p=conf.TOP_P,
            max_tokens=conf.MAX_TOKENS or 8192,
            seed=conf.SEED,
            safety_settings=conf.SAFETY_SETTINGS
        )

    # ==================== Response Processing Functions ====================

    def __process_response(self, response: Any, print_response: bool = True) -> Dict[str, Any]:
        """Process the model's response, including any tool calls."""
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # Display model reasoning in debug mode
        self._extract_and_display_reasoning(response)

        self.messages.append(response_message)
        final_response = response_message

        # Process tool calls if present
        try:
            if tool_calls:
                self._handle_reasoning_display(response_message, print_response)
                self.console.print(f"[bold cyan]Running {len(tool_calls)} tool operation(s):[/]")
                
                # Process each tool call
                for tool_call in tool_calls:
                    self._execute_tool_call(tool_call)

                # Add a visual separator after all tool calls
                self.console.print("[cyan]───────────────────────────────────────[/]")
                
                # Get the final response after tool execution
                final_response = self.get_completion()
                tool_calls = final_response.choices[0].message.tool_calls
                
                if not tool_calls:
                    response_message = final_response.choices[0].message
                    self.messages.append(response_message)
                    if print_response:
                        # Add a visual indicator that this is the final response
                        self.console.print("[bold green]Final Response:[/]")
                        self.print_ai(response_message.content)
                    return response_message
                
                # Handle any additional tool calls recursively
                return self.__process_response(final_response, print_response=print_response)
            else:
                # No tool calls - display the response directly
                if print_response:
                    self.print_ai(response_message.content)
                return response_message
        except Exception as e:
            self.console.print(f"[error]Error in processing response: {e}[/]")
            traceback.print_exc()
            return {"error": str(e)}

    def _extract_and_display_reasoning(self, response: Any) -> None:
        """Extract and display model reasoning if in debug mode."""
        if not conf.DEBUG_MODE:
            return
            
        reasoning = None
        
        # Try different locations for reasoning information
        if hasattr(response, 'model_reasoning'):
            reasoning = response.model_reasoning
        elif hasattr(response, '_hidden_params') and hasattr(response._hidden_params, 'model_reasoning'):
            reasoning = response._hidden_params.model_reasoning
        elif hasattr(response, 'completion_create_params') and 'model_reasoning' in response.completion_create_params:
            reasoning = response.completion_create_params['model_reasoning']
        
        # Try litellm debug logs
        if reasoning is None and hasattr(litellm, '_debug_log'):
            for log in litellm._debug_log:
                if isinstance(log, dict) and 'model_reasoning' in log:
                    reasoning = log['model_reasoning']
                    break
        
        # Display the reasoning if found
        if reasoning:
            self.console.print(f"[dim cyan]Model reasoning:[/] [dim]{reasoning}[/]")
            self.console.print()  # Add a blank line for readability

    def _handle_reasoning_display(self, response_message: Any, print_response: bool) -> None:
        """Display model's reasoning before tool calls if present."""
        if response_message.content and print_response:
            self.console.print("[dim italic]Model thinking: " + response_message.content.strip() + "[/]")
            self.console.print()  # Add space for readability

    def _execute_tool_call(self, tool_call: Any) -> None:
        """Execute a single tool call and handle the result."""
        function_name = tool_call.function.name

        # Check if function exists
        function_to_call = self.available_functions.get(function_name, None)
        if function_to_call is None:
            err_msg = f"Function not found with name: {function_name}"
            self.console.print(f"[error]Error: {err_msg}[/]")
            self.add_toolcall_output(tool_call.id, function_name, err_msg)
            return

        # Process function arguments
        try:
            function_args = json.loads(tool_call.function.arguments)
            self._display_tool_call(function_name, function_args)
            
            # Convert arguments to appropriate types based on annotations
            sig = inspect.signature(function_to_call)
            for param_name, param in sig.parameters.items():
                if param_name in function_args:
                    function_args[param_name] = self.convert_to_pydantic_model(
                        param.annotation, function_args[param_name]
                    )

            # Execute the function
            start_time = time.time()
            function_response = function_to_call(**function_args)
            execution_time = time.time() - start_time
            
            # Display the result based on function type
            self._display_tool_result(function_name, function_response, execution_time)
            
            # Add tool call output to messages
            self.add_toolcall_output(
                tool_call.id, function_name, function_response
            )
        except Exception as e:
            self.console.print(f"[error]Error executing {function_name}: {e}[/]")
            self.console.print()  # Add space for readability
            self.add_toolcall_output(tool_call.id, function_name, str(e))

    def _display_tool_call(self, function_name: str, function_args: Dict[str, Any]) -> None:
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
        self.console.print(f"[cyan]→ {function_name}({args_str})[/]")

    def _display_tool_result(self, function_name: str, result: Any, execution_time: float) -> None:
        """Display the result of a tool execution based on the tool type."""
        if function_name in SEARCH_TOOLS:
            # For search tools, just show count of results
            result_count = self._count_search_results(result)
            self.console.print(f"[success]✓ Completed in {execution_time:.4f}s: received {result_count} results[/]")
        else:
            # For non-search tools, show brief result
            brief_response = self._get_brief_response(result)
            self.console.print(f"[success]✓ Completed in {execution_time:.4f}s: {brief_response}[/]")
        
        self.console.print()  # Add space for readability

    def _count_search_results(self, result: Any) -> int:
        """Count the number of results in a search response."""
        result_count = 0
        if isinstance(result, list):
            result_count = len(result)
        elif isinstance(result, dict) and 'pages' in result:
            result_count = len(result.get('pages', []))
        elif isinstance(result, dict):
            # For nested results like meta_search
            for source, results in result.items():
                if isinstance(results, list):
                    result_count += len(results)
        return result_count

    def _get_brief_response(self, result: Any) -> str:
        """Get a brief representation of a result for display."""
        if isinstance(result, str) and len(result) > 100:
            return result[:97] + "..."
        return str(result)

    # ==================== Message History Functions ====================

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

    @cmd(["save"], "Saves the current chat session to pickle file.")
    def save_session(self, name: str, filepath: str = "chats") -> None:
        """
        Save the current chat session to a file.
        
        Args:
            name: The name of the file to save the session to (without extension)
            filepath: The path to the directory to save the file to (default: "chats")
        """
        try:
            # create directory if default path doesn't exist
            if filepath == "chats":
                os.makedirs(filepath, exist_ok=True)

            final_path = os.path.join(filepath, name + ".pkl")
            with open(final_path, "wb") as f:
                pickle.dump(self.messages, f)

            print(
                f"{Fore.GREEN}Chat session saved to {Fore.BLUE}{final_path}{Style.RESET_ALL}"
            )
        except Exception as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")

    @cmd(["load"], "Loads a chat session from a pickle file. Resets the session.")
    def load_session(self, name: str, filepath: str = "chats") -> None:
        """
        Load a chat session from a file.
        
        Args:
            name: The name of the file to load the session from (without extension)
            filepath: The path to the directory to load the file from (default: "chats")
        """
        try:
            final_path = os.path.join(filepath, name + ".pkl")
            with open(final_path, "rb") as f:
                self.messages = pickle.load(f)
            print(
                f"{Fore.GREEN}Chat session loaded from {Fore.BLUE}{final_path}{Style.RESET_ALL}"
            )
        except FileNotFoundError:
            print(
                f"{Fore.RED}Chat session not found{Style.RESET_ALL} {Fore.BLUE}{final_path}{Style.RESET_ALL}"
            )
        except Exception as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")

    @cmd(["reset"], "Resets the chat session.")
    def reset_session(self) -> None:
        """Reset the current chat session."""
        self.messages = []
        if self.system_instruction:
            self.messages.append({"role": "system", "content": self.system_instruction})

    @cmd(["reasoning"], "Displays the last reasoning plan from the assistant.")
    def show_last_reasoning(self) -> None:
        """Display the last reasoning plan that the assistant generated."""
        if self.last_reasoning:
            # Get console width for proper text wrapping
            console_width = os.get_terminal_size().columns if hasattr(os, 'get_terminal_size') else 80
            effective_width = console_width - 4  # Allow for some margin
            
            self.console.print("\n[bold blue]Last Reasoning Plan:[/]")
            self.console.print(
                Markdown(self.last_reasoning, justify="left"),
                style="dim italic",
                width=effective_width,
                overflow="fold",
                no_wrap=False
            )
            self.console.print()
        else:
            self.console.print("[warning]No reasoning plan available yet.[/]")

    # ==================== Output/Display Functions ====================

    def print_ai(self, msg: str) -> None:
        """Display the assistant's response with proper formatting and wrapping."""
        # Get console width to enable proper text wrapping
        console_width = os.get_terminal_size().columns if hasattr(os, 'get_terminal_size') else 80
        
        # Leave space for the prefix and some margin
        effective_width = console_width - 15  # Account for prefix and safety margin
        
        # Simple display without panels
        self.console.print(f"[assistant]{self.name}:[/] ", end="")
        
        # Process and standardize the message formatting if it's not empty
        if msg:
            # Ensure code blocks have proper syntax highlighting
            formatted_msg = msg.strip()
            
            # Use width parameter to control text wrapping
            self.console.print(Markdown(formatted_msg, code_theme="monokai", justify="left"), 
                               width=effective_width, 
                               overflow="fold", 
                               no_wrap=False)
        else:
            self.console.print("I don't have a response for that.")
            
        print()  # Add a blank line after assistant response

    def _display_debug_info(self, message: str) -> None:
        """Display debug information in a dimmed format."""
        if conf.DEBUG_MODE:
            console.print(Text(message, style="debug"))

    # ==================== Type Conversion Functions ====================

    def convert_to_pydantic_model(self, annotation: Any, arg_value: Any) -> Any:
        """
        Convert a value to its appropriate type based on type annotation.
        
        Args:
            annotation: The type annotation to convert to
            arg_value: The value to convert
            
        Returns:
            The converted value
        """
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            try:
                return annotation(**arg_value)
            except (TypeError, ValueError):
                return arg_value  # not a valid Pydantic model or data mismatch
        elif hasattr(annotation, "__origin__"):
            origin = annotation.__origin__
            args = annotation.__args__

            if origin is list:
                return [
                    self.convert_to_pydantic_model(args[0], item) for item in arg_value
                ]
            elif origin is dict:
                return {
                    key: self.convert_to_pydantic_model(args[1], value)
                    for key, value in arg_value.items()
                }
            elif origin is Union:
                for arg_type in args:
                    try:
                        return self.convert_to_pydantic_model(arg_type, arg_value)
                    except (ValueError, TypeError):
                        continue
                raise ValueError(f"Could not convert {arg_value} to any type in {args}")
            elif origin is tuple:
                return tuple(
                    self.convert_to_pydantic_model(args[i], arg_value[i])
                    for i in range(len(args))
                )
            elif origin is set:
                return {
                    self.convert_to_pydantic_model(args[0], item) for item in arg_value
                }
        return arg_value


def main():
    """Main entry point for the assistant when imported as a module."""
    colorama.init(autoreset=True)
    console = Console(theme=custom_theme)
    
    # Only enable litellm debug mode if DEBUG_MODE is enabled
    if conf.DEBUG_MODE:
        litellm._turn_on_debug()
        console.print("[dim cyan]Debug mode is enabled. Model reasoning will be displayed.[/]")
        console.print()
    
    # Setup prompt_toolkit with history and styling
    history_file = os.path.join(os.path.expanduser("~"), ".gem_assist_history")
    session = PromptSession(
        history=FileHistory(history_file),
        auto_suggest=AutoSuggestFromHistory(),
        enable_history_search=True,
    )

    # Load notes if available
    notes = _load_notes()

    # Create the system instruction with notes
    sys_instruct = (
        conf.get_system_prompt()
        + ("Here are the things previously saved on your notes:\n" + notes if notes else "")
    ).strip()

    # Initialize the assistant
    assistant = Assistant(
        model=conf.MODEL, system_instruction=sys_instruct, tools=TOOLS
    )

    # Handle commands
    command = gem.CommandExecuter.register_commands(
        gem.builtin_commands.COMMANDS + [assistant.save_session, assistant.load_session, assistant.reset_session]
    )

    # Clear screen if configured
    if conf.CLEAR_BEFORE_START:
        gem.clear_screen()

    # Display header
    _display_header(console)

    # Main interaction loop
    _run_interaction_loop(session, assistant)


def _load_notes() -> str:
    """Load saved notes if they exist."""
    if os.path.exists("./ai-log.txt"):
        try:
            with open("./ai-log.txt", "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""
    return ""


def _display_header(console: Console) -> None:
    """Display the application header."""
    console.print()
    console.print(f"[header]{conf.NAME} CHAT INTERFACE[/]", justify="center", style="bold")
    console.print(f"Using model: [bold]{conf.MODEL}[/] • Type [command]/help[/] for commands.", justify="center")
    console.print()


def _run_interaction_loop(session: PromptSession, assistant: Assistant) -> None:
    """Run the main interaction loop."""
    while True:
        try:
            # Get user input with prompt_toolkit
            msg = session.prompt(
                HTML('<span style="color:magenta;font-weight:bold">You:</span> '),
                mouse_support=True
            )
            
            if not msg:
                continue

            # Handle commands
            if msg.startswith("/"):
                CommandExecuter.execute(msg)
                continue
            
            # Send the message to the assistant
            assistant.send_message(msg)

        except KeyboardInterrupt:
            console.print("\n\n[success]Chat session interrupted.[/]")
            break
        except InvalidCommand as e:
            console.print(f"[error]Error: {e}[/]")
        except CommandNotFound as e:
            console.print(f"[error]Error: {e}[/]")
        except Exception as e:
            console.print(f"[error]An error occurred: {e}[/]")
            traceback.print_exc()


if __name__ == "__main__":
    main()
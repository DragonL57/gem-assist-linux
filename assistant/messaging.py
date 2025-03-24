"""
Message processing and conversation flow management.
"""
import json
from typing import Dict, Any, List
import traceback
import config as conf

class MessageProcessor:
    """Handles message processing and conversation flow."""
    
    def __init__(self, assistant):
        """Initialize with parent assistant reference."""
        self.assistant = assistant
        
        # Model parameters
        self.temperature = conf.TEMPERATURE
        self.top_p = conf.TOP_P
        self.max_tokens = conf.MAX_TOKENS or 8192
        self.seed = conf.SEED
        self.safety_settings = conf.SAFETY_SETTINGS
        
    def process_with_reasoning(self, message: str, reasoning: str) -> Dict[str, Any]:
        """Process a user message with the reasoning already generated."""
        # Create a new message list for execution phase
        execution_messages = []
        
        # Add the base execution system prompt
        execution_messages.append({
            "role": "system", 
            "content": f"{conf.EXECUTION_SYSTEM_PROMPT}\n\nYour reasoning plan: {reasoning}"
        })
        
        # Add the conversation history (except the system message)
        for msg in self.assistant.messages:
            if msg["role"] != "system":
                execution_messages.append(msg)
                
        # Add the user's message
        execution_messages.append({"role": "user", "content": message})
        
        # Store the user message in the main message history
        self.assistant.messages.append({"role": "user", "content": message})
        
        # Get the execution response with completely separate message context
        response = self.assistant.get_completion_with_retry(execution_messages)
        return self.process_response(response)
    
    def process_response(self, response: Any, print_response: bool = True) -> Dict[str, Any]:
        """Process the model's response, including any tool calls."""
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # Add automatic prompt for memory tools when personal information is detected
        if not tool_calls and response_message.content:
            # Check for personal information in user's last message
            if len(self.assistant.messages) >= 2 and self.assistant.messages[-1]["role"] == "user":
                last_user_msg = self.assistant.messages[-1]["content"].lower()
                memory_triggers = ["my name is", "i am", "i like", "i love", "i hate", "i live in", "i work", "you can call me"]
                
                if any(trigger in last_user_msg for trigger in memory_triggers):
                    self.assistant.console.print("[bold yellow]⚠️ Personal information detected but no memory update performed![/]")
                    self.assistant.console.print("[yellow]Consider using memory tools (update_memory, analyze_user_input) to remember user details.[/]")

        # Display model reasoning in debug mode
        self.assistant.display.extract_and_display_reasoning(response)

        self.assistant.messages.append(response_message)
        final_response = response_message

        # Process tool calls if present
        try:
            if tool_calls:
                self._handle_reasoning_display(response_message, print_response)
                self.assistant.console.print(f"[bold cyan]Running {len(tool_calls)} tool operation(s):[/]")
                
                # Process each tool call
                for tool_call in tool_calls:
                    self.assistant.tool_executor.execute_tool_call(tool_call)

                # Add a visual separator after all tool calls
                self.assistant.console.print("[cyan]───────────────────────────────────────[/]")
                
                # Get the final response after tool execution
                final_response = self.assistant.get_completion()
                tool_calls = final_response.choices[0].message.tool_calls
                
                if not tool_calls:
                    response_message = final_response.choices[0].message
                    self.assistant.messages.append(response_message)
                    if print_response:
                        # Add a visual indicator that this is the final response
                        self.assistant.console.print("[bold green]Final Response:[/]")
                        self.assistant.display.print_ai(response_message.content)
                    return response_message
                
                # Handle any additional tool calls recursively
                return self.process_response(final_response, print_response=print_response)
            else:
                # No tool calls - display the response directly
                if print_response:
                    self.assistant.display.print_ai(response_message.content)
                return response_message
        except Exception as e:
            self.assistant.console.print(f"[error]Error in processing response: {e}[/]")
            traceback.print_exc()
            return {"error": str(e)}
            
    def _handle_reasoning_display(self, response_message: Any, print_response: bool) -> None:
        """Display model's reasoning before tool calls if present."""
        if response_message.content and print_response:
            self.assistant.console.print("[dim italic]Model thinking: " + response_message.content.strip() + "[/]")
            self.assistant.console.print()  # Add space for readability
            
            # Auto-detect personal information to prompt memory updates
            if any(trigger in response_message.content.lower() for trigger in ["name is", "you can call me", "my name", "introduce myself"]):
                self.assistant.console.print("[bold yellow]💡 Personal information detected - check memory tools![/]")

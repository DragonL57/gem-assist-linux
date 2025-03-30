"""
Main assistant implementation that coordinates the conversation flow.
"""
import config as conf
from typing import List, Dict, Any, Optional
from rich.console import Console
from .reasoning import ReasoningEngine
from .tool_executor import ToolExecutor
from .display import AssistantDisplay
from .session import SessionManager
from .exceptions.base import MessageProcessingError
from .reasoning_validator import ReasoningValidator

class Assistant:
    """
    Main assistant class that coordinates conversation and tools.
    """
    def __init__(
        self, 
        model: str, 
        name: str = "Assistant", 
        system_instruction: str = "",
        discover_plugins_on_start: bool = True
    ):
        """Initialize the assistant.
        
        Args:
            model: The language model to use
            name: The assistant's name
            system_instruction: The system instruction for the assistant
            discover_plugins_on_start: Whether to discover plugins on start
        """
        self.model = model
        self.name = name
        self.system_instruction = system_instruction
        self.messages = [{"role": "system", "content": system_instruction}]
        self.console = Console(theme=conf.THEME_LOCALS)
        
        # Initialize components
        self.session_manager = SessionManager(self)
        self.reasoning_engine = ReasoningEngine(self)
        self.tool_executor = ToolExecutor(self)
        self.display = AssistantDisplay(self)
        self.validator = ReasoningValidator()
        
        # Configuration settings
        self.show_reasoning = conf.REQUIRE_USER_VERIFICATION
        self.validate_reasoning = conf.ENABLE_REASONING_VALIDATION
        
        # Discover plugins if requested
        if discover_plugins_on_start:
            self._discover_plugins()
    
    def _discover_plugins(self):
        """Discover and register plugins."""
        try:
            from plugins import discover_plugins
            discover_plugins()
            # Update validator tools registry
            self.validator.update_tools_registry()
        except Exception as e:
            self.console.print(f"[warning]Warning: Failed to discover plugins: {e}[/]")
    
    async def send_message(self, message: str) -> str:
        """
        Send a message to the assistant and get a response.
        
        Args:
            message: The user message to send
            
        Returns:
            The assistant's response
        """
        # Add user message to history
        self.messages.append({"role": "user", "content": message})
        
        # Process the message and get response
        try:
            response = await self.process_message(message)
            
            # Add assistant response to history
            if response:
                self.messages.append({"role": "assistant", "content": response})
            
            return response
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            self.console.print(f"[error]{error_msg}[/]")
            return error_msg
    
    async def process_message(self, message: str, **kwargs) -> str:
        """
        Process a user message through the assistant pipeline.
        
        Args:
            message: The user's message
            **kwargs: Additional keyword arguments
            
        Returns:
            The assistant's response
        """
        # Check if reasoning phase should be skipped
        if conf.get_settings().DISABLE_REASONING:
            # Generate a simplified execution plan
            reasoning_plan = self.reasoning_engine.generate_direct_execution_plan(message)
            self.console.print("[dim italic]Reasoning phase disabled. Proceeding directly to execution.[/]")
            
            # Execute directly with the simplified plan
            response = await self.tool_executor.execute_with_plan(message, reasoning_plan)
            return response
            
        # Normal flow with reasoning phase
        reasoning_plan = await self.reasoning_engine.get_reasoning(message)
        
        # Validate reasoning plan if enabled
        if self.validate_reasoning:
            validation_results = self.validator.validate_plan(reasoning_plan)
            if not validation_results["is_valid"]:
                self.console.print("[warning]Warning: The reasoning plan may have issues:[/]")
                for warning in validation_results.get("warnings", []):
                    self.console.print(f"[yellow]- {warning}[/]")
                
                # If below quality threshold, ask for confirmation even if not normally required
                if validation_results.get("score", 1.0) < conf.REASONING_QUALITY_THRESHOLD:
                    self.console.print("[warning]The reasoning plan quality is below threshold.[/]")
                    if not self.show_reasoning:
                        self.show_reasoning = True
        
        # Show reasoning and get user confirmation if enabled
        if self.show_reasoning:
            approved = self.display.show_reasoning(reasoning_plan)
            if not approved:
                return "Execution cancelled."
        
        # Execute with the detailed reasoning plan
        response = await self.tool_executor.execute_with_plan(message, reasoning_plan)
        return response
    
    def reset(self):
        """Reset the assistant's conversation history."""
        self.messages = [{"role": "system", "content": self.system_instruction}]

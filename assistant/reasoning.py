"""
Reasoning engine for planning approach without tool execution.
"""
import litellm
import config as conf

class ReasoningEngine:
    """Handles the reasoning phase of the assistant."""
    
    def __init__(self, assistant):
        """Initialize with parent assistant reference."""
        self.assistant = assistant
        
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
        history_limit = 40  # Limit to last 20 exchanges (40 messages)
        if len(self.assistant.messages) > 1:  # Skip system message
            for msg in self.assistant.messages[-history_limit:]:
                if msg["role"] != "system":
                    reasoning_messages.append(msg)
        
        # Add the user's message with explicit task framing
        reasoning_messages.append({"role": "user", "content": f"TASK: {message}\n\nProvide your step-by-step reasoning plan."})
        
        # Make the API call without tools for the reasoning phase
        try:
            response = litellm.completion(
                model=self.assistant.model,
                messages=reasoning_messages,
                temperature=conf.TEMPERATURE,
                top_p=conf.TOP_P,
                max_tokens=conf.MAX_TOKENS or 8192,  # Limit reasoning length
                seed=conf.SEED,
                safety_settings=conf.SAFETY_SETTINGS
            )
            
            reasoning = response.choices[0].message.content.strip()
            return reasoning
            
        except Exception as e:
            self.assistant.console.print(f"[error]Error in reasoning phase: {e}[/]")
            return f"I encountered an error while planning my approach: {e}. I'll try to answer directly."

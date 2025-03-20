"""
Base agent class that all specialized agents will inherit from.
"""
from typing import Dict, Any, List, Optional, Callable
import json
import time
import litellm
from rich.console import Console
from func_to_schema import function_to_json_schema

class BaseAgent:
    def __init__(
        self,
        name: str,
        model: str,
        tools: List[Callable] = [],
        system_instruction: str = "",
        console: Optional[Console] = None,
    ):
        self.name = name
        self.model = model
        self.system_instruction = system_instruction
        self.messages = []
        self.available_functions = {func.__name__: func for func in tools}
        self.tools = list(map(function_to_json_schema, tools))
        self.console = console or Console()
        
        if system_instruction:
            self.messages.append({"role": "system", "content": system_instruction})
    
    def act(self, query: str) -> Dict[str, Any]:
        """
        Process a query and execute appropriate tools.
        Returns results and any reflections.
        """
        # Add a generic instruction to guide the agent
        enhanced_query = f"""TASK: {query}
        
        As you address this task:
        - Use the most appropriate tools for this specific request
        - Consider what information or actions are needed
        - Be thorough in your approach
        - Format your response clearly
        
        Begin working on this task now.
        """
        
        self.messages.append({"role": "user", "content": enhanced_query})
        response = self._get_completion()
        result = self._process_response(response)
        return result
    
    def _get_completion(self):
        """Get a completion from the model with the current messages and tools."""
        return litellm.completion(
            model=self.model,
            messages=self.messages,
            tools=self.tools,
            temperature=0.25,
            top_p=1.0,
            max_tokens=8192  # Increase to model's max output tokens
        )
    
    def _process_response(self, response):
        """Process the model's response, executing tools as needed."""
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        
        self.messages.append(response_message)
        
        # If there are no tool calls, just return the message content
        if not tool_calls:
            return {"content": response_message.content}
            
        # Process tool calls and collect results
        results = []
        tool_responses = []
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            function_to_call = self.available_functions.get(function_name)
            if not function_to_call:
                error = f"Function {function_name} not found"
                results.append({"tool": function_name, "status": "error", "result": error})
                tool_responses.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": error
                })
                continue
            
            try:
                start_time = time.time()
                function_response = function_to_call(**function_args)
                execution_time = time.time() - start_time
                
                result_text = str(function_response)
                # Don't truncate results to ensure complete information is available
                
                results.append({
                    "tool": function_name,
                    "status": "success",
                    "result": function_response,
                    "time": execution_time
                })
                
                # Add the tool response to the messages
                tool_responses.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": result_text
                })
                
            except Exception as e:
                error = str(e)
                results.append({
                    "tool": function_name,
                    "status": "error",
                    "result": error
                })
                
                # Add error response
                tool_responses.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": error
                })
        
        # Add all tool responses to the conversation
        self.messages.extend(tool_responses)
        
        # Get a new response that uses the tool outputs
        final_response = self._get_completion()
        final_message = final_response.choices[0].message
        self.messages.append(final_message)
        
        # Return the final response
        return {
            "content": final_message.content,
            "tool_results": results
        }

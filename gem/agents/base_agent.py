"""
Base agent class that all specialized agents will inherit from.
"""
from typing import Dict, Any, List, Optional, Callable, Union
import json
import time
import random  # Add this import for random jitter
import litellm
from rich.console import Console
from func_to_schema import function_to_json_schema
from ..context import global_context

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
        self.context = global_context  # Share the global context
        
        # Add context-aware and error handling capabilities
        base_tools = [
            self.complete_task, 
            self.request_assistance, 
            self.notify_orchestrator,
            self.find_tools
        ]
        all_tools = base_tools + tools
        
        self.available_functions = {func.__name__: func for func in all_tools}
        
        # Fix function schemas to ensure no empty object properties
        self.tools = []
        for tool in all_tools:
            schema = function_to_json_schema(tool)
            # Ensure object properties are not empty
            if "function" in schema and "parameters" in schema["function"]:
                self._fix_empty_object_properties(schema["function"]["parameters"])
            self.tools.append(schema)
        
        self.console = console or Console()
        
        # Update system instruction with context awareness
        context_instruction = """
        IMPORTANT CONTEXT GUIDELINES:
        - Maintain awareness of the current system context
        - Track your operations and their results
        - When tasks depend on previous results, reference them explicitly
        - Use the complete_task tool to return your final results
        - If you encounter errors, use request_assistance or notify_orchestrator
        - Use find_tools to discover available tools when needed
        """
        
        full_instruction = f"{system_instruction}\n\n{context_instruction}" if system_instruction else context_instruction
        
        if full_instruction:
            self.messages.append({"role": "system", "content": full_instruction})
    
    def act(self, query: str, task_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a query and execute appropriate tools.
        Returns results and any reflections.
        """
        # Track the current task in context
        task_info = {
            "agent": self.name,
            "query": query,
            "start_time": time.time(),
        }
        if task_context:
            task_info["context"] = task_context
            
        self.context.current_task = task_info
        
        # Add relevant context to the query to make the agent context-aware
        context_summary = self._get_relevant_context_summary(query)
        enhanced_query = f"""TASK: {query}

CONTEXT:
{context_summary}

As you address this task:
- Use the most appropriate tools for this specific request
- Consider what information or actions are needed
- Be thorough in your approach
- Format your response clearly
- When finished, use the complete_task tool to submit your results

Begin working on this task now.
"""
        
        # Add to conversation history
        self.context.add_message("user", query, self.name)
        self.messages.append({"role": "user", "content": enhanced_query})
        
        response = self._get_completion()
        result = self._process_response(response)
        
        # Mark task as completed
        task_info["end_time"] = time.time()
        task_info["result"] = result
        self.context.completed_tasks.append(task_info)
        self.context.current_task = None
        
        return result
    
    def _get_relevant_context_summary(self, query: str) -> str:
        """Generate a summary of relevant context for the current query."""
        context_parts = []
        
        # Add current directory information
        context_parts.append(f"Current directory: {self.context.current_directory}")
        
        # Add recent operations if any
        if self.context.operations_log:
            context_parts.append("Recent operations:")
            context_parts.append(self.context.get_recent_operation_summary())
            
        # Add recent files if any
        if self.context.recent_files:
            recent_files = self.context.recent_files[-3:]  # Last 3 files
            context_parts.append("Recently accessed files:")
            for file_info in recent_files:
                context_parts.append(f"- {file_info['path']} ({file_info['operation']})")
        
        return "\n".join(context_parts)
    
    def _get_completion(self):
        """Get a completion from the model with the current messages and tools."""
        max_retries = 5
        base_delay = 2  # Base delay in seconds
        
        for attempt in range(max_retries):
            try:
                # For Vertex AI, we need a direct approach without nested tool calls
                # Create a simplified view of the messages
                simplified_messages = []
                # Always include system message if present
                for msg in self.messages:
                    if msg["role"] == "system":
                        simplified_messages.append(msg)
                
                # Add the last user message (most recent query)
                for i in range(len(self.messages) - 1, -1, -1):
                    if self.messages[i]["role"] == "user":
                        simplified_messages.append(self.messages[i])
                        break
                
                # If we have very few messages, use the original conversation
                if len(simplified_messages) < 2:
                    simplified_messages = self.messages
                
                self.console.print(f"[dim]Attempting completion ({attempt+1}/{max_retries})...[/]")
                return litellm.completion(
                    model=self.model,
                    messages=simplified_messages,  # Use simplified messages
                    tools=self.tools,
                    temperature=0.25,
                    top_p=1.0,
                    max_tokens=8192
                )
            except litellm.RateLimitError as e:
                # Always retry rate limits with backoff
                retryable = True
                self.console.print(f"[yellow]Rate limit hit: {e}. Retrying with backoff...[/]")
            except Exception as e:
                # Check if this is a retryable error
                retryable = False
                error_message = str(e).lower()
                
                # List of errors that warrant a retry
                retryable_errors = [
                    "overloaded", 
                    "rate limit", 
                    "timeout", 
                    "too many requests",
                    "server error",
                    "unavailable",
                    "capacity",
                    "internal server error",
                    "resource exhausted",  # Vertex AI specific
                    "503",
                    "502",
                    "429"
                ]
                
                for term in retryable_errors:
                    if term in error_message:
                        retryable = True
                        break
                
                # If error is not retryable or this was our last attempt, raise the exception
                if not retryable or attempt == max_retries - 1:
                    self.console.print(f"[error]Failed to get model completion: {e}[/]")
                    raise
                
                self.console.print(f"[yellow]API error: {e}. Will retry...[/]")
            
            # Calculate delay with exponential backoff and jitter
            delay = min(30, base_delay * (2 ** attempt) + (random.random() * base_delay))
            self.console.print(f"[dim]Waiting {delay:.2f}s before retry {attempt + 1}/{max_retries}...[/]")
            time.sleep(delay)
        
        # This should not be reached due to the raise in the loop, but just in case
        raise Exception("Failed to get model completion after maximum retries")
    
    def _process_response(self, response):
        """Process the model's response, executing tools as needed."""
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        
        self.messages.append(response_message)
        self.context.add_message("assistant", response_message.content, self.name)
        
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
                
                # Sanitize function response for JSON safety
                safe_response = self.context.sanitize_for_json(function_response)
                result_text = json.dumps(safe_response) if not isinstance(safe_response, str) else safe_response
                
                # Track the successful operation
                self.context.track_operation(
                    self.name,
                    function_name,
                    function_args,
                    True
                )
                
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
                # Log the error in context
                self.context.log_error(
                    self.name,
                    function_name,
                    function_args,
                    error
                )
                
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
        
        # For Vertex AI: Either get a new completion without tools, or return current results
        try:
            # Create a new simple prompt for final response synthesis
            synthesis_prompt = f"""Based on the tools I've used and information gathered, here is my response:

Task: {self.context.current_task.get('query', 'Answer the query') if self.context.current_task else 'Process the request'}

Tool Results Summary:
"""
            for i, result in enumerate(results, 1):
                status = "✓" if result["status"] == "success" else "✗"
                tool_name = result["tool"]
                result_summary = str(result["result"])[:150] + "..." if len(str(result["result"])) > 150 else str(result["result"])
                synthesis_prompt += f"{i}. {status} {tool_name}: {result_summary}\n"
            
            synthesis_prompt += "\nPlease provide a comprehensive response based on these results."
            
            # Get completion using a fresh conversation (no tools, no history)
            fresh_messages = [{"role": "user", "content": synthesis_prompt}]
            try:
                final_response = litellm.completion(
                    model=self.model,
                    messages=fresh_messages,  # Use completely fresh conversation
                    temperature=0.25, 
                    max_tokens=4096,  # Reduced to avoid potential issues
                    timeout=30  # Add explicit timeout
                )
                
                final_message = final_response.choices[0].message
                
                # Use this final text response without further tool calls
                return {
                    "content": final_message.content,
                    "tool_results": results
                }
            except Exception as synth_error:
                self.console.print(f"[error]Error in response synthesis: {synth_error}. Using simplified response.[/]")
                # Create a basic summary from the results
                summary = "I gathered the following information:\n\n"
                for result in results:
                    if result["status"] == "success":
                        summary += f"- From {result['tool']}: {str(result['result'])[:250]}...\n\n"
                    else:
                        summary += f"- {result['tool']} encountered an error.\n\n"
                return {"content": summary}
                
        except Exception as e:
            self.console.print(f"[error]Error getting final response: {e}. Using partial results.[/]")
            # Fall back to the simplest possible response
            return {
                "content": f"I processed your request and gathered some information, but encountered issues synthesizing a final response. Here's what I found: {', '.join([r['tool'] for r in results if r['status'] == 'success'])}.",
                "tool_results": results
            }

    def _fix_empty_object_properties(self, schema: Dict[str, Any]) -> None:
        """
        Fix any empty object properties in the schema, including deeply nested ones.
        
        Args:
            schema: The JSON schema to fix
        """
        if not schema or not isinstance(schema, dict):
            return
        
        # If this is an object type with properties
        if "type" in schema and schema["type"] == "object":
            # Ensure properties exists
            if "properties" not in schema:
                schema["properties"] = {"_placeholder": {"type": "string", "description": "Placeholder property"}}
            
            # Ensure properties is not empty
            if not schema["properties"]:
                schema["properties"] = {"_placeholder": {"type": "string", "description": "Placeholder property"}}
            
            # Process all nested properties
            for prop_name, prop_schema in schema["properties"].items():
                if isinstance(prop_schema, dict):
                    self._fix_empty_object_properties(prop_schema)
        
        # If this is an array type with items
        elif "type" in schema and schema["type"] == "array" and "items" in schema:
            if isinstance(schema["items"], dict):
                self._fix_empty_object_properties(schema["items"])
            elif isinstance(schema["items"], list):
                # Handle array with multiple item types (tuple validation)
                for item_schema in schema["items"]:
                    if isinstance(item_schema, dict):
                        self._fix_empty_object_properties(item_schema)
        
        # Handle anyOf, oneOf, allOf schemas
        for prop in ["anyOf", "oneOf", "allOf"]:
            if prop in schema and isinstance(schema[prop], list):
                for sub_schema in schema[prop]:
                    if isinstance(sub_schema, dict):
                        self._fix_empty_object_properties(sub_schema)
        
        # Look for any nested object properties that might not be directly under "properties"
        for key, value in schema.items():
            if key not in ["properties", "items", "anyOf", "oneOf", "allOf"] and isinstance(value, dict):
                if "type" in value and value["type"] == "object":
                    self._fix_empty_object_properties(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and "type" in item and item["type"] == "object":
                        self._fix_empty_object_properties(item)
    
    # Base communication tools that all agents must implement
    def complete_task(self, result: Dict[str, Any], status: str = "success") -> Dict[str, Any]:
        """
        Complete the current task and return results to the orchestrator.
        
        Args:
            result: The result data to return
            status: The status of the task (success, partial, failed)
        
        Returns:
            A dictionary confirming task completion
        """
        sanitized_result = self.context.sanitize_for_json(result)
        self.context.track_operation(
            self.name,
            "complete_task",
            {"status": status, "result_type": type(result).__name__},
            status == "success"
        )
        return {
            "agent": self.name,
            "status": status,
            "result": sanitized_result,
            "timestamp": time.time()
        }
    
    def request_assistance(self, problem: str, target_agent: str, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Request assistance from another agent when facing an issue.
        
        Args:
            problem: Description of the problem
            target_agent: Name of the agent to request help from
            details: Additional details about the problem
        
        Returns:
            Response from the orchestrator
        """
        self.context.track_operation(
            self.name,
            "request_assistance",
            {"problem": problem, "target_agent": target_agent},
            True
        )
        
        # This would normally be handled by the orchestrator
        # For now, just acknowledge the request
        return {
            "status": "acknowledged",
            "message": f"Assistance request for {target_agent} has been registered",
            "request_id": str(time.time())
        }
    
    def notify_orchestrator(self, notification_type: str, message: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Notify the orchestrator of an important event or issue.
        
        Args:
            notification_type: Type of notification (error, warning, info)
            message: The notification message
            data: Additional data related to the notification
        
        Returns:
            Response from the orchestrator
        """
        safe_data = self.context.sanitize_for_json(data) if data else {}
        self.context.track_operation(
            self.name,
            "notify_orchestrator",
            {"type": notification_type, "message": message},
            True
        )
        return {
            "status": "received",
            "message": f"Notification received: {notification_type}"
        }
    
    def find_tools(self, query: str = "all") -> List[List[str]]:
        """
        Find available tools that match the query.
        
        Args:
            query: Search string to filter tools (use "all" for all tools)
        
        Returns:
            List of matching tools with their descriptions
        """
        query = query.lower()
        tool_list = []
        
        for func_name, func in self.available_functions.items():
            if query == "all" or query in func_name.lower():
                desc = ""
                if func.__doc__:
                    desc = func.__doc__.strip().split("\n")[0]
                tool_list.append([func_name, desc])
        
        if not tool_list:
            # If no matches found, include a note
            return [["No matching tools found", f"No tools matched the query: {query}"]]
        
        return tool_list
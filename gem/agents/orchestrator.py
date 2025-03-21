"""
Orchestrator agent that coordinates specialized agents.
"""
from typing import Dict, List, Any, Optional
from rich.console import Console
from .base_agent import BaseAgent
from .agent_registry import AgentRegistry
import json
import re
import litellm
import time
import traceback
from ..context import global_context

class OrchestratorAgent(BaseAgent):
    def __init__(
        self,
        model: str,
        agent_registry: AgentRegistry,
        system_instruction: str = "",
        console: Optional[Console] = None,
    ):
        # Initialize base agent with orchestration-specific tools
        orchestrator_tools = [
            self.send_message_to_user,
            self.call_agent,
            self.evaluate_result
        ]
        
        super().__init__(
            name="Orchestrator",
            model=model,
            tools=orchestrator_tools,
            system_instruction=system_instruction,
            console=console,
        )
        
        self.agent_registry = agent_registry
        
    def process_query(self, query: str) -> Dict[str, Any]:
        """Process a user query by delegating tasks to specialized agents."""
        self.console.print("[dim]Orchestrator processing query...[/]")
        
        # Add to conversation history
        self.context.add_message("user", query, "User")
        
        try:
            # Create a streamlined execution plan
            plan = self._create_simple_execution_plan(query)
            
            # Store the plan in context
            self.context.share_data("execution_plan", plan)
            
            # Execute subtasks with appropriate agents - LIMIT TO 2 AGENTS FOR STABILITY
            results = []
            
            # Limit the plan to max 2 agents to prevent Vertex API errors
            limited_plan = plan[:min(2, len(plan))]
            if len(plan) > 2:
                self.console.print("[warning]Plan truncated to 2 agents for API stability.[/]")
            
            for i, task in enumerate(limited_plan):
                agent_name = task["agent"]
                subtask = task["task"]
                
                try:
                    # Prepare context for the subtask - keep it minimal
                    task_context = {
                        "task_id": i,
                        "total_tasks": len(limited_plan),
                        "original_query": query
                    }
                    
                    self.console.print(f"[cyan]Delegating to {agent_name}: {subtask}[/]")
                    agent = self.agent_registry.get_agent(agent_name)
                    if not agent:
                        self.console.print(f"[error]Agent {agent_name} not found. Skipping task.[/]")
                        continue
                    
                    # Use a simplified direct call approach
                    try:
                        result = self._safe_agent_call(agent, subtask, task_context)
                        results.append({"agent": agent_name, "task": subtask, "result": result})
                    except Exception as e:
                        self.console.print(f"[error]API error with {agent_name} agent: {e}[/]")
                        results.append({
                            "agent": agent_name, 
                            "task": subtask,
                            "result": {"content": f"Error executing task: {str(e)}"}
                        })
                except Exception as subtask_error:
                    self.console.print(f"[error]Error in subtask {i}: {subtask_error}[/]")
                    results.append({
                        "agent": agent_name,
                        "task": subtask,
                        "result": {"content": f"Error processing subtask: {str(subtask_error)}"}
                    })
            
            # Synthesize final response using a direct approach
            try:
                final_response = self._ultra_simple_synthesize(query, results)
                return {"plan": plan, "agent_results": results, "response": final_response}
            except Exception as synth_error:
                self.console.print(f"[error]Error synthesizing response: {synth_error}[/]")
                return {"plan": plan, "agent_results": results, "response": self._emergency_fallback_response(query, results)}
            
        except Exception as e:
            self.console.print(f"[error]Orchestration error: {e}[/]")
            return {
                "plan": [],
                "agent_results": [],
                "response": f"I encountered an error while processing your query: {str(e)}. Let me try a simpler approach:\n\n{self._fallback_response(query)}"
            }

    def _safe_agent_call(self, agent, subtask: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Safely call an agent with built-in retry logic."""
        max_retries = 3
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                # Make the agent call
                return agent.act(subtask, context)
            except (litellm.RateLimitError, litellm.BadRequestError) as e:
                if attempt == max_retries - 1:
                    # Last attempt failed
                    raise
                
                # Use simplified context on retry attempts
                if "previous_results" in context:
                    del context["previous_results"]  # Simplify context
                
                error_msg = str(e).lower()
                delay = base_delay * (2 ** attempt)
                self.console.print(f"[yellow]API error with agent call: {e}. Retrying in {delay}s ({attempt+1}/{max_retries})...[/]")
                time.sleep(delay)
        
        # Fallback response if we somehow exit the loop without returning or raising
        return {"content": f"I attempted to process the task '{subtask}' but encountered persistent issues."}

    def _create_simple_execution_plan(self, query: str) -> List[Dict[str, str]]:
        """Create a simplified execution plan based on query classification."""
        # Analyze query for likely needs
        all_agents = self.agent_registry.list_agents()
        plan = []
        
        # Identify query intent through a simple local analysis
        query_lower = query.lower()
        
        # File system operations
        if any(term in query_lower for term in ["file", "directory", "folder", "path", "list", "read", "write", "create"]):
            if "FileSystem" in all_agents:
                plan.append({
                    "agent": "FileSystem",
                    "task": f"Analyze if there are file operations needed for: '{query}'. If yes, execute them."
                })
        
        # System operations
        if any(term in query_lower for term in ["system", "command", "run", "execute", "terminal", "info", "environment"]):
            if "System" in all_agents:
                plan.append({
                    "agent": "System",
                    "task": f"Determine if system operations are needed for: '{query}'. If yes, execute them safely."
                })
        
        # Research/information needs
        if any(term in query_lower for term in ["what", "how", "why", "when", "where", "who", "which", "search", "find", "lookup", "research"]):
            if "Research" in all_agents:
                plan.append({
                    "agent": "Research",
                    "task": f"Research information related to: '{query}'"
                })
        
        # If no specific intent detected, default to research
        if not plan and "Research" in all_agents:
            plan.append({
                "agent": "Research",
                "task": f"Process and research information about: '{query}'"
            })
            
        # If research not available but system is, use system
        if not plan and "System" in all_agents:
            plan.append({
                "agent": "System", 
                "task": f"Process the user request: '{query}'"
            })
            
        # Last resort - use the first available agent
        if not plan and all_agents:
            plan.append({
                "agent": all_agents[0],
                "task": f"Process the user request: '{query}'"
            })
        
        return plan

    def _ultra_simple_synthesize(self, query: str, results: List[Dict[str, Any]]) -> str:
        """Ultra-simplified synthesis approach to avoid API errors."""
        # Create a direct, simple prompt 
        synthesis_text = f"Original query: {query}\n\nResults:\n\n"
        
        for i, result in enumerate(results, 1):
            agent = result['agent']
            task = result['task']
            
            synthesis_text += f"RESULT {i} from {agent} (task: {task}):\n"
            if isinstance(result['result'], dict) and 'content' in result['result']:
                content = result['result']['content']
                synthesis_text += f"{content}\n\n"
            else:
                synthesis_text += f"{str(result['result'])}\n\n"
            
            synthesis_text += "---\n\n"
        
        synthesis_text += "Please synthesize these results into a comprehensive, well-formatted response that directly addresses the original query."
        
        # Make a direct, simple call
        try:
            synthesis_response = litellm.completion(
                model=self.model,
                messages=[{"role": "user", "content": synthesis_text}],
                temperature=0.25,
                max_tokens=4096
            )
            return synthesis_response.choices[0].message.content
        except Exception as e:
            # If synthesis fails, use emergency fallback
            self.console.print(f"[error]Error in ultra simple synthesis: {e}[/]")
            return self._emergency_fallback_response(query, results)

    def _emergency_fallback_response(self, query: str, results: List[Dict[str, Any]]) -> str:
        """Last-resort emergency fallback when everything else fails."""
        response = f"I tried to find information about your query: '{query}'\n\n"
        
        success_results = [r for r in results if isinstance(r.get('result'), dict) and 'content' in r.get('result')]
        
        if success_results:
            response += "Here's what I found:\n\n"
            for result in success_results:
                agent = result['agent']
                content = result['result']['content']
                # Keep it brief in the emergency response
                summary = content[:500] + "..." if len(content) > 500 else content
                response += f"From {agent}:\n{summary}\n\n"
        else:
            response += "Unfortunately, I wasn't able to gather any useful information. Please try rephrasing your question or asking something else."
        
        return response

    def analyze_complexity(self, query: str) -> Dict[str, Any]:
        """
        Analyze a query to determine if it's complex enough to warrant multi-agent processing.
        """
        # First, check if we have a threshold setting in config
        threshold_modifier = 0.0
        try:
            import config as conf
            if hasattr(conf, 'MULTI_AGENT_THRESHOLD'):
                if conf.MULTI_AGENT_THRESHOLD.lower() == "low":
                    threshold_modifier = -0.3  # More likely to use multi-agent
                elif conf.MULTI_AGENT_THRESHOLD.lower() == "high":
                    threshold_modifier = 0.3   # Less likely to use multi-agent
                # Medium is default, no modifier
        except ImportError:
            pass  # No config module, use defaults
            
        analysis_prompt = f"""
        Analyze this query complexity: "{query}"
        
        Determine:
        1. Is this query complex enough to require multiple specialized agents?
        2. Which agents would be best suited to handle this query?
        
        COMPLEXITY THRESHOLD: {"Low (use multi-agent mode more often)" if threshold_modifier < 0 else "High (use multi-agent mode sparingly)" if threshold_modifier > 0 else "Medium (balanced approach)"}
        
        Respond in JSON format:
        {{
            "is_complex": true/false,
            "reasoning": "Brief explanation of why this is or isn't complex",
            "suggested_agents": ["Agent1", "Agent2"]
        }}
        
        Available agents: {', '.join(self.agent_registry.list_agents())}
        """
        
        # Important change: Use a direct completion without tools for analysis
        try:
            messages = [{"role": "user", "content": analysis_prompt}]
            response = litellm.completion(
                model=self.model,
                messages=messages,  # Use fresh messages without tools
                temperature=0.2,
                top_p=1.0,
                max_tokens=1024
            )
            
            # Extract the JSON response
            content = response.choices[0].message.content
            
            # Attempt to find JSON in the content
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                content = json_match.group(0)
                
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                # If JSON parsing fails, create a fallback result
                self.console.print("[warning]Failed to parse complexity analysis response as JSON. Using default values.[/]")
                return {
                    "is_complex": True,
                    "reasoning": "Failed to analyze complexity properly. Treating as complex by default.",
                    "suggested_agents": list(self.agent_registry.list_agents())
                }
            
            # Validate the result has required fields
            if not all(key in result for key in ["is_complex", "reasoning", "suggested_agents"]):
                # Default to treating as complex if analysis fails
                return {
                    "is_complex": True,
                    "reasoning": "Could not properly analyze complexity, treating as complex by default.",
                    "suggested_agents": list(self.agent_registry.list_agents())
                }
                
            return result
            
        except Exception as e:
            self.console.print(f"[error]Error analyzing query complexity: {e}[/]")
            # Default to treating as complex if analysis fails
            return {
                "is_complex": True,
                "reasoning": f"Error analyzing complexity: {str(e)}. Treating as complex by default.",
                "suggested_agents": list(self.agent_registry.list_agents())
            }
    
    def _analyze_query(self, query: str) -> List[Dict[str, str]]:
        """Analyze the query and determine subtasks and agents."""
        # Simplified example: Assign all tasks to the Research agent
        return [{"task": query, "agent": "Research"}]
    
    def _synthesize_response(self, query: str, results: List[Dict[str, Any]], context: Dict[str, Any] = None) -> str:
        """Combine results into a final response."""
        if not context:
            context = {}
        
        # Handle case where there are no valid results
        if not results or all("error" in r.get("result", {}) for r in results):
            return self._fallback_response(query)
            
        synthesis_prompt = f"""
        Based on the results from various agents, provide a comprehensive response to the original query:
        
        Original query: "{query}"
        
        Agent results:
        {self._format_results(results)}
        
        Guidelines for your response:
        1. Be thorough and detailed in addressing all aspects of the query
        2. Organize information in a clear, logical structure with appropriate headings
        3. Include specific examples, data points, or evidence from the research
        4. Use formatting (headings, bullet points, etc.) to improve readability
        5. If the query is asking for elaboration on a previous answer, make sure to expand significantly
        6. Ensure your response has substantial depth and breadth
        7. Be accurate about available information - if information is missing or ambiguous, acknowledge this
        8. IMPORTANT: Never truncate content - provide the full information without abbreviation
        
        IMPORTANT PRESENTATION REQUIREMENTS:
        - For file listings, use formatted tables or bullet points
        - For technical information, use code blocks where appropriate
        - Make complex information visually clear with proper formatting
        
        Synthesize a complete, coherent response that addresses all aspects of the user's query.
        """
        
        try:
            # Use direct LLM call without tools to avoid the Vertex AI error
            messages = [{"role": "system", "content": "You are a helpful assistant."}, 
                        {"role": "user", "content": synthesis_prompt}]
                        
            response = litellm.completion(
                model=self.model,
                messages=messages,
                temperature=0.25,
                max_tokens=4096  # Reduced to avoid potential issues
            )
            
            return response.choices[0].message.content
        except Exception as e:
            self.console.print(f"[error]Error in synthesis: {e}[/]")
            
            # Fall back to simple result compilation
            fallback = f"Here's what I found about {query}:\n\n"
            for result in results:
                if isinstance(result['result'], dict) and 'content' in result['result']:
                    content = result['result']['content']
                    fallback += f"• {content[:500]}...\n\n"
                
            return fallback

    def _format_results(self, results: List[Dict[str, Any]]) -> str:
        """Format agent results for the synthesis prompt without truncation."""
        formatted = ""
        for i, result in enumerate(results):
            formatted += f"Agent {i+1}: {result['agent']}\n"
            formatted += f"Task: {result['task']}\n"
            
            if isinstance(result['result'], dict):
                if 'content' in result['result']:
                    # Include the full content without truncation
                    content = result['result']['content']
                    formatted += f"Result: {content}\n\n"
                elif 'tool_results' in result['result']:
                    # For results with tool outputs, include the full outputs
                    tool_results = []
                    for tool_result in result['result']['tool_results']:
                        tool_name = tool_result.get('tool', 'unknown')
                        tool_output = tool_result.get('result', 'No output')
                        tool_results.append(f"- {tool_name}: {tool_output}")
                    
                    formatted += f"Tool Results: \n" + "\n".join(tool_results) + "\n\n"
            else:
                formatted += f"Result: {str(result['result'])}\n\n"
                
            formatted += "-" * 50 + "\n\n"  # Add separator between agents
                
        return formatted

    def _create_execution_plan(self, query: str, suggested_agents: List[str]) -> List[Dict[str, str]]:
        """Create a detailed execution plan based on the query and suggested agents."""
        planning_prompt = f"""
        Create an execution plan for this query: "{query}"
        
        Break this query down into specific subtasks that can be assigned to these agents: {', '.join(suggested_agents)}
        
        IMPORTANT GUIDELINES:
        - Subtasks must directly relate to the user's query
        - Each task should have a clear purpose that advances the goal
        - Organize tasks in a logical sequence
        - Include interdependencies between tasks when relevant
        - For tasks that build on previous results, specify the context needed
        - Consider the full capabilities of each agent:
          * FileSystem: Working with files, directories, and paths
          * System: Executing shell commands, retrieving system information, environment variables
          * Research: Finding information online, searching Wikipedia, web content

        For each subtask, specify:
        1. The exact task description
        2. Which agent should handle it  
        3. Context needed from previous tasks (optional)
        
        Format your response as a JSON array:
        [
            {{"task": "specific subtask description", "agent": "AgentName"}},
            {{"task": "another subtask description", "agent": "AnotherAgentName", "context": "all"}},
            {{"task": "a context-dependent task", "agent": "AgentName", "context": "definition,types"}}
        ]
        
        Note: The "context" field is optional and should only be included for tasks that need information from previous tasks.
        """
        
        # Use a direct completion without tools for planning
        try:
            messages = [{"role": "user", "content": planning_prompt}]
            response = litellm.completion(
                model=self.model,
                messages=messages,
                temperature=0.2,
                top_p=1.0,
                max_tokens=8192
            )
            
            content = response.choices[0].message.content
            # Extract JSON even if it's embedded in explanatory text
            json_match = re.search(r'\[[\s\S]*\]', content)
            if json_match:
                content = json_match.group(0)
            
            try:
                plan = json.loads(content)
                return plan
            except json.JSONDecodeError:
                # If parsing fails, create a simple fallback plan
                self.console.print("[warning]Failed to parse execution plan as JSON. Using simplified plan.[/]")
                default_tasks = []
                for agent in suggested_agents:
                    task_description = f"Analyze the input string '{query}'"
                    if agent == "FileSystem":
                        task_description += f" for potential file system operations."
                    elif agent == "Research":
                        task_description += f" for information needs that require research."
                    elif agent == "System":
                        task_description += f" to determine if it's a valid command or query."
                    
                    default_tasks.append({
                        "task": task_description,
                        "agent": agent
                    })
                    
                return default_tasks
                
        except Exception as e:
            self.console.print(f"[error]Error creating execution plan: {e}[/]")
            # Fallback to a simple plan if planning fails
            return self._standard_execution_plan(query, suggested_agents)

    def _standard_execution_plan(self, query: str, suggested_agents: List[str]) -> List[Dict[str, str]]:
        """Create standard execution plan when the primary planning method fails."""
        # Create a simple plan by assigning each agent a generic task
        default_tasks = []
        for agent in suggested_agents:
            task_description = f"Process the query: '{query}'"
            if agent == "FileSystem":
                task_description = f"Check if any file system operations are needed for: '{query}'"
            elif agent == "Research":
                task_description = f"Research information related to: '{query}'"
            elif agent == "System":
                task_description = f"Check if any system operations are needed for: '{query}'"
            
            default_tasks.append({
                "task": task_description,
                "agent": agent
            })
        
        return default_tasks

    def send_message_to_user(self, message: str) -> Dict[str, Any]:
        """
        Send a message directly to the user.
        
        Args:
            message: The message content to send to the user
            
        Returns:
            Status of the message sending operation
        """
        # This method is meant to be called by the assistant directly
        # Here we just log that it was called and return the message
        self.context.track_operation(
            agent=self.name,
            operation="send_message_to_user",
            details={"message_length": len(message)},
            success=True
        )
        
        return {
            "status": "success",
            "message": message,
            "timestamp": time.time()
        }
    
    def call_agent(self, agent_name: str, task: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Call a specific agent to perform a task.
        
        Args:
            agent_name: Name of the agent to call
            task: The task description for the agent
            context: Optional context to provide to the agent
            
        Returns:
            Result returned by the agent
        """
        self.console.print(f"[cyan]Direct call to {agent_name}: {task}[/]")
        agent = self.agent_registry.get_agent(agent_name)
        
        if not agent:
            error_msg = f"Agent {agent_name} not found"
            self.console.print(f"[error]{error_msg}[/]")
            return {
                "status": "error",
                "message": error_msg,
                "result": None
            }
        
        # Prepare task context if none provided
        if not context:
            context = {
                "direct_call": True,
                "caller": "Orchestrator",
                "task_id": time.time(),
                "original_query": task
            }
        
        # Call the agent and get the result
        try:
            result = agent.act(task, context)
            
            self.context.track_operation(
                agent=self.name,
                operation="call_agent",
                details={
                    "target_agent": agent_name,
                    "task": task,
                    "success": True
                },
                success=True
            )
            
            return {
                "status": "success",
                "agent": agent_name,
                "result": result
            }
            
        except Exception as e:
            error_msg = str(e)
            self.console.print(f"[error]Error calling agent {agent_name}: {error_msg}[/]")
            
            self.context.log_error(
                agent=self.name,
                operation="call_agent",
                details={
                    "target_agent": agent_name,
                    "task": task
                },
                error_message=error_msg
            )
            
            return {
                "status": "error",
                "agent": agent_name,
                "message": error_msg,
                "result": None
            }
    
    def evaluate_result(self, result: Dict[str, Any], criteria: List[str] = None) -> Dict[str, Any]:
        """
        Evaluate the quality or correctness of a result.
        
        Args:
            result: The result to evaluate
            criteria: Optional list of evaluation criteria
            
        Returns:
            Evaluation of the result
        """
        # Default criteria if none provided
        if not criteria:
            criteria = ["completeness", "relevance", "accuracy"]
            
        # Simple placeholder evaluation - in a real system this would be more sophisticated
        evaluation = {}
        
        # Check if result has content
        if "content" in result:
            content = result["content"]
            evaluation["completeness"] = 0.8 if len(content) > 100 else 0.5
            evaluation["relevance"] = 0.7  # Placeholder score
            evaluation["accuracy"] = 0.8   # Placeholder score
        else:
            evaluation["completeness"] = 0.2
            evaluation["relevance"] = 0.5
            evaluation["accuracy"] = 0.5
            
        # Calculate overall score
        evaluation["overall"] = sum(evaluation.values()) / len(evaluation)
        
        return {
            "evaluation": evaluation,
            "result": result,
            "feedback": "This is an automated evaluation"
        }

    def _fallback_response(self, query: str) -> str:
        """Generate a fallback response when orchestration fails."""
        try:
            # Use direct LLM call without tools
            messages = [{"role": "user", "content": f"Answer this user query simply: {query}"}]
            response = litellm.completion(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=2048
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"I'm unable to process your query at this moment. Please try asking in a different way or try again later."

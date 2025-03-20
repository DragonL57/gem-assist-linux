"""
Orchestrator agent that coordinates specialized agents.
"""
from typing import Dict, List, Any, Optional
from rich.console import Console
from .base_agent import BaseAgent
from .agent_registry import AgentRegistry
import json
import re
import litellm  # Add this import for direct completion calls

class OrchestratorAgent(BaseAgent):
    def __init__(
        self,
        model: str,
        agent_registry: AgentRegistry,
        system_instruction: str = "",
        console: Optional[Console] = None,
    ):
        super().__init__(
            name="Orchestrator",
            model=model,
            tools=[],  # Orchestrator doesn't use tools directly
            system_instruction=system_instruction,
            console=console,
        )
        self.agent_registry = agent_registry
        
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a user query by delegating tasks to specialized agents.
        """
        self.console.print("[dim]Orchestrator processing query...[/]")
        
        # Analyze the query and determine which agents to use
        complexity_info = self.analyze_complexity(query)
        
        # Create a more detailed plan based on complexity analysis
        plan = self._create_execution_plan(query, complexity_info["suggested_agents"])
        
        # Execute subtasks with appropriate agents
        results = []
        context = {"original_query": query, "collected_data": {}}
        
        for i, task in enumerate(plan):
            agent_name = task["agent"]
            subtask = task["task"]
            
            # Augment task with context from previous results when appropriate
            if i > 0 and "context" in task and task["context"]:
                # Add context from previous results if specified
                context_needed = task["context"]
                context_sources = []
                
                for previous_result in results:
                    # Only include relevant context from specific agents or tasks
                    if (context_needed == "all" or 
                        previous_result["agent"] in context_needed or 
                        any(keyword in previous_result["task"].lower() for keyword in context_needed.split(","))):
                        
                        content = previous_result["result"].get("content", "")
                        if content:
                            context_sources.append(f"[From {previous_result['agent']}]: {content[:500]}...")
                
                if context_sources:
                    subtask = f"""{subtask}
                    
                    CONTEXT FROM PREVIOUS RESULTS:
                    {chr(10).join(context_sources)}
                    """
            
            self.console.print(f"[cyan]Delegating to {agent_name}: {subtask}[/]")
            agent = self.agent_registry.get_agent(agent_name)
            if not agent:
                self.console.print(f"[error]Agent {agent_name} not found. Skipping task.[/]")
                continue
                
            result = agent.act(subtask)
            
            # Extract key information from result to build context
            if isinstance(result, dict) and "content" in result:
                # Store the result for future context
                context["collected_data"][f"result_{i}"] = result["content"]
            
            results.append({"agent": agent_name, "task": subtask, "result": result})
        
        # Synthesize final response
        final_response = self._synthesize_response(query, results, context)
        return {"plan": plan, "agent_results": results, "response": final_response}
    
    def analyze_complexity(self, query: str) -> Dict[str, Any]:
        """
        Analyze a query to determine if it's complex enough to warrant multi-agent processing.
        """
        self.console.print("[dim]Analyzing query complexity...[/]")
        
        # Remove hardcoded special handling for informational/research queries
        # and instead use a more flexible prompt-based approach
        
        analysis_prompt = f"""
        Analyze this query: "{query}"
        
        Your task is to determine if this query requires complex processing with multiple specialized agents,
        or if it's a simple query that can be handled directly with basic tools.
        
        Consider the following factors:
        1. Does the query involve multiple distinct steps or operations?
        2. Does it require knowledge from different domains?
        3. Would it benefit from specialized tools for research, file operations, or system tasks?
        4. Is there context or history needed to properly address the query?
        5. Does it involve complex reasoning or planning?
        6. For informational requests (e.g., "What is X?"), consider whether the topic requires:
           - Comprehensive research across multiple sources
           - Verification of facts from different perspectives
           - Structuring complex information in a digestible way
           
        THIS IS VERY IMPORTANT: 
        - For simple greetings, clarification requests, or very short follow-ups, choose is_complex=false
        - For factual questions that need thorough research, choose is_complex=true and include "Research" agent
        - Let the content and requirements of the query guide your decision, not just the query format
        
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
            messages = [{"role": "user", "content": synthesis_prompt}]
            response = litellm.completion(
                model=self.model,
                messages=messages,
                temperature=0.25,
                top_p=1.0,
                max_tokens=8192  # Increase to model's max output tokens
            )
            
            return response.choices[0].message.content
        except Exception as e:
            self.console.print(f"[error]Error synthesizing response: {e}[/]")
            # Fall back to simple result compilation
            response = f"Results for query: {query}\n\n"
            for result in results:
                content = result['result'].get('content', '')
                if content:
                    response += f"From {result['agent']} agent:\n{content}\n\n"
            
            return response

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

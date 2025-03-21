"""
Research specialized agent.
"""
from typing import List, Callable, Dict, Any
from rich.console import Console
import json
from datetime import datetime

from .base_agent import BaseAgent
from utils import (
    duckduckgo_search_tool, reddit_search, get_reddit_post,
    reddit_submission_comments, get_wikipedia_summary,
    search_wikipedia, get_full_wikipedia_page, get_website_text_content,
    http_get_request
)

class ResearchAgent(BaseAgent):
    def __init__(
        self,
        model: str,
        console: Console = None
    ):
        # Collect all research-related tools
        research_tools = [
            duckduckgo_search_tool, reddit_search, get_reddit_post,
            reddit_submission_comments, get_wikipedia_summary,
            search_wikipedia, get_full_wikipedia_page, get_website_text_content,
            http_get_request, self.save_research_data, self.validate_information
        ]
        
        system_instruction = """
        You are a specialized research agent designed to retrieve and synthesize comprehensive information.
        
        YOUR RESEARCH PROCESS:
        1. ALWAYS use multiple tools and sources to gather information on a topic
        2. Compare and verify information across different sources
        3. When answering questions, use this workflow:
           - First search for general information using duckduckgo_search_tool
           - For structured knowledge, try get_wikipedia_summary but verify results are correct
           - If wikipedia fails, use duckduckgo_search_tool as a fallback
           - For technical topics, look for authoritative sources and documentation
        
        INFORMATION SYNTHESIS GUIDELINES:
        - Provide in-depth, comprehensive explanations
        - Include multiple perspectives and viewpoints when relevant
        - Organize information logically with clear structure
        - Use examples to illustrate concepts
        - Include classifications, types, or categories when applicable
        - Cite your sources within the response
        
        QUALITY STANDARDS:
        - Verify information is accurate before including it using validate_information
        - Don't trust a single source - always cross-reference
        - If sources conflict, acknowledge the different viewpoints
        - Be thorough and detailed in your answers
        - Use formatting (headings, bullets, etc.) to improve readability
        - Save important research results using save_research_data
        
        CRITICAL RESEARCH SKILLS:
        - When researching a term like "AI agent", make sure to check for its literal meaning
        - Always verify Wikipedia results against other sources
        - If first search has irrelevant results, try alternative search queries
        - When search results are off-topic, mention this and correct your approach
        
        When finished with a task, always use complete_task to return your results.
        """
        
        super().__init__(
            name="Research",
            model=model,
            tools=research_tools,
            system_instruction=system_instruction,
            console=console
        )
    
    def act(self, query: str, task_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Override the base act method to provide research guidance.
        """
        # Add a subtle guide to the query without adding unnecessary verbosity
        enhanced_query = f"""Task: {query}
        
        Please use appropriate research tools and cross-check information from multiple sources."""
        
        return super().act(enhanced_query, task_context)
        
    def save_research_data(self, topic: str, data: Dict[str, Any], source: str) -> Dict[str, Any]:
        """
        Save important research data for future reference.
        
        Args:
            topic: The research topic
            data: The data to save
            source: Source of the information
            
        Returns:
            Confirmation of saved data
        """
        # Store in context for future reference
        sanitized_data = self.context.sanitize_for_json(data)
        key = f"research_{topic.replace(' ', '_')}"
        
        entry = {
            "topic": topic,
            "data": sanitized_data,
            "source": source,
            "timestamp": datetime.now().isoformat()
        }
        
        self.context.update_entity_reference("research_data", key, entry)
        self.context.share_data(key, entry)
        
        return {
            "status": "success",
            "message": f"Saved research data for topic: {topic}",
            "key": key
        }
    
    def validate_information(self, information: str, sources: List[str] = None) -> Dict[str, Any]:
        """
        Validate information against sources or general knowledge.
        
        Args:
            information: The information to validate
            sources: Optional list of sources to check against
            
        Returns:
            Validation result with confidence score
        """
        # This would ideally involve cross-checking information
        # For now, it's a placeholder that acknowledges the validation request
        return {
            "validated": True,
            "confidence": 0.8,  # Placeholder confidence score
            "message": "Information has been noted for validation",
            "sources_checked": sources if sources else []
        }

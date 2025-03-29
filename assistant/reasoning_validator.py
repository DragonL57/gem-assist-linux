from typing import Dict
from config import get_config

class ReasoningValidator:
    """Validates assistant reasoning plans."""
    
    def __init__(self):
        self.required_sections = [
            "Problem Analysis", 
            "Information Needs", 
            "Tool Selection Strategy", 
            "Verification Strategy"
        ]
        self.tools_registry = {}
        # Define rate-limited tools that should be used sparingly
        self.rate_limited_tools = ["web_search", "get_reddit_search", "search_arxiv"]
        # Maximum recommended uses for rate-limited tools
        self.max_search_calls = 2

    def update_tools_registry(self):
        """Update the tools registry from the available tools."""
        try:
            from gem.tools import TOOL_REGISTRY
            self.tools_registry = {tool_name: tool for tool_name, tool in TOOL_REGISTRY.items()}
        except ImportError:
            from assistant.tools_registry import get_tools
            self.tools_registry = {tool.name: tool for tool in get_tools()}

    def validate_plan(self, reasoning: str) -> Dict[str, any]:
        """Validates a reasoning plan and returns validation results."""
        results = {
            "is_valid": True,
            "missing_sections": [],
            "invalid_tools": [],
            "warnings": [],
            "rate_limit_warnings": [],
            "score": 0.0,
        }
        
        # Validate required sections
        for section in self.required_sections:
            if section.lower() not in reasoning.lower():
                results["missing_sections"].append(section)
                results["is_valid"] = False
        
        # Validate tools exist
        import re
        tool_references = re.findall(r'(\w+)\(', reasoning)
        for tool in tool_references:
            if tool not in self.tools_registry and tool not in ["if", "for", "while", "print"]:
                results["invalid_tools"].append(tool)
                results["is_valid"] = False
        
        # Check for rate limit compliance
        self._check_rate_limit_compliance(reasoning, results)
        
        # Calculate score
        score = 100
        score -= len(results["missing_sections"]) * 15
        score -= len(results["invalid_tools"]) * 10
        score -= len(results["rate_limit_warnings"]) * 15  # Penalize rate limit issues heavily
        results["score"] = max(0, score) / 100
        
        return results
        
    def _check_rate_limit_compliance(self, reasoning: str, results: Dict[str, any]) -> None:
        """Check if the reasoning plan respects rate limits for search tools."""
        import re
        
        # Check each rate-limited tool
        for tool in self.rate_limited_tools:
            # Count occurrences of the tool in the reasoning plan
            tool_calls = re.findall(f"{tool}\\(", reasoning)
            if len(tool_calls) > self.max_search_calls:
                warning = f"Too many {tool} calls ({len(tool_calls)}). Maximum recommended is {self.max_search_calls}."
                results["rate_limit_warnings"].append(warning)
                results["warnings"].append(warning)
        
        # Check if web_search is followed by content extraction
        if "web_search" in reasoning:
            if "get_website_text_content" not in reasoning and "smart_content_extraction" not in reasoning:
                warning = "Web search should be followed by content extraction (get_website_text_content or smart_content_extraction)"
                results["rate_limit_warnings"].append(warning)
                results["warnings"].append(warning)

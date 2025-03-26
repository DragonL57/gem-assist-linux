"""
Result handlers for different types of tool execution results.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List
from dataclasses import dataclass

@dataclass
class ResultContext:
    """Context information for result handling."""
    execution_time: float
    max_lines: int = 3
    max_length: int = 200

class ToolResultHandler(ABC):
    """Base class for handling tool results."""
    
    @abstractmethod
    def format_result(self, result: Any, context: ResultContext) -> str:
        """Format the result for display.
        
        Args:
            result: The result to format
            context: Context information for formatting
            
        Returns:
            Formatted string representation of the result
        """
        raise NotImplementedError

class SearchResultHandler(ToolResultHandler):
    """Handler for search tool results."""
    
    def format_result(self, result: Any, context: ResultContext) -> str:
        """Format search results, showing the count of results."""
        result_count = self._count_results(result)
        return f"Received {result_count} results in {context.execution_time:.2f}s"
        
    def _count_results(self, result: Any) -> int:
        """Count the number of results in a search response."""
        try:
            if isinstance(result, dict):
                # Check common result container keys
                for key in ["results", "matches", "posts", "items"]:
                    if key in result and isinstance(result[key], list):
                        return len(result[key])
                # If no recognized container, count the dict itself
                return 1
            elif isinstance(result, list):
                return len(result)
            return 1  # Default for single-result responses
        except Exception:
            return 0

class DefaultResultHandler(ToolResultHandler):
    """Default handler for general tool results."""
    
    def format_result(self, result: Any, context: ResultContext) -> str:
        """Format general results with a condensed preview."""
        preview = self._create_preview(result, context.max_lines, context.max_length)
        return f"{preview} [dim]({context.execution_time:.2f}s)[/]"
        
    def _create_preview(self, result: Any, max_lines: int, max_length: int) -> str:
        """Create a condensed preview of a result.
        
        Args:
            result: Result to preview
            max_lines: Maximum number of lines to show
            max_length: Maximum length of the preview
            
        Returns:
            Condensed preview string
        """
        try:
            # Convert to string first
            if not isinstance(result, str):
                if isinstance(result, (dict, list)):
                    result_str = str(result)[:max_length]
                else:
                    result_str = str(result)[:max_length]
            else:
                result_str = result[:max_length]
            
            # Truncate to specified number of lines with ellipsis
            lines = result_str.split("\n")
            if len(lines) > max_lines:
                short_result = "\n".join(lines[:max_lines]) + "..."
            else:
                short_result = result_str
                
            # Further truncate if too long
            if len(short_result) > max_length:
                short_result = short_result[:(max_length - 3)] + "..."
                
            return short_result
        except Exception:
            return "[Preview not available]"
            
class LongTextResultHandler(ToolResultHandler):
    """Handler for long text results like file contents or API responses."""
    
    def format_result(self, result: Any, context: ResultContext) -> str:
        """Format long text results with word count and preview."""
        if isinstance(result, str):
            word_count = len(result.split())
            preview = DefaultResultHandler()._create_preview(result, context.max_lines, context.max_length)
            return (
                f"Text response ({word_count} words) "
                f"[dim]in {context.execution_time:.2f}s:[/]\n{preview}"
            )
        return DefaultResultHandler().format_result(result, context)

class JsonResultHandler(ToolResultHandler):
    """Handler for JSON/dictionary results."""
    
    def format_result(self, result: Any, context: ResultContext) -> str:
        """Format JSON/dictionary results with structure information."""
        if isinstance(result, (dict, list)):
            structure = self._describe_structure(result)
            preview = self._format_json(result, context)
            return (
                f"{structure} [dim]in {context.execution_time:.2f}s:[/]\n{preview}"
            )
        return DefaultResultHandler().format_result(result, context)
        
    def _describe_structure(self, result: Any) -> str:
        """Create a brief description of the data structure."""
        if isinstance(result, dict):
            key_count = len(result)
            return f"Dictionary with {key_count} keys"
        elif isinstance(result, list):
            item_count = len(result)
            return f"List with {item_count} items"
        return "Unknown structure"
        
    def _format_json(self, result: Any, context: ResultContext) -> str:
        """Format result as JSON with proper indentation."""
        try:
            import json
            formatted = json.dumps(result, indent=2)
            return DefaultResultHandler()._create_preview(formatted, context.max_lines, context.max_length)
        except Exception:
            return "[JSON formatting failed]"

"""
Base exception classes for the assistant.
"""
from typing import Dict, Any, Optional

class AssistantError(Exception):
    """Base exception class for assistant errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.identifier = self.__class__.__name__.upper()
        self.message = message
        self.details = details or {}
        super().__init__(f"[{self.identifier}] {message}")

class ToolExecutionError(AssistantError):
    """Raised when a tool execution fails."""
    
    def __init__(self, message: str, tool_name: str, tool_args: Any, details: Optional[Dict[str, Any]] = None):
        self.tool_name = tool_name
        self.tool_args = tool_args
        details = details or {}
        details.update({
            "tool_name": tool_name,
            "tool_args": tool_args
        })
        super().__init__(message, details)

class ConfigurationError(AssistantError):
    """Raised when there is a configuration issue."""
    pass

class MessageProcessingError(AssistantError):
    """Raised when message processing fails."""
    
    def __init__(self, message: str, phase: str, details: Optional[Dict[str, Any]] = None):
        self.phase = phase
        details = details or {}
        details["phase"] = phase
        super().__init__(f"[{self.phase.upper()}_FAILURE] {message}", details)

class AsyncOperationError(AssistantError):
    """Raised when an async operation fails."""
    
    def __init__(self, message: str, operation: str, details: Optional[Dict[str, Any]] = None):
        self.operation = operation
        details = details or {}
        details["operation"] = operation
        super().__init__(f"[ASYNC_{operation.upper()}_FAILURE] {message}", details)

class APICallError(AssistantError):
    """Raised when an API call fails."""
    
    def __init__(self, message: str, model_name: str, retries: int, details: Optional[Dict[str, Any]] = None):
        self.model_name = model_name
        self.retries = retries
        details = details or {}
        details.update({
            "model_name": model_name,
            "retries": retries
        })
        super().__init__(message, details)

class AsyncToolExecutionError(ToolExecutionError):
    """Raised when an async tool execution fails."""
    
    def __init__(self, message: str, tool_name: str, tool_args: Any, is_async: bool = True, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["is_async"] = is_async
        super().__init__(message, tool_name, tool_args, details)

"""
Base exceptions for the assistant system.
"""
from typing import Optional, Dict, Any

class AssistantError(Exception):
    """Base exception for all assistant-related errors."""
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        error_string = f"{self.message}"
        if self.error_code:
            error_string = f"[{self.error_code}] {error_string}"
        if self.details:
            error_string = f"{error_string}\nDetails: {self.details}"
        return error_string

class ToolExecutionError(AssistantError):
    """Raised when a tool execution fails."""
    def __init__(self, message: str, tool_name: str, tool_args: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(message, error_code="EXEC_TOOL_EXECUTION_FAILED", **kwargs)
        self.tool_name = tool_name
        self.tool_args = tool_args or {}
        self.details.update({
            "tool_name": tool_name,
            "tool_args": tool_args
        })

class ConfigurationError(AssistantError):
    """Raised for configuration-related errors."""
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="CONFIG_LOAD_FAILURE", **kwargs)
        self.config_key = config_key
        if config_key:
            self.details["config_key"] = config_key

class PluginError(AssistantError):
    """Base class for plugin-related errors."""
    def __init__(self, message: str, plugin_name: str, **kwargs):
        super().__init__(message, error_code="PLUGIN_REGISTRATION_FAILURE", **kwargs)
        self.plugin_name = plugin_name
        self.details["plugin_name"] = plugin_name

class MessageProcessingError(AssistantError):
    """Raised when message processing fails."""
    def __init__(self, message: str, message_id: Optional[str] = None, phase: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="MSG_PROCESSING_FAILURE", **kwargs)
        self.message_id = message_id
        self.phase = phase
        if message_id:
            self.details["message_id"] = message_id
        if phase:
            self.details["phase"] = phase

class ValidationError(AssistantError):
    """Raised when input validation fails."""
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None, **kwargs):
        super().__init__(message, error_code="VALIDATION_INPUT_INVALID", **kwargs)
        self.field = field
        self.value = value
        if field:
            self.details["field"] = field
        if value:
            self.details["value"] = str(value)

class APICallError(AssistantError):
    """Raised when an API call fails after multiple retries."""
    def __init__(self, message: str, model_name: Optional[str] = None, retries: Optional[int] = None, **kwargs):
        super().__init__(message, error_code="LLM_API_CALL_FAILURE", **kwargs)
        self.model_name = model_name
        self.retries = retries
        if model_name:
            self.details["model_name"] = model_name
        if retries is not None:
            self.details["retries"] = retries

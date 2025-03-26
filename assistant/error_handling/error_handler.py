"""
Error handling service for the assistant system.
"""
import logging
import traceback
from typing import Optional, Dict, Any, Callable
from datetime import datetime

from ..exceptions.base import AssistantError

class ErrorHandler:
    """Centralized error handling service."""
    
    def __init__(self):
        self.error_handlers: Dict[type, Callable] = {}
        self.logger = logging.getLogger(__name__)
        
    def register_handler(self, error_type: type, handler: Callable) -> None:
        """Register a handler for a specific error type.
        
        Args:
            error_type: The type of error this handler handles
            handler: Callback function that handles the error
        """
        self.error_handlers[error_type] = handler
        
    def handle_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle an error using registered handlers or default handling.
        
        Args:
            error: The error to handle
            context: Optional context information about when/where the error occurred
            
        Returns:
            Dict containing error details and handling results
        """
        error_type = type(error)
        handler = self.error_handlers.get(error_type)
        
        error_info = self._create_error_info(error, context)
        self._log_error(error_info)
        
        if handler:
            try:
                handling_result = handler(error, context)
                error_info["handling_result"] = handling_result
            except Exception as handler_error:
                self.logger.error(f"Error handler failed: {handler_error}")
                error_info["handler_error"] = str(handler_error)
                
        return error_info
    
    def _create_error_info(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create detailed error information dictionary.
        
        Args:
            error: The error that occurred
            context: Optional context information
            
        Returns:
            Dict containing comprehensive error details
        """
        error_info = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": error.__class__.__name__,
            "message": str(error),
            "traceback": traceback.format_exc(),
        }
        
        if isinstance(error, AssistantError):
            error_info.update({
                "error_code": error.error_code,
                "details": error.details
            })
            
        if context:
            error_info["context"] = context
            
        return error_info
    
    def _log_error(self, error_info: Dict[str, Any]) -> None:
        """Log error information appropriately.
        
        Args:
            error_info: Dictionary containing error details
        """
        log_message = f"Error: {error_info['error_type']}"
        if "error_code" in error_info:
            log_message += f" [{error_info['error_code']}]"
        log_message += f" - {error_info['message']}"
        
        self.logger.error(log_message, extra={"error_info": error_info})

    def create_error_report(self, error_info: Dict[str, Any]) -> str:
        """Create a formatted error report string.
        
        Args:
            error_info: Dictionary containing error details
            
        Returns:
            Formatted error report string
        """
        report = [
            f"Error Report - {error_info['timestamp']}",
            f"Type: {error_info['error_type']}",
        ]
        
        if "error_code" in error_info:
            report.append(f"Code: {error_info['error_code']}")
            
        report.extend([
            f"Message: {error_info['message']}",
            "\nTraceback:",
            error_info['traceback'],
        ])
        
        if "details" in error_info:
            report.append("\nDetails:")
            for key, value in error_info["details"].items():
                report.append(f"  {key}: {value}")
                
        if "context" in error_info:
            report.append("\nContext:")
            for key, value in error_info["context"].items():
                report.append(f"  {key}: {value}")
                
        return "\n".join(report)

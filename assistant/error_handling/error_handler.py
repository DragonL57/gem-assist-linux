"""
Error handling for the assistant.
"""
import logging
import inspect
import traceback
from typing import Dict, Any, Optional

from ..exceptions.base import AssistantError
from ..logging.logger import AssistantLogger

class ErrorHandler:
    """Handles error processing and logging."""
    
    def __init__(self):
        """Initialize the error handler."""
        self.logger = AssistantLogger()
        
    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process an error and create error information.
        
        Args:
            error: The error that occurred
            context: Additional context about when the error occurred
            
        Returns:
            Dictionary containing error information
        """
        try:
            # Create error info
            error_info = self._create_error_info(error, context or {})
            
            # Log the error with the new format
            self.logger.log_error(
                error_info["message"],
                details={
                    "error_type": error_info["type"],
                    "error_details": error_info["details"]
                }
            )
            
            return error_info
            
        except Exception as e:
            # Fallback error handling
            self.logger.log_error(
                f"Error in error handler: {str(e)}",
                details={
                    "original_error": str(error),
                    "handler_error": str(e)
                }
            )
            return {
                "type": "ERROR_HANDLER_FAILURE",
                "message": "Error occurred while handling another error",
                "details": {
                    "original_error": str(error),
                    "handler_error": str(e)
                }
            }
            
    def _create_error_info(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create structured error information."""
        if isinstance(error, AssistantError):
            error_info = {
                "type": error.identifier,
                "message": error.message,
                "details": {
                    **error.details,
                    "context": context
                }
            }
        else:
            error_info = {
                "type": error.__class__.__name__.upper(),
                "message": str(error),
                "details": {
                    "traceback": traceback.format_exc(),
                    "context": context
                }
            }
            
        return error_info

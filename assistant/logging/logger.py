"""
Logging configuration for the assistant system.
"""
import logging
import sys
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any

class AssistantLogger:
    """Configures and manages logging for the assistant system."""

    def __init__(
        self,
        log_dir: str = "logs",
        log_level: int = logging.INFO,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ):
        self.logger = logging.getLogger("assistant")
        self.logger.setLevel(log_level)
        
        # Create logs directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)
        
        # Generate log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = os.path.join(log_dir, f"assistant_{timestamp}.log")
        
        # Create handlers
        self.file_handler = self._create_file_handler(
            log_file, log_level, max_bytes, backup_count
        )
        self.console_handler = self._create_console_handler(log_level)
        
        # Add handlers to logger
        self.logger.addHandler(self.file_handler)
        self.logger.addHandler(self.console_handler)
        
    def _create_file_handler(
        self,
        log_file: str,
        log_level: int,
        max_bytes: int,
        backup_count: int
    ) -> RotatingFileHandler:
        """Create and configure the file handler.
        
        Args:
            log_file: Path to the log file
            log_level: Logging level
            max_bytes: Maximum size of each log file
            backup_count: Number of backup files to keep
            
        Returns:
            Configured RotatingFileHandler
        """
        handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        handler.setLevel(log_level)
        handler.setFormatter(self._create_file_formatter())
        return handler
        
    def _create_console_handler(self, log_level: int) -> logging.StreamHandler:
        """Create and configure the console handler.
        
        Args:
            log_level: Logging level
            
        Returns:
            Configured StreamHandler
        """
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        handler.setFormatter(self._create_console_formatter())
        return handler
        
    def _create_file_formatter(self) -> logging.Formatter:
        """Create formatter for file logging.
        
        Returns:
            Configured Formatter for file logs
        """
        return logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
    def _create_console_formatter(self) -> logging.Formatter:
        """Create formatter for console logging.
        
        Returns:
            Configured Formatter for console logs
        """
        return logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        
    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance.
        
        Returns:
            Configured Logger instance
        """
        return self.logger

    def log_error(self, error_info: Dict[str, Any]) -> None:
        """Log an error with full context.
        
        Args:
            error_info: Dictionary containing error details
        """
        self.logger.error(
            error_info["message"],
            extra={
                "error_type": error_info.get("error_type"),
                "error_code": error_info.get("error_code"),
                "details": error_info.get("details"),
                "context": error_info.get("context")
            }
        )

    def log_warning(self, warning: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Log a warning with optional details.
        
        Args:
            warning: Warning message
            details: Optional dictionary of additional details
        """
        self.logger.warning(
            warning,
            extra={"details": details} if details else {}
        )

    def log_info(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Log an info message with optional details.
        
        Args:
            message: Info message
            details: Optional dictionary of additional details
        """
        self.logger.info(
            message,
            extra={"details": details} if details else {}
        )

    def log_debug(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Log a debug message with optional details.
        
        Args:
            message: Debug message
            details: Optional dictionary of additional details
        """
        self.logger.debug(
            message,
            extra={"details": details} if details else {}
        )

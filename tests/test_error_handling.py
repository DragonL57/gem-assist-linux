"""
Tests for the error handling system.
"""
import pytest
from datetime import datetime
from typing import Dict, Any

from assistant.exceptions.base import (
    AssistantError,
    ToolExecutionError,
    ConfigurationError,
    PluginError,
    MessageProcessingError,
    ValidationError
)
from assistant.error_handling.error_handler import ErrorHandler
from assistant.logging.logger import AssistantLogger

def test_base_assistant_error():
    """Test the base AssistantError class."""
    error = AssistantError("Test error", "TEST_ERR", {"key": "value"})
    assert error.message == "Test error"
    assert error.error_code == "TEST_ERR"
    assert error.details == {"key": "value"}
    assert "[TEST_ERR]" in str(error)

def test_tool_execution_error():
    """Test ToolExecutionError specifics."""
    error = ToolExecutionError(
        message="Tool failed",
        tool_name="test_tool",
        tool_args={"param": "value"}
    )
    assert error.error_code == "TOOL_EXEC_ERR"
    assert error.tool_name == "test_tool"
    assert error.tool_args == {"param": "value"}
    assert all(key in error.details for key in ["tool_name", "tool_args"])

def test_configuration_error():
    """Test ConfigurationError specifics."""
    error = ConfigurationError("Invalid config", "test_key")
    assert error.error_code == "CONFIG_ERR"
    assert error.config_key == "test_key"
    assert "config_key" in error.details

def test_plugin_error():
    """Test PluginError specifics."""
    error = PluginError("Plugin failed", "test_plugin")
    assert error.error_code == "PLUGIN_ERR"
    assert error.plugin_name == "test_plugin"
    assert "plugin_name" in error.details

def test_message_processing_error():
    """Test MessageProcessingError specifics."""
    error = MessageProcessingError(
        message="Processing failed",
        message_id="123",
        phase="reasoning"
    )
    assert error.error_code == "MSG_PROC_ERR"
    assert error.message_id == "123"
    assert error.phase == "reasoning"
    assert all(key in error.details for key in ["message_id", "phase"])

def test_validation_error():
    """Test ValidationError specifics."""
    error = ValidationError(
        message="Invalid value",
        field="test_field",
        value=123
    )
    assert error.error_code == "VALIDATION_ERR"
    assert error.field == "test_field"
    assert error.value == 123
    assert all(key in error.details for key in ["field", "value"])

class TestErrorHandler:
    """Tests for the ErrorHandler class."""
    
    @pytest.fixture
    def error_handler(self):
        """Create an ErrorHandler instance for testing."""
        return ErrorHandler()
    
    def test_register_and_handle_error(self, error_handler):
        """Test registering and using an error handler."""
        def custom_handler(error: Exception, context: Dict[str, Any]) -> str:
            return "Handled error"
            
        error_handler.register_handler(ValueError, custom_handler)
        result = error_handler.handle_error(ValueError("test error"))
        
        assert result["error_type"] == "ValueError"
        assert result["handling_result"] == "Handled error"
        
    def test_error_info_creation(self, error_handler):
        """Test error info dictionary creation."""
        error = AssistantError(
            message="Test error",
            error_code="TEST_ERR",
            details={"test": "value"}
        )
        context = {"context_key": "context_value"}
        
        error_info = error_handler._create_error_info(error, context)
        
        assert isinstance(error_info["timestamp"], str)
        assert error_info["error_type"] == "AssistantError"
        assert error_info["message"] == "Test error"
        assert error_info["error_code"] == "TEST_ERR"
        assert error_info["details"] == {"test": "value"}
        assert error_info["context"] == context
        
    def test_error_report_creation(self, error_handler):
        """Test error report string creation."""
        error_info = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": "TestError",
            "message": "Test error message",
            "error_code": "TEST_ERR",
            "traceback": "Test traceback",
            "details": {"key": "value"},
            "context": {"ctx_key": "ctx_value"}
        }
        
        report = error_handler.create_error_report(error_info)
        
        assert "Error Report" in report
        assert "TestError" in report
        assert "TEST_ERR" in report
        assert "Test error message" in report
        assert "key: value" in report
        assert "ctx_key: ctx_value" in report

class TestAssistantLogger:
    """Tests for the AssistantLogger class."""
    
    @pytest.fixture
    def logger(self, tmp_path):
        """Create an AssistantLogger instance for testing."""
        log_dir = tmp_path / "logs"
        return AssistantLogger(str(log_dir))
    
    def test_error_logging(self, logger, caplog):
        """Test error logging functionality."""
        error_info = {
            "message": "Test error",
            "error_type": "TestError",
            "error_code": "TEST_ERR",
            "details": {"key": "value"},
            "context": {"ctx": "test"}
        }
        
        logger.log_error(error_info)
        
        assert "Test error" in caplog.text
        assert "TestError" in str(caplog.records[0].error_type)
        assert "TEST_ERR" in str(caplog.records[0].error_code)
        
    def test_warning_logging(self, logger, caplog):
        """Test warning logging functionality."""
        logger.log_warning("Test warning", {"detail": "test"})
        assert "Test warning" in caplog.text
        assert "detail" in str(caplog.records[0].details)
        
    def test_info_logging(self, logger, caplog):
        """Test info logging functionality."""
        logger.log_info("Test info", {"detail": "test"})
        assert "Test info" in caplog.text
        assert "detail" in str(caplog.records[0].details)
        
    def test_debug_logging(self, logger, caplog):
        """Test debug logging functionality."""
        logger.log_debug("Test debug", {"detail": "test"})
        assert "Test debug" in caplog.text
        assert "detail" in str(caplog.records[0].details)

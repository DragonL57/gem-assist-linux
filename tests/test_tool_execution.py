"""
Tests for the tool execution system.
"""
import pytest
from rich.console import Console
from typing import Dict, Any

from assistant.execution import (
    ToolExecutor,
    ToolDisplayManager,
    DisplayConfig,
    ResultContext,
    SearchResultHandler,
    DefaultResultHandler,
    LongTextResultHandler,
    JsonResultHandler
)
from assistant.exceptions.base import ToolExecutionError

class MockAssistant:
    """Mock assistant for testing."""
    def __init__(self):
        self.console = Console(no_color=True)
        self.available_functions = {
            "test_tool": lambda x: f"Result: {x}",
            "search_tool": lambda: {"results": ["result1", "result2"]},
        }
        self.type_converter = MockTypeConverter()
        self.outputs = []

    def add_toolcall_output(self, tool_id: str, name: str, content: Any) -> None:
        self.outputs.append((tool_id, name, content))

class MockTypeConverter:
    """Mock type converter for testing."""
    def convert_to_pydantic_model(self, annotation: Any, value: Any) -> Any:
        return value

@pytest.fixture
def mock_assistant():
    """Create a mock assistant for testing."""
    return MockAssistant()

@pytest.fixture
def executor(mock_assistant):
    """Create a ToolExecutor instance for testing."""
    return ToolExecutor(mock_assistant)

@pytest.fixture
def display_manager(mock_assistant):
    """Create a ToolDisplayManager instance for testing."""
    return ToolDisplayManager(mock_assistant.console)

def test_successful_tool_execution(executor):
    """Test successful execution of a simple tool."""
    class MockToolCall:
        function = type('obj', (object,), {
            'name': 'test_tool',
            'arguments': '{"x": "test"}'
        })
        id = "test_id"

    executor.execute_tool_call(MockToolCall())
    assert len(executor.assistant.outputs) == 1
    assert executor.assistant.outputs[0][1] == "test_tool"
    assert executor.assistant.outputs[0][2] == "Result: test"

def test_missing_tool_handling(executor):
    """Test handling of missing tool."""
    class MockToolCall:
        function = type('obj', (object,), {
            'name': 'nonexistent_tool',
            'arguments': '{}'
        })
        id = "test_id"

    executor.execute_tool_call(MockToolCall())
    assert len(executor.assistant.outputs) == 1
    assert "Tool not found" in executor.assistant.outputs[0][2]

def test_invalid_arguments_handling(executor):
    """Test handling of invalid tool arguments."""
    class MockToolCall:
        function = type('obj', (object,), {
            'name': 'test_tool',
            'arguments': 'invalid json'
        })
        id = "test_id"

    executor.execute_tool_call(MockToolCall())
    assert len(executor.assistant.outputs) == 1
    assert "Failed to process arguments" in executor.assistant.outputs[0][2]

def test_search_result_handler():
    """Test search result handler formatting."""
    handler = SearchResultHandler()
    result = {"results": ["result1", "result2", "result3"]}
    context = ResultContext(execution_time=1.5)
    
    formatted = handler.format_result(result, context)
    assert "3 results" in formatted
    assert "1.50s" in formatted

def test_default_result_handler():
    """Test default result handler formatting."""
    handler = DefaultResultHandler()
    result = "Simple result"
    context = ResultContext(execution_time=0.5)
    
    formatted = handler.format_result(result, context)
    assert "Simple result" in formatted
    assert "0.50s" in formatted

def test_long_text_result_handler():
    """Test long text result handler formatting."""
    handler = LongTextResultHandler()
    result = "This is a long text " * 50  # Create long text
    context = ResultContext(execution_time=1.0)
    
    formatted = handler.format_result(result, context)
    assert "words" in formatted
    assert "1.00s" in formatted
    assert len(formatted.splitlines()) <= context.max_lines + 1

def test_json_result_handler():
    """Test JSON result handler formatting."""
    handler = JsonResultHandler()
    result = {"key1": "value1", "key2": {"nested": "value2"}}
    context = ResultContext(execution_time=0.75)
    
    formatted = handler.format_result(result, context)
    assert "Dictionary with 2 keys" in formatted
    assert "0.75s" in formatted
    assert "key1" in formatted

def test_display_manager_formatting():
    """Test display manager formatting functions."""
    console = Console(no_color=True)
    display = ToolDisplayManager(console)
    
    # Test argument formatting
    args = {"long_arg": "x" * 100, "short_arg": "value"}
    display.display_tool_call("test_tool", args)
    
    # Test result formatting
    display.display_tool_result("test_tool", "Success result")
    
    # Test error formatting
    display.display_tool_error("test_tool", "Test error")

def test_tool_execution_context_handling(executor):
    """Test tool execution context handling."""
    class MockToolCall:
        function = type('obj', (object,), {
            'name': 'test_tool',
            'arguments': '{"x": "test_context"}'
        })
        id = "context_test_id"

    # Execute tool and verify context is properly handled
    executor.execute_tool_call(MockToolCall())
    
    # Check that output was added with correct context
    assert len(executor.assistant.outputs) == 1
    assert executor.assistant.outputs[0][0] == "context_test_id"  # tool_call_id
    assert executor.assistant.outputs[0][1] == "test_tool"  # name
    assert "test_context" in executor.assistant.outputs[0][2]  # content

def test_result_handler_selection(executor):
    """Test correct result handler selection based on result type."""
    # Test search tool handler
    assert isinstance(
        executor._get_result_handler({"results": []}, "web_search"),
        SearchResultHandler
    )
    
    # Test JSON handler
    assert isinstance(
        executor._get_result_handler({"key": "value"}, "any_tool"),
        JsonResultHandler
    )
    
    # Test long text handler
    assert isinstance(
        executor._get_result_handler("x" * 300, "any_tool"),
        LongTextResultHandler
    )
    
    # Test default handler
    assert isinstance(
        executor._get_result_handler("short text", "any_tool"),
        DefaultResultHandler
    )

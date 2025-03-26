"""
Tests for the context management service.
"""
import pytest
from datetime import datetime
from unittest.mock import patch, Mock

from config.services.context import (
    get_context_info,
    format_prompt_with_context,
    get_system_prompt
)

@pytest.fixture
def mock_services():
    """Mock system and location services."""
    with patch('config.services.context.get_system_service') as mock_system, \
         patch('config.services.context.get_location_service') as mock_location:
        
        # Mock system info
        system_info = Mock()
        system_info.os_name = "Test OS"
        system_info.os_version = "1.0"
        system_info.python_version = "3.9.0"
        mock_system().get_system_info.return_value = system_info
        
        # Mock location info
        location_info = Mock()
        location_info.formatted = "Location: Test Location"
        mock_location().get_location.return_value = location_info
        
        yield {
            'system': mock_system,
            'location': mock_location
        }

async def test_context_info_generation(mock_services):
    """Test generation of context information."""
    context = await get_context_info()
    
    # Check that all required information is present
    assert "Test OS 1.0" in context
    assert "Python Version: 3.9.0" in context
    assert "Location: Test Location" in context
    
    # Check timestamp format
    timestamp = datetime.now().strftime("%Y-%m-%d")
    assert timestamp in context

async def test_prompt_formatting():
    """Test formatting prompts with context."""
    test_prompt = """
    Hello {name}!
    {context}
    """
    
    # Test with default name
    formatted = await format_prompt_with_context(test_prompt)
    assert "Hello Assistant!" in formatted
    assert "SYSTEM CONTEXT" in formatted
    
    # Test with custom name
    formatted = await format_prompt_with_context(test_prompt, "TestBot")
    assert "Hello TestBot!" in formatted
    assert "SYSTEM CONTEXT" in formatted

@patch('config.services.context.get_prompt_manager')
async def test_system_prompt_generation(mock_prompt_manager, mock_services):
    """Test generation of system prompt with context."""
    # Mock base prompt from prompt manager
    mock_prompt_manager().base_system_prompt = """
    Base prompt for {name}
    System info:
    {context}
    """
    
    prompt = await get_system_prompt("TestBot")
    
    # Check content
    assert "Base prompt for TestBot" in prompt
    assert "Test OS 1.0" in prompt
    assert "Python Version: 3.9.0" in prompt
    assert "Location: Test Location" in prompt

def test_context_info_error_handling(mock_services):
    """Test error handling in context generation."""
    # Make system service raise an error
    mock_services['system']().get_system_info.side_effect = Exception("System error")
    
    # Should still return some context even if parts fail
    context = get_context_info()
    assert "SYSTEM CONTEXT" in context
    assert "Current Time:" in context

def test_prompt_formatting_with_missing_placeholders():
    """Test formatting prompts with missing placeholders."""
    test_prompt = "Hello! No placeholders here."
    
    # Should not raise any errors
    formatted = format_prompt_with_context(test_prompt)
    assert formatted == test_prompt

def test_prompt_formatting_with_extra_placeholders():
    """Test formatting prompts with unexpected placeholders."""
    test_prompt = """
    Hello {name}!
    {context}
    {unknown_placeholder}
    """
    
    # Should raise KeyError for unknown placeholder
    with pytest.raises(KeyError):
        format_prompt_with_context(test_prompt)

"""
Tests for the prompt management system.
"""
import pytest
from pathlib import Path
import yaml
from typing import Dict

from config.prompts import (
    Prompts,
    PromptManager,
    get_prompt_manager
)

@pytest.fixture
def temp_prompts_file(tmp_path) -> Path:
    """Create a temporary prompts configuration file."""
    prompts_file = tmp_path / "prompts.yml"
    prompts = {
        "reasoning_prompt": "Test reasoning prompt",
        "execution_prompt": "Test execution prompt",
        "base_system_prompt": "Test base prompt"
    }
    with open(prompts_file, "w") as f:
        yaml.safe_dump(prompts, f)
    return prompts_file

def test_prompts_initialization():
    """Test basic Prompts class initialization."""
    prompts = Prompts(
        reasoning_prompt="Test reasoning",
        execution_prompt="Test execution",
        base_system_prompt="Test base"
    )
    
    assert prompts.reasoning_prompt == "Test reasoning"
    assert prompts.execution_prompt == "Test execution"
    assert prompts.base_system_prompt == "Test base"

def test_prompts_serialization():
    """Test serialization to and from dictionary."""
    original = Prompts(
        reasoning_prompt="Test reasoning",
        execution_prompt="Test execution",
        base_system_prompt="Test base"
    )
    
    # Convert to dictionary
    data = original.to_dict()
    
    # Create new instance from dictionary
    restored = Prompts.from_dict(data)
    
    assert restored.reasoning_prompt == original.reasoning_prompt
    assert restored.execution_prompt == original.execution_prompt
    assert restored.base_system_prompt == original.base_system_prompt

def test_prompt_manager_loading(temp_prompts_file: Path):
    """Test loading prompts from file."""
    manager = PromptManager()
    manager.load_prompts(temp_prompts_file)
    
    assert manager.reasoning_prompt == "Test reasoning prompt"
    assert manager.execution_prompt == "Test execution prompt"
    assert manager.base_system_prompt == "Test base prompt"

def test_prompt_manager_saving(tmp_path: Path):
    """Test saving prompts to file."""
    manager = PromptManager()
    prompts = Prompts(
        reasoning_prompt="Save test reasoning",
        execution_prompt="Save test execution",
        base_system_prompt="Save test base"
    )
    manager._prompts = prompts
    
    save_path = tmp_path / "saved_prompts.yml"
    manager.save_prompts(save_path)
    
    # Load saved file and verify
    with open(save_path) as f:
        data = yaml.safe_load(f)
        
    assert data["reasoning_prompt"] == "Save test reasoning"
    assert data["execution_prompt"] == "Save test execution"
    assert data["base_system_prompt"] == "Save test base"

def test_prompt_manager_default_prompts():
    """Test default prompts are loaded when no file is provided."""
    manager = PromptManager()
    manager.load_prompts()  # No file provided
    
    # Verify defaults are loaded
    assert manager.reasoning_prompt is not None
    assert manager.execution_prompt is not None
    assert manager.base_system_prompt is not None
    
    # Verify content
    assert "ROLE AND CAPABILITIES" in manager.reasoning_prompt
    assert "EXECUTION REQUIREMENTS" in manager.execution_prompt
    assert "terminal-based AI assistant" in manager.base_system_prompt

def test_singleton_pattern():
    """Test prompt manager singleton pattern."""
    manager1 = get_prompt_manager()
    manager2 = get_prompt_manager()
    
    assert manager1 is manager2  # Should be same instance

def test_prompt_manager_lazy_loading():
    """Test prompts are loaded lazily."""
    manager = PromptManager()
    assert manager._prompts is None  # Not loaded yet
    
    # Access a prompt to trigger loading
    _ = manager.reasoning_prompt
    assert manager._prompts is not None  # Now loaded

def test_invalid_prompts_file(tmp_path: Path):
    """Test handling of invalid prompts file."""
    invalid_file = tmp_path / "invalid.yml"
    invalid_file.write_text("invalid: yaml: content")
    
    manager = PromptManager()
    
    # Should fall back to defaults on invalid file
    manager.load_prompts(invalid_file)
    assert manager.reasoning_prompt is not None
    assert "ROLE AND CAPABILITIES" in manager.reasoning_prompt

def test_missing_prompts_file():
    """Test handling of missing prompts file."""
    manager = PromptManager()
    
    # Should load defaults for non-existent file
    manager.load_prompts(Path("nonexistent.yml"))
    assert manager.reasoning_prompt is not None
    assert manager.execution_prompt is not None
    assert manager.base_system_prompt is not None

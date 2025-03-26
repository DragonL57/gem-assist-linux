"""
Tests for the configuration management system.
"""
import pytest
from pathlib import Path
import os
from typing import Dict, Any

from config import Configuration, get_config, initialize_config
from config.settings import Settings
from config.schemas.safety import SafetyConfig, HarmCategory, ThresholdLevel
from config.schemas.theme import ThemeConfig, Theme

@pytest.fixture
def temp_env_file(tmp_path) -> Path:
    """Create a temporary environment file."""
    env_file = tmp_path / ".env"
    env_content = """
    ASSISTANT_MODEL=test-model
    ASSISTANT_NAME=TestBot
    ASSISTANT_TEMPERATURE=0.5
    ASSISTANT_DEBUG_MODE=true
    """
    env_file.write_text(env_content)
    return env_file

@pytest.fixture
def temp_safety_config(tmp_path) -> Path:
    """Create a temporary safety configuration file."""
    safety_file = tmp_path / "safety.yml"
    safety_config = {
        "safety_settings": [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_HIGH"
            }
        ]
    }
    import yaml
    with open(safety_file, "w") as f:
        yaml.safe_dump(safety_config, f)
    return safety_file

@pytest.fixture
def temp_theme_config(tmp_path) -> Path:
    """Create a temporary theme configuration file."""
    theme_file = tmp_path / "themes.yml"
    theme_config = {
        "test_theme": {
            "PRIMARY": "#000000",
            "SECONDARY": "#111111",
            "ACCENT": "#222222",
            "BACKGROUND": "#333333",
            "TEXT": "#ffffff"
        }
    }
    import yaml
    with open(theme_file, "w") as f:
        yaml.safe_dump(theme_config, f)
    return theme_file

def test_configuration_initialization(
    temp_env_file: Path,
    temp_safety_config: Path,
    temp_theme_config: Path
):
    """Test basic configuration initialization."""
    config = Configuration(
        env_file=str(temp_env_file),
        safety_config=temp_safety_config,
        theme_config=temp_theme_config
    )
    
    assert config.settings.MODEL == "test-model"
    assert config.settings.NAME == "TestBot"
    assert config.settings.TEMPERATURE == 0.5
    assert config.settings.DEBUG_MODE is True

def test_safety_settings_loading(temp_safety_config: Path):
    """Test loading safety settings from file."""
    config = Configuration(safety_config=temp_safety_config)
    settings = config.safety_settings
    
    assert len(settings) == 1
    assert settings[0]["category"] == "HARM_CATEGORY_HARASSMENT"
    assert settings[0]["threshold"] == "BLOCK_HIGH"

def test_theme_loading(temp_theme_config: Path):
    """Test loading theme configuration from file."""
    config = Configuration(theme_config=temp_theme_config)
    theme = config.get_theme("test_theme")
    
    assert theme["PRIMARY"] == "#000000"
    assert theme["TEXT"] == "#ffffff"
    assert "test_theme" in config.theme_names

def test_global_config_singleton():
    """Test global configuration singleton pattern."""
    config1 = get_config()
    config2 = get_config()
    assert config1 is config2

def test_configuration_reload(
    temp_env_file: Path,
    temp_safety_config: Path,
    temp_theme_config: Path
):
    """Test configuration reload functionality."""
    config = Configuration(
        env_file=str(temp_env_file),
        safety_config=temp_safety_config,
        theme_config=temp_theme_config
    )
    
    # Modify configurations
    with open(temp_env_file, "a") as f:
        f.write("ASSISTANT_NAME=UpdatedBot\n")
        
    config.reload()
    assert config.settings.NAME == "UpdatedBot"

def test_default_configurations():
    """Test default configuration values."""
    config = Configuration()
    
    # Check default safety settings
    safety = config.safety_settings
    assert any(s["category"] == "HARM_CATEGORY_HARASSMENT" for s in safety)
    
    # Check default theme
    theme = config.get_theme()
    assert all(k in theme for k in ["PRIMARY", "SECONDARY", "ACCENT", "BACKGROUND", "TEXT"])

def test_theme_validation():
    """Test theme color validation."""
    with pytest.raises(ValueError):
        Theme(
            primary="invalid",
            secondary="#123456",
            accent="#123456",
            background="#123456",
            text="#123456"
        ).validate_colors()

def test_safety_config_validation():
    """Test safety configuration validation."""
    settings = [
        {
            "category": "INVALID_CATEGORY",
            "threshold": "BLOCK_NONE"
        }
    ]
    with pytest.raises(ValueError):
        SafetyConfig.from_dict({"safety_settings": settings})

def test_configuration_environment_override(monkeypatch: pytest.MonkeyPatch):
    """Test environment variable overrides."""
    monkeypatch.setenv("ASSISTANT_MODEL", "env-test-model")
    monkeypatch.setenv("ASSISTANT_TEMPERATURE", "0.75")
    
    config = Configuration()
    assert config.settings.MODEL == "env-test-model"
    assert config.settings.TEMPERATURE == 0.75

def test_location_service_initialization(monkeypatch: pytest.MonkeyPatch):
    """Test location service initialization."""
    monkeypatch.setenv("ASSISTANT_LOCATION_TIMEOUT", "5")
    config = Configuration()
    
    assert config.location_service.settings.LOCATION_TIMEOUT == 5

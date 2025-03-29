"""
All project configuration will be saved here

Needs restart if anything is changed here.

This is a modular configuration system that manages:
- Environment-based settings
- Safety configurations
- Theme settings
- System prompts
- Location and system services
"""
from pathlib import Path
from typing import Optional, Dict, Any, List

from .settings import Settings, get_settings, initialize_settings
from .schemas.safety import get_safety_config, get_safety_settings, SafetyConfig
from .schemas.theme import get_theme_config, get_theme, get_theme_colors, ThemeConfig
from .services.location import get_location_service, LocationService
from .services.system import get_system_service, SystemService
from .services.context import format_prompt_with_context
from .prompts import get_prompt_manager, PromptManager

class Configuration:
    """Main configuration interface."""
    
    def __init__(
        self,
        env_file: Optional[str] = None,
        safety_config: Optional[Path] = None,
        theme_config: Optional[Path] = None,
        prompts_config: Optional[Path] = None
    ):
        """Initialize configuration system.
        
        Args:
            env_file: Optional path to environment file
            safety_config: Optional path to safety configuration
            theme_config: Optional path to theme configuration
        """
        # Initialize settings first as other components may depend on it
        initialize_settings(env_file)
        self.settings = get_settings()
        
        # Initialize other configuration components
        if safety_config:
            initialize_safety_config(safety_config)
        if theme_config:
            initialize_theme_config(theme_config)
            
        # Initialize configurations
        self.safety_config = get_safety_config()
        self.theme_config = get_theme_config()
        self.prompt_manager = get_prompt_manager()
        
        # Load any provided configurations
        if prompts_config:
            self.prompt_manager.load_prompts(prompts_config)
        
        # Initialize services
        self.location_service = get_location_service(
            self.settings.LOCATION_API_URL,
            self.settings.LOCATION_TIMEOUT
        )
        self.system_service = get_system_service()
    
    @property
    def safety_settings(self) -> List[Dict[str, str]]:
        """Get current safety settings."""
        return get_safety_settings()
    
    def get_theme(self, name: str = "default") -> Dict[str, str]:
        """Get theme colors by name."""
        return get_theme_colors(name)

    @property
    def execution_prompt(self) -> str:
        """Get execution system prompt."""
        return EXECUTION_SYSTEM_PROMPT
        
    @property
    def theme_names(self) -> List[str]:
        """Get list of available theme names."""
        return list(self.theme_config.themes.keys())
        
    def reload(self, prompts_config: Optional[Path] = None) -> None:
        """Reload all configuration from disk."""
        initialize_settings()
        self.settings = get_settings()
        self.safety_config = get_safety_config()
        self.theme_config = get_theme_config()
        if prompts_config:
            self.prompt_manager.load_prompts(prompts_config)
        self.location_service = get_location_service(self.settings)

# Global configuration instance
_config: Optional[Configuration] = None

def get_config() -> Configuration:
    """Get the global configuration instance.
    
    Returns:
        Configuration instance
    """
    global _config
    if _config is None:
        _config = Configuration()
    return _config

def initialize_config(
    env_file: Optional[str] = None,
    safety_config: Optional[Path] = None,
    theme_config: Optional[Path] = None
) -> None:
    """Initialize the global configuration.
    
    Args:
        env_file: Optional path to environment file
        safety_config: Optional path to safety configuration
        theme_config: Optional path to theme configuration
    """
    global _config
    _config = Configuration(env_file, safety_config, theme_config)

# NOTE: Backward compatibility variables removed (lines 126-164).
# Access configuration via get_config() or get_settings().
# Prompt formatting moved to main application entry point (main.py).

"""
Theme configuration management.
"""
from typing import Dict, Optional
from dataclasses import dataclass
from pathlib import Path
import yaml

@dataclass
class Theme:
    """Theme color configuration."""
    primary: str
    secondary: str
    accent: str
    background: str
    text: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert theme to dictionary.
        
        Returns:
            Dictionary of color values
        """
        return {
            "PRIMARY": self.primary,
            "SECONDARY": self.secondary,
            "ACCENT": self.accent,
            "BACKGROUND": self.background,
            "TEXT": self.text,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'Theme':
        """Create theme from dictionary.
        
        Args:
            data: Dictionary of color values
            
        Returns:
            Theme instance
        """
        return cls(
            primary=data["PRIMARY"],
            secondary=data["SECONDARY"],
            accent=data["ACCENT"],
            background=data["BACKGROUND"],
            text=data["TEXT"],
        )
    
    def validate_colors(self) -> None:
        """Validate all colors are valid hex codes.
        
        Raises:
            ValueError: If any color is invalid
        """
        for name, color in self.to_dict().items():
            if not color.startswith("#"):
                raise ValueError(f"Color {name} must start with #")
            if len(color) != 7:  # #RRGGBB format
                raise ValueError(f"Color {name} must be in #RRGGBB format")

class ThemeConfig:
    """Theme configuration manager."""
    
    def __init__(self, themes: Dict[str, Theme]):
        """Initialize theme configuration.
        
        Args:
            themes: Dictionary of named themes
        """
        self.themes = themes
        
    def to_dict(self) -> Dict[str, Dict[str, str]]:
        """Convert configuration to dictionary.
        
        Returns:
            Dictionary of theme configurations
        """
        return {
            name: theme.to_dict()
            for name, theme in self.themes.items()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Dict[str, str]]) -> 'ThemeConfig':
        """Create configuration from dictionary.
        
        Args:
            data: Dictionary of theme configurations
            
        Returns:
            ThemeConfig instance
        """
        themes = {
            name: Theme.from_dict(theme_data)
            for name, theme_data in data.items()
        }
        return cls(themes)
    
    def to_yaml(self, path: Path) -> None:
        """Save configuration to YAML file.
        
        Args:
            path: Path to save file
        """
        with open(path, 'w') as f:
            yaml.safe_dump(self.to_dict(), f)
    
    @classmethod
    def from_yaml(cls, path: Path) -> 'ThemeConfig':
        """Load configuration from YAML file.
        
        Args:
            path: Path to load file from
            
        Returns:
            ThemeConfig instance
        """
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)
    
    @classmethod
    def default(cls) -> 'ThemeConfig':
        """Create default theme configuration.
        
        Returns:
            ThemeConfig instance with default themes
        """
        return cls({
            "default": Theme(
                primary="#584ea8",
                secondary="#4a4464", 
                accent="#7c6f9f",
                background="#f5f5f5",
                text="#333333"
            ),
            "dark": Theme(
                primary="#7c6f9f",
                secondary="#4a4464",
                accent="#584ea8", 
                background="#1e1e1e",
                text="#ffffff"
            )
        })

# Global instance
_theme_config: Optional[ThemeConfig] = None

def get_theme_config() -> ThemeConfig:
    """Get the global theme configuration.
    
    Returns:
        ThemeConfig instance
    """
    global _theme_config
    if _theme_config is None:
        config_path = Path("config/themes.yml")
        if config_path.exists():
            _theme_config = ThemeConfig.from_yaml(config_path)
        else:
            _theme_config = ThemeConfig.default()
            _theme_config.to_yaml(config_path)
    return _theme_config

def initialize_theme_config(config_path: Optional[Path] = None) -> None:
    """Initialize theme configuration.
    
    Args:
        config_path: Optional path to configuration file
    """
    global _theme_config
    if config_path and config_path.exists():
        _theme_config = ThemeConfig.from_yaml(config_path)
    else:
        _theme_config = ThemeConfig.default()

def get_theme(name: str = "default") -> Theme:
    """Get a specific theme by name.
    
    Args:
        name: Theme name
        
    Returns:
        Theme instance
        
    Raises:
        KeyError: If theme doesn't exist
    """
    config = get_theme_config()
    return config.themes[name]

def get_theme_colors(name: str = "default") -> Dict[str, str]:
    """Get theme colors dictionary.
    
    Args:
        name: Theme name
        
    Returns:
        Dictionary of color values
    """
    theme = get_theme(name)
    return theme.to_dict()

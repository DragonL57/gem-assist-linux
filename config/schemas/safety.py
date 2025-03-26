"""
Safety settings schema and configuration management.
"""
from enum import Enum
from typing import List, Optional
from dataclasses import dataclass
from pathlib import Path
import yaml

class HarmCategory(str, Enum):
    """Categories of potential harm to monitor."""
    HARASSMENT = "HARM_CATEGORY_HARASSMENT"
    HATE_SPEECH = "HARM_CATEGORY_HATE_SPEECH"
    SEXUALLY_EXPLICIT = "HARM_CATEGORY_SEXUALLY_EXPLICIT"
    DANGEROUS_CONTENT = "HARM_CATEGORY_DANGEROUS_CONTENT"

class ThresholdLevel(str, Enum):
    """Threshold levels for content filtering."""
    BLOCK_NONE = "BLOCK_NONE"
    BLOCK_LOW = "BLOCK_LOW"
    BLOCK_MEDIUM = "BLOCK_MEDIUM"
    BLOCK_HIGH = "BLOCK_HIGH"

@dataclass
class SafetySetting:
    """Individual safety setting configuration."""
    category: HarmCategory
    threshold: ThresholdLevel

    def to_dict(self) -> dict:
        """Convert to dictionary format.
        
        Returns:
            Dictionary representation
        """
        return {
            "category": self.category,
            "threshold": self.threshold
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'SafetySetting':
        """Create from dictionary.
        
        Args:
            data: Dictionary data
            
        Returns:
            SafetySetting instance
        """
        return cls(
            category=HarmCategory(data["category"]),
            threshold=ThresholdLevel(data["threshold"])
        )

class SafetyConfig:
    """Safety configuration manager."""
    
    def __init__(self, settings: List[SafetySetting]):
        """Initialize safety configuration.
        
        Args:
            settings: List of safety settings
        """
        self.settings = settings

    def to_dict(self) -> dict:
        """Convert to dictionary format.
        
        Returns:
            Dictionary representation
        """
        return {
            "safety_settings": [
                setting.to_dict() for setting in self.settings
            ]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'SafetyConfig':
        """Create from dictionary.
        
        Args:
            data: Dictionary data
            
        Returns:
            SafetyConfig instance
        """
        settings = [
            SafetySetting.from_dict(setting)
            for setting in data["safety_settings"]
        ]
        return cls(settings)

    def to_yaml(self, path: Path) -> None:
        """Save configuration to YAML file.
        
        Args:
            path: Path to save file
        """
        with open(path, 'w') as f:
            yaml.safe_dump(self.to_dict(), f)

    @classmethod
    def from_yaml(cls, path: Path) -> 'SafetyConfig':
        """Load configuration from YAML file.
        
        Args:
            path: Path to load file from
            
        Returns:
            SafetyConfig instance
        """
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    @classmethod
    def default(cls) -> 'SafetyConfig':
        """Create default safety configuration.
        
        Returns:
            SafetyConfig instance with default settings
        """
        return cls([
            SafetySetting(
                category=HarmCategory.HARASSMENT,
                threshold=ThresholdLevel.BLOCK_NONE
            ),
            SafetySetting(
                category=HarmCategory.HATE_SPEECH,
                threshold=ThresholdLevel.BLOCK_NONE
            ),
            SafetySetting(
                category=HarmCategory.SEXUALLY_EXPLICIT,
                threshold=ThresholdLevel.BLOCK_NONE
            ),
            SafetySetting(
                category=HarmCategory.DANGEROUS_CONTENT,
                threshold=ThresholdLevel.BLOCK_NONE
            ),
        ])

# Global instance
_safety_config: SafetyConfig = None

def get_safety_config() -> SafetyConfig:
    """Get the global safety configuration.
    
    Returns:
        SafetyConfig instance
    """
    global _safety_config
    if _safety_config is None:
        config_path = Path("config/safety_settings.yml")
        if config_path.exists():
            _safety_config = SafetyConfig.from_yaml(config_path)
        else:
            _safety_config = SafetyConfig.default()
            _safety_config.to_yaml(config_path)
    return _safety_config
    
def initialize_safety_config(config_path: Optional[Path] = None) -> None:
    """Initialize safety configuration.
    
    Args:
        config_path: Optional path to configuration file
    """
    global _safety_config
    if config_path and config_path.exists():
        _safety_config = SafetyConfig.from_yaml(config_path)
    else:
        _safety_config = SafetyConfig.default()

def get_safety_settings() -> List[dict]:
    """Get safety settings in format needed by models.
    
    Returns:
        List of safety setting dictionaries
    """
    config = get_safety_config()
    return [setting.to_dict() for setting in config.settings]

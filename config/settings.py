"""
Core settings with Pydantic-based configuration management.
"""
from typing import Optional, Dict, Any
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field, validator

class Settings(BaseSettings):
    """Core application settings loaded from environment variables."""
    
    # Model settings
    MODEL: str = Field(
        default="gemini/gemini-2.0-flash",
        description="AI model identifier"
    )
    NAME: str = Field(
        default="Gemini",
        description="Assistant name"
    )
    TEMPERATURE: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Model temperature for response generation"
    )
    TOP_P: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Top p sampling parameter"
    )
    MAX_TOKENS: int = Field(
        default=8192,
        gt=0,
        description="Maximum tokens for model responses"
    )
    SEED: Optional[int] = Field(
        default=None,
        description="Random seed for reproducible responses"
    )

    # Operation settings
    DEBUG_MODE: bool = Field(
        default=False,
        description="Enable debug output"
    )
    CLEAR_TERMINAL: bool = Field(
        default=True,
        description="Clear terminal on startup"
    )
    TAKE_ONLY_ONE_MESSAGE: bool = Field(
        default=True,
        description="Process one message at a time"
    )
    PRINT_OS_ERROR: bool = Field(
        default=False,
        description="Print OS-level error messages"
    )

    # Search settings
    DUCKDUCKGO_TIMEOUT: int = Field(
        default=20,
        gt=0,
        description="DuckDuckGo search timeout in seconds"
    )
    MAX_DUCKDUCKGO_RESULTS: int = Field(
        default=4,
        gt=0,
        description="Maximum number of DuckDuckGo search results"
    )
    MAX_REDDIT_RESULTS: int = Field(
        default=5,
        gt=0,
        description="Maximum number of Reddit search results"
    )
    MAX_REDDIT_COMMENTS: int = Field(
        default=-1,
        description="Maximum number of Reddit comments to fetch (-1 for all)"
    )

    # Theme settings - will be moved to themes.yml
    THEME_LOCALS: Dict[str, str] = Field(
        default={
            "PRIMARY": "#584ea8",
            "SECONDARY": "#4a4464",
            "ACCENT": "#7c6f9f",
            "BACKGROUND": "#f5f5f5",
            "TEXT": "#333333",
        },
        description="Theme color configuration"
    )

    # Location service settings
    LOCATION_API_URL: str = Field(
        default="http://www.geoplugin.net/json.gp",
        description="Location service API URL"
    )
    LOCATION_TIMEOUT: int = Field(
        default=10,
        gt=0,
        description="Location service timeout in seconds"
    )

    class Config:
        """Pydantic configuration."""
        env_prefix = "ASSISTANT_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        validate_assignment = True
        extra = "ignore"

        @classmethod
        def customise_sources(
            cls,
            init_settings,
            env_settings,
            file_secret_settings,
        ):
            """Customize settings load order:
            1. Environment variables
            2. .env file
            3. Default values
            """
            return env_settings, file_secret_settings, init_settings

    @validator("THEME_LOCALS")
    def validate_theme_colors(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Validate theme color hex codes."""
        for key, color in v.items():
            if not color.startswith("#"):
                raise ValueError(f"Color {key} must start with #")
            if len(color) != 7:  # #RRGGBB format
                raise ValueError(f"Color {key} must be in #RRGGBB format")
        return v


# Create settings instance
settings = Settings()

def get_settings() -> Settings:
    """Get settings singleton instance.
    
    Returns:
        Settings instance
    """
    return settings

def initialize_settings(env_file: Optional[str] = None) -> None:
    """Initialize settings with optional environment file.
    
    Args:
        env_file: Optional path to environment file
    """
    global settings
    env_file = env_file or ".env"
    if Path(env_file).exists():
        settings = Settings(_env_file=env_file)
    else:
        settings = Settings()

# Backwards compatibility
MODEL = settings.MODEL
NAME = settings.NAME
TEMPERATURE = settings.TEMPERATURE
TOP_P = settings.TOP_P
MAX_TOKENS = settings.MAX_TOKENS
SEED = settings.SEED
DEBUG_MODE = settings.DEBUG_MODE
CLEAR_TERMINAL = settings.CLEAR_TERMINAL
CLEAR_BEFORE_START = CLEAR_TERMINAL  # For backward compatibility
TAKE_ONLY_ONE_MESSAGE = settings.TAKE_ONLY_ONE_MESSAGE
PRINT_OS_ERROR = settings.PRINT_OS_ERROR
THEME_LOCALS = settings.THEME_LOCALS

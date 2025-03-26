# Configuration System

The configuration system has been reorganized for better modularity and maintainability. All configuration is now managed through environment variables and YAML configuration files.

## Directory Structure

```
config/
├── __init__.py         # Main configuration interface
├── settings.py         # Environment-based settings
├── services/          
│   ├── location.py    # Location service
│   └── system.py      # System information service
└── schemas/           
    ├── safety.py      # Safety settings schema
    └── theme.py       # Theme configuration
```

## Environment Variables

All environment variables are prefixed with `ASSISTANT_`. See `.env.template` for all available options.

Example:
```bash
ASSISTANT_MODEL=gemini/gemini-2.0-flash
ASSISTANT_NAME=Gemini
ASSISTANT_TEMPERATURE=0.25
```

## Configuration Files

### Safety Settings
`config/safety_settings.yml`:
```yaml
safety_settings:
  - category: HARM_CATEGORY_HARASSMENT
    threshold: BLOCK_NONE
  # ... other safety settings
```

### Theme Configuration
`config/themes.yml`:
```yaml
default:
  PRIMARY: "#584ea8"
  SECONDARY: "#4a4464"
  # ... other theme colors

dark:
  PRIMARY: "#7c6f9f"
  # ... dark theme colors
```

## Usage Examples

### Basic Configuration
```python
from config import get_config

config = get_config()
model_name = config.settings.MODEL
theme_colors = config.get_theme("dark")
```

### Location Service
```python
from config.services.location import get_location_service

location_service = get_location_service()
location_info = await location_service.get_location()
print(location_info.formatted)
```

### System Information
```python
from config.services.system import get_system_service

system_service = get_system_service()
system_info = system_service.get_system_info()
print(system_info.formatted)
```

## Migration from Old Config

The old `config.py` has been replaced with a modular configuration system. All configuration is now accessed through the `config` package.

Old way:
```python
from config import MODEL, NAME, SAFETY_SETTINGS

print(MODEL)  # "gemini/gemini-2.0-flash"
```

New way:
```python
from config import get_config

config = get_config()
print(config.settings.MODEL)  # "gemini/gemini-2.0-flash"
```

Old global variables are still available through the `config` package for backwards compatibility, but it's recommended to use the new modular approach for new code.

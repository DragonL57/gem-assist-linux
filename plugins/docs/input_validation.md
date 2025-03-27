# Plugin Input Validation

This guide explains how to add input validation to your plugin tools.

## Overview

The plugin system includes built-in parameter validation capabilities. You can define validation rules for each parameter in your tool functions using the `params` argument of the `@tool` decorator.

## Basic Usage

Here's a simple example:

```python
@tool(
    params={
        "name": {
            "type": str,
            "required": True,
            "regex": r"^\w+$"
        },
        "age": {
            "type": int,
            "range": {"min": 0, "max": 150}
        }
    }
)
def create_user(name: str, age: int) -> None:
    # The parameters will be validated before this function is called
    pass
```

## Validation Options

### Type Validation
- `type`: Python type to validate against (str, int, float, etc.)
- Automatically inferred from type hints if not specified
- Required for parameters without type hints

```python
"param_name": {
    "type": str  # or int, float, bool, etc.
}
```

### Required/Optional
- `required`: Boolean indicating if parameter is required
- Defaults to True for parameters without default values
- Defaults to False for parameters with default values

```python
"param_name": {
    "type": str,
    "required": False  # Parameter is optional
}
```

### Regular Expressions
- `regex`: String pattern to validate against
- Only applies to string parameters

```python
"filename": {
    "type": str,
    "regex": r"^[\w-]+\.[a-z]+$"  # Validate filename format
}
```

### Numeric Ranges
- `range`: Dictionary with min/max values
- Applies to numeric parameters (int, float)

```python
"count": {
    "type": int,
    "range": {
        "min": 1,
        "max": 100
    }
}
```

### Allowed Values
- `allowed_values`: List of valid values
- Useful for enums or fixed choices

```python
"log_level": {
    "type": str,
    "allowed_values": ["DEBUG", "INFO", "WARNING", "ERROR"]
}
```

### Custom Validation
- `custom`: Dictionary with validator function and error message
- Most flexible option for complex validation

```python
"directory": {
    "type": str,
    "custom": {
        "validator": lambda x: os.path.exists(x),
        "message": "Directory must exist"
    }
}
```

## Example Plugin

Here's a complete example showing various validation rules:

```python
from plugins import Plugin, tool

class ExamplePlugin(Plugin):
    @tool(
        params={
            "filename": {
                "type": str,
                "required": True,
                "regex": r"^[\w-]+\.[a-z]+$",
                "custom": {
                    "validator": lambda x: not os.path.exists(x),
                    "message": "File already exists"
                }
            },
            "mode": {
                "type": str,
                "required": False,
                "allowed_values": ["r", "w", "a"]
            },
            "buffer_size": {
                "type": int,
                "range": {
                    "min": 1024,
                    "max": 8192
                }
            }
        }
    )
    def open_file(filename: str, mode: str = "r", buffer_size: int = 4096):
        # All parameters are validated before reaching here
        pass
```

## Error Handling

Validation errors are raised as `PluginError` exceptions with clear error messages:

```python
try:
    plugin.open_file("invalid/file.txt", mode="x", buffer_size=0)
except PluginError as e:
    print(e)  # Will show which parameter failed and why
```

## Best Practices

1. Always validate critical parameters that could cause errors
2. Use type hints - they're automatically used for type validation
3. Combine multiple validators when needed
4. Provide clear error messages in custom validators
5. Keep validation rules simple and focused
6. Document validation requirements in function docstrings

## Common Validation Patterns

### File System Operations
```python
"path": {
    "type": str,
    "custom": {
        "validator": lambda x: os.path.exists(x),
        "message": "Path must exist"
    }
}
```

### Network Operations
```python
"url": {
    "type": str,
    "regex": r"^https?://[\w\-\.]+"
}
```

### Configuration Values
```python
"settings": {
    "type": dict,
    "custom": {
        "validator": lambda x: all(required in x for required in ["host", "port"]),
    "message": "Settings must include host and port"
    }
}
```

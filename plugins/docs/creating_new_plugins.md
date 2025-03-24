# Creating New Plugins for GEM-Assist

This guide explains how to create new plugins and tools for the GEM-Assist system.

## Overview

GEM-Assist uses a plugin architecture to organize related tools. This makes the codebase more maintainable and allows for easy extension of functionality. Plugins are automatically discovered and registered at runtime.

## Creating a Basic Plugin

Here's how to create a simple plugin with a single tool:

### Step 1: Create a New Plugin File

Create a new Python file in the `/plugins` directory. Name it according to its purpose (e.g., `image_plugin.py` for image-related tools).

```python
"""
Image plugin providing image processing capabilities.
"""
from typing import Dict, Any, List, Optional
import os

from plugins import Plugin, tool, capability
from core_utils import tool_message_print, tool_report_print

class ImagePlugin(Plugin):
    """Plugin providing image processing capabilities."""
    
    @staticmethod
    @tool(
        categories=["image", "metadata"],
        requires_filesystem=True
    )
    def get_image_metadata(file_path: str) -> Dict[str, Any]:
        """
        Get metadata for an image file.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Dictionary containing image metadata
        """
        tool_message_print(f"Getting metadata for image: {file_path}")
        
        try:
            # Your implementation here
            result = {
                "file_path": file_path,
                "size_kb": os.path.getsize(file_path) / 1024,
                "format": os.path.splitext(file_path)[1][1:].lower()
            }
            
            # Report completion
            tool_report_print(f"Retrieved metadata for image: {os.path.basename(file_path)}")
            
            return result
            
        except Exception as e:
            return {"error": str(e), "file_path": file_path}
```

### Step 2: Plugin Structure

Every plugin should follow these principles:

1. **Import the necessary modules**: Always import `Plugin`, `tool`, and `capability` from `plugins`.
2. **Create a class that inherits from `Plugin`**: Name the class descriptively.
3. **Add docstrings**: Provide a clear description of your plugin and each tool.
4. **Define static methods decorated with `@tool`**: Each method becomes a tool available to the assistant.
5. **Use type hints**: Always specify parameter and return types.

## Tool Decorators and Capabilities

The `@tool` decorator registers a function as a tool and can include capability metadata:

```python
@tool(
    categories=["category1", "category2"],
    requires_network=True,
    requires_filesystem=True,
    rate_limited=True,
    example_usage="example_function('parameter')"
)
def example_function(parameter: str) -> Dict[str, Any]:
    """Function documentation here."""
    # Implementation
```

### Available Capability Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `categories` | List[str] | Categories this tool belongs to |
| `requires_network` | bool | Whether tool needs internet access |
| `requires_filesystem` | bool | Whether tool needs filesystem access |
| `rate_limited` | bool | Whether tool is subject to rate limits |
| `example_usage` | str | Example of how to use the tool |
| `version` | str | Tool version |
| `author` | str | Tool author |

## Function Structure Best Practices

For consistent tool behavior:

1. **Begin with `tool_message_print`**: Display what the tool is doing
2. **Use try/except**: Handle exceptions gracefully
3. **Report completion with `tool_report_print`**: Display the result summary
4. **Return structured data**: Prefer dictionaries with clear field names

```python
@staticmethod
@tool(categories=["example"])
def example_tool(parameter: str) -> Dict[str, Any]:
    """Tool description."""
    tool_message_print(f"Processing {parameter}")
    
    try:
        # Implementation
        result = {"key": "value"}
        
        tool_report_print(f"Completed processing {parameter}")
        return result
        
    except Exception as e:
        return {"error": str(e)}
```

## Adding Multiple Tools to a Plugin

A plugin can contain multiple related tools. Just add more methods to your plugin class:

```python
class ImagePlugin(Plugin):
    """Plugin providing image processing capabilities."""
    
    @staticmethod
    @tool(categories=["image", "metadata"])
    def get_image_metadata(file_path: str) -> Dict[str, Any]:
        """Get metadata for an image file."""
        # Implementation...
    
    @staticmethod
    @tool(categories=["image", "conversion"])
    def convert_image_format(file_path: str, target_format: str) -> Dict[str, Any]:
        """Convert image to a different format."""
        # Implementation...
    
    @staticmethod
    @tool(categories=["image", "processing"])
    def resize_image(file_path: str, width: int, height: int) -> Dict[str, Any]:
        """Resize an image to specified dimensions."""
        # Implementation...
```

## Using Dependencies

If your tool requires external libraries:

1. **Add imports inside the method**: This prevents errors if the dependency is missing
2. **Handle ImportError**: Return a helpful message suggesting how to install the dependency

```python
@staticmethod
@tool(categories=["image", "processing"])
def process_with_pillow(file_path: str) -> Dict[str, Any]:
    """Process image using Pillow."""
    tool_message_print(f"Processing image: {file_path}")
    
    try:
        try:
            from PIL import Image
        except ImportError:
            return {"error": "Pillow is required. Install with 'pip install Pillow'"}
        
        # Implementation using Pillow
        # ...
        
        return result
        
    except Exception as e:
        return {"error": str(e), "file_path": file_path}
```

## Testing Your Plugin

To test your plugin:

1. Place your plugin file in the `/plugins` directory
2. Run GEM-Assist: `uv run main.py`
3. Use the `/find_tools` command to verify your tool is registered
4. Test your tool by asking the assistant to use it

## Troubleshooting

If your plugin isn't being recognized:

1. Check for syntax errors in your plugin file
2. Ensure your plugin class inherits from `Plugin`
3. Verify all methods you want to expose are decorated with `@tool`
4. Check the console for any plugin loading errors
5. Check for circular imports in your plugin

## Advanced: Custom Registration

For specialized registration needs, you can override the `register` class method:

```python
@classmethod
def register(cls):
    """Custom registration logic."""
    # Your custom registration logic here
    # For example, conditionally registering tools based on environment
    
    # You can still use the default registration by calling super()
    super().register()
```

## Example: Complete Plugin

Here's a complete example of a calculator plugin:

```python
"""
Calculator plugin providing mathematical operations.
"""
from typing import Dict, Any, Union, List
import math

from plugins import Plugin, tool, capability
from core_utils import tool_message_print, tool_report_print

class CalculatorPlugin(Plugin):
    """Plugin providing calculator functionality."""
    
    @staticmethod
    @tool(
        categories=["math", "calculation"],
        example_usage="basic_calculator(2, '+', 3)"
    )
    def basic_calculator(a: Union[int, float], operation: str, b: Union[int, float]) -> Dict[str, Any]:
        """
        Perform a basic calculation between two numbers.
        
        Args:
            a: First number
            operation: One of '+', '-', '*', '/', '^', 'root'
            b: Second number
            
        Returns:
            Dictionary with calculation result
        """
        tool_message_print(f"Calculating: {a} {operation} {b}")
        
        try:
            result = None
            
            if operation == '+':
                result = a + b
            elif operation == '-':
                result = a - b
            elif operation == '*':
                result = a * b
            elif operation == '/':
                if b == 0:
                    return {"error": "Division by zero"}
                result = a / b
            elif operation == '^' or operation == '**':
                result = a ** b
            elif operation == 'root':
                result = a ** (1/b)
            else:
                return {"error": f"Unknown operation: {operation}"}
                
            tool_report_print(f"Result: {result}")
            
            return {
                "result": result,
                "operation": f"{a} {operation} {b}",
                "success": True
            }
            
        except Exception as e:
            return {"error": str(e), "success": False}
    
    @staticmethod
    @tool(
        categories=["math", "statistics"]
    )
    def calculate_statistics(numbers: List[float]) -> Dict[str, float]:
        """
        Calculate basic statistics for a list of numbers.
        
        Args:
            numbers: List of numbers to analyze
            
        Returns:
            Dictionary with statistical measures
        """
        tool_message_print(f"Calculating statistics for {len(numbers)} numbers")
        
        try:
            if not numbers:
                return {"error": "Empty list provided"}
                
            count = len(numbers)
            total = sum(numbers)
            mean = total / count
            
            # Calculate median
            sorted_nums = sorted(numbers)
            mid = count // 2
            if count % 2 == 0:
                median = (sorted_nums[mid-1] + sorted_nums[mid]) / 2
            else:
                median = sorted_nums[mid]
                
            # Calculate variance and standard deviation
            variance = sum((x - mean) ** 2 for x in numbers) / count
            std_dev = math.sqrt(variance)
            
            # Get min and max
            minimum = min(numbers)
            maximum = max(numbers)
            
            tool_report_print(f"Calculated statistics: mean={mean:.2f}, min={minimum}, max={maximum}")
            
            return {
                "count": count,
                "sum": total,
                "mean": mean,
                "median": median,
                "variance": variance,
                "std_deviation": std_dev,
                "min": minimum,
                "max": maximum,
                "range": maximum - minimum
            }
            
        except Exception as e:
            return {"error": str(e)}
```

## Conclusion

By following these guidelines, you can create well-structured plugins that integrate seamlessly with GEM-Assist. Remember to maintain consistency with the existing codebase and provide proper documentation for your tools.

For more examples, examine the existing plugins in the `/plugins` directory.

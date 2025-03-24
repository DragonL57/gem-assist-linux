"""
Type conversion utilities for the assistant.
"""
import inspect
from typing import Any, get_origin, get_args, Union, List, Dict, Tuple, Set
from pydantic import BaseModel

class TypeConverter:
    """Handles type conversion for tool arguments."""
    
    def convert_to_pydantic_model(self, annotation: Any, arg_value: Any) -> Any:
        """
        Convert a value to the appropriate type based on the type annotation.
        Handles complex types including Pydantic models, lists, dictionaries, etc.
        """
        if annotation is None or annotation == inspect.Parameter.empty:
            return arg_value

        # If annotation is a Pydantic model
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return annotation.parse_obj(arg_value) if isinstance(arg_value, dict) else arg_value

        # Handle standard types
        if annotation in (str, int, float, bool):
            try:
                return annotation(arg_value)
            except (ValueError, TypeError):
                return arg_value

        # Handle generic types from typing module
        origin = get_origin(annotation)
        args = get_args(annotation)

        if origin:
            if origin is list or origin is List:
                # Convert list elements
                if not isinstance(arg_value, list):
                    return arg_value  # Can't convert non-list to list
                if not args:
                    return arg_value  # No type info for elements
                return [self.convert_to_pydantic_model(args[0], item) for item in arg_value]
                
            elif origin is dict or origin is Dict:
                # Convert dictionary values
                if not isinstance(arg_value, dict):
                    return arg_value  # Can't convert non-dict
                if len(args) < 2:
                    return arg_value  # Insufficient type info
                return {
                    key: self.convert_to_pydantic_model(args[1], val) 
                    for key, val in arg_value.items()
                }
                
            elif origin is Union:
                # Try each possible type
                for arg_type in args:
                    try:
                        return self.convert_to_pydantic_model(arg_type, arg_value)
                    except (ValueError, TypeError):
                        continue
                raise ValueError(f"Could not convert {arg_value} to any type in {args}")
                
            elif origin is tuple or origin is Tuple:
                return tuple(
                    self.convert_to_pydantic_model(args[i], arg_value[i])
                    for i in range(len(args))
                )
                
            elif origin is set or origin is Set:
                return {
                    self.convert_to_pydantic_model(args[0], item) for item in arg_value
                }
                
        return arg_value

"""
This package provides functionality to convert Python functions into JSON schemas,
primarily for use with Large Language Models (LLMs) that support function calling.

It leverages type hints, docstrings, and function signatures to automatically
generate a JSON schema representing the function's parameters, descriptions, and
other relevant information. This allows LLMs to understand the function's
purpose and how to call it correctly.
"""

import inspect
from types import UnionType
from typing import Any, Dict, get_type_hints, get_origin, get_args, Literal, Callable, Optional, Union
import docstring_parser
from pydantic import BaseModel
import warnings
import re

from .vertex_compatibility import clean_schema_for_vertex

def function_to_json_schema(func: Callable, vertex_compatible: bool = True) -> Dict[str, Any]:
    """
    Convert a Python function to a JSON schema compatible with OpenAI's function calling API.
    
    Args:
        func: The function to convert
        vertex_compatible: Whether to make the schema compatible with Vertex AI (default: True)
        
    Returns:
        A JSON schema representation of the function
    """
    sig = inspect.signature(func)
    
    # Get function name
    function_name = func.__name__
    # Get documentation
    docstring = docstring_parser.parse(inspect.getdoc(func) or "")
    doc_str_desc = docstring.short_description or ""
    if docstring.long_description:
        doc_str_desc += " " + docstring.long_description

    doc_str_desc = re.sub(r'\s+', ' ', doc_str_desc).strip()

    # Process function parameters
    parameters = {}
    required_params = []
    type_hints = get_type_hints(func)
    
    # Process docstring parameter descriptions
    param_descriptions = {param.arg_name: param.description for param in docstring.params}
    
    for param_name, param in sig.parameters.items():
        if param_name == 'self':  # Skip 'self' in methods
            continue
        
        # Get parameter annotation if available, otherwise use Any
        has_annotation = True  # Track if we have a real annotation or using Any as fallback
        if param_name in type_hints:
            type_annotation = type_hints[param_name]
        elif param.annotation != inspect.Parameter.empty:
            type_annotation = param.annotation
        else:
            type_annotation = Any
            has_annotation = False  # Mark that we're using Any as a fallback

        # Check if parameter is required
        if param.default == inspect.Parameter.empty:
            required_params.append(param_name)
        
        # Convert Python type to JSON schema type
        param_schema = type_hint_to_json_schema(type_annotation) if has_annotation else {}
        
        # Add documentation if available
        if param_name in param_descriptions and param_descriptions[param_name]:
            param_schema["description"] = param_descriptions[param_name].strip()
        
        # Only add default type for explicitly annotated parameters
        if has_annotation:
            # Ensure type is always specified (explicit empty dict case)
            if not param_schema:
                param_schema = {"type": "object"}
            elif "type" not in param_schema and not any(x in param_schema for x in ["oneOf", "anyOf", "allOf"]):
                # Default to object if no type is specified and no composition keywords
                param_schema["type"] = "object"
        
        parameters[param_name] = param_schema

    json_schema = {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": doc_str_desc or "",
        }
    }

    if parameters:
        json_schema["function"]["parameters"] = {}
        json_schema["function"]["parameters"]["type"] = "object"
        json_schema["function"]["parameters"]["properties"] = parameters
        json_schema["function"]["parameters"]["required"] = required_params if required_params else []
    
    if docstring.returns and docstring.returns.description:
        json_schema["function"]["returns"] = {
            "description": docstring.returns.description
        }
    
    # Fix any empty object properties
    _fix_empty_object_properties(json_schema["function"].get("parameters", {}))
    
    # Optionally clean the schema for Vertex AI compatibility
    if vertex_compatible:
        json_schema = clean_schema_for_vertex(json_schema)
        
    return json_schema

def _fix_empty_object_properties(schema):
    """Recursively fix empty object properties by adding a default type."""
    if not isinstance(schema, dict):
        return
    
    # Add type to schema itself if missing
    if "properties" in schema and "type" not in schema:
        schema["type"] = "object"
    
    # Process all properties recursively
    if "properties" in schema and isinstance(schema["properties"], dict):
        for prop_name, prop_schema in schema["properties"].items():
            # Skip completely empty dictionaries - we want to keep those as {}
            if prop_schema == {}:
                continue
                
            if isinstance(prop_schema, dict):
                # Only add default type if there's content but no type
                if prop_schema and "type" not in prop_schema and not any(key in prop_schema for key in ["oneOf", "anyOf", "allOf"]):
                    prop_schema["type"] = "object"
                
                # Recursively fix nested properties
                _fix_empty_object_properties(prop_schema)

def type_hint_to_json_schema(type_hint) -> Dict[str, Any]:
    """Convert Python type hints to JSON schema types."""
    # Handle None type
    if type_hint is type(None):
        return {"type": "null"}
    
    # Handle primitive types
    elif type_hint is str:
        return {"type": "string"}
    elif type_hint is int:
        return {"type": "integer"}
    elif type_hint is float:
        return {"type": "number"}
    elif type_hint is bool:
        return {"type": "boolean"}
    elif type_hint is list or type_hint is tuple:
        return {"type": "array"}
    elif type_hint is dict:
        return {"type": "object"}
    
    # Handle typing.Literal
    elif getattr(type_hint, "__origin__", None) is Literal:
        total_types = set()
        for arg in type_hint.__args__:
            if isinstance(arg, (str, int, float, bool)):
                python_type = type(arg).__name__
                # Map Python types to JSON schema types
                if python_type == 'str':
                    total_types.add('string')
                elif python_type == 'int':
                    total_types.add('integer')
                elif python_type == 'float':
                    total_types.add('number')
                elif python_type == 'bool':
                    total_types.add('boolean')
        
        # If all values are of the same type, use "type" and "enum"
        if len(total_types) == 1:
            return {"type": list(total_types)[0], "enum": list(type_hint.__args__)}
        # Otherwise, use oneOf
        return {"oneOf": [{"type": t, "enum": [v for v in type_hint.__args__ if type(v).__name__ == t]} 
                          for t in total_types]}
    
    # Handle Optional and Union types
    elif get_origin(type_hint) is Union or get_origin(type_hint) is UnionType or isinstance(type_hint, UnionType):
        args = get_args(type_hint)
        
        # Handle Optional[T] (which is Union[T, None])
        if type(None) in args:
            non_none_args = [arg for arg in args if arg is not type(None)]  # noqa: E721
            if len(non_none_args) == 1:
                # Optional[T] case - Use nullable instead of array type
                schema = type_hint_to_json_schema(non_none_args[0])
                # Use nullable: true instead of type: ["string", "null"]
                schema["nullable"] = True
                return schema
            
            # Handle Union[T1, T2, None] case - add oneOf entries
            schemas = [type_hint_to_json_schema(arg) for arg in non_none_args]
            return {"oneOf": schemas, "nullable": True}
        
        # Handle regular Union types with oneOf
        schemas = [type_hint_to_json_schema(arg) for arg in args]
        return {"oneOf": schemas}
    
    # Handle collections.abc.Sequence and List[T]
    elif get_origin(type_hint) is list:
        args = get_args(type_hint)
        if args:
            item_schema = type_hint_to_json_schema(args[0])
            return {"type": "array", "items": item_schema}
        else:
            return {"type": "array"}
    
    # Handle Dict[K, V]
    elif get_origin(type_hint) is dict:
        args = get_args(type_hint)
        key_type, val_type = args if len(args) == 2 else (Any, Any)
        
        # Only string keys are supported in JSON
        if key_type is not str:
            warnings.warn(f"Dict keys should be strings for JSON serialization, got {key_type}", UserWarning)
        
        # For Vertex AI compatibility, we need to provide properties
        result = {"type": "object"}
        
        # Add properties with a default "_any" key for Vertex AI compatibility
        result["properties"] = {"_any": {"type": "string", "description": "Any dictionary property"}}
        
        # Add additionalProperties if we have value type info
        if val_type is not Any:
            val_schema = type_hint_to_json_schema(val_type)
            result["additionalProperties"] = val_schema
        
        return result
    
    # Handle tuple
    elif get_origin(type_hint) is tuple:
        args = get_args(type_hint)
        if not args:
            return {"type": "array"}
        
        # Handle Tuple[T, ...] (variable-length homogeneous tuple)
        if len(args) == 2 and args[1] == ...:
            return {
                "type": "array",
                "items": type_hint_to_json_schema(args[0])
            }
        
        # Handle fixed-length heterogeneous tuple
        return {
            "type": "array",
            "prefixItems": [type_hint_to_json_schema(arg) for arg in args],
            "minItems": len(args),
            "maxItems": len(args)
        }
    
    # Handle Optional[T]
    elif get_origin(type_hint) is Optional:
        args = get_args(type_hint)
        if args:
            base_schema = type_hint_to_json_schema(args[0])
            # Add nullable: true instead of type: ["string", "null"]
            base_schema["nullable"] = True
            return base_schema
    
    # Handle Pydantic models
    elif isinstance(type_hint, type) and issubclass(type_hint, BaseModel):
        schema = type_hint.model_json_schema()
        # Clean up schema for better integration
        if 'title' in schema:
            del schema['title']
        if "properties" in schema:
            for _, prop_schema in schema["properties"].items():
                if "title" in prop_schema:
                    del prop_schema["title"]
        return schema
    
    # Handle Any
    elif type_hint is Any:
        # For Any, we don't specify a type to allow any value
        # But we should add a default type for API compatibility
        return {"type": "object"}
    
    # Handle unsupported types with a warning
    warnings.warn(f"Unsupported type hint: {type_hint}. Treating as Any.", UserWarning)
    return {"type": "object"}


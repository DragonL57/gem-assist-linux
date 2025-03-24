"""
Utilities to make function schemas compatible with Vertex AI requirements.
"""
from typing import Dict, Any


def clean_schema_for_vertex(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean a function schema to make it compatible with Vertex AI.
    
    Removes unsupported fields like 'additionalProperties' and ensures
    object types have non-empty properties.
    
    Args:
        schema: The original function schema
        
    Returns:
        Cleaned function schema compatible with Vertex AI
    """
    if not isinstance(schema, dict):
        return schema
    
    result = {}
    for key, value in schema.items():
        # Skip additionalProperties field which Vertex AI doesn't support
        if key == 'additionalProperties':
            continue
            
        # Recursively clean nested dictionaries
        elif isinstance(value, dict):
            result[key] = clean_schema_for_vertex(value)
            
        # Clean items in lists/arrays
        elif isinstance(value, list):
            result[key] = [
                clean_schema_for_vertex(item) if isinstance(item, dict) else item 
                for item in value
            ]
        else:
            result[key] = value
    
    # Handle object types with missing properties
    if "type" in result and result["type"] == "object" and "properties" not in result:
        result["properties"] = {"_any": {"type": "string", "description": "Any property"}}
    
    # Ensure property objects have non-empty properties field
    if "properties" in result:
        for prop_name, prop_schema in result["properties"].items():
            if isinstance(prop_schema, dict) and prop_schema.get("type") == "object" and "properties" not in prop_schema:
                # Add a default property for object types
                result["properties"][prop_name]["properties"] = {
                    "_any": {"type": "string", "description": "Any property"}
                }
    
    return result

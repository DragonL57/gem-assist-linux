"""
Input validation framework for plugin tools.
"""
from typing import Any, List, Type, Dict, Optional, Union, Callable
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

class ValidationError(Exception):
    """Raised when parameter validation fails."""
    def __init__(self, message: str, param_name: str):
        self.param_name = param_name
        super().__init__(f"Parameter '{param_name}': {message}")

class Validator(ABC):
    """Base class for parameter validators."""
    
    @abstractmethod
    def validate(self, value: Any, param_name: str) -> None:
        """
        Validate a parameter value.
        
        Args:
            value: Value to validate
            param_name: Name of parameter being validated
            
        Raises:
            ValidationError: If validation fails
        """
        pass

class TypeValidator(Validator):
    """Validates parameter type."""
    
    def __init__(self, expected_type: Union[Type, tuple[Type, ...]]):
        self.expected_type = expected_type
        
    def validate(self, value: Any, param_name: str) -> None:
        if not isinstance(value, self.expected_type):
            raise ValidationError(
                f"Expected type {self.expected_type.__name__}, got {type(value).__name__}",
                param_name
            )

class RangeValidator(Validator):
    """Validates numeric range."""
    
    def __init__(self, min_value: Optional[float] = None, max_value: Optional[float] = None):
        self.min_value = min_value
        self.max_value = max_value
        
    def validate(self, value: Any, param_name: str) -> None:
        if not isinstance(value, (int, float)):
            raise ValidationError("Value must be numeric", param_name)
            
        if self.min_value is not None and value < self.min_value:
            raise ValidationError(f"Value must be >= {self.min_value}", param_name)
            
        if self.max_value is not None and value > self.max_value:
            raise ValidationError(f"Value must be <= {self.max_value}", param_name)

class RegexValidator(Validator):
    """Validates string pattern."""
    
    def __init__(self, pattern: str):
        self.pattern = pattern
        self.regex = re.compile(pattern)
        
    def validate(self, value: Any, param_name: str) -> None:
        if not isinstance(value, str):
            raise ValidationError("Value must be a string", param_name)
            
        if not self.regex.match(value):
            raise ValidationError(f"Value must match pattern: {self.pattern}", param_name)

class EnumValidator(Validator):
    """Validates value is one of allowed choices."""
    
    def __init__(self, allowed_values: List[Any]):
        self.allowed_values = allowed_values
        
    def validate(self, value: Any, param_name: str) -> None:
        if value not in self.allowed_values:
            raise ValidationError(
                f"Value must be one of: {', '.join(str(v) for v in self.allowed_values)}",
                param_name
            )

class CustomValidator(Validator):
    """Validator using custom validation function."""
    
    def __init__(self, func: Callable[[Any], bool], error_message: str):
        self.func = func
        self.error_message = error_message
        
    def validate(self, value: Any, param_name: str) -> None:
        if not self.func(value):
            raise ValidationError(self.error_message, param_name)

@dataclass
class ParameterSpec:
    """Parameter specification with validation rules."""
    name: str
    type: Type
    required: bool = True
    validators: List[Validator] = None
    
    def __post_init__(self):
        if self.validators is None:
            self.validators = []
        # Always include type validation
        self.validators.insert(0, TypeValidator(self.type))
    
    def validate(self, value: Any) -> None:
        """
        Validate a parameter value against all validators.
        
        Args:
            value: Value to validate
            
        Raises:
            ValidationError: If validation fails
        """
        # Handle optional parameters
        if not self.required and value is None:
            return
            
        for validator in self.validators:
            validator.validate(value, self.name)

def create_parameter_spec(name: str, spec: Dict[str, Any]) -> ParameterSpec:
    """
    Create a ParameterSpec from a specification dictionary.
    
    Args:
        name: Parameter name
        spec: Specification dictionary
        
    Returns:
        ParameterSpec instance
        
    Example spec:
        {
            "type": str,
            "required": True,
            "regex": r"^\w+$",
            "allowed_values": ["a", "b", "c"],
            "range": {"min": 0, "max": 100},
            "custom": {
                "validator": lambda x: x > 0,
                "message": "Value must be positive"
            }
        }
    """
    validators = []
    
    if "regex" in spec:
        validators.append(RegexValidator(spec["regex"]))
        
    if "allowed_values" in spec:
        validators.append(EnumValidator(spec["allowed_values"]))
        
    if "range" in spec:
        range_spec = spec["range"]
        validators.append(RangeValidator(
            range_spec.get("min"),
            range_spec.get("max")
        ))
        
    if "custom" in spec:
        custom = spec["custom"]
        validators.append(CustomValidator(
            custom["validator"],
            custom["message"]
        ))
    
    return ParameterSpec(
        name=name,
        type=spec["type"],
        required=spec.get("required", True),
        validators=validators
    )

"""
Template Parameter Validator

Validates user-provided parameters against template parameter definitions.
"""

import re
import json
from typing import Dict, List, Any, Tuple, Optional
from urllib.parse import urlparse


class ParameterValidationError(Exception):
    """Raised when parameter validation fails"""
    pass


class TemplateValidator:
    """Validates parameters for a template"""

    def __init__(self, template):
        """
        Initialize validator with a template

        Args:
            template: Template object from TemplateLoader
        """
        self.template = template

    def validate(self, params: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate all parameters

        Args:
            params: Dictionary of parameter values

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check all required parameters are provided
        for param_def in self.template.parameters:
            param_name = param_def['name']
            is_required = param_def.get('required', False)

            if is_required and param_name not in params:
                errors.append(
                    f"Missing required parameter: {param_name}"
                )

        # Validate each provided parameter
        for param_name, param_value in params.items():
            # Get parameter definition
            param_def = self.template.get_parameter(param_name)

            if param_def is None:
                errors.append(
                    f"Unknown parameter: {param_name}"
                )
                continue

            # Validate the parameter
            param_errors = self._validate_parameter(
                param_name, param_value, param_def
            )
            errors.extend(param_errors)

        return (len(errors) == 0, errors)

    def _validate_parameter(
        self,
        param_name: str,
        value: Any,
        param_def: Dict
    ) -> List[str]:
        """Validate a single parameter"""
        errors = []
        param_type = param_def.get('type', 'string')

        # Type validation
        if param_type == 'string':
            errors.extend(self._validate_string(param_name, value, param_def))
        elif param_type == 'integer':
            errors.extend(self._validate_integer(param_name, value, param_def))
        elif param_type == 'float':
            errors.extend(self._validate_float(param_name, value, param_def))
        elif param_type == 'boolean':
            errors.extend(self._validate_boolean(param_name, value, param_def))
        elif param_type == 'choice':
            errors.extend(self._validate_choice(param_name, value, param_def))
        elif param_type == 'json':
            errors.extend(self._validate_json(param_name, value, param_def))
        elif param_type == 'url':
            errors.extend(self._validate_url(param_name, value, param_def))
        elif param_type == 'email':
            errors.extend(self._validate_email(param_name, value, param_def))
        elif param_type == 'path':
            errors.extend(self._validate_path(param_name, value, param_def))
        else:
            errors.append(
                f"Unknown parameter type '{param_type}' for {param_name}"
            )

        return errors

    def _validate_string(
        self,
        param_name: str,
        value: Any,
        param_def: Dict
    ) -> List[str]:
        """Validate string parameter"""
        errors = []

        if not isinstance(value, str):
            errors.append(f"{param_name}: expected string, got {type(value).__name__}")
            return errors

        validation = param_def.get('validation', {})

        # Pattern validation
        if 'pattern' in validation:
            pattern = validation['pattern']
            if not re.match(pattern, value):
                errors.append(
                    f"{param_name}: value '{value}' does not match pattern '{pattern}'"
                )

        # Length validation
        if 'min_length' in validation:
            min_len = validation['min_length']
            if len(value) < min_len:
                errors.append(
                    f"{param_name}: minimum length is {min_len}, got {len(value)}"
                )

        if 'max_length' in validation:
            max_len = validation['max_length']
            if len(value) > max_len:
                errors.append(
                    f"{param_name}: maximum length is {max_len}, got {len(value)}"
                )

        return errors

    def _validate_integer(
        self,
        param_name: str,
        value: Any,
        param_def: Dict
    ) -> List[str]:
        """Validate integer parameter"""
        errors = []

        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"{param_name}: expected integer, got {type(value).__name__}")
            return errors

        validation = param_def.get('validation', {})

        # Range validation
        if 'min' in validation:
            min_val = validation['min']
            if value < min_val:
                errors.append(
                    f"{param_name}: minimum value is {min_val}, got {value}"
                )

        if 'max' in validation:
            max_val = validation['max']
            if value > max_val:
                errors.append(
                    f"{param_name}: maximum value is {max_val}, got {value}"
                )

        return errors

    def _validate_float(
        self,
        param_name: str,
        value: Any,
        param_def: Dict
    ) -> List[str]:
        """Validate float parameter"""
        errors = []

        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"{param_name}: expected number, got {type(value).__name__}")
            return errors

        validation = param_def.get('validation', {})

        # Range validation
        if 'min' in validation:
            min_val = validation['min']
            if value < min_val:
                errors.append(
                    f"{param_name}: minimum value is {min_val}, got {value}"
                )

        if 'max' in validation:
            max_val = validation['max']
            if value > max_val:
                errors.append(
                    f"{param_name}: maximum value is {max_val}, got {value}"
                )

        return errors

    def _validate_boolean(
        self,
        param_name: str,
        value: Any,
        param_def: Dict
    ) -> List[str]:
        """Validate boolean parameter"""
        errors = []

        if not isinstance(value, bool):
            errors.append(f"{param_name}: expected boolean, got {type(value).__name__}")

        return errors

    def _validate_choice(
        self,
        param_name: str,
        value: Any,
        param_def: Dict
    ) -> List[str]:
        """Validate choice parameter"""
        errors = []

        choices = param_def.get('choices', [])

        if value not in choices:
            errors.append(
                f"{param_name}: value '{value}' not in allowed choices {choices}"
            )

        return errors

    def _validate_json(
        self,
        param_name: str,
        value: Any,
        param_def: Dict
    ) -> List[str]:
        """Validate JSON parameter"""
        errors = []

        if isinstance(value, str):
            # Try to parse as JSON
            try:
                json.loads(value)
            except json.JSONDecodeError as e:
                errors.append(f"{param_name}: invalid JSON - {e}")
        elif not isinstance(value, (dict, list)):
            errors.append(
                f"{param_name}: expected JSON string or dict/list, got {type(value).__name__}"
            )

        return errors

    def _validate_url(
        self,
        param_name: str,
        value: Any,
        param_def: Dict
    ) -> List[str]:
        """Validate URL parameter"""
        errors = []

        if not isinstance(value, str):
            errors.append(f"{param_name}: expected string, got {type(value).__name__}")
            return errors

        try:
            result = urlparse(value)
            if not all([result.scheme, result.netloc]):
                errors.append(f"{param_name}: invalid URL format")
        except Exception as e:
            errors.append(f"{param_name}: invalid URL - {e}")

        return errors

    def _validate_email(
        self,
        param_name: str,
        value: Any,
        param_def: Dict
    ) -> List[str]:
        """Validate email parameter"""
        errors = []

        if not isinstance(value, str):
            errors.append(f"{param_name}: expected string, got {type(value).__name__}")
            return errors

        # Simple email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            errors.append(f"{param_name}: invalid email format")

        return errors

    def _validate_path(
        self,
        param_name: str,
        value: Any,
        param_def: Dict
    ) -> List[str]:
        """Validate path parameter"""
        errors = []

        if not isinstance(value, str):
            errors.append(f"{param_name}: expected string, got {type(value).__name__}")
            return errors

        validation = param_def.get('validation', {})

        # Check if path should exist
        if validation.get('exists', False):
            from pathlib import Path
            if not Path(value).exists():
                errors.append(f"{param_name}: path does not exist: {value}")

        return errors

    def apply_defaults(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply default values for missing parameters

        Args:
            params: User-provided parameters

        Returns:
            Parameters with defaults applied
        """
        result = params.copy()

        for param_def in self.template.parameters:
            param_name = param_def['name']

            # Apply default if parameter not provided and has default value
            if param_name not in result:
                if 'default' in param_def:
                    result[param_name] = param_def['default']

        return result

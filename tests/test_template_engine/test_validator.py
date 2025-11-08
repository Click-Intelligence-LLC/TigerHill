"""
Tests for TemplateValidator
"""

import pytest
from pathlib import Path
from tigerhill.template_engine.loader import TemplateLoader
from tigerhill.template_engine.validator import TemplateValidator, ParameterValidationError


class TestTemplateValidator:
    """Test TemplateValidator functionality"""

    @pytest.fixture
    def loader(self):
        """Create a template loader"""
        project_root = Path(__file__).parent.parent.parent
        templates_dir = project_root / "templates"
        return TemplateLoader(templates_dir=str(templates_dir))

    @pytest.fixture
    def http_template(self, loader):
        """Load HTTP API test template"""
        return loader.load_template("http/http-api-test.yaml")

    @pytest.fixture
    def validator(self, http_template):
        """Create validator for HTTP template"""
        return TemplateValidator(http_template)

    def test_validate_valid_params(self, validator):
        """Test validation with valid parameters"""
        params = {
            "agent_name": "test-api",
            "api_url": "https://api.example.com",
            "http_method": "GET",
            "expected_status": 200,
            "validate_response": True
        }

        is_valid, errors = validator.validate(params)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_missing_required(self, validator):
        """Test validation with missing required parameter"""
        params = {
            "api_url": "https://api.example.com",
            # Missing required 'agent_name'
        }

        is_valid, errors = validator.validate(params)
        assert is_valid is False
        assert len(errors) > 0
        assert any("agent_name" in error for error in errors)

    def test_validate_invalid_type(self, validator):
        """Test validation with invalid parameter type"""
        params = {
            "agent_name": "test-api",
            "api_url": "https://api.example.com",
            "http_method": "GET",
            "expected_status": "not-a-number",  # Should be integer
            "validate_response": True
        }

        is_valid, errors = validator.validate(params)
        assert is_valid is False
        assert any("expected_status" in error for error in errors)

    def test_validate_invalid_choice(self, validator):
        """Test validation with invalid choice value"""
        params = {
            "agent_name": "test-api",
            "api_url": "https://api.example.com",
            "http_method": "INVALID",  # Not in choices
            "expected_status": 200,
            "validate_response": True
        }

        is_valid, errors = validator.validate(params)
        assert is_valid is False
        assert any("http_method" in error for error in errors)

    def test_validate_pattern(self, validator):
        """Test validation with pattern constraint"""
        params = {
            "agent_name": "invalid name!",  # Contains invalid characters
            "api_url": "https://api.example.com",
            "http_method": "GET",
            "expected_status": 200,
            "validate_response": True
        }

        is_valid, errors = validator.validate(params)
        assert is_valid is False
        assert any("agent_name" in error for error in errors)

    def test_validate_url(self, validator):
        """Test URL validation"""
        params = {
            "agent_name": "test-api",
            "api_url": "not-a-valid-url",
            "http_method": "GET",
            "expected_status": 200,
            "validate_response": True
        }

        is_valid, errors = validator.validate(params)
        assert is_valid is False
        assert any("api_url" in error for error in errors)

    def test_validate_integer_range(self, validator):
        """Test integer range validation"""
        params = {
            "agent_name": "test-api",
            "api_url": "https://api.example.com",
            "http_method": "GET",
            "expected_status": 999,  # Outside valid range (100-599)
            "validate_response": True
        }

        is_valid, errors = validator.validate(params)
        assert is_valid is False
        assert any("expected_status" in error for error in errors)

    def test_apply_defaults(self, validator):
        """Test applying default values"""
        params = {
            "agent_name": "test-api",
            "api_url": "https://api.example.com",
            # Missing optional params with defaults
        }

        params_with_defaults = validator.apply_defaults(params)

        assert "http_method" in params_with_defaults
        assert params_with_defaults["http_method"] == "GET"  # Default value
        assert "expected_status" in params_with_defaults
        assert params_with_defaults["expected_status"] == 200  # Default value

    def test_validate_boolean(self, validator):
        """Test boolean parameter validation"""
        params = {
            "agent_name": "test-api",
            "api_url": "https://api.example.com",
            "http_method": "GET",
            "expected_status": 200,
            "validate_response": "yes"  # Should be boolean
        }

        is_valid, errors = validator.validate(params)
        assert is_valid is False
        assert any("validate_response" in error for error in errors)

    def test_validate_json(self, loader):
        """Test JSON parameter validation"""
        template = loader.load_template("http/http-api-test.yaml")
        validator = TemplateValidator(template)

        # Valid JSON string
        params = {
            "agent_name": "test-api",
            "api_url": "https://api.example.com",
            "http_method": "POST",
            "expected_status": 200,
            "request_body": '{"key": "value"}',
            "validate_response": True
        }

        is_valid, errors = validator.validate(params)
        assert is_valid is True

        # Invalid JSON string
        params["request_body"] = '{invalid json}'
        is_valid, errors = validator.validate(params)
        assert is_valid is False
        assert any("request_body" in error for error in errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Integration tests for CLI template generation
"""

import pytest
import tempfile
from pathlib import Path
from tigerhill.template_engine.cli import TemplateWizard


class TestCLIIntegration:
    """Test CLI wizard integration"""

    @pytest.fixture
    def wizard(self):
        """Create template wizard"""
        project_root = Path(__file__).parent.parent.parent
        templates_dir = project_root / "templates"
        return TemplateWizard(templates_dir=str(templates_dir))

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_list_templates(self, wizard):
        """Test listing templates via CLI"""
        templates = wizard.catalog.list_all()

        assert len(templates) >= 11  # We created 11 templates
        assert any(t['id'] == 'http-api-test' for t in templates)
        assert any(t['id'] == 'llm-prompt-response' for t in templates)

    def test_load_template_by_name(self, wizard):
        """Test loading template by name"""
        template = wizard._load_template_by_name("http-api-test")

        assert template is not None
        assert template.name == "http-api-test"

    def test_load_template_by_path(self, wizard):
        """Test loading template by path"""
        template = wizard._load_template_by_name("http/http-api-test.yaml")

        assert template is not None
        assert template.name == "http-api-test"

    def test_end_to_end_generation(self, wizard, temp_output_dir):
        """Test complete template generation flow"""
        # Load template
        template = wizard._load_template_by_name("http-api-test")
        assert template is not None

        # Define parameters
        params = {
            "agent_name": "test-api",
            "api_url": "https://api.example.com",
            "http_method": "GET",
            "expected_status": 200,
            "request_body": "{}",
            "validate_response": True
        }

        # Validate
        from tigerhill.template_engine.validator import TemplateValidator
        validator = TemplateValidator(template)
        params = validator.apply_defaults(params)
        is_valid, errors = validator.validate(params)

        assert is_valid is True, f"Validation errors: {errors}"

        # Generate
        from tigerhill.template_engine.generator import CodeGenerator
        generator = CodeGenerator(template)
        generated_files = generator.generate(
            params=params,
            output_dir=temp_output_dir,
            overwrite=False
        )

        # Verify files were generated
        assert len(generated_files) == 3

        # Verify file contents
        test_file = Path(temp_output_dir) / "test_test-api.py"
        assert test_file.exists()

        with open(test_file, 'r') as f:
            content = f.read()

        assert "https://api.example.com" in content
        assert "pytest" in content

    def test_multiple_templates_generation(self, wizard, temp_output_dir):
        """Test generating different types of templates"""
        templates_to_test = [
            {
                "name": "cli-basic",
                "params": {
                    "agent_name": "my-cli",
                    "command": "python my_tool.py",
                    "args": "",
                    "expected_exit_code": 0,
                    "validate_output": True,
                    "timeout": 30
                }
            },
            {
                "name": "llm-prompt-response",
                "params": {
                    "agent_name": "my-llm",
                    "model_name": "gpt-4",
                    "prompt": "Test prompt",
                    "max_tokens": 100,
                    "temperature": 0.7,
                    "validate_quality": True,
                    "expected_keywords": ""
                }
            }
        ]

        from tigerhill.template_engine.validator import TemplateValidator
        from tigerhill.template_engine.generator import CodeGenerator

        for template_info in templates_to_test:
            # Load template
            template = wizard._load_template_by_name(template_info["name"])
            assert template is not None, f"Failed to load {template_info['name']}"

            # Validate
            validator = TemplateValidator(template)
            params = validator.apply_defaults(template_info["params"])
            is_valid, errors = validator.validate(params)
            assert is_valid is True, f"Validation failed for {template_info['name']}: {errors}"

            # Generate in subdirectory
            output_subdir = Path(temp_output_dir) / template_info["name"]
            output_subdir.mkdir(exist_ok=True)

            generator = CodeGenerator(template)
            generated_files = generator.generate(
                params=params,
                output_dir=str(output_subdir),
                overwrite=False
            )

            assert len(generated_files) >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Tests for CodeGenerator
"""

import pytest
import tempfile
from pathlib import Path
from tigerhill.template_engine.loader import TemplateLoader
from tigerhill.template_engine.generator import CodeGenerator, CodeGenerationError


class TestCodeGenerator:
    """Test CodeGenerator functionality"""

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
    def generator(self, http_template):
        """Create generator for HTTP template"""
        return CodeGenerator(http_template)

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_generate_files(self, generator, temp_output_dir):
        """Test generating files from template"""
        params = {
            "agent_name": "test-api",
            "api_url": "https://api.example.com",
            "http_method": "GET",
            "expected_status": 200,
            "request_body": "{}",
            "validate_response": True
        }

        generated_files = generator.generate(
            params=params,
            output_dir=temp_output_dir,
            overwrite=False
        )

        # Check that files were generated
        assert len(generated_files) == 3  # main_script, requirements, readme
        assert any("test_test-api.py" in f for f in generated_files)
        assert any("requirements.txt" in f for f in generated_files)
        assert any("README.md" in f for f in generated_files)

        # Check that files exist
        for file_path in generated_files:
            assert Path(file_path).exists()

    def test_generate_file_content(self, generator, temp_output_dir):
        """Test that generated file content is correct"""
        params = {
            "agent_name": "my-weather-api",
            "api_url": "https://api.weather.com",
            "http_method": "GET",
            "expected_status": 200,
            "request_body": "{}",
            "validate_response": True
        }

        generated_files = generator.generate(
            params=params,
            output_dir=temp_output_dir
        )

        # Find the main test file
        test_file = next(f for f in generated_files if f.endswith(".py"))

        # Read content
        with open(test_file, 'r') as f:
            content = f.read()

        # Check that parameters were substituted
        assert "my-weather-api" in content or "MyWeatherApi" in content or "my_weather_api" in content
        assert "https://api.weather.com" in content
        assert "GET" in content

        # Check that template structure is intact
        assert "import pytest" in content
        assert "TraceStore" in content
        assert "def test_" in content

    def test_generate_with_overwrite(self, generator, temp_output_dir):
        """Test overwriting existing files"""
        params = {
            "agent_name": "test-api",
            "api_url": "https://api.example.com",
            "http_method": "GET",
            "expected_status": 200,
            "request_body": "{}",
            "validate_response": True
        }

        # Generate once
        generator.generate(params=params, output_dir=temp_output_dir)

        # Try to generate again without overwrite - should fail
        with pytest.raises(CodeGenerationError):
            generator.generate(params=params, output_dir=temp_output_dir, overwrite=False)

        # Generate with overwrite - should succeed
        generated_files = generator.generate(
            params=params,
            output_dir=temp_output_dir,
            overwrite=True
        )
        assert len(generated_files) > 0

    def test_preview_generation(self, generator):
        """Test previewing generated content"""
        params = {
            "agent_name": "test-api",
            "api_url": "https://api.example.com",
            "http_method": "POST",
            "expected_status": 201,
            "request_body": '{"name": "test"}',
            "validate_response": True
        }

        preview = generator.preview(params)

        # Check that preview contains rendered content
        assert len(preview) == 3  # 3 files
        assert any("test_test-api.py" in path for path in preview.keys())

        # Check content preview
        for path, content in preview.items():
            assert len(content) > 0
            if path.endswith(".py"):
                assert "import pytest" in content

    def test_get_file_list(self, generator):
        """Test getting list of files that will be generated"""
        params = {
            "agent_name": "test-api",
            "api_url": "https://api.example.com",
            "http_method": "GET",
            "expected_status": 200,
            "request_body": "{}",
            "validate_response": True
        }

        file_list = generator.get_file_list(params)

        assert len(file_list) == 3
        assert "test_test-api.py" in file_list
        assert "requirements.txt" in file_list
        assert "README.md" in file_list

    def test_custom_filters(self, generator):
        """Test Jinja2 custom filters"""
        params = {
            "agent_name": "my-test-agent",
            "api_url": "https://api.example.com",
            "http_method": "GET",
            "expected_status": 200,
            "request_body": "{}",
            "validate_response": True
        }

        preview = generator.preview(params)

        # Find the Python file
        py_file_content = next(
            content for path, content in preview.items()
            if path.endswith(".py")
        )

        # Check that filters were applied
        # CamelCase: MyTestAgent
        assert "MyTestAgent" in py_file_content or "class Test" in py_file_content

        # snake_case: my_test_agent
        assert "my_test_agent" in py_file_content or "def test_" in py_file_content

    def test_generate_llm_template(self, loader, temp_output_dir):
        """Test generating LLM template with different parameters"""
        template = loader.load_template("llm/llm-prompt-response.yaml")
        generator = CodeGenerator(template)

        params = {
            "agent_name": "gpt4-test",
            "model_name": "gpt-4",
            "prompt": "What is the capital of France?",
            "max_tokens": 100,
            "temperature": 0.7,
            "validate_quality": True,
            "expected_keywords": "Paris"
        }

        generated_files = generator.generate(
            params=params,
            output_dir=temp_output_dir
        )

        assert len(generated_files) == 3

        # Check that model and prompt were substituted
        test_file = next(f for f in generated_files if f.endswith(".py"))
        with open(test_file, 'r') as f:
            content = f.read()

        assert "gpt-4" in content
        assert "What is the capital of France?" in content

    def test_generate_cli_template(self, loader, temp_output_dir):
        """Test generating CLI template"""
        template = loader.load_template("cli/cli-basic.yaml")
        generator = CodeGenerator(template)

        params = {
            "agent_name": "my-cli-tool",
            "command": "python my_tool.py",
            "args": "--verbose --debug",
            "expected_exit_code": 0,
            "validate_output": True,
            "timeout": 60
        }

        generated_files = generator.generate(
            params=params,
            output_dir=temp_output_dir
        )

        assert len(generated_files) == 3

        # Check content
        test_file = next(f for f in generated_files if f.endswith(".py"))
        with open(test_file, 'r') as f:
            content = f.read()

        assert "python my_tool.py" in content
        assert "--verbose --debug" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

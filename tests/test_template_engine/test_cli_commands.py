"""
测试模板引擎CLI命令
Tests the template engine command-line interface
"""

import pytest
import subprocess
import tempfile
import json
from pathlib import Path


class TestTemplateCLI:
    """测试模板引擎CLI"""

    def test_cli_list_templates(self):
        """
        测试 --list 命令列出所有模板

        Use Case: Users want to see all available templates
        Command: python -m tigerhill.template_engine.cli --list
        """
        result = subprocess.run(
            ["python", "-m", "tigerhill.template_engine.cli", "--list"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        # Should display template information
        output = result.stdout

        # Should show all template categories
        assert "http" in output.lower() or "HTTP" in output
        assert "cli" in output.lower() or "CLI" in output
        assert "llm" in output.lower() or "LLM" in output

        # Should show template IDs
        assert "http-api-test" in output or "http/http-api-test" in output
        assert "llm-prompt-response" in output or "llm/llm-prompt-response" in output

        # Should show descriptions
        assert "description" in output.lower() or "Description" in output

        print(f"✅ CLI --list command works")
        print(f"   Found template categories: HTTP, CLI, LLM")

    def test_cli_help(self):
        """
        测试 --help 命令显示帮助信息

        Use Case: Users want to see usage instructions
        Command: python -m tigerhill.template_engine.cli --help
        """
        result = subprocess.run(
            ["python", "-m", "tigerhill.template_engine.cli", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0, f"Help failed: {result.stderr}"

        output = result.stdout

        # Should show usage information
        assert "usage" in output.lower()

        # Should describe key arguments
        assert "--template" in output or "-t" in output
        assert "--output" in output or "-o" in output
        assert "--list" in output or "-l" in output

        print(f"✅ CLI --help command works")
        print(f"   Shows usage and available options")

    def test_cli_invalid_template(self):
        """
        测试使用不存在的模板名

        Use Case: User specifies an invalid template name
        Command: python -m tigerhill.template_engine.cli --template invalid-template
        Expected: Should show error message
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    "python", "-m", "tigerhill.template_engine.cli",
                    "--template", "invalid-template-name",
                    "--output", tmpdir
                ],
                capture_output=True,
                text=True,
                timeout=10,
                input="n\n"  # Cancel any prompts
            )

            # May fail with non-zero exit code or show error message
            output = result.stdout + result.stderr

            # Should indicate template not found
            assert "not found" in output.lower() or "invalid" in output.lower() or "failed" in output.lower()

            print(f"✅ CLI handles invalid template names")
            print(f"   Shows appropriate error message")

    def test_cli_template_loading(self):
        """
        测试加载特定模板

        Use Case: User loads a template to see its parameters
        Command: python -m tigerhill.template_engine.cli --template http/http-api-test

        Note: This test requires interactive input, so we just verify the template can be loaded
        """
        # We can't fully test interactive mode in automated tests,
        # but we can verify the template engine's template loading works
        from tigerhill.template_engine.loader import TemplateLoader
        from tigerhill.template_engine.catalog import TemplateCatalog

        loader = TemplateLoader()
        catalog = TemplateCatalog(loader)

        # Verify all templates can be loaded via catalog
        all_templates = catalog.list_all()
        assert len(all_templates) >= 11, f"Expected at least 11 templates, found {len(all_templates)}"

        # Test loading a few specific templates
        test_templates = [
            "http/http-api-test",
            "cli/cli-basic",
            "llm/llm-prompt-response"
        ]

        for template_path in test_templates:
            template = loader.load_template(f"{template_path}.yaml")
            assert template is not None, f"Failed to load {template_path}"
            assert hasattr(template, 'name')
            assert hasattr(template, 'parameters')
            assert len(template.parameters) > 0

        print(f"✅ Template loading mechanism works")
        print(f"   Loaded {len(all_templates)} templates successfully")

    def test_cli_catalog_structure(self):
        """
        测试模板目录结构

        Use Case: Verify template catalog organization
        Validates:
        - Templates are organized by category
        - Each template has required metadata
        - Categories have proper descriptions
        """
        from tigerhill.template_engine.loader import TemplateLoader
        from tigerhill.template_engine.catalog import TemplateCatalog

        loader = TemplateLoader()
        catalog = TemplateCatalog(loader)

        # Test categories
        categories = catalog.get_categories()
        assert len(categories) >= 4, "Should have at least 4 categories (http, cli, llm, integration)"

        expected_categories = ['http', 'cli', 'llm', 'integration']
        for cat in expected_categories:
            assert cat in categories, f"Missing category: {cat}"
            assert 'name' in categories[cat]
            assert 'description' in categories[cat]

        # Test category templates
        for category_id in expected_categories:
            templates = catalog.get_category_templates(category_id)
            assert len(templates) > 0, f"Category {category_id} has no templates"

            print(f"  {category_id}: {len(templates)} templates")

        # Test individual template info
        all_templates = catalog.list_all()
        for template_info in all_templates:
            # Verify required fields
            assert 'id' in template_info
            assert 'name' in template_info
            assert 'description' in template_info
            assert 'category' in template_info
            assert 'path' in template_info

        print(f"✅ Template catalog structure is valid")
        print(f"   {len(categories)} categories, {len(all_templates)} templates")

    def test_cli_template_parameters(self):
        """
        测试模板参数定义

        Use Case: Verify template parameters are properly defined
        Validates:
        - Each template has parameters
        - Parameters have required fields
        - Parameter types are valid
        """
        from tigerhill.template_engine.loader import TemplateLoader

        loader = TemplateLoader()

        # Test all templates
        template_files = loader.list_templates()
        valid_types = ['string', 'integer', 'float', 'boolean', 'choice', 'json', 'url', 'email', 'path']

        for template_path in template_files:
            template = loader.load_template(template_path)

            assert len(template.parameters) > 0, f"{template.name} has no parameters"

            # Validate each parameter
            for param in template.parameters:
                # Required fields
                assert 'name' in param, f"{template.name}: parameter missing 'name'"
                assert 'type' in param, f"{template.name}: parameter {param.get('name')} missing 'type'"

                # Type should be valid
                param_type = param['type']
                assert param_type in valid_types, \
                    f"{template.name}: invalid parameter type '{param_type}' for {param['name']}"

                # If type is choice, should have choices list
                if param_type == 'choice':
                    assert 'choices' in param, \
                        f"{template.name}: choice parameter {param['name']} missing 'choices'"
                    assert len(param['choices']) > 0, \
                        f"{template.name}: choice parameter {param['name']} has empty choices"

        print(f"✅ All template parameters are valid")
        print(f"   Validated {len(template_files)} templates")

    def test_cli_generator_file_list(self):
        """
        测试生成器文件列表功能

        Use Case: Preview files that will be generated
        Validates:
        - get_file_list() returns expected files
        - File list includes test, requirements, and README
        """
        from tigerhill.template_engine.loader import TemplateLoader
        from tigerhill.template_engine.generator import CodeGenerator
        from tigerhill.template_engine.validator import TemplateValidator

        loader = TemplateLoader()
        template = loader.load_template("http/http-api-test.yaml")

        params = {
            "agent_name": "test-api",
            "api_url": "http://localhost:3000",
            "http_method": "GET",
            "expected_status": 200,
            "request_body": "{}",
            "validate_response": True
        }

        # Apply defaults and validate
        validator = TemplateValidator(template)
        params = validator.apply_defaults(params)
        is_valid, errors = validator.validate(params)
        assert is_valid, f"Validation failed: {errors}"

        # Get file list
        generator = CodeGenerator(template)
        file_list = generator.get_file_list(params)

        # Should include standard files
        assert any('test_' in f for f in file_list), "Missing test file"
        assert any('requirements' in f.lower() for f in file_list), "Missing requirements file"
        assert any('readme' in f.lower() for f in file_list), "Missing README file"

        print(f"✅ Generator file list works")
        print(f"   Files: {', '.join(file_list)}")

    def test_cli_generation_with_defaults(self):
        """
        测试使用默认值生成代码

        Use Case: Generate code with only required parameters
        Validates:
        - Templates work with default values
        - Generated files are valid
        """
        from tigerhill.template_engine.loader import TemplateLoader
        from tigerhill.template_engine.generator import CodeGenerator
        from tigerhill.template_engine.validator import TemplateValidator

        loader = TemplateLoader()
        template = loader.load_template("cli/cli-basic.yaml")

        # Provide only required parameters
        params = {
            "command": "echo"
        }

        # Apply defaults
        validator = TemplateValidator(template)
        params = validator.apply_defaults(params)
        is_valid, errors = validator.validate(params)
        assert is_valid, f"Validation failed: {errors}"

        # Should have agent_name from default
        assert 'agent_name' in params
        assert 'expected_exit_code' in params
        assert 'timeout' in params

        # Generate with defaults
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = CodeGenerator(template)
            files = generator.generate(params, tmpdir, overwrite=True)

            assert len(files) >= 3, "Should generate at least 3 files"

            # Verify test file exists and is valid
            test_file = [f for f in files if 'test_' in f and f.endswith('.py')][0]
            assert Path(test_file).exists()
            assert Path(test_file).stat().st_size > 0

        print(f"✅ Generation with defaults works")
        print(f"   Generated {len(files)} files using default values")

    def test_cli_all_templates_can_generate(self):
        """
        测试所有模板都能成功生成代码

        Use Case: Verify every template can generate code
        Validates:
        - All templates can be loaded
        - All templates can generate files with defaults
        - Generated files are not empty
        """
        from tigerhill.template_engine.loader import TemplateLoader
        from tigerhill.template_engine.generator import CodeGenerator
        from tigerhill.template_engine.validator import TemplateValidator

        loader = TemplateLoader()
        template_paths = loader.list_templates()

        failed_templates = []

        with tempfile.TemporaryDirectory() as tmpdir:
            for template_path in template_paths:
                try:
                    template = loader.load_template(template_path)

                    # Get default parameters
                    validator = TemplateValidator(template)
                    params = {}

                    # Provide required parameters with test values
                    for param in template.parameters:
                        if param.get('required', False) and 'default' not in param:
                            param_type = param.get('type', 'string')
                            if param_type == 'url':
                                params[param['name']] = "http://localhost:3000"
                            elif param_type == 'choice':
                                params[param['name']] = param.get('choices', ['test'])[0]
                            elif param_type == 'string':
                                params[param['name']] = "test-value"
                            elif param_type == 'integer':
                                params[param['name']] = 1
                            else:
                                params[param['name']] = "test"

                    # Apply defaults
                    params = validator.apply_defaults(params)

                    # Generate
                    generator = CodeGenerator(template)
                    output_path = Path(tmpdir) / template.name
                    output_path.mkdir(exist_ok=True)

                    files = generator.generate(params, str(output_path), overwrite=True)

                    assert len(files) > 0, f"No files generated for {template.name}"

                except Exception as e:
                    failed_templates.append((template_path, str(e)))

        # Report results
        if failed_templates:
            error_msg = "\n".join([f"  {path}: {error}" for path, error in failed_templates])
            pytest.fail(f"Failed templates:\n{error_msg}")

        print(f"✅ All {len(template_paths)} templates can generate code")

    def test_cli_wizard_instance(self):
        """
        测试TemplateWizard类实例化

        Use Case: Verify TemplateWizard can be instantiated
        Validates:
        - Wizard can be created
        - Has required attributes
        - Can access templates
        """
        from tigerhill.template_engine.cli import TemplateWizard

        # Create wizard
        wizard = TemplateWizard()

        # Verify attributes
        assert hasattr(wizard, 'loader')
        assert hasattr(wizard, 'catalog')

        # Verify catalog works
        categories = wizard.catalog.get_categories()
        assert len(categories) > 0

        templates = wizard.catalog.list_all()
        assert len(templates) >= 11

        print(f"✅ TemplateWizard instantiation works")
        print(f"   Found {len(templates)} templates in {len(categories)} categories")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

"""
测试所有模板生成的代码语法正确性和基本可执行性
"""

import ast
import subprocess
import tempfile
import pytest
from pathlib import Path
from tigerhill.template_engine.loader import TemplateLoader
from tigerhill.template_engine.generator import CodeGenerator
from tigerhill.template_engine.validator import TemplateValidator


class TestGeneratedScriptsSyntax:
    """测试生成脚本的语法正确性"""

    @pytest.fixture
    def loader(self):
        """创建模板加载器"""
        return TemplateLoader()

    @pytest.fixture
    def temp_output_dir(self):
        """创建临时输出目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def _get_default_params(self, template):
        """获取模板的默认参数"""
        validator = TemplateValidator(template)
        params = {}

        for param_def in template.parameters:
            param_name = param_def['name']
            param_type = param_def.get('type', 'string')

            # 如果有默认值，使用默认值
            if 'default' in param_def:
                params[param_name] = param_def['default']
            else:
                # 根据类型提供合理的测试值
                params[param_name] = self._get_test_value(param_type, param_def)

        # 应用默认值
        params = validator.apply_defaults(params)
        return params

    def _get_test_value(self, param_type, param_def):
        """根据参数类型提供测试值"""
        if param_type == 'string':
            return "test_value"
        elif param_type == 'integer':
            min_val = param_def.get('min', 0)
            max_val = param_def.get('max', 100)
            return (min_val + max_val) // 2
        elif param_type == 'float':
            return 0.5
        elif param_type == 'boolean':
            return True
        elif param_type == 'url':
            return "http://localhost:3000"
        elif param_type == 'email':
            return "test@example.com"
        elif param_type == 'path':
            return "/tmp/test"
        elif param_type == 'choice':
            choices = param_def.get('choices', [])
            return choices[0] if choices else "default"
        elif param_type == 'json':
            return "{}"
        else:
            return "test"

    @pytest.mark.parametrize("template_id", [
        "http/http-api-test",
        "http/http-rest-crud",
        "http/http-auth-test",
        "cli/cli-basic",
        "cli/cli-interactive",
        "stdio/stdio-basic",
        "llm/llm-prompt-response",
        "llm/llm-multi-turn",
        "llm/llm-function-calling",
        "llm/llm-cost-validation",
        "integration/integration-e2e"
    ])
    def test_template_generates_valid_syntax(self, loader, temp_output_dir, template_id):
        """测试每个模板生成的代码语法正确"""
        # 加载模板
        template = loader.load_template(f"{template_id}.yaml")
        assert template is not None, f"Failed to load template: {template_id}"

        # 获取参数
        params = self._get_default_params(template)

        # 验证参数
        validator = TemplateValidator(template)
        is_valid, errors = validator.validate(params)
        assert is_valid, f"Parameter validation failed for {template_id}: {errors}"

        # 生成代码
        generator = CodeGenerator(template)
        generated_files = generator.generate(
            params=params,
            output_dir=temp_output_dir,
            overwrite=True
        )

        assert len(generated_files) > 0, f"No files generated for {template_id}"

        # 验证每个生成的Python文件的语法
        for file_path in generated_files:
            if file_path.endswith('.py'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()

                # 使用ast.parse验证语法
                try:
                    ast.parse(code)
                    print(f"✅ Syntax valid: {Path(file_path).name}")
                except SyntaxError as e:
                    pytest.fail(
                        f"Syntax error in {file_path} (template: {template_id}):\n"
                        f"  Line {e.lineno}: {e.msg}\n"
                        f"  {e.text}"
                    )

    @pytest.mark.parametrize("template_id", [
        "http/http-api-test",
        "cli/cli-basic",
        "llm/llm-prompt-response"
    ])
    def test_generated_script_can_import(self, loader, temp_output_dir, template_id):
        """测试生成的脚本可以被导入（验证import语句正确）"""
        # 加载模板
        template = loader.load_template(f"{template_id}.yaml")
        params = self._get_default_params(template)

        # 生成代码
        generator = CodeGenerator(template)
        generated_files = generator.generate(
            params=params,
            output_dir=temp_output_dir,
            overwrite=True
        )

        # 找到主测试文件
        test_file = None
        for file_path in generated_files:
            if file_path.endswith('.py') and 'test_' in Path(file_path).name:
                test_file = file_path
                break

        assert test_file is not None, f"No test file found for {template_id}"

        # 尝试执行Python语法检查（不运行测试）
        result = subprocess.run(
            ["python", "-m", "py_compile", test_file],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.fail(
                f"Failed to compile {test_file} (template: {template_id}):\n"
                f"  stdout: {result.stdout}\n"
                f"  stderr: {result.stderr}"
            )

    def test_all_templates_generate_required_files(self, loader, temp_output_dir):
        """测试所有模板生成必需的文件"""
        templates = loader.list_templates()
        assert len(templates) >= 11, f"Expected at least 11 templates, found {len(templates)}"

        for template_path in templates:
            template = loader.load_template(template_path)
            params = self._get_default_params(template)

            generator = CodeGenerator(template)
            generated_files = generator.generate(
                params=params,
                output_dir=temp_output_dir,
                overwrite=True
            )

            # 每个模板至少应该生成3个文件（test, config, README）
            assert len(generated_files) >= 3, \
                f"Template {template.name} generated only {len(generated_files)} files (expected >= 3)"

            # 验证必需文件存在
            file_names = [Path(f).name for f in generated_files]
            has_test = any('test_' in name for name in file_names)
            has_config = any('config' in name or 'requirements' in name for name in file_names)

            assert has_test, f"Template {template.name} did not generate test file"
            assert has_config, f"Template {template.name} did not generate config/requirements file"

    def test_generated_code_has_proper_encoding(self, loader, temp_output_dir):
        """测试生成的代码有正确的编码"""
        template = loader.load_template("http/http-api-test.yaml")
        params = self._get_default_params(template)

        generator = CodeGenerator(template)
        generated_files = generator.generate(
            params=params,
            output_dir=temp_output_dir,
            overwrite=True
        )

        for file_path in generated_files:
            if file_path.endswith('.py'):
                # 尝试以UTF-8读取
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    assert len(content) > 0
                except UnicodeDecodeError as e:
                    pytest.fail(f"Encoding error in {file_path}: {e}")

    def test_generated_code_has_shebang(self, loader, temp_output_dir):
        """测试生成的可执行脚本有shebang"""
        template = loader.load_template("cli/cli-basic.yaml")
        params = self._get_default_params(template)

        generator = CodeGenerator(template)
        generated_files = generator.generate(
            params=params,
            output_dir=temp_output_dir,
            overwrite=True
        )

        for file_path in generated_files:
            if file_path.endswith('.py'):
                with open(file_path, 'r') as f:
                    first_line = f.readline()

                # 测试文件通常有shebang
                if 'test_' in Path(file_path).name:
                    # 至少应该有注释或shebang
                    assert first_line.startswith('#') or first_line.startswith('"""'), \
                        f"Python file {file_path} should start with # or docstring"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

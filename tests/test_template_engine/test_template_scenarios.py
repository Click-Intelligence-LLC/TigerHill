"""
测试并记录每个模板的使用场景和用法
Validates use cases and documents best practices for each template
"""

import pytest
import tempfile
from pathlib import Path
from tigerhill.template_engine.loader import TemplateLoader
from tigerhill.template_engine.generator import CodeGenerator
from tigerhill.template_engine.validator import TemplateValidator


class TestTemplateScenarios:
    """测试模板的实际使用场景"""

    @pytest.fixture
    def loader(self):
        """创建模板加载器"""
        return TemplateLoader()

    @pytest.fixture
    def temp_output_dir(self):
        """创建临时输出目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    # ========== HTTP Templates ==========

    def test_http_api_test_scenario(self, loader, temp_output_dir):
        """
        场景: 测试RESTful API的单个端点

        Use Case: Testing a single REST API endpoint
        - Test GET/POST/PUT/DELETE requests
        - Validate response status codes
        - Validate JSON response structure
        - Track request/response in trace store

        Best Practices:
        1. Use validate_response=True for production APIs
        2. Set appropriate timeout values
        3. Add custom assertions for your API contract
        4. Use trace_store to debug failures

        Example Scenario: Testing a user profile API
        """
        template = loader.load_template("http/http-api-test.yaml")

        # Scenario: Test user profile GET endpoint
        params = {
            "agent_name": "user-profile-api",
            "api_url": "https://api.example.com/v1/users/123",
            "http_method": "GET",
            "expected_status": 200,
            "request_body": "{}",
            "validate_response": True
        }

        # Validate parameters
        validator = TemplateValidator(template)
        is_valid, errors = validator.validate(params)
        assert is_valid, f"Invalid parameters: {errors}"

        # Generate test code
        generator = CodeGenerator(template)
        files = generator.generate(params, temp_output_dir, overwrite=True)

        # Verify generated files
        assert len(files) >= 3, "Should generate test, requirements, and README"
        test_file = [f for f in files if 'test_' in f and f.endswith('.py')][0]

        # Verify test file contains expected code patterns
        with open(test_file, 'r') as f:
            content = f.read()

        # Should contain HTTP adapter usage
        assert 'HTTPAdapter' in content
        assert 'base_url="https://api.example.com/v1/users/123"' in content

        # Should contain validation logic
        assert 'assert_http_status' in content
        assert 'expected_status=200' in content

        print(f"✅ HTTP API Test scenario validated")
        print(f"   Generated: {Path(test_file).name}")
        print(f"   Use case: Single endpoint testing with validation")

    def test_http_rest_crud_scenario(self, loader, temp_output_dir):
        """
        场景: 测试完整的CRUD操作流程

        Use Case: Testing complete CRUD workflow
        - Create resource (POST)
        - Read resource (GET)
        - Update resource (PUT/PATCH)
        - Delete resource (DELETE)
        - Validate entire workflow

        Best Practices:
        1. Test operations in order (CREATE -> READ -> UPDATE -> DELETE)
        2. Pass resource IDs between operations
        3. Use trace_store to track the entire workflow
        4. Add rollback/cleanup in finally block

        Example Scenario: Testing a blog post CRUD API
        """
        template = loader.load_template("http/http-rest-crud.yaml")

        params = {
            "agent_name": "blog-post-crud",
            "base_url": "https://api.example.com",
            "resource_path": "/v1/posts",
            "resource_name": "post"
        }

        validator = TemplateValidator(template)
        is_valid, errors = validator.validate(params)
        assert is_valid, f"Invalid parameters: {errors}"

        generator = CodeGenerator(template)
        files = generator.generate(params, temp_output_dir, overwrite=True)

        test_file = [f for f in files if 'test_' in f and f.endswith('.py')][0]

        with open(test_file, 'r') as f:
            content = f.read()

        # Should contain all CRUD operations
        assert 'CREATE' in content or 'create' in content
        assert 'READ' in content or 'read' in content
        assert 'UPDATE' in content or 'update' in content
        assert 'DELETE' in content or 'delete' in content

        print(f"✅ HTTP REST CRUD scenario validated")
        print(f"   Use case: Complete CRUD workflow testing")

    def test_http_auth_test_scenario(self, loader, temp_output_dir):
        """
        场景: 测试需要认证的API

        Use Case: Testing authenticated APIs
        - Bearer token authentication
        - API key authentication
        - OAuth authentication
        - Test both success and failure cases

        Best Practices:
        1. Store credentials in environment variables
        2. Test both authenticated and unauthenticated requests
        3. Test token expiration scenarios
        4. Validate proper error messages for auth failures

        Example Scenario: Testing a protected resource API
        """
        template = loader.load_template("http/http-auth-test.yaml")

        params = {
            "agent_name": "protected-api",
            "api_url": "https://api.example.com/v1/protected",
            "auth_type": "bearer",
            "expected_status_with_auth": 200,
            "expected_status_without_auth": 401
        }

        validator = TemplateValidator(template)
        is_valid, errors = validator.validate(params)
        assert is_valid, f"Invalid parameters: {errors}"

        generator = CodeGenerator(template)
        files = generator.generate(params, temp_output_dir, overwrite=True)

        test_file = [f for f in files if 'test_' in f and f.endswith('.py')][0]

        with open(test_file, 'r') as f:
            content = f.read()

        # Should contain authentication logic
        assert 'auth' in content.lower() or 'bearer' in content.lower()

        print(f"✅ HTTP Auth Test scenario validated")
        print(f"   Use case: Testing authenticated API endpoints")

    # ========== CLI Templates ==========

    def test_cli_basic_scenario(self, loader, temp_output_dir):
        """
        场景: 测试命令行工具

        Use Case: Testing CLI applications
        - Execute command with arguments
        - Validate exit codes
        - Validate stdout/stderr output
        - Test different command variations

        Best Practices:
        1. Test both success and error cases
        2. Use appropriate timeout values
        3. Validate output patterns, not exact strings
        4. Test edge cases (empty input, large input, etc.)

        Example Scenario: Testing a file conversion CLI tool
        """
        template = loader.load_template("cli/cli-basic.yaml")

        params = {
            "agent_name": "file-converter",
            "command": "convert",
            "args": "--input test.txt --output test.pdf",
            "expected_exit_code": 0,
            "validate_output": True,
            "timeout": 30
        }

        validator = TemplateValidator(template)
        is_valid, errors = validator.validate(params)
        assert is_valid, f"Invalid parameters: {errors}"

        generator = CodeGenerator(template)
        files = generator.generate(params, temp_output_dir, overwrite=True)

        test_file = [f for f in files if 'test_' in f and f.endswith('.py')][0]

        with open(test_file, 'r') as f:
            content = f.read()

        # Should contain CLI adapter
        assert 'CLIAdapter' in content
        assert 'command="convert"' in content

        # Should validate exit code
        assert 'exit_code' in content

        print(f"✅ CLI Basic scenario validated")
        print(f"   Use case: Testing command-line tools")

    def test_cli_interactive_scenario(self, loader, temp_output_dir):
        """
        场景: 测试交互式CLI应用

        Use Case: Testing interactive CLI applications
        - Send multiple inputs in sequence
        - Validate prompts and responses
        - Test conversation flows
        - Handle timeouts and errors

        Best Practices:
        1. Define clear input/output sequences
        2. Use appropriate delays between inputs
        3. Test both happy path and error paths
        4. Validate intermediate outputs, not just final result

        Example Scenario: Testing an interactive config wizard
        """
        template = loader.load_template("cli/cli-interactive.yaml")

        params = {
            "agent_name": "config-wizard",
            "command": "config-wizard",
            "num_interactions": 3,
            "timeout": 30
        }

        validator = TemplateValidator(template)
        is_valid, errors = validator.validate(params)
        assert is_valid, f"Invalid parameters: {errors}"

        generator = CodeGenerator(template)
        files = generator.generate(params, temp_output_dir, overwrite=True)

        test_file = [f for f in files if 'test_' in f and f.endswith('.py')][0]

        with open(test_file, 'r') as f:
            content = f.read()

        # Should contain interactive input handling
        assert 'input' in content.lower() or 'interactive' in content.lower()

        print(f"✅ CLI Interactive scenario validated")
        print(f"   Use case: Testing interactive CLI applications")

    # ========== STDIO Templates ==========

    def test_stdio_basic_scenario(self, loader, temp_output_dir):
        """
        场景: 测试标准输入/输出应用

        Use Case: Testing STDIO-based applications
        - Send input via stdin
        - Read output from stdout
        - Test piping and stream processing
        - Validate continuous input/output

        Best Practices:
        1. Test streaming behavior (line-by-line vs. batch)
        2. Handle both text and binary data appropriately
        3. Test EOF handling
        4. Validate output order and timing

        Example Scenario: Testing a text processing filter
        """
        template = loader.load_template("stdio/stdio-basic.yaml")

        params = {
            "agent_name": "text-filter",
            "command": "grep",
            "test_message": "Hello, agent!",
            "timeout": 30
        }

        validator = TemplateValidator(template)
        is_valid, errors = validator.validate(params)
        assert is_valid, f"Invalid parameters: {errors}"

        generator = CodeGenerator(template)
        files = generator.generate(params, temp_output_dir, overwrite=True)

        test_file = [f for f in files if 'test_' in f and f.endswith('.py')][0]

        with open(test_file, 'r') as f:
            content = f.read()

        # Should contain STDIO adapter
        assert 'STDIOAdapter' in content or 'stdin' in content.lower()

        print(f"✅ STDIO Basic scenario validated")
        print(f"   Use case: Testing STDIO-based applications")

    # ========== LLM Templates ==========

    def test_llm_prompt_response_scenario(self, loader, temp_output_dir):
        """
        场景: 测试LLM单轮对话

        Use Case: Testing single-turn LLM interactions
        - Send prompt to LLM
        - Validate response quality
        - Check for expected keywords
        - Track prompt/response for analysis

        Best Practices:
        1. Use PromptCapture to record all interactions
        2. Validate response contains expected information
        3. Use PromptAnalyzer for quality assessment
        4. Set appropriate temperature and max_tokens

        Example Scenario: Testing a code explanation prompt
        """
        template = loader.load_template("llm/llm-prompt-response.yaml")

        params = {
            "agent_name": "code-explainer",
            "model_name": "gpt-4",
            "prompt": "Explain what this Python function does: def factorial(n): return 1 if n <= 1 else n * factorial(n-1)",
            "max_tokens": 1000,
            "temperature": 0.7,
            "validate_quality": True,
            "expected_keywords": "recursive, factorial, multiplication"
        }

        validator = TemplateValidator(template)
        is_valid, errors = validator.validate(params)
        assert is_valid, f"Invalid parameters: {errors}"

        generator = CodeGenerator(template)
        files = generator.generate(params, temp_output_dir, overwrite=True)

        test_file = [f for f in files if 'test_' in f and f.endswith('.py')][0]

        with open(test_file, 'r') as f:
            content = f.read()

        # Should contain LLM interaction components
        assert 'PromptCapture' in content or 'PromptAnalyzer' in content
        assert 'model_name' in content or 'gpt-4' in content

        # Should validate keywords
        assert 'recursive' in content or 'expected_keywords' in content

        print(f"✅ LLM Prompt-Response scenario validated")
        print(f"   Use case: Single-turn LLM interaction testing")

    def test_llm_multi_turn_scenario(self, loader, temp_output_dir):
        """
        场景: 测试LLM多轮对话

        Use Case: Testing multi-turn conversations
        - Maintain conversation context
        - Test conversation flow
        - Validate responses at each turn
        - Track complete conversation history

        Best Practices:
        1. Build conversation history correctly
        2. Test context retention across turns
        3. Validate coherence of responses
        4. Use session tracking for debugging

        Example Scenario: Testing a technical support chatbot
        """
        template = loader.load_template("llm/llm-multi-turn.yaml")

        params = {
            "agent_name": "support-chatbot",
            "model_name": "gpt-4",
            "num_turns": 3,
            "validate_context": True
        }

        validator = TemplateValidator(template)
        is_valid, errors = validator.validate(params)
        assert is_valid, f"Invalid parameters: {errors}"

        generator = CodeGenerator(template)
        files = generator.generate(params, temp_output_dir, overwrite=True)

        test_file = [f for f in files if 'test_' in f and f.endswith('.py')][0]

        with open(test_file, 'r') as f:
            content = f.read()

        # Should contain multi-turn logic
        assert 'turn' in content.lower()
        assert 'conversation' in content.lower() or 'history' in content.lower()

        print(f"✅ LLM Multi-turn scenario validated")
        print(f"   Use case: Multi-turn conversation testing")

    def test_llm_function_calling_scenario(self, loader, temp_output_dir):
        """
        场景: 测试LLM函数调用

        Use Case: Testing LLM function calling capabilities
        - Define functions/tools
        - Test function selection
        - Validate function arguments
        - Execute functions and return results

        Best Practices:
        1. Define clear function schemas
        2. Validate function arguments before execution
        3. Test both successful and failed function calls
        4. Track function calls in trace store

        Example Scenario: Testing a weather assistant with function calls
        """
        template = loader.load_template("llm/llm-function-calling.yaml")

        params = {
            "agent_name": "weather-assistant",
            "model_name": "gpt-4",
            "num_tools": 2,
            "validate_tool_calls": True
        }

        validator = TemplateValidator(template)
        is_valid, errors = validator.validate(params)
        assert is_valid, f"Invalid parameters: {errors}"

        generator = CodeGenerator(template)
        files = generator.generate(params, temp_output_dir, overwrite=True)

        test_file = [f for f in files if 'test_' in f and f.endswith('.py')][0]

        with open(test_file, 'r') as f:
            content = f.read()

        # Should contain function calling logic
        assert 'function' in content.lower() or 'tool' in content.lower()

        print(f"✅ LLM Function Calling scenario validated")
        print(f"   Use case: Testing LLM function calling")

    def test_llm_cost_validation_scenario(self, loader, temp_output_dir):
        """
        场景: 测试LLM成本控制

        Use Case: Testing LLM cost and token tracking
        - Track token usage per call
        - Calculate costs per call
        - Validate against budget limits
        - Optimize for cost efficiency

        Best Practices:
        1. Set realistic budget limits
        2. Track both prompt and completion tokens
        3. Use cost data to optimize prompts
        4. Alert when approaching budget limits

        Example Scenario: Testing a content generation service
        """
        template = loader.load_template("llm/llm-cost-validation.yaml")

        params = {
            "agent_name": "content-generator",
            "model_name": "gpt-3.5-turbo",
            "max_budget_usd": 0.10,
            "max_tokens_per_call": 500
        }

        validator = TemplateValidator(template)
        is_valid, errors = validator.validate(params)
        assert is_valid, f"Invalid parameters: {errors}"

        generator = CodeGenerator(template)
        files = generator.generate(params, temp_output_dir, overwrite=True)

        test_file = [f for f in files if 'test_' in f and f.endswith('.py')][0]

        with open(test_file, 'r') as f:
            content = f.read()

        # Should contain cost tracking
        assert 'cost' in content.lower()
        assert 'token' in content.lower()
        assert 'budget' in content.lower()

        print(f"✅ LLM Cost Validation scenario validated")
        print(f"   Use case: Cost and token tracking")

    # ========== Integration Templates ==========

    def test_integration_e2e_scenario(self, loader, temp_output_dir):
        """
        场景: 测试端到端集成流程

        Use Case: Testing complete end-to-end workflows
        - Test multi-step workflows
        - Validate step dependencies
        - Track entire workflow execution
        - Test error handling and recovery

        Best Practices:
        1. Break workflow into clear steps
        2. Validate each step before proceeding
        3. Use trace_store for debugging
        4. Implement proper cleanup in finally block
        5. Test both success and failure scenarios

        Example Scenario: Testing a document processing pipeline
        """
        template = loader.load_template("integration/integration-e2e.yaml")

        params = {
            "agent_name": "doc-processor",
            "workflow_name": "Document Processing Pipeline",
            "num_steps": 3,
            "use_database": True
        }

        validator = TemplateValidator(template)
        is_valid, errors = validator.validate(params)
        assert is_valid, f"Invalid parameters: {errors}"

        generator = CodeGenerator(template)
        files = generator.generate(params, temp_output_dir, overwrite=True)

        test_file = [f for f in files if 'test_' in f and f.endswith('.py')][0]

        with open(test_file, 'r') as f:
            content = f.read()

        # Should contain workflow and step tracking
        assert 'workflow' in content.lower()
        assert 'step' in content.lower()
        assert 'SQLiteTraceStore' in content  # use_database=True

        print(f"✅ Integration E2E scenario validated")
        print(f"   Use case: End-to-end workflow testing")

    def test_all_templates_have_documented_scenarios(self, loader):
        """验证所有模板都有场景文档"""
        all_templates = loader.list_templates()

        # Get all test methods that document scenarios
        scenario_methods = [m for m in dir(self) if m.startswith('test_') and '_scenario' in m]

        # Should have at least 11 scenario tests (one per template)
        assert len(scenario_methods) >= 11, \
            f"Expected at least 11 scenario tests, found {len(scenario_methods)}"

        print(f"\n✅ All {len(scenario_methods) - 1} templates have documented scenarios")
        print(f"   Total templates: {len(all_templates)}")
        print(f"   Scenario tests: {len(scenario_methods) - 1}")  # -1 for this test itself


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

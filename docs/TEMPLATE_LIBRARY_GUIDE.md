# TigerHill Template Library Guide

## Overview

The TigerHill Template Library provides pre-built, customizable test script templates for common testing scenarios. Instead of writing test scripts from scratch, you can use our interactive CLI wizard to generate production-ready test code in minutes.

## Features

- **11+ Pre-built Templates** - Cover HTTP APIs, CLI tools, LLMs, and more
- **Interactive CLI Wizard** - Easy-to-use command-line interface
- **Parameter Validation** - Automatic validation of user inputs
- **Customizable** - Generated code is fully customizable
- **Best Practices** - Templates follow testing best practices

## Quick Start

### 1. List Available Templates

```bash
python -m tigerhill.template_engine.cli --list
```

This will show all available templates with descriptions.

### 2. Generate a Test (Interactive Mode)

```bash
python -m tigerhill.template_engine.cli
```

The interactive wizard will guide you through:
1. Selecting a template category
2. Choosing a specific template
3. Configuring parameters
4. Reviewing and confirming
5. Generating files

### 3. Generate a Test (Non-Interactive Mode)

```bash
python -m tigerhill.template_engine.cli \
  --template http-api-test \
  --output ./my_tests
```

## Available Templates

### HTTP Testing (3 templates)

#### 1. HTTP API Testing (`http-api-test`)

Test a single HTTP API endpoint with request/response validation.

**Use Cases:**
- Testing REST API endpoints
- Validating API responses
- Basic HTTP integration testing

**Parameters:**
- `agent_name`: Name for your test agent
- `api_url`: The API endpoint URL
- `http_method`: GET, POST, PUT, DELETE, or PATCH
- `expected_status`: Expected HTTP status code
- `request_body`: JSON body (for POST/PUT)
- `validate_response`: Enable/disable validation

**Example:**
```bash
python -m tigerhill.template_engine.cli --template http-api-test
```

**Generated Files:**
- `test_{agent_name}.py` - Main test script
- `requirements.txt` - Python dependencies
- `README.md` - Usage instructions

#### 2. REST CRUD Testing (`http-rest-crud`)

Test complete CRUD (Create, Read, Update, Delete) operations on a REST API.

**Use Cases:**
- Testing RESTful resource management
- Validating full CRUD lifecycle
- Integration testing for REST APIs

**Parameters:**
- `agent_name`: Test agent name
- `base_url`: Base URL of the API
- `resource_path`: Resource endpoint path
- `resource_name`: Name of the resource being tested

**Example Flow:**
1. CREATE - POST a new resource
2. READ - GET the created resource
3. UPDATE - PUT/PATCH to modify
4. DELETE - DELETE the resource
5. VERIFY - Confirm deletion

#### 3. HTTP Authentication Testing (`http-auth-test`)

Test HTTP APIs with various authentication methods.

**Use Cases:**
- Testing authenticated endpoints
- Validating auth requirements
- Security testing

**Supported Auth Types:**
- Bearer Token
- Basic Authentication
- API Key

**Parameters:**
- `agent_name`: Test agent name
- `api_url`: API endpoint URL
- `auth_type`: bearer, basic, or api_key
- `expected_status_with_auth`: Status when authenticated
- `expected_status_without_auth`: Status when not authenticated

### CLI Testing (2 templates)

#### 4. CLI Basic Testing (`cli-basic`)

Test command-line applications with input/output validation.

**Use Cases:**
- Testing CLI tools
- Validating command output
- Exit code verification

**Parameters:**
- `agent_name`: Test agent name
- `command`: Command to execute
- `args`: Command arguments
- `expected_exit_code`: Expected exit code
- `validate_output`: Enable output validation
- `timeout`: Execution timeout

#### 5. CLI Interactive Testing (`cli-interactive`)

Test interactive CLI applications with multi-step user input.

**Use Cases:**
- Testing interactive prompts
- Multi-step CLI workflows
- User input simulation

**Parameters:**
- `agent_name`: Test agent name
- `command`: Interactive command
- `num_interactions`: Number of input/output cycles
- `timeout`: Timeout per interaction

**Dependencies:**
- `pexpect` - For interactive process control

### STDIO Testing (1 template)

#### 6. STDIO Protocol Testing (`stdio-basic`)

Test agents using STDIO protocol for communication.

**Use Cases:**
- Testing STDIO-based agents
- Inter-process communication testing
- Protocol validation

**Parameters:**
- `agent_name`: Test agent name
- `command`: Agent command to launch
- `test_message`: Message to send
- `timeout`: Communication timeout

### LLM Testing (4 templates)

#### 7. LLM Prompt-Response Testing (`llm-prompt-response`)

Test basic LLM prompt and response with quality validation.

**Use Cases:**
- Testing LLM integrations
- Prompt quality validation
- Response validation

**Parameters:**
- `agent_name`: Test agent name
- `model_name`: LLM model (gpt-4, claude-3, etc.)
- `prompt`: Test prompt text
- `max_tokens`: Maximum response tokens
- `temperature`: Sampling temperature
- `validate_quality`: Enable quality checks
- `expected_keywords`: Keywords to validate

#### 8. LLM Multi-turn Testing (`llm-multi-turn`)

Test multi-turn conversations with context tracking.

**Use Cases:**
- Testing conversation flows
- Context maintenance validation
- Multi-turn interactions

**Parameters:**
- `agent_name`: Test agent name
- `model_name`: LLM model
- `num_turns`: Number of conversation turns
- `validate_context`: Enable context validation

#### 9. LLM Cost Validation (`llm-cost-validation`)

Test LLM with cost tracking, token limits, and budget validation.

**Use Cases:**
- Cost optimization
- Token usage tracking
- Budget enforcement

**Parameters:**
- `agent_name`: Test agent name
- `model_name`: LLM model
- `max_budget_usd`: Maximum allowed cost
- `max_tokens_per_call`: Token limit per call

**Features:**
- Automatic cost calculation
- Token usage tracking
- Budget utilization reporting

#### 10. LLM Function Calling (`llm-function-calling`)

Test LLM function calling with tool definitions and execution.

**Use Cases:**
- Testing function calling
- Tool use validation
- Agent workflows

**Parameters:**
- `agent_name`: Test agent name
- `model_name`: LLM model
- `num_tools`: Number of tools to define
- `validate_tool_calls`: Enable tool call validation

### Integration Testing (1 template)

#### 11. End-to-End Integration (`integration-e2e`)

Test complete workflow with multiple steps and validation.

**Use Cases:**
- End-to-end testing
- Multi-step workflows
- Integration validation

**Parameters:**
- `agent_name`: Test agent name
- `workflow_name`: Name of the workflow
- `num_steps`: Number of workflow steps
- `use_database`: Use SQLite for trace storage

## Usage Examples

### Example 1: Generate HTTP API Test

```bash
# Interactive mode
python -m tigerhill.template_engine.cli

# Follow the prompts:
# 1. Select category: HTTP Testing
# 2. Select template: HTTP API Testing
# 3. Enter parameters:
#    - Agent Name: weather-api
#    - API URL: https://api.weather.com/current
#    - HTTP Method: GET
#    - Expected Status: 200
# 4. Confirm generation

# Files generated:
# ./tests/test_weather-api.py
# ./tests/requirements.txt
# ./tests/README.md
```

### Example 2: Generate LLM Test

```bash
python -m tigerhill.template_engine.cli --template llm-prompt-response

# Configure via interactive prompts:
# - Agent Name: gpt4-qa
# - Model: gpt-4
# - Prompt: "What is the capital of France?"
# - Max Tokens: 100
# - Temperature: 0.7
# - Validate Quality: yes
# - Expected Keywords: Paris

# Generated test includes:
# - Prompt capture
# - Response validation
# - Quality analysis
# - Keyword checking
```

### Example 3: Generate CLI Test

```bash
python -m tigerhill.template_engine.cli --template cli-basic

# Parameters:
# - Agent Name: my-cli-tool
# - Command: python my_tool.py
# - Args: --verbose
# - Expected Exit Code: 0
# - Validate Output: yes
# - Timeout: 30

# Generated test validates:
# - Exit code
# - Output content
# - Execution time
```

## Template Structure

Each template consists of:

### 1. Metadata
- Name and display name
- Description
- Category and tags
- Version information

### 2. Parameters
- Name and type
- Required/optional flag
- Default values
- Validation rules

### 3. Dependencies
- Python packages (pip)
- System dependencies

### 4. File Templates
- Main test script
- Requirements file
- README/documentation
- Additional files (e.g., .env.example)

### 5. Jinja2 Templates
- Parameterized code templates
- Custom filters for formatting
- Conditional logic

## Customizing Generated Tests

All generated tests are fully customizable:

### 1. Modify Parameters

Edit the generated test to change:
- URLs, endpoints, or commands
- Validation criteria
- Timeout values
- Additional assertions

### 2. Add More Test Cases

```python
# Generated file: test_my_agent.py
class TestMyAgent:
    def test_basic_case(self, ...):
        # Auto-generated test
        pass

    def test_edge_case(self, ...):
        # Add your custom test
        pass

    def test_error_handling(self, ...):
        # Add error scenarios
        pass
```

### 3. Extend Functionality

- Add custom fixtures
- Integrate with existing test suites
- Add logging or reporting
- Customize trace storage

## Advanced Usage

### Creating Custom Templates

1. Create a new YAML file in `templates/{category}/`
2. Define metadata, parameters, and templates
3. Add Jinja2 template code
4. Update `templates/catalog.yaml`

Example template structure:
```yaml
metadata:
  name: "my-custom-template"
  display_name: "My Custom Template"
  description: "Description here"
  category: "custom"
  version: "1.0.0"
  tags: ["custom", "test"]

parameters:
  - name: "param1"
    type: "string"
    required: true
    default: "value"

dependencies:
  pip:
    - "pytest>=7.4.0"

files:
  - path: "test_{{name}}.py"
    template: "main_script"

templates:
  main_script: |
    # Your Jinja2 template here
    import pytest
    # ...
```

### Non-Interactive Generation

Use command-line parameters for automation:

```bash
# Specify all parameters via CLI (future feature)
python -m tigerhill.template_engine.cli \
  --template http-api-test \
  --param agent_name=my-api \
  --param api_url=https://api.example.com \
  --param http_method=GET \
  --param expected_status=200 \
  --output ./tests
```

## Tips & Best Practices

### 1. Start with Templates

- Use templates as a starting point
- Customize after generation
- Learn by examining generated code

### 2. Parameter Validation

- Templates validate inputs automatically
- Check validation errors carefully
- Use defaults when available

### 3. Test Organization

- Generate tests in a dedicated directory
- Use descriptive agent names
- Group related tests together

### 4. Customization

- Don't be afraid to modify generated code
- Add project-specific logic
- Extend with custom assertions

### 5. Version Control

- Commit generated tests to version control
- Track changes over time
- Document customizations

## Troubleshooting

### Template Not Found

```
❌ Template not found: my-template
```

**Solution**: Use `--list` to see available templates.

### Validation Errors

```
❌ Validation errors:
  - agent_name: value 'my agent!' does not match pattern '^[a-zA-Z0-9_-]+$'
```

**Solution**: Check parameter constraints in template definition.

### File Already Exists

```
❌ File already exists: ./tests/test_my_agent.py
```

**Solution**: Use a different output directory or delete existing files.

## FAQ

**Q: Can I modify generated tests?**
A: Yes! Generated tests are fully customizable. They're meant to be a starting point.

**Q: How do I add more templates?**
A: Create a YAML file in `templates/{category}/` following the template structure.

**Q: Can I use templates in CI/CD?**
A: Yes! Use non-interactive mode with `--template` and `--param` flags.

**Q: What if I need a template that doesn't exist?**
A: You can either create a custom template or start with the closest existing template and modify it.

**Q: Are templates maintained?**
A: Yes, templates are updated with new TigerHill features and best practices.

## Next Steps

1. **Try the Quick Start** - Generate your first test
2. **Explore Templates** - Browse available templates
3. **Customize** - Modify generated tests for your needs
4. **Create** - Build custom templates for your team

## Resources

- [TigerHill Documentation](../README.md)
- [Template System Design](design/template_system_design.md)
- [API Reference](API_REFERENCE.md)
- [Contributing Guide](CONTRIBUTING.md)

## Support

For issues or questions:
- GitHub Issues: [tigerhill/issues](https://github.com/yourusername/tigerhill/issues)
- Documentation: [tigerhill/docs](https://github.com/yourusername/tigerhill/docs)

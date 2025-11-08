# TigerHill Project - Cursor AI Rules

## Project Type
AI Agent Testing Framework with Template-based Test Generation

## When User Requests Test Generation

### Step 1: Identify Test Type
Ask user or infer from context:
- HTTP API test → Use `http/http-api-test` or `http/http-rest-crud`
- LLM agent test → Use `llm/llm-prompt-response` or `llm/llm-multi-turn`
- CLI tool test → Use `cli/cli-basic`
- E2E workflow → Use `integration/integration-e2e`

### Step 2: Generate Using TigerHill CLI
```bash
# Single test
python -m tigerhill.template_engine.cli \
  --template <template-name> \
  --param key=value \
  --output <directory>

# Batch tests (preferred for multiple tests)
python -m tigerhill.template_engine.cli \
  --config <config-file>.yaml
```

### Step 3: Create Config for Batch
For multiple tests, create YAML config in `tests/config/`:
```yaml
output_base: ./tests
shared_params:
  base_url: http://localhost:3000

templates:
  - template: <template-name>
    output: <subdir>
    params:
      param1: value1
      param2: ${base_url}/path  # Use variable substitution
```

## Available Templates

### HTTP Templates
- `http/http-api-test` - Single endpoint test
  Required: agent_name, api_url, http_method, expected_status, validate_response

- `http/http-rest-crud` - Complete CRUD
  Required: agent_name, base_url, resource_path, resource_name

- `http/http-auth-test` - Auth testing
  Required: agent_name, api_url, auth_type, expected_status_with_auth, expected_status_without_auth

### LLM Templates
- `llm/llm-prompt-response` - Single-turn
  Required: agent_name, model_name, prompt, max_tokens, temperature, validate_quality

- `llm/llm-multi-turn` - Conversation
  Required: agent_name, model_name, num_turns, validate_context

- `llm/llm-function-calling` - Function calls
  Required: agent_name, model_name, num_tools, validate_tool_calls

- `llm/llm-cost-validation` - Cost tracking
  Required: agent_name, model_name, max_budget_usd, max_tokens_per_call

### CLI Templates
- `cli/cli-basic` - CLI tool
  Required: agent_name, command, args, expected_exit_code, timeout, validate_output

- `cli/cli-interactive` - Interactive CLI
  Required: agent_name, command, num_interactions, timeout

### Other Templates
- `stdio/stdio-basic` - STDIO test
- `integration/integration-e2e` - E2E workflow

## Code Generation Rules

1. **Never write test code from scratch** - Use TigerHill templates
2. **Prefer YAML configs** - More maintainable than CLI params
3. **Use shared_params** - Reduce duplication in batch configs
4. **Name tests descriptively** - Format: `<resource>-<operation>` (e.g., `user-get`, `post-create`)
5. **Organize by feature** - Use output subdirectories (e.g., `api/users`, `llm/chatbot`)

## Testing Commands
```bash
# List templates
python -m tigerhill.template_engine.cli --list

# Run generated tests
pytest tests/ -v

# Run specific test
pytest tests/api/test_user-api.py -v
```

## Examples

### Example 1: Generate API Test
User: "Create a test for GET /api/users"
You should:
```bash
python -m tigerhill.template_engine.cli \
  -t http/http-api-test \
  -p agent_name=user-get \
  -p api_url=http://localhost:3000/api/users \
  -p http_method=GET \
  -p expected_status=200 \
  -o ./tests/api
```

### Example 2: Generate Multiple Tests
User: "Create tests for all user endpoints"
You should:
1. Create `tests/config/user_api_tests.yaml`:
```yaml
output_base: ./tests/api
shared_params:
  base_url: http://localhost:3000

templates:
  - template: http/http-api-test
    output: users
    params:
      agent_name: user-list
      api_url: ${base_url}/api/users
      http_method: GET

  - template: http/http-api-test
    output: users
    params:
      agent_name: user-get
      api_url: ${base_url}/api/users/1
      http_method: GET

  - template: http/http-rest-crud
    output: users
    params:
      agent_name: user-crud
      base_url: ${base_url}
      resource_path: /api/users
      resource_name: user
```

2. Execute:
```bash
python -m tigerhill.template_engine.cli --config tests/config/user_api_tests.yaml
```

## Documentation References
- Template Guide: `docs/TEMPLATE_AUTO_GENERATION_GUIDE.md`
- Template Scenarios: `tests/test_template_engine/test_template_scenarios.py`
- Example Configs: `examples/template_configs/`

## Style Guide
- Python: Follow PEP 8
- Type hints required for public methods
- Docstrings required for public classes/methods
- Tests required for new features

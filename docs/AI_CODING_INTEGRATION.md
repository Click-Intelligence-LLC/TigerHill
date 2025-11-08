# TigerHill Project Rules

## Project Context
This is TigerHill, an AI Agent testing and evaluation platform with template-based test generation.

## When User Asks to Generate Tests

1. **Check requirements first**:
   - What type of agent? (HTTP API, LLM, CLI, etc.)
   - What parameters are needed?
   - Single test or batch?

2. **Use TigerHill templates**:
   ```bash
   # List available templates
   python -m tigerhill.template_engine.cli --list

   # Generate single test
   python -m tigerhill.template_engine.cli \
     -t <template-name> \
     -p param1=value1 \
     -p param2=value2 \
     -o <output-dir>

   # Generate from config
   python -m tigerhill.template_engine.cli --config <config.yaml>
   ```

3. **Prefer YAML config for batch**:
   - Create config file in `tests/config/`
   - Use shared_params for common values
   - Use ${variable} for substitution

## Available Templates

- `http/http-api-test` - Single API endpoint test
- `http/http-rest-crud` - REST CRUD operations
- `http/http-auth-test` - Authentication testing
- `cli/cli-basic` - CLI application test
- `cli/cli-interactive` - Interactive CLI test
- `stdio/stdio-basic` - STDIO-based test
- `llm/llm-prompt-response` - LLM single-turn test
- `llm/llm-multi-turn` - LLM conversation test
- `llm/llm-function-calling` - LLM function calling test
- `llm/llm-cost-validation` - LLM cost tracking
- `integration/integration-e2e` - End-to-end workflow

## Code Style

- Follow existing code style in the project
- Use type hints
- Add docstrings for public methods
- Write tests for new features

## Testing

- Run tests: `pytest tests/ -v`
- Generate coverage: `pytest --cov=tigerhill`
- Run specific test: `pytest tests/test_file.py::test_name`

## Documentation

- Update docs/ when adding features
- Keep examples/ up to date
- Document breaking changes in CHANGELOG.md

## When Modifying Templates

- Test template generation after changes
- Validate generated code syntax
- Update template documentation
- Add example configurations

## Best Practices

1. Use YAML configs for reproducibility
2. Version control config files
3. Use shared_params to reduce duplication
4. Name tests descriptively: `<resource>-<operation>`
5. Organize tests by feature/module

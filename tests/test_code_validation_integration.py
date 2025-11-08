"""
Integration tests for code validation functionality.

Tests the integration of code validation with:
- TraceStore
- Assertions system
- UniversalAgentTester
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from tigerhill.adapters import CLIAgentAdapter, UniversalAgentTester
from tigerhill.eval.assertions import run_assertions
from tigerhill.eval.code_validator import CodeExtractor, PythonValidator, CodeValidator
from tigerhill.storage.trace_store import TraceStore


class TestCodeExtractor:
    """Test CodeExtractor functionality"""

    def test_extract_single_python_block(self):
        """Test extracting a single Python code block"""
        text = """
Here's some Python code:

```python
def hello():
    print("Hello, World!")
```

That's it!
"""
        blocks = CodeExtractor.extract_code_blocks(text)
        assert len(blocks) == 1
        assert blocks[0]["language"] == "python"
        assert "def hello" in blocks[0]["code"]

    def test_extract_multiple_blocks(self):
        """Test extracting multiple code blocks"""
        text = """
Python:
```python
print("Python")
```

JavaScript:
```javascript
console.log("JS")
```
"""
        blocks = CodeExtractor.extract_code_blocks(text)
        assert len(blocks) == 2
        assert blocks[0]["language"] == "python"
        assert blocks[1]["language"] == "javascript"

    def test_extract_first_code(self):
        """Test extracting first code block of specific language"""
        text = """
```javascript
console.log("First")
```

```python
print("Second")
```

```python
print("Third")
```
"""
        python_code = CodeExtractor.extract_first_code(text, language="python")
        assert python_code is not None
        assert 'print("Second")' in python_code

    def test_no_code_blocks(self):
        """Test handling text with no code blocks"""
        text = "Just plain text, no code here."
        blocks = CodeExtractor.extract_code_blocks(text)
        assert len(blocks) == 0

        python_code = CodeExtractor.extract_first_code(text, language="python")
        assert python_code is None


class TestPythonValidator:
    """Test PythonValidator functionality"""

    def test_syntax_check_valid_code(self):
        """Test syntax check on valid Python code"""
        code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
        success, error = PythonValidator.check_syntax(code)
        assert success is True
        assert error is None

    def test_syntax_check_invalid_code(self):
        """Test syntax check on invalid Python code"""
        code = """
def broken(x)  # Missing colon
    return x
"""
        success, error = PythonValidator.check_syntax(code)
        assert success is False
        assert error is not None
        assert "SyntaxError" in error

    def test_execute_simple_code(self):
        """Test executing simple Python code"""
        code = """
result = 2 + 2
print(result)
"""
        success, stdout, stderr = PythonValidator.execute_code(code, timeout=5)
        assert success is True
        assert "4" in stdout
        assert stderr == ""

    def test_execute_code_with_error(self):
        """Test executing code that raises an error"""
        code = """
x = 1 / 0  # Division by zero
"""
        success, stdout, stderr = PythonValidator.execute_code(code, timeout=5)
        assert success is False
        assert "ZeroDivisionError" in stderr


class TestCodeValidator:
    """Test unified CodeValidator interface"""

    def test_validate_syntax(self):
        """Test syntax validation"""
        validator = CodeValidator()
        text = """
Here's a function:

```python
def add(a, b):
    return a + b
```
"""
        result = validator.validate(
            text,
            language="python",
            validation_type="syntax"
        )

        assert result["ok"] is True
        assert result["validation_type"] == "syntax"
        assert result["language"] == "python"
        assert "def add" in result["extracted_code"]

    def test_validate_syntax_error(self):
        """Test validation of code with syntax error"""
        validator = CodeValidator()
        text = """
```python
def broken(x)
    return x
```
"""
        result = validator.validate(
            text,
            language="python",
            validation_type="syntax"
        )

        assert result["ok"] is False
        assert "SyntaxError" in result["details"]

    def test_validate_execution(self):
        """Test code execution validation"""
        validator = CodeValidator()
        text = """
```python
print("Hello from validator!")
```
"""
        result = validator.validate(
            text,
            language="python",
            validation_type="execution",
            timeout=10
        )

        assert result["ok"] is True
        assert result["validation_type"] == "execution"
        assert "Hello from validator!" in result["details"]

    def test_validate_no_code_block(self):
        """Test validation when no code block is found"""
        validator = CodeValidator()
        text = "Just plain text, no code."

        result = validator.validate(
            text,
            language="python",
            validation_type="syntax"
        )

        assert result["ok"] is False
        assert "No python code block found" in result["details"]


class TestCodeValidationAssertion:
    """Test code_validation assertion type"""

    def test_code_validation_assertion_syntax(self):
        """Test code_validation assertion for syntax"""
        llm_output = """
Here's a factorial function:

```python
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
```
"""
        assertions = [
            {
                "type": "code_validation",
                "language": "python",
                "validation_type": "syntax"
            }
        ]

        results = run_assertions(llm_output, assertions)
        assert len(results) == 1
        assert results[0]["ok"] is True
        assert results[0]["type"] == "code_validation"

    def test_code_validation_assertion_with_syntax_error(self):
        """Test code_validation assertion detects syntax errors"""
        llm_output = """
```python
def broken(x)
    return x
```
"""
        assertions = [
            {
                "type": "code_validation",
                "language": "python",
                "validation_type": "syntax"
            }
        ]

        results = run_assertions(llm_output, assertions)
        assert len(results) == 1
        assert results[0]["ok"] is False

    def test_mixed_assertions(self):
        """Test mixing code_validation with other assertion types"""
        llm_output = """
Here's a prime number checker:

```python
def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True
```

This implementation is efficient.
"""
        assertions = [
            {"type": "contains", "expected": "is_prime"},
            {"type": "contains", "expected": "efficient"},
            {
                "type": "code_validation",
                "language": "python",
                "validation_type": "syntax"
            },
            {
                "type": "code_validation",
                "language": "python",
                "validation_type": "execution",
                "timeout": 10
            }
        ]

        results = run_assertions(llm_output, assertions)
        assert len(results) == 4
        # Check all assertions passed
        assert all(r["ok"] for r in results)


class TestIntegrationWithUniversalTester:
    """Test code validation integration with UniversalAgentTester"""

    def test_agent_test_with_code_validation(self):
        """Test complete workflow: Agent -> Trace -> Code Validation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            store = TraceStore(storage_path=tmpdir)
            adapter = CLIAgentAdapter(
                command="python",
                args_template=[
                    "-c",
                    "print('```python\\ndef add(a, b):\\n    return a + b\\n```')"
                ],
                timeout=10
            )
            tester = UniversalAgentTester(adapter, store)

            # Define task with code validation
            task = {
                "prompt": "Generate an add function",
                "assertions": [
                    {"type": "contains", "expected": "def add"},
                    {
                        "type": "code_validation",
                        "language": "python",
                        "validation_type": "syntax"
                    }
                ]
            }

            # Execute test
            result = tester.test(task, agent_name="code_generator")

            # Verify
            assert result["success"] is True
            assert result["passed"] == 2
            assert result["total"] == 2

            # Check trace
            trace_id = result["trace_id"]
            summary = store.get_summary(trace_id)
            assert summary["agent_name"] == "code_generator"
            assert summary["total_events"] > 0

    def test_batch_with_code_validation(self):
        """Test batch testing with code validation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TraceStore(storage_path=tmpdir)
            adapter = CLIAgentAdapter(
                command="python",
                args_template=[
                    "-c",
                    "print('```python\\nprint(\"test\")\\n```')"
                ],
                timeout=10
            )
            tester = UniversalAgentTester(adapter, store)

            tasks = [
                {
                    "prompt": "Task 1",
                    "assertions": [
                        {
                            "type": "code_validation",
                            "language": "python",
                            "validation_type": "syntax"
                        }
                    ]
                },
                {
                    "prompt": "Task 2",
                    "assertions": [
                        {
                            "type": "code_validation",
                            "language": "python",
                            "validation_type": "syntax"
                        }
                    ]
                }
            ]

            results = tester.test_batch(tasks, agent_name="batch_tester")
            assert len(results) == 2
            assert all(r["success"] for r in results)

            report = tester.generate_report(results)
            assert report["total_tests"] == 2
            assert report["successful_tests"] == 2
            assert report["assertion_pass_rate"] == 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

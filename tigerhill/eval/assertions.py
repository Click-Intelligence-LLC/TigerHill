"""Simple assertion helpers for dataset-driven evaluations."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional

# Code validation import (lazy loading to avoid circular dependencies)
_code_validator_instance = None


@dataclass
class AssertionResult:
    type: str
    ok: bool
    expected: Any
    actual: Any
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "ok": self.ok,
            "expected": self.expected,
            "actual": self.actual,
            "message": self.message,
        }


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return str(value)


def _contains(output: str, spec: Dict[str, Any]) -> AssertionResult:
    expected = _stringify(spec.get("expected", ""))
    ok = expected in output
    message = "" if ok else "substring not found"
    return AssertionResult("contains", ok, expected=expected, actual=output, message=message)


def _equals(output: str, spec: Dict[str, Any]) -> AssertionResult:
    expected_raw = spec.get("expected", "")
    normalize = spec.get("normalize", False)
    if normalize:
        actual = output.strip()
        expected = _stringify(expected_raw).strip()
    else:
        actual = output
        expected = _stringify(expected_raw)
    ok = actual == expected
    message = "" if ok else "values differ"
    return AssertionResult("equals", ok, expected=expected, actual=actual, message=message)


def _regex(output: str, spec: Dict[str, Any]) -> AssertionResult:
    pattern = spec.get("pattern")
    flags = 0
    if spec.get("ignore_case"):
        flags |= re.IGNORECASE
    try:
        regex = re.compile(pattern, flags=flags)
    except re.error as exc:
        return AssertionResult(
            "regex",
            ok=False,
            expected=pattern,
            actual=output,
            message=f"invalid regex: {exc}",
        )

    match = regex.search(output)
    ok = match is not None
    message = "" if ok else "pattern not matched"
    return AssertionResult("regex", ok, expected=pattern, actual=output, message=message)


def _starts_with(output: str, spec: Dict[str, Any]) -> AssertionResult:
    expected = _stringify(spec.get("expected", ""))
    ok = output.startswith(expected)
    message = "" if ok else "output does not start with expected prefix"
    return AssertionResult("starts_with", ok, expected=expected, actual=output, message=message)


def _ends_with(output: str, spec: Dict[str, Any]) -> AssertionResult:
    expected = _stringify(spec.get("expected", ""))
    ok = output.endswith(expected)
    message = "" if ok else "output does not end with expected suffix"
    return AssertionResult("ends_with", ok, expected=expected, actual=output, message=message)


def _code_validation(output: str, spec: Dict[str, Any]) -> AssertionResult:
    """
    验证生成的代码

    spec 参数:
        - language: 编程语言 (default: "python")
        - validation_type: 验证类型 ("syntax", "execution", "test")
        - timeout: 超时时间（秒）
        - test_command: 测试命令（仅用于 validation_type="test"）
    """
    global _code_validator_instance

    # Lazy import
    if _code_validator_instance is None:
        from tigerhill.eval.code_validator import CodeValidator
        _code_validator_instance = CodeValidator()

    language = spec.get("language", "python")
    validation_type = spec.get("validation_type", "syntax")

    # 执行验证
    result = _code_validator_instance.validate(
        output,
        language=language,
        validation_type=validation_type,
        timeout=spec.get("timeout", 30),
        test_command=spec.get("test_command", "pytest")
    )

    return AssertionResult(
        "code_validation",
        ok=result["ok"],
        expected=f"{validation_type} validation for {language}",
        actual=result.get("extracted_code", "")[:200] + "...",  # 截断显示
        message=result.get("details", "")
    )


_HANDLER_REGISTRY: Dict[str, Callable[[str, Dict[str, Any]], AssertionResult]] = {
    "contains": _contains,
    "equals": _equals,
    "regex": _regex,
    "starts_with": _starts_with,
    "ends_with": _ends_with,
    "code_validation": _code_validation,
}


def _maybe_negate(result: AssertionResult, negate: bool) -> AssertionResult:
    if not negate:
        return result
    message = result.message or ""
    message = f"negated assertion expected failure" if result.ok else message
    return AssertionResult(
        type=result.type,
        ok=not result.ok,
        expected=result.expected,
        actual=result.actual,
        message=message,
    )


def run_assertions(output: Any, assertions: Optional[Iterable[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Evaluate assertion specs against an output string.

    Each assertion dict must include a ``type`` key that corresponds to one of the
    supported handlers in ``_HANDLER_REGISTRY``. Unsupported types are reported as
    failed assertions so dataset authors can spot typos quickly.
    """

    results: List[Dict[str, Any]] = []
    output_text = _stringify(output)

    for spec in assertions or []:
        a_type = spec.get("type", "contains")
        handler = _HANDLER_REGISTRY.get(a_type)
        if not handler:
            result = AssertionResult(
                a_type,
                ok=False,
                expected=spec.get("expected"),
                actual=output_text,
                message=f"unknown assertion type '{a_type}'",
            )
        else:
            result = handler(output_text, spec)

        negate = bool(spec.get("negate"))
        result = _maybe_negate(result, negate)
        results.append(result.to_dict())

    return results


__all__ = ["run_assertions"]

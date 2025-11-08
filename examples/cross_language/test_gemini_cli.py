"""
TigerHill example: testing the local Gemini CLI agent via CLIAgentAdapter.

Pre-requisites:
1. Install and build the Gemini CLI repository that lives next to this TigerHill repo:
     cd ../gemini-cli
     npm install              # or npm ci
     npm run build            # generates bundle/gemini.js
2. Export GEMINI_API_KEY (or other supported auth vars) so the CLI can call Gemini.
3. (Optional, required for AgentBay validation) Export AGENTBAY_API_KEY and ensure
   the AgentBay SDK dependencies are installed.

Run this example from the TigerHill repo root:
    python examples/cross_language/test_gemini_cli.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import base64
import re
import textwrap
from typing import Any, Dict, Optional, List

# Ensure the TigerHill package is importable when running directly from source.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tigerhill.adapters import CLIAgentAdapter, UniversalAgentTester
from tigerhill.storage.trace_store import TraceStore, EventType
from tigerhill.agentbay.client import AgentBayClient


def resolve_gemini_bundle() -> Path:
    """Resolve the path to the locally built gemini.js entrypoint."""
    repo_root = Path(__file__).resolve().parents[2]
    bundle_path = (repo_root.parent / "gemini-cli" / "bundle" / "gemini.js").resolve()
    if not bundle_path.exists():
        raise FileNotFoundError(
            f"Gemini CLI bundle not found at {bundle_path}. "
            "Run `npm install && npm run build` inside ../gemini-cli first."
        )
    return bundle_path


def ensure_auth_env() -> None:
    """Fail early if no Gemini authentication is configured."""
    if not any(
        os.getenv(var)
        for var in (
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
            "GOOGLE_GENAI_API_KEY",
            "GOOGLE_GENAI_USE_VERTEXAI",
        )
    ):
        raise EnvironmentError(
            "No Gemini authentication environment variables detected. "
            "Set GEMINI_API_KEY (or compatible auth vars) before running this script."
        )


def ensure_agentbay_env() -> None:
    """Ensure AgentBay credentials are present."""
    if not os.getenv("AGENTBAY_API_KEY"):
        raise EnvironmentError(
            "AGENTBAY_API_KEY not found. Export it to enable AgentBay validation."
        )


def build_adapter(bundle_path: Path) -> CLIAgentAdapter:
    """Create a CLI adapter that invokes the local Gemini CLI bundle."""
    return CLIAgentAdapter(
        command="node",
        args_template=[
            str(bundle_path),
            "-p",
            "{prompt}",
            "--output-format",
            "text",
        ],
        timeout=180,
    )


def build_task(
    prompt: str,
    assertions: List[Dict[str, Any]],
    bundle_path: Path,
    description: str
) -> Dict[str, Any]:
    """Construct a task dict with rich context for tracing."""
    command_template = f"node {bundle_path} -p <prompt> --output-format text"
    return {
        "prompt": prompt,
        "assertions": assertions,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Gemini CLI is being exercised by the TigerHill automated testing harness. "
                    "Follow the user's instruction exactly and strive for deterministic output."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "trace_metadata": {
            "adapter_command": command_template,
            "task": description,
        },
    }


def _extract_python_code(markdown: str) -> Optional[str]:
    """Pull the first Python code block from markdown output."""
    match = re.search(r"```python\s+(.*?)```", markdown, re.DOTALL | re.IGNORECASE)
    if not match:
        return None
    return textwrap.dedent(match.group(1)).strip()


def _extract_pytest_command(markdown: str) -> Optional[str]:
    """Find the first pytest command mentioned in the output."""
    match = re.search(r"^\s*(pytest[^\n\r]*)", markdown, re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip()


def _write_remote_file(client: AgentBayClient, session_id: str, path: str, content: str) -> Dict[str, str]:
    """Upload content to AgentBay session using base64 encoding."""
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
    script = textwrap.dedent(
        f"""
        python - <<'PY'
        import base64
        from pathlib import Path
        data = {encoded!r}
        target = Path({path!r})
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base64.b64decode(data))
        PY
        """
    ).strip()
    return client.execute_command(session_id, script)


def _record_tool_event(store: TraceStore, trace_id: str, command: str, result: Dict[str, str]) -> None:
    """Record AgentBay command invocation and result into the trace."""
    store.write_event(
        {
            "type": "tool_call",
            "tool": "AgentBay",
            "command": command,
        },
        trace_id=trace_id,
        event_type=EventType.TOOL_CALL,
    )
    store.write_event(
        {
            "type": "tool_result",
            "tool": "AgentBay",
            "command": command,
            "exit_code": result.get("exit_code"),
            "output": result.get("output"),
            "error": result.get("error"),
        },
        trace_id=trace_id,
        event_type=EventType.TOOL_RESULT,
    )


def validate_with_agentbay(store: TraceStore, trace_id: str, output: Optional[str]) -> str:
    """
    Use AgentBay to validate generated artifacts.

    Returns:
        "pass", "fail", or "skipped"
    """
    if not output:
        store.write_event(
            {
                "type": "tool_result",
                "tool": "AgentBay",
                "command": "No output to validate",
                "exit_code": None,
                "error": "Skipped AgentBay validation due to empty output.",
            },
            trace_id=trace_id,
            event_type=EventType.TOOL_RESULT,
        )
        return "skipped"

    code = _extract_python_code(output)
    if not code:
        store.write_event(
            {
                "type": "tool_result",
                "tool": "AgentBay",
                "command": "Extract implementation code",
                "exit_code": None,
                "error": "No Python code block found in output. Validation skipped.",
            },
            trace_id=trace_id,
            event_type=EventType.TOOL_RESULT,
        )
        return "skipped"

    try:
        ensure_agentbay_env()
    except EnvironmentError as exc:
        store.write_event(
            {
                "type": "tool_result",
                "tool": "AgentBay",
                "command": "AgentBay credential check",
                "exit_code": None,
                "error": str(exc),
            },
            trace_id=trace_id,
            event_type=EventType.TOOL_RESULT,
        )
        return "skipped"

    pytest_command = _extract_pytest_command(output)

    client = AgentBayClient()
    session = client.create_session()
    session_id = session["session_id"]
    try:
        # Upload implementation code
        result = _write_remote_file(client, session_id, "tigerhill_artifacts/agent.py", code)
        _record_tool_event(store, trace_id, "upload agent.py", result)
        if result.get("exit_code", 0) != 0:
            return "fail"

        # Basic syntax validation
        compile_cmd = "cd tigerhill_artifacts && python -m compileall agent.py"
        result = client.execute_command(session_id, compile_cmd)
        _record_tool_event(store, trace_id, compile_cmd, result)
        if result.get("exit_code", 1) != 0:
            return "fail"

        if pytest_command:
            # Attempt to run pytest if a command is provided
            run_pytest = f"cd tigerhill_artifacts && {pytest_command}"
            result = client.execute_command(session_id, run_pytest)
            _record_tool_event(store, trace_id, run_pytest, result)
            if result.get("exit_code", 1) != 0:
                return "fail"
        else:
            store.write_event(
                {
                    "type": "tool_result",
                    "tool": "AgentBay",
                    "command": "pytest command detection",
                    "exit_code": None,
                    "output": "No pytest command detected; skipped pytest execution.",
                },
                trace_id=trace_id,
                event_type=EventType.TOOL_RESULT,
            )

        return "pass"
    except Exception as exc:  # pylint: disable=broad-except
        store.write_event(
            {
                "type": "tool_result",
                "tool": "AgentBay",
                "command": "AgentBay validation failure",
                "exit_code": None,
                "error": str(exc),
            },
            trace_id=trace_id,
            event_type=EventType.TOOL_RESULT,
        )
        return "fail"
    finally:
        client.delete_session(session_id)


def main() -> int:
    try:
        ensure_auth_env()
        bundle_path = resolve_gemini_bundle()
    except (EnvironmentError, FileNotFoundError) as exc:
        print(f"[TigerHill][Gemini CLI] {exc}", file=sys.stderr)
        return 1

    store = TraceStore(storage_path="test_traces/gemini_cli", auto_save=True)
    adapter = build_adapter(bundle_path)
    tester = UniversalAgentTester(adapter, store)

    tasks = [
        build_task(
            prompt=(
                "You are participating in an automated integration check. "
                "Reply with exactly the phrase 'TigerHill integration test pass' "
                "and nothing else."
            ),
            assertions=[
                {"type": "contains", "expected": "TigerHill integration test pass"},
            ],
            bundle_path=bundle_path,
            description="Literal response compliance check",
        ),
        build_task(
            prompt=(
                "Act as a senior LangChain engineer. Based on the latest LangChain "
                "developer documentation, produce a comprehensive delivery package "
                "for an agent that can crawl any user-specified website and extract "
                "arbitrary data on demand. The package must include the following "
                "sections with exact headings:\n"
                "1. LANGCHAIN REFERENCE SUMMARY – key APIs or modules you will use.\n"
                "2. SYSTEM ARCHITECTURE – bullet list covering ingestion, crawling logic, "
                "tool integration, safety controls, and data output.\n"
                "3. IMPLEMENTATION – Python code using LangChain to define the agent, "
                "tools, and workflow.\n"
                "4. TEST PLAN – describe automated tests and provide concrete pytest "
                "commands.\n"
                "5. USAGE GUIDE – numbered steps for running the agent locally.\n"
                "6. TEST REPORT – summarize expected test outcomes.\n"
                "Ensure the response is self-contained, uses Markdown headings that match "
                "the section titles above exactly, and render EACH heading as a level-2 "
                "Markdown header using the `##` prefix (for example, `## LANGCHAIN REFERENCE SUMMARY`). "
                "Explicitly mention web scraping capabilities, LangChain components, and pytest, "
                "and include the literal phrase 'web scraping' at least once."
            ),
            assertions=[
                {"type": "contains", "expected": "## LANGCHAIN REFERENCE SUMMARY"},
                {"type": "contains", "expected": "LangChain"},
                {"type": "contains", "expected": "web scraping"},
                {"type": "contains", "expected": "pytest"},
                {"type": "contains", "expected": "## SYSTEM ARCHITECTURE"},
                {"type": "contains", "expected": "## IMPLEMENTATION"},
                {"type": "contains", "expected": "## TEST PLAN"},
                {"type": "contains", "expected": "## USAGE GUIDE"},
                {"type": "contains", "expected": "## TEST REPORT"},
            ],
            bundle_path=bundle_path,
            description="LangChain web crawler blueprint with validation",
        ),
    ]

    results = tester.test_batch(tasks, agent_name="gemini_cli")
    report = tester.generate_report(results)

    print("\n=== Gemini CLI TigerHill Report ===")
    print(f"Total tests: {report['total_tests']}")
    print(f"Successful tests: {report['successful_tests']}")
    print(f"Failed tests: {report['failed_tests']}")
    print(f"Assertion pass rate: {report['assertion_pass_rate']:.1f}%")

    for idx, result in enumerate(results, 1):
        status = "PASS" if result.get("success") else "FAIL"
        print(f"\n[{status}] Test {idx}")
        print(f"Prompt: {tasks[idx-1]['prompt']}")
        if result.get("output") is not None:
            print(f"Output: {result['output']}")
        if not result.get("success"):
            print(f"Error: {result.get('error', 'Assertions failed')}")

    validation_status = "skipped"
    if len(results) >= 2:
        print("\n--- AgentBay Validation ---")
        validation_status = validate_with_agentbay(store, results[1]["trace_id"], results[1].get("output"))
        print(f"AgentBay validation result: {validation_status}")
        store.save_all()

    overall_success = report["failed_tests"] == 0 and validation_status != "fail"
    return 0 if overall_success else 2


if __name__ == "__main__":
    raise SystemExit(main())

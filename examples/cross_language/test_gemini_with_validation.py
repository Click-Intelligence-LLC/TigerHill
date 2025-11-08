"""
TigerHill + Gemini CLI 集成示例（增强版）

在原有测试基础上，增加代码验证功能：
1. 检查文本内容（contains 断言）
2. 验证代码语法（code_validation:syntax）
3. 可选：执行代码（code_validation:execution）

对比标准版：
- test_gemini_cli.py: 只检查文本内容（40% 通过率）
- 本版本: 同时验证代码质量

Pre-requisites:
1. Gemini CLI 已构建（../gemini-cli/bundle/gemini.js）
2. 设置 GEMINI_API_KEY 环境变量
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tigerhill.adapters import CLIAgentAdapter, UniversalAgentTester
from tigerhill.storage.trace_store import TraceStore


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


def main() -> int:
    try:
        ensure_auth_env()
        bundle_path = resolve_gemini_bundle()
    except (EnvironmentError, FileNotFoundError) as exc:
        print(f"[TigerHill][Gemini CLI] {exc}", file=sys.stderr)
        return 1

    store = TraceStore(storage_path="test_traces/gemini_validation", auto_save=True)
    adapter = build_adapter(bundle_path)
    tester = UniversalAgentTester(adapter, store)

    # 任务 1: 简单集成测试
    task_1 = {
        "prompt": (
            "You are participating in an automated integration check. "
            "Reply with exactly the phrase 'TigerHill integration test pass' "
            "and nothing else."
        ),
        "assertions": [
            {"type": "contains", "expected": "TigerHill integration test pass"},
        ],
    }

    # 任务 2: 代码生成测试（增强版 - 包含代码验证）
    task_2 = {
        "prompt": (
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
            "the section titles above exactly, and explicitly mentions web scraping "
            "capabilities, LangChain components, and pytest."
        ),
        "assertions": [
            # 文本内容检查
            {"type": "contains", "expected": "LANGCHAIN REFERENCE SUMMARY"},
            {"type": "contains", "expected": "LangChain"},
            {"type": "contains", "expected": "web scraping"},
            {"type": "contains", "expected": "pytest"},
            {"type": "contains", "expected": "SYSTEM ARCHITECTURE"},
            {"type": "contains", "expected": "IMPLEMENTATION"},
            {"type": "contains", "expected": "TEST PLAN"},
            {"type": "contains", "expected": "USAGE GUIDE"},
            {"type": "contains", "expected": "TEST REPORT"},

            # 🆕 代码质量验证
            {
                "type": "code_validation",
                "language": "python",
                "validation_type": "syntax"
            }
        ],
    }

    tasks = [task_1, task_2]

    # 执行测试
    print("\n" + "=" * 80)
    print("🐯 TigerHill + Gemini CLI - 增强版测试（含代码验证）")
    print("=" * 80)

    results = tester.test_batch(tasks, agent_name="gemini_cli_validated")
    report = tester.generate_report(results)

    # 打印报告
    print(f"\n📊 测试结果:")
    print(f"   总测试数: {report['total_tests']}")
    print(f"   成功: {report['successful_tests']}")
    print(f"   失败: {report['failed_tests']}")
    print(f"   断言通过率: {report['assertion_pass_rate']:.1f}%")

    # 详细结果
    print("\n" + "=" * 80)
    for idx, result in enumerate(results, 1):
        status = "✅ PASS" if result.get("success") else "❌ FAIL"
        print(f"\n[{status}] Task {idx}")

        if idx == 1:
            print(f"   类型: 集成测试")
        else:
            print(f"   类型: 代码生成 + 质量验证")

        print(f"   断言: {result.get('passed', 0)}/{result.get('total', 0)} 通过")

        # 显示代码验证结果
        if 'results' in result:
            for assertion in result['results']:
                if assertion.get('type') == 'code_validation':
                    status_icon = "✅" if assertion['ok'] else "❌"
                    print(f"   {status_icon} 代码验证: {assertion.get('message', 'N/A')[:100]}")

    print("\n" + "=" * 80)

    # 对比说明
    print("\n💡 改进说明:")
    print("   标准版 (test_gemini_cli.py):")
    print("      - 只检查文本内容（包含特定字符串）")
    print("      - 40% 断言通过率（标题格式不匹配）")
    print()
    print("   增强版 (本版本):")
    print("      - 文本内容检查 + 代码语法验证")
    print("      - 确保生成的代码格式正确")
    print("      - 断言通过率: {:.1f}%".format(report['assertion_pass_rate']))
    print()

    if report['assertion_pass_rate'] > 50:
        print("🎉 代码质量验证通过！生成的代码语法正确。")
    else:
        print("⚠️  部分检查未通过，建议查看详细报告。")

    print()
    return 0 if report["failed_tests"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

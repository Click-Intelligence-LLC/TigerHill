"""
批量测试多语言 Agent

演示如何使用 TigerHill 同时测试多种编程语言编写的 Agent。

支持的语言:
- Node.js (HTTP API)
- Go (CLI)
- Python (本地函数)

使用前提:
1. Node.js Agent 运行中: node nodejs_agent.js
2. Go Agent 已编译: go build -o go_agent go_agent.go

运行测试:
    python examples/cross_language/batch_test_multilang.py
"""

import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tigerhill.adapters import (
    HTTPAgentAdapter,
    CLIAgentAdapter,
    UniversalAgentTester
)
from tigerhill.storage.trace_store import TraceStore


class PythonFunctionAdapter:
    """Python 函数适配器 - 直接调用 Python 函数"""

    def __init__(self, func):
        self.func = func

    def invoke(self, prompt: str, **kwargs) -> str:
        return self.func(prompt)

    def cleanup(self):
        pass


def python_simple_agent(prompt: str) -> str:
    """一个简单的 Python Agent 函数"""
    if "计算" in prompt or "calculate" in prompt.lower():
        return "Python Agent: 计算功能已激活"
    elif "代码" in prompt or "code" in prompt.lower():
        return "Python Agent: 代码生成功能"
    else:
        return f"Python Agent 处理: {prompt}"


def check_nodejs_available():
    """检查 Node.js Agent 是否可用"""
    try:
        import requests
        response = requests.get("http://localhost:3000/health", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def check_go_available():
    """检查 Go Agent 是否可用"""
    agent_path = Path(__file__).parent / "go_agent"
    return agent_path.exists()


def create_test_suite() -> List[Dict[str, Any]]:
    """创建跨语言测试套件"""

    test_suite = []

    # Node.js Agent 测试配置
    if check_nodejs_available():
        test_suite.append({
            "name": "nodejs_http_agent",
            "language": "Node.js",
            "adapter": HTTPAgentAdapter("http://localhost:3000", "/api/agent"),
            "tasks": [
                {
                    "prompt": "计算 10 + 20",
                    "assertions": [{"type": "contains", "expected": "30"}]
                },
                {
                    "prompt": "什么是质数",
                    "assertions": [{"type": "contains", "expected": "质数"}]
                }
            ]
        })
    else:
        print("⚠️  Node.js Agent 不可用，跳过相关测试")

    # Go Agent 测试配置
    if check_go_available():
        agent_path = str(Path(__file__).parent / "go_agent")
        test_suite.append({
            "name": "go_cli_agent",
            "language": "Go",
            "adapter": CLIAgentAdapter(agent_path, ["{prompt}"]),
            "tasks": [
                {
                    "prompt": "列出文件",
                    "assertions": [{"type": "contains", "expected": "文件"}]
                },
                {
                    "prompt": "生成 Go 代码",
                    "assertions": [{"type": "contains", "expected": "func"}]
                }
            ]
        })
    else:
        print("⚠️  Go Agent 不可用，跳过相关测试")

    # Python Agent 测试配置
    test_suite.append({
        "name": "python_function_agent",
        "language": "Python",
        "adapter": PythonFunctionAdapter(python_simple_agent),
        "tasks": [
            {
                "prompt": "计算数据",
                "assertions": [{"type": "contains", "expected": "Python Agent"}]
            },
            {
                "prompt": "生成代码",
                "assertions": [{"type": "contains", "expected": "代码"}]
            }
        ]
    })

    return test_suite


def run_batch_tests():
    """执行批量多语言测试"""

    print("=" * 70)
    print(" " * 20 + "TigerHill 跨语言批量测试")
    print("=" * 70)

    # 创建主 TraceStore
    store = TraceStore(storage_path="./traces/multilang_batch")

    # 获取测试套件
    test_suite = create_test_suite()

    if not test_suite:
        print("\n❌ 没有可用的 Agent 进行测试")
        print("\n请确保至少有一个 Agent 可用:")
        print("  - Node.js: node examples/cross_language/nodejs_agent.js")
        print("  - Go: go build -o examples/cross_language/go_agent examples/cross_language/go_agent.go")
        return

    print(f"\n检测到 {len(test_suite)} 个可用 Agent\n")

    # 存储所有结果
    all_results = []
    agent_summaries = []

    # 逐个测试每个 Agent
    for config in test_suite:
        agent_name = config["name"]
        language = config["language"]
        adapter = config["adapter"]
        tasks = config["tasks"]

        print("=" * 70)
        print(f"测试 {language} Agent: {agent_name}")
        print("=" * 70)

        # 创建测试器
        tester = UniversalAgentTester(adapter, store)

        # 执行测试
        task_results = []
        for i, task in enumerate(tasks, 1):
            print(f"\n执行任务 {i}/{len(tasks)}: {task['prompt'][:40]}...")

            try:
                result = tester.test(
                    task=task,
                    agent_name=f"{agent_name}_task_{i}",
                    metadata={"language": language, "task_index": i}
                )

                task_results.append(result)
                all_results.append(result)

                success = "✅" if result.get("success", False) else "❌"
                print(f"  结果: {success}")
                print(f"  断言: {result['passed']}/{result['total']} 通过")
                print(f"  耗时: {result['duration']:.3f} 秒")

            except Exception as e:
                print(f"  ❌ 失败: {e}")
                all_results.append({
                    "success": False,
                    "passed": 0,
                    "total": len(task.get("assertions", [])),
                    "duration": 0,
                    "error": str(e)
                })

        # 生成该 Agent 的汇总
        agent_report = tester.generate_report(task_results)
        agent_summaries.append({
            "agent_name": agent_name,
            "language": language,
            "report": agent_report
        })

        print(f"\n{language} Agent 汇总:")
        print(f"  成功率: {agent_report['success_rate']:.1f}%")
        print(f"  断言通过率: {agent_report['assertion_pass_rate']:.1f}%")
        print(f"  平均耗时: {agent_report['average_duration']:.3f} 秒")

    # 生成总体报告
    print("\n" + "=" * 70)
    print(" " * 25 + "总体测试报告")
    print("=" * 70)

    total_tests = sum(s["report"]["total_tests"] for s in agent_summaries)
    total_successful = sum(s["report"]["successful_tests"] for s in agent_summaries)
    total_assertions = sum(s["report"]["total_assertions"] for s in agent_summaries)
    total_passed = sum(s["report"]["passed_assertions"] for s in agent_summaries)
    total_duration = sum(s["report"]["total_duration"] for s in agent_summaries)

    print(f"\n测试的语言数: {len(agent_summaries)}")
    print(f"总测试数: {total_tests}")
    print(f"成功测试: {total_successful}")
    print(f"失败测试: {total_tests - total_successful}")
    print(f"总体成功率: {total_successful/total_tests*100:.1f}%")
    print(f"\n总断言数: {total_assertions}")
    print(f"通过断言: {total_passed}")
    print(f"断言通过率: {total_passed/total_assertions*100:.1f}%")
    print(f"\n总耗时: {total_duration:.2f} 秒")
    print(f"平均每测试: {total_duration/total_tests:.3f} 秒")

    # 按语言分组统计
    print("\n" + "-" * 70)
    print("按语言统计:")
    print("-" * 70)

    for summary in agent_summaries:
        language = summary["language"]
        report = summary["report"]

        print(f"\n{language}:")
        print(f"  测试数: {report['total_tests']}")
        print(f"  成功率: {report['success_rate']:.1f}%")
        print(f"  断言通过率: {report['assertion_pass_rate']:.1f}%")
        print(f"  平均耗时: {report['average_duration']:.3f} 秒")

    print("\n" + "=" * 70)
    print("✅ 批量测试完成")
    print("=" * 70)

    print("\n追踪数据保存在: traces/multilang_batch/")

    return {
        "total_tests": total_tests,
        "successful_tests": total_successful,
        "total_assertions": total_assertions,
        "passed_assertions": total_passed,
        "agent_summaries": agent_summaries
    }


def run_performance_comparison():
    """运行性能对比测试"""

    print("\n" + "=" * 70)
    print(" " * 20 + "跨语言性能对比")
    print("=" * 70)

    test_suite = create_test_suite()

    if len(test_suite) < 2:
        print("\n⚠️  至少需要2个 Agent 进行性能对比")
        return

    # 相同的测试任务
    common_task = {
        "prompt": "执行标准测试任务",
        "assertions": []
    }

    store = TraceStore(storage_path="./traces/performance_comparison")
    performance_results = []

    for config in test_suite:
        agent_name = config["name"]
        language = config["language"]
        adapter = config["adapter"]

        print(f"\n测试 {language}...")

        # 多次运行取平均
        durations = []
        for run in range(3):
            tester = UniversalAgentTester(adapter, store)
            result = tester.test(
                task=common_task,
                agent_name=f"{agent_name}_perf_{run}"
            )
            durations.append(result["duration"])
            time.sleep(0.1)  # 短暂延迟

        avg_duration = sum(durations) / len(durations)
        performance_results.append({
            "language": language,
            "agent_name": agent_name,
            "average_duration": avg_duration,
            "min_duration": min(durations),
            "max_duration": max(durations)
        })

    # 显示对比结果
    print("\n" + "-" * 70)
    print("性能对比结果 (执行相同任务):")
    print("-" * 70)

    # 排序
    performance_results.sort(key=lambda x: x["average_duration"])

    for i, result in enumerate(performance_results, 1):
        print(f"\n{i}. {result['language']} Agent")
        print(f"   平均: {result['average_duration']:.3f} 秒")
        print(f"   最快: {result['min_duration']:.3f} 秒")
        print(f"   最慢: {result['max_duration']:.3f} 秒")

    # 相对性能
    if len(performance_results) > 1:
        baseline = performance_results[0]["average_duration"]
        print("\n相对性能 (以最快为基准):")
        for result in performance_results:
            ratio = result["average_duration"] / baseline
            print(f"  {result['language']}: {ratio:.2f}x")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    print("\n🚀 TigerHill - 跨语言批量测试\n")

    try:
        # 执行批量测试
        overall_report = run_batch_tests()

        # 执行性能对比（可选）
        if overall_report and overall_report["total_tests"] > 0:
            print("\n\n")
            # run_performance_comparison()  # 取消注释以运行性能对比

        print("\n✅ 所有测试完成！")

    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

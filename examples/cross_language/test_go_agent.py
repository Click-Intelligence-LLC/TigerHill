"""
测试 Go Agent 示例

演示如何使用 TigerHill 测试 Go 命令行 Agent。

使用前提:
1. 编译 Go Agent: go build -o go_agent go_agent.go
2. 确保可执行文件存在: ./go_agent

运行测试:
    python examples/cross_language/test_go_agent.py
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tigerhill.adapters import CLIAgentAdapter, UniversalAgentTester
from tigerhill.storage.trace_store import TraceStore


def check_go_agent_exists():
    """检查 Go Agent 是否已编译"""
    agent_path = Path(__file__).parent / "go_agent"
    return agent_path.exists()


def compile_go_agent():
    """编译 Go Agent"""
    import subprocess

    agent_dir = Path(__file__).parent
    go_file = agent_dir / "go_agent.go"
    output_file = agent_dir / "go_agent"

    print("正在编译 Go Agent...")
    try:
        result = subprocess.run(
            ["go", "build", "-o", str(output_file), str(go_file)],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            print(f"编译失败: {result.stderr}")
            return False

        print("✓ Go Agent 编译成功")
        return True

    except FileNotFoundError:
        print("❌ 错误: 未找到 Go 编译器")
        print("请安装 Go: https://golang.org/dl/")
        return False
    except Exception as e:
        print(f"编译出错: {e}")
        return False


def test_go_cli_agent():
    """测试 Go CLI Agent"""

    print("=" * 60)
    print("测试 Go CLI Agent")
    print("=" * 60)

    # 1. 初始化
    store = TraceStore(storage_path="./traces/go_agent")
    print("✓ TraceStore 初始化完成")

    # 2. 创建 CLI Agent 适配器
    agent_path = str(Path(__file__).parent / "go_agent")
    adapter = CLIAgentAdapter(
        command=agent_path,
        args_template=["{prompt}"],
        timeout=10
    )
    print("✓ CLI Agent 适配器创建完成")

    # 3. 创建通用测试器
    tester = UniversalAgentTester(adapter, store)
    print("✓ 通用测试器创建完成\n")

    # 4. 定义测试任务
    tasks = [
        {
            "prompt": "列出文件",
            "assertions": [
                {"type": "contains", "expected": "Go Agent"},
                {"type": "contains", "expected": "文件"}
            ]
        },
        {
            "prompt": "生成 Go 代码",
            "assertions": [
                {"type": "contains", "expected": "func"},
                {"type": "contains", "expected": "package"}
            ]
        },
        {
            "prompt": "分析代码质量",
            "assertions": [
                {"type": "contains", "expected": "分析"},
                {"type": "regex", "pattern": r"\d+"}
            ]
        }
    ]

    # 5. 执行批量测试
    print("开始批量测试...\n")
    results = tester.test_batch(tasks, agent_name="go_cli_agent")

    # 6. 显示每个测试的结果
    print("\n" + "=" * 60)
    print("测试结果详情")
    print("=" * 60)

    for i, result in enumerate(results, 1):
        success = "✅" if result.get("success", False) else "❌"
        print(f"\n测试 {i}:")
        print(f"  状态: {success}")
        print(f"  提示: {tasks[i-1]['prompt']}")
        print(f"  输出: {result.get('output', 'N/A')[:100]}")
        print(f"  断言: {result['passed']}/{result['total']} 通过")
        print(f"  耗时: {result['duration']:.3f} 秒")
        print(f"  追踪 ID: {result['trace_id']}")

        if not result.get("success", False):
            print(f"  错误: {result.get('error', 'Unknown error')}")

    # 7. 生成汇总报告
    report = tester.generate_report(results)

    print("\n" + "=" * 60)
    print("测试汇总报告")
    print("=" * 60)
    print(f"总测试数: {report['total_tests']}")
    print(f"成功: {report['successful_tests']}")
    print(f"失败: {report['failed_tests']}")
    print(f"成功率: {report['success_rate']:.1f}%")
    print(f"总断言数: {report['total_assertions']}")
    print(f"通过断言: {report['passed_assertions']}")
    print(f"断言通过率: {report['assertion_pass_rate']:.1f}%")
    print(f"总耗时: {report['total_duration']:.3f} 秒")
    print(f"平均耗时: {report['average_duration']:.3f} 秒")
    print("=" * 60)

    return report


def test_go_with_json_args():
    """测试 Go Agent 使用 JSON 参数"""

    print("\n" + "=" * 60)
    print("测试 Go Agent JSON 参数")
    print("=" * 60)

    store = TraceStore(storage_path="./traces/go_agent_json")

    agent_path = str(Path(__file__).parent / "go_agent")
    adapter = CLIAgentAdapter(
        command=agent_path,
        args_template=["{prompt}"]
    )

    tester = UniversalAgentTester(adapter, store)

    result = tester.test(
        task={
            "prompt": "执行复杂任务",
            "assertions": [
                {"type": "contains", "expected": "Go Agent"}
            ]
        },
        agent_name="go_json_agent"
    )

    success = "✅" if result.get("success", False) else "❌"
    print(f"\n测试结果: {success}")
    print(f"断言: {result['passed']}/{result['total']} 通过")

    return result


if __name__ == "__main__":
    print("\n🚀 TigerHill - Go Agent 测试示例\n")

    # 检查并编译 Go Agent
    if not check_go_agent_exists():
        print("Go Agent 未编译，正在编译...")
        if not compile_go_agent():
            print("\n❌ 无法编译 Go Agent")
            print("\n手动编译:")
            print("  cd examples/cross_language")
            print("  go build -o go_agent go_agent.go")
            sys.exit(1)
    else:
        print("✓ Go Agent 已存在\n")

    try:
        # 测试 1: 基础 CLI 测试
        report1 = test_go_cli_agent()

        # 测试 2: JSON 参数测试（可选）
        # report2 = test_go_with_json_args()

        print("\n✅ 所有测试完成！")
        print("\n查看追踪数据:")
        print("  traces/go_agent/")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

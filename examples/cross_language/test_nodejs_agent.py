"""
测试 Node.js Agent 示例

演示如何使用 TigerHill 测试通过 HTTP/REST API 提供服务的 Node.js Agent。

使用前提:
1. 确保 Node.js Agent 正在运行: node examples/cross_language/nodejs_agent.js
2. Agent 监听在 http://localhost:3000/api/agent

运行测试:
    python examples/cross_language/test_nodejs_agent.py
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tigerhill.adapters import HTTPAgentAdapter, UniversalAgentTester
from tigerhill.storage.trace_store import TraceStore
from tigerhill.core.models import Task


def test_nodejs_calculator():
    """测试 Node.js 计算器 Agent"""

    print("=" * 60)
    print("测试 Node.js 计算器 Agent")
    print("=" * 60)

    # 1. 初始化 TraceStore
    store = TraceStore(storage_path="./traces/nodejs_agent")
    print("✓ TraceStore 初始化完成")

    # 2. 创建 HTTP Agent 适配器
    adapter = HTTPAgentAdapter(
        base_url="http://localhost:3000",
        endpoint="/api/agent",
        timeout=30
    )
    print("✓ HTTP Agent 适配器创建完成")

    # 3. 创建通用测试器
    tester = UniversalAgentTester(adapter, store)
    print("✓ 通用测试器创建完成\n")

    # 4. 定义测试任务
    tasks = [
        {
            "prompt": "计算 6 + 7",
            "assertions": [
                {"type": "contains", "expected": "13"}
            ]
        },
        {
            "prompt": "计算 10 * 5",
            "assertions": [
                {"type": "contains", "expected": "50"}
            ]
        },
        {
            "prompt": "什么是质数？",
            "assertions": [
                {"type": "regex", "pattern": r"(质数|prime)"}
            ]
        }
    ]

    # 5. 执行批量测试
    print("开始批量测试...\n")
    results = tester.test_batch(tasks, agent_name="nodejs_calculator")

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
        print(f"  耗时: {result['duration']:.2f} 秒")
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
    print(f"总耗时: {report['total_duration']:.2f} 秒")
    print(f"平均耗时: {report['average_duration']:.2f} 秒")
    print("=" * 60)

    return report


def test_nodejs_with_authentication():
    """测试需要认证的 Node.js Agent"""

    print("\n" + "=" * 60)
    print("测试带认证的 Node.js Agent")
    print("=" * 60)

    store = TraceStore(storage_path="./traces/nodejs_agent_auth")

    # 带认证头的 HTTP 适配器
    adapter = HTTPAgentAdapter(
        base_url="http://localhost:3000",
        endpoint="/api/agent",
        headers={"Authorization": "Bearer test_token_123"}
    )

    tester = UniversalAgentTester(adapter, store)

    result = tester.test(
        task={
            "prompt": "获取用户信息",
            "assertions": [
                {"type": "contains", "expected": "用户"}
            ]
        },
        agent_name="nodejs_auth_agent"
    )

    success = "✅" if result.get("success", False) else "❌"
    print(f"\n测试结果: {success}")
    print(f"断言: {result['passed']}/{result['total']} 通过")

    return result


def check_agent_availability():
    """检查 Agent 是否可用"""
    try:
        import requests
        response = requests.get("http://localhost:3000/health", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


if __name__ == "__main__":
    print("\n🚀 TigerHill - Node.js Agent 测试示例\n")

    # 检查 Agent 是否运行
    if not check_agent_availability():
        print("❌ 错误: Node.js Agent 未运行")
        print("\n请先启动 Agent:")
        print("  cd examples/cross_language")
        print("  node nodejs_agent.js")
        print("\n然后重新运行此测试:")
        print("  python examples/cross_language/test_nodejs_agent.py")
        sys.exit(1)

    print("✓ Node.js Agent 正在运行\n")

    try:
        # 测试 1: 基础功能测试
        report1 = test_nodejs_calculator()

        # 测试 2: 认证测试（可选）
        # report2 = test_nodejs_with_authentication()

        print("\n✅ 所有测试完成！")
        print("\n查看追踪数据:")
        print("  traces/nodejs_agent/")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

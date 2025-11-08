"""
跨语言集成测试

测试完整的跨语言 Agent 测试工作流。
"""

import pytest
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from tigerhill.adapters import (
    CLIAgentAdapter,
    UniversalAgentTester,
    HTTPAgentAdapter
)
from tigerhill.storage.trace_store import TraceStore


class TestCrossLanguageWorkflow:
    """测试跨语言工作流"""

    def test_python_cli_agent_workflow(self):
        """测试 Python CLI Agent 完整工作流"""

        # 1. 创建 TraceStore
        store = TraceStore(storage_path="./test_traces/python_cli")

        # 2. 创建 CLI 适配器 - 使用 python -c 作为简单 agent
        adapter = CLIAgentAdapter(
            command="python",
            args_template=["-c", "print('Agent处理: ' + '{prompt}')"],
            timeout=10
        )

        # 3. 创建通用测试器
        tester = UniversalAgentTester(adapter, store)

        # 4. 执行测试
        result = tester.test(
            task={
                "prompt": "测试消息",
                "assertions": [
                    {"type": "contains", "expected": "Agent处理"},
                    {"type": "contains", "expected": "测试消息"}
                ]
            },
            agent_name="python_cli_agent",
            task_id="test_001"
        )

        # 5. 验证结果
        assert result["success"] is True
        assert result["passed"] == 2
        assert result["total"] == 2
        assert "Agent处理" in result["output"]
        assert "测试消息" in result["output"]

        # 6. 验证追踪已保存
        trace_id = result["trace_id"]
        summary = store.get_summary(trace_id)
        assert summary["agent_name"] == "python_cli_agent"
        assert summary["total_events"] > 0

    def test_batch_python_agents(self):
        """测试批量 Python Agent"""

        store = TraceStore(storage_path="./test_traces/batch_python")

        # 使用不同的 Python 命令作为不同的 agent
        adapters = [
            CLIAgentAdapter(
                "python",
                ["-c", "print('Agent1: ' + '{prompt}')"]
            ),
            CLIAgentAdapter(
                "python",
                ["-c", "print('Agent2: ' + '{prompt}'.upper())"]
            )
        ]

        tasks = [
            {
                "prompt": "hello",
                "assertions": [{"type": "contains", "expected": "hello"}]
            },
            {
                "prompt": "world",
                "assertions": [{"type": "contains", "expected": "WORLD"}]
            }
        ]

        all_results = []

        for i, adapter in enumerate(adapters):
            tester = UniversalAgentTester(adapter, store)
            result = tester.test(
                task=tasks[i],
                agent_name=f"python_agent_{i+1}"
            )
            all_results.append(result)

        # 验证所有测试都通过
        assert len(all_results) == 2
        assert all(r["success"] for r in all_results)
        assert all(r["passed"] == 1 for r in all_results)

    def test_python_structured_output(self):
        """测试 Python Agent 返回结构化输出"""

        store = TraceStore(storage_path="./test_traces/python_structured")

        # 测试返回格式化的输出
        adapter = CLIAgentAdapter(
            "python",
            ["-c", "print('结果: {prompt}'); print('状态: 成功')"]
        )

        tester = UniversalAgentTester(adapter, store)

        result = tester.test(
            task={
                "prompt": "测试",
                "assertions": [
                    {"type": "contains", "expected": "结果"},
                    {"type": "contains", "expected": "状态"}
                ]
            },
            agent_name="python_structured_agent"
        )

        assert result["success"] is True
        assert result["passed"] == 2

    def test_agent_with_error_handling(self):
        """测试 Agent 错误处理"""

        store = TraceStore(storage_path="./test_traces/error_handling")

        # 创建一个会失败的 agent
        adapter = CLIAgentAdapter(
            "python",
            ["-c", "import sys; sys.exit(1)"],  # 退出码非0
            timeout=5
        )

        tester = UniversalAgentTester(adapter, store)

        result = tester.test(
            task={"prompt": "test", "assertions": []},
            agent_name="failing_agent"
        )

        # 验证测试记录了失败
        assert result["success"] is False
        assert "error" in result

        # 验证追踪仍然被保存
        trace_id = result["trace_id"]
        summary = store.get_summary(trace_id)
        assert summary is not None

    def test_performance_tracking(self):
        """测试性能追踪"""

        store = TraceStore(storage_path="./test_traces/performance")

        # 创建一个有延迟的 agent
        adapter = CLIAgentAdapter(
            "python",
            ["-c", "import time; time.sleep(0.1); print('完成')"]
        )

        tester = UniversalAgentTester(adapter, store)

        result = tester.test(
            task={"prompt": "test", "assertions": []},
            agent_name="slow_agent"
        )

        # 验证记录了执行时间
        assert result["duration"] > 0.1
        assert result["duration"] < 1.0  # 不应该太慢

    def test_report_generation(self):
        """测试报告生成"""

        store = TraceStore(storage_path="./test_traces/reports")

        adapter = CLIAgentAdapter(
            "python",
            ["-c", "print('输出 {prompt}')"]
        )

        tester = UniversalAgentTester(adapter, store)

        # 执行多个测试
        tasks = [
            {"prompt": "任务1", "assertions": [{"type": "contains", "expected": "输出"}]},
            {"prompt": "任务2", "assertions": [{"type": "contains", "expected": "输出"}]},
            {"prompt": "任务3", "assertions": [{"type": "contains", "expected": "不存在"}]},  # 会失败
        ]

        results = tester.test_batch(tasks, agent_name="report_agent")

        # 生成报告
        report = tester.generate_report(results)

        assert report["total_tests"] == 3
        # 所有测试都成功（没有异常），但第3个断言失败
        assert report["successful_tests"] == 3
        assert report["failed_tests"] == 0
        assert report["total_assertions"] == 3
        assert report["passed_assertions"] == 2
        assert 60 < report["assertion_pass_rate"] < 70

    def test_trace_query(self):
        """测试追踪查询"""

        store = TraceStore(storage_path="./test_traces/query")

        adapter = CLIAgentAdapter(
            "python",
            ["-c", "print('测试')"]
        )

        tester = UniversalAgentTester(adapter, store)

        # 执行多个测试
        for i in range(3):
            tester.test(
                task={"prompt": f"任务{i}", "assertions": []},
                agent_name="query_agent",
                task_id=f"task_{i}"
            )

        # 查询所有追踪
        traces = store.get_all_traces()
        # Trace 对象，访问属性而不是字典
        agent_traces = [t for t in traces if t.agent_name == "query_agent"]

        assert len(agent_traces) >= 3

    def test_custom_metadata(self):
        """测试自定义元数据"""

        store = TraceStore(storage_path="./test_traces/metadata")

        adapter = CLIAgentAdapter(
            "python",
            ["-c", "print('测试')"]
        )

        tester = UniversalAgentTester(adapter, store)

        result = tester.test(
            task={"prompt": "测试", "assertions": []},
            agent_name="metadata_agent",
            metadata={
                "language": "python",
                "version": "1.0",
                "environment": "test"
            }
        )

        # 验证元数据被保存
        trace_id = result["trace_id"]
        summary = store.get_summary(trace_id)
        assert summary["metadata"]["language"] == "python"
        assert summary["metadata"]["version"] == "1.0"


class TestRealWorldScenarios:
    """真实场景测试"""

    def test_calculator_agent(self):
        """测试计算器 Agent"""

        store = TraceStore(storage_path="./test_traces/calculator")

        # 创建一个简单的计算器 agent
        adapter = CLIAgentAdapter(
            "python",
            ["-c", """
import sys
prompt = '{prompt}'
if '+' in prompt:
    parts = prompt.split('+')
    result = sum(int(p.strip()) for p in parts)
    print(f'计算结果: {{result}}')
else:
    print('无法计算')
"""]
        )

        tester = UniversalAgentTester(adapter, store)

        result = tester.test(
            task={
                "prompt": "5 + 3",
                "assertions": [
                    {"type": "contains", "expected": "8"}
                ]
            },
            agent_name="calculator_agent"
        )

        assert result["success"] is True
        assert result["passed"] == 1

    def test_code_generation_agent(self):
        """测试代码生成 Agent"""

        store = TraceStore(storage_path="./test_traces/code_gen")

        adapter = CLIAgentAdapter(
            "python",
            ["-c", """
prompt = '{prompt}'
if 'python' in prompt.lower():
    print('''def hello():
    print("Hello World")''')
else:
    print('无法生成代码')
"""]
        )

        tester = UniversalAgentTester(adapter, store)

        result = tester.test(
            task={
                "prompt": "生成一个 Python 函数",
                "assertions": [
                    {"type": "contains", "expected": "def"},
                    {"type": "contains", "expected": "print"}
                ]
            },
            agent_name="code_gen_agent"
        )

        assert result["success"] is True
        assert result["passed"] == 2


def test_cleanup_test_traces():
    """清理测试追踪（测试后执行）"""
    import shutil

    test_traces_dir = Path("./test_traces")
    if test_traces_dir.exists():
        # 不删除，保留用于检查
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

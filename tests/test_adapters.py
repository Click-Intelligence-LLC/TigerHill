"""
测试跨语言 Agent 适配器

测试 tigerhill.adapters.multi_language 模块的各个适配器。
"""

import pytest
import json
import subprocess
from unittest.mock import Mock, patch, MagicMock
from tigerhill.adapters.multi_language import (
    AgentAdapter,
    HTTPAgentAdapter,
    CLIAgentAdapter,
    STDIOAgentAdapter,
    UniversalAgentTester
)
from tigerhill.storage.trace_store import TraceStore


class TestAgentAdapter:
    """测试 AgentAdapter 基类"""

    def test_abstract_methods(self):
        """测试抽象方法必须实现"""
        with pytest.raises(TypeError):
            # 不能直接实例化抽象类
            adapter = AgentAdapter()

    def test_context_manager(self):
        """测试上下文管理器"""
        class TestAdapter(AgentAdapter):
            def __init__(self):
                self.cleaned = False

            def invoke(self, prompt: str, **kwargs) -> str:
                return "test"

            def cleanup(self):
                self.cleaned = True

        adapter = TestAdapter()
        with adapter:
            pass

        assert adapter.cleaned is True


class TestHTTPAgentAdapter:
    """测试 HTTPAgentAdapter"""

    def test_initialization(self):
        """测试初始化"""
        adapter = HTTPAgentAdapter(
            base_url="http://localhost:3000",
            endpoint="/api/agent",
            timeout=30
        )

        assert adapter.base_url == "http://localhost:3000"
        assert adapter.endpoint == "/api/agent"
        assert adapter.timeout == 30

    def test_base_url_normalization(self):
        """测试 URL 规范化"""
        adapter = HTTPAgentAdapter(base_url="http://localhost:3000/")
        assert adapter.base_url == "http://localhost:3000"

    @patch('requests.post')
    def test_invoke_post_json_response(self, mock_post):
        """测试 POST 请求和 JSON 响应"""
        # Mock 响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"output": "test response"}
        mock_post.return_value = mock_response

        adapter = HTTPAgentAdapter("http://localhost:3000")
        result = adapter.invoke("test prompt")

        assert result == "test response"
        mock_post.assert_called_once()

    @patch('requests.post')
    def test_invoke_with_custom_headers(self, mock_post):
        """测试自定义请求头"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"output": "test"}
        mock_post.return_value = mock_response

        adapter = HTTPAgentAdapter(
            "http://localhost:3000",
            headers={"Authorization": "Bearer token123"}
        )
        adapter.invoke("test")

        # 验证请求头
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs['headers']['Authorization'] == "Bearer token123"

    @patch('requests.post')
    def test_invoke_http_error(self, mock_post):
        """测试 HTTP 错误"""
        mock_post.side_effect = Exception("Connection error")

        adapter = HTTPAgentAdapter("http://localhost:3000")

        with pytest.raises(Exception):
            adapter.invoke("test")

    @patch('requests.post')
    def test_invoke_different_response_formats(self, mock_post):
        """测试不同的响应格式"""
        adapter = HTTPAgentAdapter("http://localhost:3000")

        # 测试 "response" 字段
        mock_response = Mock()
        mock_response.json.return_value = {"response": "test1"}
        mock_post.return_value = mock_response
        assert adapter.invoke("test") == "test1"

        # 测试 "result" 字段
        mock_response.json.return_value = {"result": "test2"}
        assert adapter.invoke("test") == "test2"

        # 测试字符串响应
        mock_response.json.return_value = "test3"
        assert adapter.invoke("test") == "test3"


class TestCLIAgentAdapter:
    """测试 CLIAgentAdapter"""

    def test_initialization(self):
        """测试初始化"""
        adapter = CLIAgentAdapter(
            command="./agent",
            args_template=["{prompt}"],
            timeout=10
        )

        assert adapter.command == "./agent"
        assert adapter.args_template == ["{prompt}"]
        assert adapter.timeout == 10

    @patch('subprocess.run')
    def test_invoke_success(self, mock_run):
        """测试成功调用"""
        # Mock subprocess.run
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        adapter = CLIAgentAdapter("./agent", ["{prompt}"])
        result = adapter.invoke("test prompt")

        assert result == "test output"
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_invoke_with_json_output(self, mock_run):
        """测试 JSON 输出"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '{"output": "json response"}'
        mock_run.return_value = mock_result

        adapter = CLIAgentAdapter("./agent")
        result = adapter.invoke("test")

        assert result == "json response"

    @patch('subprocess.run')
    def test_invoke_command_failure(self, mock_run):
        """测试命令执行失败"""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "error message"
        mock_run.return_value = mock_result

        adapter = CLIAgentAdapter("./agent")

        with pytest.raises(RuntimeError):
            adapter.invoke("test")

    @patch('subprocess.run')
    def test_invoke_timeout(self, mock_run):
        """测试超时"""
        mock_run.side_effect = subprocess.TimeoutExpired("./agent", 10)

        adapter = CLIAgentAdapter("./agent", timeout=10)

        with pytest.raises(TimeoutError):
            adapter.invoke("test")

    @patch('subprocess.run')
    def test_args_template_substitution(self, mock_run):
        """测试参数模板替换"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "output"
        mock_run.return_value = mock_result

        adapter = CLIAgentAdapter(
            "./agent",
            args_template=["--mode={mode}", "{prompt}"]
        )
        adapter.invoke("test prompt", mode="debug")

        # 验证命令参数
        call_args = mock_run.call_args[0][0]
        assert call_args == ["./agent", "--mode=debug", "test prompt"]


class TestSTDIOAgentAdapter:
    """测试 STDIOAgentAdapter"""

    def test_initialization(self):
        """测试初始化"""
        adapter = STDIOAgentAdapter(
            command="java -jar agent.jar",
            end_marker="\n",
            response_timeout=30
        )

        assert adapter.command == "java -jar agent.jar"
        assert adapter.end_marker == "\n"
        assert adapter.response_timeout == 30
        assert adapter.process is None

    @patch('subprocess.Popen')
    def test_invoke_creates_process(self, mock_popen):
        """测试调用时创建进程"""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.stdout.readline.return_value = "test output\n"
        mock_popen.return_value = mock_process

        adapter = STDIOAgentAdapter("test_command")
        result = adapter.invoke("test prompt")

        assert result == "test output"
        mock_popen.assert_called_once()

    @patch('subprocess.Popen')
    def test_cleanup(self, mock_popen):
        """测试清理进程"""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.stdout.readline.return_value = "output\n"
        mock_popen.return_value = mock_process

        adapter = STDIOAgentAdapter("test_command")
        adapter.invoke("test")

        # 清理
        adapter.cleanup()

        # 验证进程被终止
        mock_process.terminate.assert_called_once()

    @patch('subprocess.Popen')
    def test_context_manager(self, mock_popen):
        """测试上下文管理器自动清理"""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.stdout.readline.return_value = "output\n"
        mock_popen.return_value = mock_process

        with STDIOAgentAdapter("test_command") as adapter:
            adapter.invoke("test")

        # 验证进程被清理
        mock_process.terminate.assert_called_once()


class TestUniversalAgentTester:
    """测试 UniversalAgentTester"""

    def test_initialization(self):
        """测试初始化"""
        store = TraceStore(storage_path="./test_traces")
        adapter = Mock(spec=AgentAdapter)

        tester = UniversalAgentTester(adapter, store)

        assert tester.adapter == adapter
        assert tester.store == store

    def test_single_test(self):
        """测试单个测试"""
        store = TraceStore(storage_path="./test_traces")

        # Mock adapter
        adapter = Mock(spec=AgentAdapter)
        adapter.invoke.return_value = "计算结果是 13"

        tester = UniversalAgentTester(adapter, store)

        result = tester.test(
            task={
                "prompt": "计算 6 + 7",
                "assertions": [
                    {"type": "contains", "expected": "13"}
                ]
            },
            agent_name="test_agent"
        )

        # 验证结果
        assert result["success"] is True
        assert result["passed"] == 1
        assert result["total"] == 1
        assert "trace_id" in result
        assert "duration" in result

        # 验证 adapter 被调用
        adapter.invoke.assert_called_once_with("计算 6 + 7")

    def test_test_with_failure(self):
        """测试失败的测试"""
        store = TraceStore(storage_path="./test_traces")

        adapter = Mock(spec=AgentAdapter)
        adapter.invoke.side_effect = Exception("Agent error")

        tester = UniversalAgentTester(adapter, store)

        result = tester.test(
            task={"prompt": "test", "assertions": []},
            agent_name="failing_agent"
        )

        assert result["success"] is False
        assert "error" in result

    def test_batch_tests(self):
        """测试批量测试"""
        store = TraceStore(storage_path="./test_traces")

        adapter = Mock(spec=AgentAdapter)
        adapter.invoke.side_effect = ["结果1", "结果2", "结果3"]

        tester = UniversalAgentTester(adapter, store)

        tasks = [
            {"prompt": "任务1", "assertions": []},
            {"prompt": "任务2", "assertions": []},
            {"prompt": "任务3", "assertions": []}
        ]

        results = tester.test_batch(tasks, agent_name="batch_agent")

        assert len(results) == 3
        assert all(r["success"] for r in results)

    def test_generate_report(self):
        """测试生成报告"""
        store = TraceStore(storage_path="./test_traces")
        adapter = Mock(spec=AgentAdapter)
        tester = UniversalAgentTester(adapter, store)

        # Mock 测试结果
        results = [
            {
                "success": True,
                "passed": 2,
                "total": 2,
                "duration": 0.1
            },
            {
                "success": True,
                "passed": 1,
                "total": 2,
                "duration": 0.2
            },
            {
                "success": False,
                "passed": 0,
                "total": 1,
                "duration": 0.3
            }
        ]

        report = tester.generate_report(results)

        assert report["total_tests"] == 3
        assert report["successful_tests"] == 2
        assert report["failed_tests"] == 1
        assert report["total_assertions"] == 5
        assert report["passed_assertions"] == 3
        assert report["total_duration"] == pytest.approx(0.6, 0.01)


class TestIntegration:
    """集成测试"""

    def test_echo_command_integration(self):
        """使用 echo 命令的真实集成测试"""
        store = TraceStore(storage_path="./test_traces")

        # 使用 echo 作为简单的 CLI agent
        adapter = CLIAgentAdapter(
            command="echo",
            args_template=["{prompt}"]
        )

        tester = UniversalAgentTester(adapter, store)

        result = tester.test(
            task={
                "prompt": "test message",
                "assertions": [
                    {"type": "contains", "expected": "test"}
                ]
            },
            agent_name="echo_agent"
        )

        assert result["success"] is True
        assert result["passed"] == 1
        assert "test message" in result["output"]

    def test_python_command_integration(self):
        """使用 python 命令的真实集成测试"""
        store = TraceStore(storage_path="./test_traces")

        adapter = CLIAgentAdapter(
            command="python",
            args_template=["-c", "print('{prompt}')"]
        )

        tester = UniversalAgentTester(adapter, store)

        result = tester.test(
            task={
                "prompt": "Hello from Python",
                "assertions": [
                    {"type": "contains", "expected": "Hello"}
                ]
            },
            agent_name="python_agent"
        )

        assert result["success"] is True
        assert result["passed"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

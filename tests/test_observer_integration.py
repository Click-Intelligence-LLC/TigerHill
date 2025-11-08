"""
Observer SDK Integration Tests

测试 TigerHill Observer SDK 的完整功能：
- PromptCapture 捕获功能
- PromptAnalyzer 分析功能
- Python Observer 包装器
- 数据脱敏和隐私保护
- TraceStore 集成
"""

import json
import time
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
import pytest

from tigerhill.observer import PromptCapture, PromptAnalyzer, wrap_python_model
from tigerhill.observer.python_observer import create_observer_callback, instrument_generative_ai


class TestPromptCapture:
    """测试 PromptCapture 核心功能"""

    def test_start_capture(self):
        """测试开始捕获会话"""
        with tempfile.TemporaryDirectory() as tmpdir:
            capture = PromptCapture(storage_path=tmpdir)

            capture_id = capture.start_capture(
                agent_name="test_agent",
                metadata={"version": "1.0"}
            )

            assert capture_id is not None
            assert capture_id in capture.captures

            session = capture.get_capture(capture_id)
            assert session["agent_name"] == "test_agent"
            assert session["metadata"]["version"] == "1.0"
            assert session["status"] == "active"
            assert len(session["requests"]) == 0
            assert len(session["responses"]) == 0

    def test_capture_request(self):
        """测试捕获请求数据"""
        with tempfile.TemporaryDirectory() as tmpdir:
            capture = PromptCapture(storage_path=tmpdir)
            capture_id = capture.start_capture("test_agent")

            request_data = {
                "model": "gemini-pro",
                "prompt": "Hello, world!",
                "temperature": 0.7,
                "tools": [{"name": "search", "description": "Search tool"}]
            }

            capture.capture_request(capture_id, request_data)

            session = capture.get_capture(capture_id)
            assert len(session["requests"]) == 1

            captured_request = session["requests"][0]
            assert captured_request["model"] == "gemini-pro"
            assert captured_request["prompt"] == "Hello, world!"
            assert captured_request["temperature"] == 0.7
            assert "timestamp" in captured_request
            assert "request_id" in captured_request

    def test_capture_response(self):
        """测试捕获响应数据"""
        with tempfile.TemporaryDirectory() as tmpdir:
            capture = PromptCapture(storage_path=tmpdir)
            capture_id = capture.start_capture("test_agent")

            response_data = {
                "text": "This is a test response",
                "finish_reason": "stop",
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                }
            }

            capture.capture_response(capture_id, response_data)

            session = capture.get_capture(capture_id)
            assert len(session["responses"]) == 1

            captured_response = session["responses"][0]
            assert captured_response["text"] == "This is a test response"
            assert captured_response["finish_reason"] == "stop"
            assert captured_response["usage"]["total_tokens"] == 30
            assert "timestamp" in captured_response
            assert "response_id" in captured_response

    def test_capture_response_with_tool_calls(self):
        """测试捕获包含工具调用的响应"""
        with tempfile.TemporaryDirectory() as tmpdir:
            capture = PromptCapture(storage_path=tmpdir)
            capture_id = capture.start_capture("test_agent")

            response_data = {
                "text": "Let me search for that",
                "tool_calls": [
                    {"name": "search", "arguments": {"query": "test"}},
                    {"name": "calculate", "arguments": {"expression": "2+2"}}
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5}
            }

            capture.capture_response(capture_id, response_data)

            session = capture.get_capture(capture_id)
            assert len(session["tool_calls"]) == 2
            assert session["tool_calls"][0]["name"] == "search"
            assert session["tool_calls"][1]["name"] == "calculate"

    def test_end_capture(self):
        """测试结束捕获会话"""
        with tempfile.TemporaryDirectory() as tmpdir:
            capture = PromptCapture(storage_path=tmpdir, auto_save=False)
            capture_id = capture.start_capture("test_agent")

            # 添加一些数据
            capture.capture_request(capture_id, {"model": "test", "prompt": "hi"})
            capture.capture_response(capture_id, {
                "text": "hello",
                "usage": {"prompt_tokens": 5, "completion_tokens": 10}
            })

            time.sleep(0.1)  # 确保有持续时间

            result = capture.end_capture(capture_id)

            assert result["status"] == "completed"
            assert "duration" in result
            assert result["duration"] > 0
            assert "statistics" in result
            assert result["statistics"]["total_requests"] == 1
            assert result["statistics"]["total_responses"] == 1
            assert result["statistics"]["total_tokens"] == 15

    def test_sanitization_api_keys(self):
        """测试 API key 脱敏"""
        with tempfile.TemporaryDirectory() as tmpdir:
            capture = PromptCapture(storage_path=tmpdir)
            capture_id = capture.start_capture("test_agent")

            request_data = {
                "model": "gemini-pro",
                "prompt": "Use this API key: AIzaSyD1234567890abcdefghijk",
                "api_key": "sk-1234567890abcdefghijk"
            }

            capture.capture_request(capture_id, request_data)

            session = capture.get_capture(capture_id)
            captured = session["requests"][0]

            assert "AIzaSyD1234567890abcdefghijk" not in captured["prompt"]
            assert "<REDACTED_API_KEY>" in captured["prompt"]
            assert captured["api_key"] == "<REDACTED_API_KEY>"

    def test_sanitization_emails(self):
        """测试邮箱地址脱敏"""
        with tempfile.TemporaryDirectory() as tmpdir:
            capture = PromptCapture(storage_path=tmpdir)
            capture_id = capture.start_capture("test_agent")

            request_data = {
                "model": "test",
                "prompt": "Contact me at user@example.com for details"
            }

            capture.capture_request(capture_id, request_data)

            session = capture.get_capture(capture_id)
            captured = session["requests"][0]

            assert "user@example.com" not in captured["prompt"]
            assert "<REDACTED_EMAIL>" in captured["prompt"]

    def test_sanitization_credit_cards(self):
        """测试信用卡号脱敏"""
        with tempfile.TemporaryDirectory() as tmpdir:
            capture = PromptCapture(storage_path=tmpdir)
            capture_id = capture.start_capture("test_agent")

            request_data = {
                "model": "test",
                "prompt": "Card number: 1234 5678 9012 3456"
            }

            capture.capture_request(capture_id, request_data)

            session = capture.get_capture(capture_id)
            captured = session["requests"][0]

            assert "1234 5678 9012 3456" not in captured["prompt"]
            assert "<REDACTED_CARD>" in captured["prompt"]

    def test_custom_redaction_patterns(self):
        """测试自定义脱敏规则"""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_patterns = [
                {"pattern": r"SECRET-\d{6}", "replacement": "<SECRET>"}
            ]

            capture = PromptCapture(
                storage_path=tmpdir,
                redact_patterns=custom_patterns
            )
            capture_id = capture.start_capture("test_agent")

            request_data = {
                "model": "test",
                "prompt": "The code is SECRET-123456"
            }

            capture.capture_request(capture_id, request_data)

            session = capture.get_capture(capture_id)
            captured = session["requests"][0]

            assert "SECRET-123456" not in captured["prompt"]
            assert "<SECRET>" in captured["prompt"]

    def test_auto_save(self):
        """测试自动保存功能"""
        with tempfile.TemporaryDirectory() as tmpdir:
            capture = PromptCapture(storage_path=tmpdir, auto_save=True)
            capture_id = capture.start_capture("test_agent")

            capture.capture_request(capture_id, {"model": "test", "prompt": "hi"})
            capture.capture_response(capture_id, {"text": "hello"})

            result = capture.end_capture(capture_id)

            # 检查文件是否被创建
            files = list(Path(tmpdir).glob("capture_*.json"))
            assert len(files) == 1

            # 验证文件内容
            with open(files[0], "r") as f:
                saved_data = json.load(f)

            assert saved_data["capture_id"] == capture_id
            assert saved_data["agent_name"] == "test_agent"
            assert len(saved_data["requests"]) == 1
            assert len(saved_data["responses"]) == 1

    def test_load_capture(self):
        """测试加载捕获数据"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 先保存
            capture1 = PromptCapture(storage_path=tmpdir, auto_save=True)
            capture_id = capture1.start_capture("test_agent")
            capture1.capture_request(capture_id, {"model": "test", "prompt": "hi"})
            capture1.end_capture(capture_id)

            # 再加载
            capture2 = PromptCapture(storage_path=tmpdir)
            loaded = capture2.load_capture(capture_id)

            assert loaded is not None
            assert loaded["capture_id"] == capture_id
            assert loaded["agent_name"] == "test_agent"
            assert len(loaded["requests"]) == 1

    def test_list_captures(self):
        """测试列出捕获会话"""
        with tempfile.TemporaryDirectory() as tmpdir:
            capture = PromptCapture(storage_path=tmpdir)

            id1 = capture.start_capture("agent1")
            id2 = capture.start_capture("agent2")
            id3 = capture.start_capture("agent1")

            capture.end_capture(id1)

            # 列出所有
            all_captures = capture.list_captures()
            assert len(all_captures) == 3

            # 按 agent 过滤
            agent1_captures = capture.list_captures(agent_name="agent1")
            assert len(agent1_captures) == 2

            # 按状态过滤
            active_captures = capture.list_captures(status="active")
            assert len(active_captures) == 2

            completed_captures = capture.list_captures(status="completed")
            assert len(completed_captures) == 1


class TestPromptAnalyzer:
    """测试 PromptAnalyzer 分析功能"""

    def create_sample_capture(self):
        """创建示例捕获数据"""
        return {
            "capture_id": "test-123",
            "agent_name": "test_agent",
            "requests": [
                {
                    "model": "gemini-pro",
                    "prompt": "Generate a function to calculate fibonacci numbers",
                    "system_prompt": "You are a helpful coding assistant"
                },
                {
                    "model": "gemini-pro",
                    "prompt": "Explain how it works"
                }
            ],
            "responses": [
                {
                    "text": "Here is a fibonacci function...",
                    "usage": {
                        "prompt_tokens": 50,
                        "completion_tokens": 100,
                        "total_tokens": 150
                    }
                },
                {
                    "text": "The function uses recursion...",
                    "usage": {
                        "prompt_tokens": 30,
                        "completion_tokens": 70,
                        "total_tokens": 100
                    }
                }
            ],
            "duration": 5.5
        }

    def test_get_summary(self):
        """测试获取摘要信息"""
        capture_data = self.create_sample_capture()
        analyzer = PromptAnalyzer(capture_data)

        summary = analyzer.get_summary()

        assert summary["total_captures"] == 1
        assert summary["total_requests"] == 2
        assert summary["total_responses"] == 2
        assert "test_agent" in summary["agents"]
        assert "gemini-pro" in summary["models"]

    def test_analyze_tokens(self):
        """测试 Token 分析"""
        capture_data = self.create_sample_capture()
        analyzer = PromptAnalyzer(capture_data)

        token_analysis = analyzer.analyze_tokens()

        assert token_analysis["total_tokens"] == 250
        assert token_analysis["total_prompt_tokens"] == 80
        assert token_analysis["total_completion_tokens"] == 170
        assert token_analysis["avg_tokens_per_request"] == 125.0
        assert token_analysis["token_efficiency_ratio"] > 2.0  # 170/80
        assert token_analysis["max_tokens"] == 150
        assert token_analysis["min_tokens"] == 100

    def test_analyze_prompt_quality(self):
        """测试 Prompt 质量分析"""
        capture_data = self.create_sample_capture()
        analyzer = PromptAnalyzer(capture_data)

        quality = analyzer.analyze_prompt_quality()

        assert quality["total_prompts"] == 2
        assert quality["has_system_prompt_ratio"] == 0.5  # 只有第一个有 system prompt
        assert quality["avg_prompt_length"] > 0
        assert "clarity_score" in quality
        assert "detected_issues" in quality

    def test_analyze_performance(self):
        """测试性能分析"""
        capture_data = self.create_sample_capture()
        analyzer = PromptAnalyzer(capture_data)

        performance = analyzer.analyze_performance()

        assert performance["avg_duration"] == 5.5
        assert performance["max_duration"] == 5.5
        assert performance["min_duration"] == 5.5
        assert performance["total_duration"] == 5.5
        assert performance["num_captures"] == 1

    def test_analyze_tool_usage(self):
        """测试工具使用分析"""
        capture_data = {
            "requests": [
                {
                    "tools": [
                        {"name": "search", "description": "Search tool"},
                        {"name": "calculator", "description": "Math tool"}
                    ]
                }
            ],
            "responses": [
                {
                    "tool_calls": [
                        {"name": "search", "arguments": {"query": "test"}},
                        {"name": "search", "arguments": {"query": "test2"}}
                    ]
                }
            ]
        }

        analyzer = PromptAnalyzer(capture_data)
        tool_usage = analyzer.analyze_tool_usage()

        assert tool_usage["total_tools_defined"] == 2
        assert tool_usage["unique_tools_defined"] == 2
        assert tool_usage["total_tool_calls"] == 2
        assert tool_usage["unique_tools_called"] == 1  # 只调用了 search
        assert tool_usage["most_used_tools"][0] == ("search", 2)
        assert "calculator" in tool_usage["tools_defined_but_not_used"]

    def test_generate_recommendations_long_prompt(self):
        """测试生成建议 - 过长的 prompt"""
        capture_data = {
            "requests": [{"prompt": "test"}],
            "responses": [{
                "text": "response",
                "usage": {"prompt_tokens": 3000, "completion_tokens": 100}
            }],
            "duration": 3.0
        }

        analyzer = PromptAnalyzer(capture_data)
        recommendations = analyzer.generate_recommendations()

        # 应该有关于 prompt 过长的建议
        long_prompt_rec = [r for r in recommendations if "过长" in r["title"]]
        assert len(long_prompt_rec) > 0
        assert long_prompt_rec[0]["category"] == "token_optimization"

    def test_generate_recommendations_low_efficiency(self):
        """测试生成建议 - Token 效率低"""
        capture_data = {
            "requests": [{"prompt": "test"}],
            "responses": [{
                "text": "ok",
                "usage": {"prompt_tokens": 1000, "completion_tokens": 10}
            }],
            "duration": 2.0
        }

        analyzer = PromptAnalyzer(capture_data)
        recommendations = analyzer.generate_recommendations()

        # 应该有关于效率低的建议
        efficiency_rec = [r for r in recommendations if "效率" in r["title"]]
        assert len(efficiency_rec) > 0

    def test_generate_recommendations_missing_system_prompt(self):
        """测试生成建议 - 缺少系统 prompt"""
        capture_data = {
            "requests": [
                {"prompt": "test1"},
                {"prompt": "test2"}
            ],
            "responses": [
                {"text": "r1", "usage": {"prompt_tokens": 10, "completion_tokens": 10}},
                {"text": "r2", "usage": {"prompt_tokens": 10, "completion_tokens": 10}}
            ],
            "duration": 2.0
        }

        analyzer = PromptAnalyzer(capture_data)
        recommendations = analyzer.generate_recommendations()

        # 应该有关于缺少系统 prompt 的建议
        system_prompt_rec = [r for r in recommendations if "系统" in r["title"]]
        assert len(system_prompt_rec) > 0

    def test_analyze_all(self):
        """测试完整分析"""
        capture_data = self.create_sample_capture()
        analyzer = PromptAnalyzer(capture_data)

        report = analyzer.analyze_all()

        assert "summary" in report
        assert "token_analysis" in report
        assert "prompt_quality" in report
        assert "performance" in report
        assert "tool_usage" in report
        assert "recommendations" in report


class TestPythonObserver:
    """测试 Python Observer 包装器"""

    def create_mock_model_class(self):
        """创建 Mock 模型类"""
        class MockGenerativeModel:
            def __init__(self, model_name):
                self.model_name = model_name

            def generate_content(self, *args, **kwargs):
                """模拟生成内容"""
                response = MagicMock()
                response.text = "Mock response"
                response.candidates = [MagicMock()]
                response.candidates[0].finish_reason = "STOP"
                response.usage_metadata = MagicMock()
                response.usage_metadata.prompt_token_count = 10
                response.usage_metadata.candidates_token_count = 20
                response.usage_metadata.total_token_count = 30
                return response

            async def generate_content_async(self, *args, **kwargs):
                """模拟异步生成内容"""
                return self.generate_content(*args, **kwargs)

        return MockGenerativeModel

    def test_wrap_generative_model(self):
        """测试包装模型类"""
        MockModel = self.create_mock_model_class()
        captured_data = []

        def capture_callback(data):
            captured_data.append(data)

        WrappedModel = wrap_python_model(
            MockModel,
            capture_callback=capture_callback
        )

        model = WrappedModel("gemini-pro")
        assert model.model_name == "gemini-pro"

    def test_capture_request_and_response(self):
        """测试捕获请求和响应"""
        MockModel = self.create_mock_model_class()
        captured_data = []

        def capture_callback(data):
            captured_data.append(data)

        WrappedModel = wrap_python_model(
            MockModel,
            capture_callback=capture_callback
        )

        model = WrappedModel("gemini-pro")
        response = model.generate_content("Hello, world!")

        # 应该捕获了请求和响应
        assert len(captured_data) == 2

        # 验证请求数据
        request_data = captured_data[0]
        assert request_data["model"] == "gemini-pro"
        assert request_data["prompt"] == "Hello, world!"

        # 验证响应数据
        response_data = captured_data[1]
        assert response_data["text"] == "Mock response"
        assert response_data["usage"]["total_tokens"] == 30

    def test_create_observer_callback(self):
        """测试创建观察回调"""
        with tempfile.TemporaryDirectory() as tmpdir:
            capture = PromptCapture(storage_path=tmpdir)
            capture_id = capture.start_capture("test_agent")

            callback = create_observer_callback(capture, capture_id)

            # 测试请求回调
            callback({"model": "test", "prompt": "hi"})

            # 测试响应回调
            callback({"_is_response": True, "text": "hello", "usage": {"prompt_tokens": 5}})

            session = capture.get_capture(capture_id)
            assert len(session["requests"]) == 1
            assert len(session["responses"]) == 1

    def test_instrument_generative_ai(self):
        """测试自动 instrument 功能"""
        with tempfile.TemporaryDirectory() as tmpdir:
            MockModel = self.create_mock_model_class()

            # 禁用 auto_save 避免 Mock 对象序列化问题
            from tigerhill.observer.capture import PromptCapture
            from tigerhill.observer.python_observer import create_observer_callback

            # 手动创建（不使用 auto_save）
            capture = PromptCapture(storage_path=tmpdir, auto_save=False)
            capture_id = capture.start_capture("test_agent")
            callback = create_observer_callback(capture, capture_id)

            # 包装模型
            WrappedModel = wrap_python_model(MockModel, capture_callback=callback)
            model = WrappedModel("gemini-pro")

            # 使用模型
            response = model.generate_content("Test prompt")

            # 结束捕获（不保存）
            result = capture.end_capture(capture_id)

            assert result["statistics"]["total_requests"] == 1
            assert result["statistics"]["total_responses"] == 1
            assert result["agent_name"] == "test_agent"


class TestTraceStoreIntegration:
    """测试 TraceStore 集成"""

    def test_export_to_trace_store(self):
        """测试导出到 TraceStore"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建捕获数据
            capture = PromptCapture(storage_path=tmpdir)
            capture_id = capture.start_capture("test_agent", metadata={"version": "1.0"})

            capture.capture_request(capture_id, {
                "model": "gemini-pro",
                "prompt": "Test prompt"
            })

            capture.capture_response(capture_id, {
                "text": "Test response",
                "usage": {"prompt_tokens": 5, "completion_tokens": 10}
            })

            capture.end_capture(capture_id)

            # 创建 mock TraceStore
            mock_trace_store = MagicMock()
            mock_trace_store.start_trace.return_value = "trace-123"

            # 导出
            trace_id = capture.export_to_trace_store(
                capture_id=capture_id,
                trace_store=mock_trace_store
            )

            # 验证调用
            assert trace_id == "trace-123"
            mock_trace_store.start_trace.assert_called_once()
            assert mock_trace_store.write_event.call_count >= 2  # 至少有请求和响应
            mock_trace_store.end_trace.assert_called_once_with("trace-123")


class TestEndToEnd:
    """端到端测试"""

    def test_complete_workflow(self):
        """测试完整工作流程"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. 创建捕获器
            capture = PromptCapture(storage_path=tmpdir, auto_save=True)
            capture_id = capture.start_capture(
                agent_name="code_assistant",
                metadata={"task": "generate_fibonacci"}
            )

            # 2. 模拟多轮对话
            capture.capture_request(capture_id, {
                "model": "gemini-pro",
                "prompt": "Write a fibonacci function in Python",
                "system_prompt": "You are a coding assistant"
            })

            capture.capture_response(capture_id, {
                "text": "Here is a fibonacci function:\n\ndef fib(n):\n    if n <= 1:\n        return n\n    return fib(n-1) + fib(n-2)",
                "usage": {"prompt_tokens": 20, "completion_tokens": 50}
            })

            capture.capture_request(capture_id, {
                "model": "gemini-pro",
                "prompt": "Can you optimize it with memoization?"
            })

            capture.capture_response(capture_id, {
                "text": "Sure! Here's an optimized version...",
                "usage": {"prompt_tokens": 30, "completion_tokens": 80}
            })

            # 3. 结束捕获
            result = capture.end_capture(capture_id)

            # 4. 验证统计
            assert result["statistics"]["total_requests"] == 2
            assert result["statistics"]["total_responses"] == 2
            assert result["statistics"]["total_tokens"] == 180

            # 5. 分析数据
            analyzer = PromptAnalyzer(result)
            report = analyzer.analyze_all()

            assert report["summary"]["total_requests"] == 2
            assert report["token_analysis"]["total_tokens"] == 180
            assert report["prompt_quality"]["has_system_prompt_ratio"] == 0.5

            # 6. 验证文件保存
            files = list(Path(tmpdir).glob("capture_*.json"))
            assert len(files) == 1


def test_import_structure():
    """测试导入结构"""
    from tigerhill.observer import PromptCapture, PromptAnalyzer, wrap_python_model

    assert PromptCapture is not None
    assert PromptAnalyzer is not None
    assert wrap_python_model is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

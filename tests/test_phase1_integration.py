"""
Phase 1 集成测试

模拟真实的gemini-cli多轮对话场景，测试完整的prompt捕获流程
"""

import pytest
import json
import time
from pathlib import Path
from tigerhill.observer import PromptCapture
from tigerhill.observer.conversation_models import MessageRole


class TestGeminiCLIIntegration:
    """模拟gemini-cli的集成测试"""

    def test_complete_multiturn_conversation_flow(self, tmp_path):
        """
        测试完整的多轮对话流程

        模拟场景：用户使用gemini-cli进行代码重构咨询
        """
        print("\n" + "=" * 80)
        print("🧪 测试场景：Gemini CLI 代码重构咨询（3轮对话）")
        print("=" * 80)

        # 初始化捕获器
        capture = PromptCapture(storage_path=str(tmp_path / "captures"))
        capture_id = capture.start_capture("gemini-cli")
        conversation_id = "conv_refactoring_001"

        # 定义系统prompt（通常在gemini-cli启动时设置）
        system_prompt = """你是一个专业的Python代码审查和重构助手。
你的职责是：
1. 分析代码质量和潜在问题
2. 提供具体的重构建议
3. 解释重构的理由和好处"""

        print(f"\n📝 系统Prompt已设置:")
        print(f"   {system_prompt[:60]}...")

        # ===== Turn 1: 用户请求代码审查 =====
        print("\n" + "-" * 80)
        print("🔵 Turn 1: 用户请求代码审查")
        print("-" * 80)

        user_code = """
def calc(a, b, op):
    if op == 'add':
        return a + b
    elif op == 'sub':
        return a - b
    elif op == 'mul':
        return a * b
    elif op == 'div':
        return a / b
"""

        turn1_request = {
            "request_id": "req_001",
            "model": "gemini-2.0-flash-exp",
            "system_prompt": system_prompt,
            "prompt": f"请审查这段代码并提供重构建议：\n```python{user_code}```",
            "timestamp": time.time(),
            "generation_config": {
                "temperature": 0.7,
                "max_tokens": 2000
            }
        }

        req_id_1 = capture.capture_request(
            capture_id,
            turn1_request,
            conversation_id=conversation_id,
            turn_number=1
        )

        print(f"   User: 请审查这段代码并提供重构建议...")
        print(f"   📤 Request ID: {req_id_1}")

        # 模拟LLM响应
        turn1_response = {
            "request_id": req_id_1,
            "text": """代码审查结果：

1. **问题分析**：
   - 使用大量if-elif导致代码不易扩展
   - 缺少错误处理（除零错误）
   - 函数命名不够描述性

2. **重构建议**：
   - 使用字典映射替代if-elif
   - 添加输入验证
   - 改进函数命名和文档

建议使用策略模式重构。""",
            "finish_reason": "STOP",
            "usage": {
                "prompt_tokens": 150,
                "completion_tokens": 120,
                "total_tokens": 270
            },
            "duration": 2.3,
            "timestamp": time.time()
        }

        capture.capture_response(capture_id, turn1_response, request_id=req_id_1)

        print(f"   Assistant: 代码审查结果：问题分析和重构建议...")
        print(f"   📊 Tokens: {turn1_response['usage']['total_tokens']}")
        print(f"   ⏱️  Duration: {turn1_response['duration']:.2f}s")

        # ===== Turn 2: 用户请求重构示例 =====
        print("\n" + "-" * 80)
        print("🔵 Turn 2: 用户请求重构示例")
        print("-" * 80)

        turn2_request = {
            "request_id": "req_002",
            "model": "gemini-2.0-flash-exp",
            "prompt": "请给出使用策略模式重构后的代码示例",
            "timestamp": time.time(),
            "generation_config": {
                "temperature": 0.7,
                "max_tokens": 2000
            }
        }

        req_id_2 = capture.capture_request(
            capture_id,
            turn2_request,
            conversation_id=conversation_id,
            turn_number=2
        )

        print(f"   User: 请给出使用策略模式重构后的代码示例")
        print(f"   📤 Request ID: {req_id_2}")

        refactored_code = """
class Calculator:
    def __init__(self):
        self.operations = {
            'add': lambda a, b: a + b,
            'sub': lambda a, b: a - b,
            'mul': lambda a, b: a * b,
            'div': lambda a, b: a / b if b != 0 else None
        }

    def calculate(self, a: float, b: float, operation: str) -> float:
        if operation not in self.operations:
            raise ValueError(f"Unsupported operation: {operation}")

        result = self.operations[operation](a, b)
        if result is None:
            raise ValueError("Division by zero")

        return result
"""

        turn2_response = {
            "request_id": req_id_2,
            "text": f"这是重构后的代码：\n```python{refactored_code}```\n\n改进点：\n1. 使用字典映射消除if-elif\n2. 添加了类型提示\n3. 添加了输入验证和错误处理\n4. 代码更易扩展（添加新操作只需添加字典项）",
            "finish_reason": "STOP",
            "usage": {
                "prompt_tokens": 180,
                "completion_tokens": 200,
                "total_tokens": 380
            },
            "duration": 3.1,
            "timestamp": time.time()
        }

        capture.capture_response(capture_id, turn2_response, request_id=req_id_2)

        print(f"   Assistant: 这是重构后的代码：[代码示例]...")
        print(f"   📊 Tokens: {turn2_response['usage']['total_tokens']}")
        print(f"   ⏱️  Duration: {turn2_response['duration']:.2f}s")

        # ===== Turn 3: 用户询问测试建议 =====
        print("\n" + "-" * 80)
        print("🔵 Turn 3: 用户询问测试建议")
        print("-" * 80)

        turn3_request = {
            "request_id": "req_003",
            "model": "gemini-2.0-flash-exp",
            "prompt": "如何为这个重构后的代码编写单元测试？",
            "timestamp": time.time()
        }

        req_id_3 = capture.capture_request(
            capture_id,
            turn3_request,
            conversation_id=conversation_id,
            turn_number=3
        )

        print(f"   User: 如何为这个重构后的代码编写单元测试？")
        print(f"   📤 Request ID: {req_id_3}")

        turn3_response = {
            "request_id": req_id_3,
            "text": """单元测试建议：

```python
import pytest

def test_calculator_add():
    calc = Calculator()
    assert calc.calculate(2, 3, 'add') == 5

def test_calculator_division_by_zero():
    calc = Calculator()
    with pytest.raises(ValueError):
        calc.calculate(5, 0, 'div')

def test_invalid_operation():
    calc = Calculator()
    with pytest.raises(ValueError):
        calc.calculate(1, 2, 'invalid')
```

测试覆盖了：正常操作、边界条件、异常处理。""",
            "finish_reason": "STOP",
            "usage": {
                "prompt_tokens": 200,
                "completion_tokens": 150,
                "total_tokens": 350
            },
            "duration": 2.8,
            "timestamp": time.time()
        }

        capture.capture_response(capture_id, turn3_response, request_id=req_id_3)

        print(f"   Assistant: 单元测试建议：[测试代码示例]...")
        print(f"   📊 Tokens: {turn3_response['usage']['total_tokens']}")
        print(f"   ⏱️  Duration: {turn3_response['duration']:.2f}s")

        # ===== 验证捕获结果 =====
        print("\n" + "=" * 80)
        print("✅ 验证捕获结果")
        print("=" * 80)

        # 1. 验证对话历史
        conv = capture.get_conversation_history(conversation_id)

        assert conv is not None, "对话历史应该存在"
        assert conv.conversation_id == conversation_id
        assert conv.agent_name == "gemini-cli"

        print(f"\n✓ 对话历史验证:")
        print(f"  • 对话ID: {conv.conversation_id}")
        print(f"  • Agent: {conv.agent_name}")
        print(f"  • 总轮次: {conv.total_turns}")
        assert conv.total_turns == 3, "应该有3轮对话"

        # 2. 验证系统prompt
        assert conv.system_prompt is not None, "应该捕获系统prompt"
        assert "代码审查和重构助手" in conv.system_prompt
        print(f"  • 系统Prompt: ✓ 已捕获 ({len(conv.system_prompt)} 字符)")

        # 3. 验证消息结构
        print(f"\n✓ 消息结构验证:")
        print(f"  • 总消息数: {len(conv.messages)}")
        assert len(conv.messages) == 7, "应该有7条消息（1 system + 3*2 user/assistant）"

        # 验证消息角色
        roles = [msg.role for msg in conv.messages]
        expected_roles = [
            MessageRole.SYSTEM,
            MessageRole.USER, MessageRole.ASSISTANT,
            MessageRole.USER, MessageRole.ASSISTANT,
            MessageRole.USER, MessageRole.ASSISTANT
        ]
        assert roles == expected_roles, "消息角色顺序应该正确"
        print(f"  • 角色序列: system → user → assistant → user → assistant → user → assistant ✓")

        # 4. 验证turn编号
        turn_numbers = [msg.turn_number for msg in conv.messages if msg.role != MessageRole.SYSTEM]
        expected_turns = [1, 1, 2, 2, 3, 3]
        assert turn_numbers == expected_turns, "Turn编号应该正确"
        print(f"  • Turn编号: {turn_numbers} ✓")

        # 5. 验证tokens统计
        total_tokens = conv.total_tokens["total_tokens"]
        expected_total = 270 + 380 + 350  # 1000
        assert total_tokens == expected_total, f"Token总数应该为{expected_total}"
        print(f"\n✓ Token统计验证:")
        print(f"  • Prompt tokens: {conv.total_tokens['prompt_tokens']}")
        print(f"  • Completion tokens: {conv.total_tokens['completion_tokens']}")
        print(f"  • Total tokens: {total_tokens} ✓")

        # 6. 验证对话摘要
        summary = capture.get_conversation_summary(conversation_id)
        assert summary["total_turns"] == 3
        assert summary["total_messages"] == 7
        assert summary["has_system_prompt"] == True
        print(f"\n✓ 对话摘要验证:")
        print(f"  • 总轮次: {summary['total_turns']} ✓")
        print(f"  • 总消息: {summary['total_messages']} ✓")
        print(f"  • 有系统Prompt: {summary['has_system_prompt']} ✓")
        print(f"  • 对话时长: {summary['duration']:.3f}s")

        # 7. 验证消息内容完整性
        print(f"\n✓ 消息内容验证:")
        for msg in conv.messages:
            assert len(msg.content) > 0, "消息内容不应为空"
            assert msg.timestamp > 0, "时间戳应该有效"
        print(f"  • 所有消息内容完整 ✓")
        print(f"  • 所有时间戳有效 ✓")

        # 8. 导出对话历史
        export_path = tmp_path / "conversation_export.json"
        capture.export_conversation(conversation_id, str(export_path))

        assert export_path.exists(), "导出文件应该存在"

        with open(export_path, 'r', encoding='utf-8') as f:
            exported_data = json.load(f)

        assert exported_data["conversation_id"] == conversation_id
        assert exported_data["total_turns"] == 3
        assert len(exported_data["messages"]) == 7
        print(f"\n✓ 导出验证:")
        print(f"  • 导出文件: {export_path.name} ✓")
        print(f"  • 文件大小: {export_path.stat().st_size} bytes")

        # 9. 结束捕获
        result = capture.end_capture(capture_id)
        print(f"\n✓ 捕获会话完成:")
        print(f"  • 总请求数: {result['statistics']['total_requests']}")
        print(f"  • 总响应数: {result['statistics']['total_responses']}")
        print(f"  • 会话时长: {result['duration']:.3f}s")

        print("\n" + "=" * 80)
        print("🎉 集成测试完成！所有验证通过！")
        print("=" * 80)

    def test_multiple_conversations_in_same_session(self, tmp_path):
        """测试在同一个capture session中处理多个对话"""
        print("\n" + "=" * 80)
        print("🧪 测试场景：同一会话中的多个独立对话")
        print("=" * 80)

        capture = PromptCapture(storage_path=str(tmp_path / "multi_conv"))
        capture_id = capture.start_capture("gemini-cli-multi")

        # 对话1：关于Python
        conv1_id = "conv_python_001"
        print("\n📝 对话1: Python基础")
        for turn in range(1, 3):
            req_id = capture.capture_request(
                capture_id,
                {
                    "model": "gemini-2.0",
                    "prompt": f"Python问题 {turn}",
                    "system_prompt": "Python助手" if turn == 1 else None
                },
                conversation_id=conv1_id,
                turn_number=turn
            )
            capture.capture_response(
                capture_id,
                {"text": f"Python回答 {turn}", "usage": {"total_tokens": 50}},
                request_id=req_id
            )
            print(f"   Turn {turn}: 完成")

        # 对话2：关于JavaScript
        conv2_id = "conv_javascript_001"
        print("\n📝 对话2: JavaScript基础")
        for turn in range(1, 3):
            req_id = capture.capture_request(
                capture_id,
                {
                    "model": "gemini-2.0",
                    "prompt": f"JavaScript问题 {turn}",
                    "system_prompt": "JavaScript助手" if turn == 1 else None
                },
                conversation_id=conv2_id,
                turn_number=turn
            )
            capture.capture_response(
                capture_id,
                {"text": f"JavaScript回答 {turn}", "usage": {"total_tokens": 50}},
                request_id=req_id
            )
            print(f"   Turn {turn}: 完成")

        # 验证两个对话都被正确追踪
        conversations = capture.list_conversations()
        assert len(conversations) == 2, "应该有2个对话"
        print(f"\n✓ 对话列表验证:")
        print(f"  • 对话总数: {len(conversations)} ✓")

        conv1 = capture.get_conversation_history(conv1_id)
        conv2 = capture.get_conversation_history(conv2_id)

        assert conv1.total_turns == 2
        assert conv2.total_turns == 2
        assert conv1.system_prompt == "Python助手"
        assert conv2.system_prompt == "JavaScript助手"

        print(f"  • 对话1 ({conv1_id}): {conv1.total_turns}轮, 系统prompt='{conv1.system_prompt}' ✓")
        print(f"  • 对话2 ({conv2_id}): {conv2.total_turns}轮, 系统prompt='{conv2.system_prompt}' ✓")

        print("\n🎉 多对话测试完成！")

    def test_conversation_without_system_prompt(self, tmp_path):
        """测试没有系统prompt的对话（兼容性测试）"""
        print("\n" + "=" * 80)
        print("🧪 测试场景：无系统Prompt的对话（向后兼容）")
        print("=" * 80)

        capture = PromptCapture(storage_path=str(tmp_path / "no_system"))
        capture_id = capture.start_capture("test-agent")
        conversation_id = "conv_no_system"

        # 没有系统prompt的对话
        for turn in range(1, 4):
            req_id = capture.capture_request(
                capture_id,
                {
                    "model": "test-model",
                    "prompt": f"User message {turn}"
                    # 注意：没有system_prompt字段
                },
                conversation_id=conversation_id,
                turn_number=turn
            )
            capture.capture_response(
                capture_id,
                {"text": f"Assistant response {turn}"},
                request_id=req_id
            )
            print(f"   Turn {turn}: 完成")

        # 验证
        conv = capture.get_conversation_history(conversation_id)
        assert conv.system_prompt is None, "不应该有系统prompt"
        assert conv.total_turns == 3
        # 应该只有user和assistant消息，没有system消息
        assert len(conv.messages) == 6  # 3 user + 3 assistant

        system_messages = conv.get_messages_by_role(MessageRole.SYSTEM)
        assert len(system_messages) == 0, "不应该有system消息"

        print(f"\n✓ 验证结果:")
        print(f"  • 系统Prompt: None ✓")
        print(f"  • 消息总数: {len(conv.messages)} (仅user+assistant) ✓")
        print(f"  • System消息数: {len(system_messages)} ✓")

        print("\n🎉 向后兼容性测试通过！")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

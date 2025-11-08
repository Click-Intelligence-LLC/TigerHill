"""
Phase 1 增强功能测试

测试系统Prompt提取和对话历史结构化功能
"""

import pytest
import time
import uuid
from tigerhill.observer.capture import PromptCapture
from tigerhill.observer.conversation_models import (
    SystemPromptExtractor,
    ConversationHistory,
    ConversationMessage,
    MessageRole
)


class TestSystemPromptExtractor:
    """测试系统Prompt提取器"""

    def test_extract_from_gemini_format(self):
        """测试从Gemini格式提取系统prompt"""
        # Gemini格式：system_instruction参数
        kwargs = {
            'system_instruction': "You are a helpful programming assistant."
        }

        result = SystemPromptExtractor.extract_from_kwargs(kwargs)
        assert result == "You are a helpful programming assistant."

    def test_extract_from_openai_format(self):
        """测试从OpenAI格式提取系统prompt"""
        # OpenAI格式：messages数组中的system role
        kwargs = {
            'messages': [
                {'role': 'system', 'content': 'You are an expert Python developer.'},
                {'role': 'user', 'content': 'Hello'}
            ]
        }

        result = SystemPromptExtractor.extract_from_kwargs(kwargs)
        assert result == 'You are an expert Python developer.'

    def test_extract_from_anthropic_format(self):
        """测试从Anthropic格式提取系统prompt"""
        # Anthropic格式：system参数
        kwargs = {
            'system': 'You are Claude, an AI assistant.'
        }

        result = SystemPromptExtractor.extract_from_kwargs(kwargs)
        assert result == 'You are Claude, an AI assistant.'

    def test_extract_with_complex_gemini_parts(self):
        """测试从复杂的Gemini parts结构提取"""
        # Mock Gemini Content object with parts
        class MockPart:
            def __init__(self, text):
                self.text = text

        class MockContent:
            def __init__(self, parts):
                self.parts = parts

        kwargs = {
            'system_instruction': MockContent([
                MockPart("You are a helpful assistant."),
                MockPart("Always be concise.")
            ])
        }

        result = SystemPromptExtractor.extract_from_kwargs(kwargs)
        assert "You are a helpful assistant." in result
        assert "Always be concise." in result

    def test_extract_returns_none_when_not_present(self):
        """测试当系统prompt不存在时返回None"""
        kwargs = {
            'messages': [
                {'role': 'user', 'content': 'Hello'}
            ]
        }

        result = SystemPromptExtractor.extract_from_kwargs(kwargs)
        assert result is None

    def test_priority_system_instruction_over_messages(self):
        """测试system_instruction优先于messages中的system"""
        kwargs = {
            'system_instruction': 'Gemini system prompt',
            'messages': [
                {'role': 'system', 'content': 'Messages system prompt'},
                {'role': 'user', 'content': 'Hello'}
            ]
        }

        result = SystemPromptExtractor.extract_from_kwargs(kwargs)
        assert result == 'Gemini system prompt'


class TestConversationHistory:
    """测试对话历史数据模型"""

    def test_create_conversation(self):
        """测试创建对话历史"""
        conv = ConversationHistory(
            conversation_id="test_conv_1",
            agent_name="test_agent"
        )

        assert conv.conversation_id == "test_conv_1"
        assert conv.agent_name == "test_agent"
        assert len(conv.messages) == 0
        assert conv.total_turns == 0

    def test_add_system_message(self):
        """测试添加系统消息"""
        conv = ConversationHistory(
            conversation_id="test_conv_2",
            agent_name="test_agent"
        )

        conv.add_system_message("You are a helpful assistant.")

        assert conv.system_prompt == "You are a helpful assistant."
        assert len(conv.messages) == 1
        assert conv.messages[0].role == MessageRole.SYSTEM
        assert conv.messages[0].turn_number == 0

    def test_add_user_message(self):
        """测试添加用户消息"""
        conv = ConversationHistory(
            conversation_id="test_conv_3",
            agent_name="test_agent"
        )

        conv.add_user_message("Hello, how are you?", turn_number=1)

        assert len(conv.messages) == 1
        assert conv.messages[0].role == MessageRole.USER
        assert conv.messages[0].content == "Hello, how are you?"
        assert conv.messages[0].turn_number == 1
        assert conv.total_turns == 1
        assert len(conv.turns) == 1

    def test_add_assistant_message(self):
        """测试添加助手消息"""
        conv = ConversationHistory(
            conversation_id="test_conv_4",
            agent_name="test_agent"
        )

        # 先添加用户消息
        conv.add_user_message("Hello", turn_number=1)

        # 然后添加助手回复
        conv.add_assistant_message(
            "Hi there! How can I help you?",
            turn_number=1,
            tokens_used={"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25}
        )

        assert len(conv.messages) == 2
        assert conv.messages[1].role == MessageRole.ASSISTANT
        assert conv.messages[1].turn_number == 1

        # 验证turn已更新
        assert len(conv.turns) == 1
        assert conv.turns[0].assistant_message is not None
        assert conv.turns[0].tokens_used == {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25}

        # 验证tokens统计
        assert conv.total_tokens["prompt_tokens"] == 10
        assert conv.total_tokens["completion_tokens"] == 15

    def test_multi_turn_conversation(self):
        """测试多轮对话"""
        conv = ConversationHistory(
            conversation_id="test_conv_5",
            agent_name="test_agent"
        )

        # Turn 1
        conv.add_user_message("What is Python?", turn_number=1)
        conv.add_assistant_message("Python is a programming language.", turn_number=1)

        # Turn 2
        conv.add_user_message("Tell me more", turn_number=2)
        conv.add_assistant_message("Python was created by Guido van Rossum.", turn_number=2)

        # Turn 3
        conv.add_user_message("When?", turn_number=3)
        conv.add_assistant_message("First released in 1991.", turn_number=3)

        assert conv.total_turns == 3
        assert len(conv.messages) == 6
        assert len(conv.turns) == 3

        # 验证消息顺序
        assert conv.messages[0].role == MessageRole.USER
        assert conv.messages[1].role == MessageRole.ASSISTANT
        assert conv.messages[2].role == MessageRole.USER
        assert conv.messages[3].role == MessageRole.ASSISTANT

    def test_get_messages_by_turn(self):
        """测试按turn获取消息"""
        conv = ConversationHistory(
            conversation_id="test_conv_6",
            agent_name="test_agent"
        )

        conv.add_user_message("Turn 1 user", turn_number=1)
        conv.add_assistant_message("Turn 1 assistant", turn_number=1)
        conv.add_user_message("Turn 2 user", turn_number=2)
        conv.add_assistant_message("Turn 2 assistant", turn_number=2)

        turn1_messages = conv.get_messages_by_turn(1)
        assert len(turn1_messages) == 2
        assert all(msg.turn_number == 1 for msg in turn1_messages)

        turn2_messages = conv.get_messages_by_turn(2)
        assert len(turn2_messages) == 2
        assert all(msg.turn_number == 2 for msg in turn2_messages)

    def test_get_messages_by_role(self):
        """测试按角色获取消息"""
        conv = ConversationHistory(
            conversation_id="test_conv_7",
            agent_name="test_agent"
        )

        conv.add_system_message("System prompt")
        conv.add_user_message("User 1", turn_number=1)
        conv.add_assistant_message("Assistant 1", turn_number=1)
        conv.add_user_message("User 2", turn_number=2)
        conv.add_assistant_message("Assistant 2", turn_number=2)

        system_messages = conv.get_messages_by_role(MessageRole.SYSTEM)
        assert len(system_messages) == 1

        user_messages = conv.get_messages_by_role(MessageRole.USER)
        assert len(user_messages) == 2

        assistant_messages = conv.get_messages_by_role(MessageRole.ASSISTANT)
        assert len(assistant_messages) == 2

    def test_to_dict(self):
        """测试导出为字典"""
        conv = ConversationHistory(
            conversation_id="test_conv_8",
            agent_name="test_agent"
        )

        conv.add_system_message("You are helpful")
        conv.add_user_message("Hello", turn_number=1)
        conv.add_assistant_message("Hi", turn_number=1)

        dict_data = conv.to_dict()

        assert dict_data["conversation_id"] == "test_conv_8"
        assert dict_data["agent_name"] == "test_agent"
        assert dict_data["system_prompt"] == "You are helpful"
        assert dict_data["total_turns"] == 1
        assert dict_data["message_count"] == 3
        assert len(dict_data["messages"]) == 3
        assert len(dict_data["turns"]) == 1


class TestPromptCaptureWithConversation:
    """测试PromptCapture的对话追踪功能"""

    def test_capture_with_conversation_id(self, tmp_path):
        """测试带conversation_id的捕获"""
        capture = PromptCapture(storage_path=str(tmp_path))
        capture_id = capture.start_capture("test_agent")

        conversation_id = "conv_test_001"

        # Turn 1
        request_id_1 = capture.capture_request(
            capture_id,
            {
                "model": "gemini-2.0-flash-exp",
                "prompt": "What is Python?",
                "system_prompt": "You are a programming tutor."
            },
            conversation_id=conversation_id,
            turn_number=1
        )

        capture.capture_response(
            capture_id,
            {
                "text": "Python is a high-level programming language.",
                "usage": {"prompt_tokens": 20, "completion_tokens": 15, "total_tokens": 35}
            },
            request_id=request_id_1
        )

        # Turn 2
        request_id_2 = capture.capture_request(
            capture_id,
            {
                "model": "gemini-2.0-flash-exp",
                "prompt": "Tell me more"
            },
            conversation_id=conversation_id,
            turn_number=2
        )

        capture.capture_response(
            capture_id,
            {
                "text": "Python was created by Guido van Rossum.",
                "usage": {"prompt_tokens": 15, "completion_tokens": 12, "total_tokens": 27}
            },
            request_id=request_id_2
        )

        # 验证对话历史
        conv = capture.get_conversation_history(conversation_id)
        assert conv is not None
        assert conv.conversation_id == conversation_id
        assert conv.total_turns == 2
        assert len(conv.messages) == 5  # system + 2*(user+assistant)

        # 验证系统prompt
        assert conv.system_prompt == "You are a programming tutor."

        # 验证消息角色
        assert conv.messages[0].role == MessageRole.SYSTEM
        assert conv.messages[1].role == MessageRole.USER
        assert conv.messages[2].role == MessageRole.ASSISTANT
        assert conv.messages[3].role == MessageRole.USER
        assert conv.messages[4].role == MessageRole.ASSISTANT

        # 验证tokens累计
        assert conv.total_tokens["total_tokens"] == 62  # 35 + 27

    def test_list_conversations(self, tmp_path):
        """测试列出对话"""
        capture = PromptCapture(storage_path=str(tmp_path))
        capture_id = capture.start_capture("test_agent")

        # 创建两个对话
        for i in range(1, 3):
            conv_id = f"conv_test_{i:03d}"
            capture.capture_request(
                capture_id,
                {
                    "model": "test-model",
                    "prompt": f"Message {i}"
                },
                conversation_id=conv_id,
                turn_number=1
            )

        conversations = capture.list_conversations()
        assert len(conversations) == 2
        assert all('conversation_id' in conv for conv in conversations)
        assert all('total_turns' in conv for conv in conversations)

    def test_export_conversation(self, tmp_path):
        """测试导出对话历史"""
        capture = PromptCapture(storage_path=str(tmp_path))
        capture_id = capture.start_capture("test_agent")

        conversation_id = "conv_export_test"
        capture.capture_request(
            capture_id,
            {
                "model": "test-model",
                "prompt": "Test message",
                "system_prompt": "Test system"
            },
            conversation_id=conversation_id,
            turn_number=1
        )

        # 导出
        export_path = tmp_path / "conversation_export.json"
        capture.export_conversation(conversation_id, str(export_path))

        # 验证文件存在
        assert export_path.exists()

        # 读取并验证内容
        import json
        with open(export_path, 'r') as f:
            data = json.load(f)

        assert data["conversation_id"] == conversation_id
        assert data["system_prompt"] == "Test system"
        assert len(data["messages"]) >= 1

    def test_get_conversation_summary(self, tmp_path):
        """测试获取对话摘要"""
        capture = PromptCapture(storage_path=str(tmp_path))
        capture_id = capture.start_capture("test_agent")

        conversation_id = "conv_summary_test"

        # 添加多轮对话
        for turn in range(1, 4):
            req_id = capture.capture_request(
                capture_id,
                {
                    "model": "test-model",
                    "prompt": f"Turn {turn} question"
                },
                conversation_id=conversation_id,
                turn_number=turn
            )

            capture.capture_response(
                capture_id,
                {
                    "text": f"Turn {turn} answer",
                    "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
                },
                request_id=req_id
            )

        # 获取摘要
        summary = capture.get_conversation_summary(conversation_id)

        assert summary["conversation_id"] == conversation_id
        assert summary["total_turns"] == 3
        assert summary["total_messages"] == 6  # 3 user + 3 assistant
        assert summary["total_tokens"]["total_tokens"] == 60  # 3 * 20
        assert len(summary["turns"]) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

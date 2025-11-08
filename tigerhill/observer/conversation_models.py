"""
Conversation Data Models - 通用对话数据结构

支持多种LLM agent的对话追踪，包括：
- Gemini CLI
- OpenAI API
- Anthropic API (Claude)
- 其他兼容架构的agent
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import time


class MessageRole(str, Enum):
    """消息角色枚举"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    FUNCTION = "function"  # 兼容OpenAI function calling


class ConversationMessage(BaseModel):
    """
    结构化的对话消息

    通用消息结构，兼容多种agent格式
    """
    role: MessageRole
    content: str
    timestamp: float = Field(default_factory=time.time)
    turn_number: int
    message_index: int  # 在turn内的消息索引

    # 可选元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # 工具相关（如果是tool/function消息）
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None

    class Config:
        use_enum_values = True


class ConversationTurn(BaseModel):
    """
    单次对话轮次

    包含一个用户输入和对应的助手响应
    """
    turn_number: int
    user_message: ConversationMessage
    assistant_message: Optional[ConversationMessage] = None

    # Turn级别的元数据
    duration: Optional[float] = None
    tokens_used: Optional[Dict[str, int]] = None
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)

    start_time: float = Field(default_factory=time.time)
    end_time: Optional[float] = None

    # 动态上下文（Phase 3支持）
    context_injections: List[Dict[str, Any]] = Field(default_factory=list)


class ConversationHistory(BaseModel):
    """
    完整的对话历史

    追踪从开始到结束的完整对话
    """
    conversation_id: str
    agent_name: str

    # 系统prompt（通常在对话开始时设置）
    system_prompt: Optional[str] = None

    # 所有消息（按时间顺序）
    messages: List[ConversationMessage] = Field(default_factory=list)

    # 结构化的turns
    turns: List[ConversationTurn] = Field(default_factory=list)

    # 对话级别统计
    total_turns: int = 0
    started_at: float = Field(default_factory=time.time)
    last_updated_at: float = Field(default_factory=time.time)
    ended_at: Optional[float] = None

    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # 总计统计
    total_tokens: Dict[str, int] = Field(default_factory=lambda: {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    })

    def add_system_message(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """添加系统消息"""
        self.system_prompt = content
        message = ConversationMessage(
            role=MessageRole.SYSTEM,
            content=content,
            turn_number=0,
            message_index=len(self.messages),
            metadata=metadata or {}
        )
        self.messages.append(message)

    def add_user_message(self, content: str, turn_number: int, metadata: Optional[Dict[str, Any]] = None):
        """添加用户消息"""
        message = ConversationMessage(
            role=MessageRole.USER,
            content=content,
            turn_number=turn_number,
            message_index=len(self.messages),
            metadata=metadata or {}
        )
        self.messages.append(message)

        # 创建新的turn
        turn = ConversationTurn(
            turn_number=turn_number,
            user_message=message
        )
        self.turns.append(turn)
        self.total_turns = max(self.total_turns, turn_number)
        self.last_updated_at = time.time()

        return message

    def add_assistant_message(self,
                             content: str,
                             turn_number: int,
                             metadata: Optional[Dict[str, Any]] = None,
                             tool_calls: Optional[List[Dict[str, Any]]] = None,
                             tokens_used: Optional[Dict[str, int]] = None):
        """添加助手消息"""
        message = ConversationMessage(
            role=MessageRole.ASSISTANT,
            content=content,
            turn_number=turn_number,
            message_index=len(self.messages),
            metadata=metadata or {}
        )
        self.messages.append(message)

        # 更新对应的turn
        for turn in self.turns:
            if turn.turn_number == turn_number:
                turn.assistant_message = message
                turn.end_time = time.time()
                if turn.start_time:
                    turn.duration = turn.end_time - turn.start_time
                if tool_calls:
                    turn.tool_calls = tool_calls
                if tokens_used:
                    turn.tokens_used = tokens_used
                    # 更新总计
                    self.total_tokens["prompt_tokens"] += tokens_used.get("prompt_tokens", 0)
                    self.total_tokens["completion_tokens"] += tokens_used.get("completion_tokens", 0)
                    self.total_tokens["total_tokens"] += tokens_used.get("total_tokens", 0)
                break

        self.last_updated_at = time.time()
        return message

    def add_tool_message(self,
                        content: str,
                        turn_number: int,
                        tool_name: str,
                        tool_call_id: Optional[str] = None,
                        metadata: Optional[Dict[str, Any]] = None):
        """添加工具执行结果消息"""
        message = ConversationMessage(
            role=MessageRole.TOOL,
            content=content,
            turn_number=turn_number,
            message_index=len(self.messages),
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.last_updated_at = time.time()
        return message

    def get_messages_by_turn(self, turn_number: int) -> List[ConversationMessage]:
        """获取指定turn的所有消息"""
        return [msg for msg in self.messages if msg.turn_number == turn_number]

    def get_messages_by_role(self, role: MessageRole) -> List[ConversationMessage]:
        """获取指定角色的所有消息"""
        return [msg for msg in self.messages if msg.role == role]

    def to_dict(self) -> Dict[str, Any]:
        """导出为字典格式"""
        return {
            "conversation_id": self.conversation_id,
            "agent_name": self.agent_name,
            "system_prompt": self.system_prompt,
            "total_turns": self.total_turns,
            "message_count": len(self.messages),
            "started_at": self.started_at,
            "last_updated_at": self.last_updated_at,
            "ended_at": self.ended_at,
            "duration": (self.ended_at or self.last_updated_at) - self.started_at,
            "total_tokens": self.total_tokens,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "turn": msg.turn_number,
                    "index": msg.message_index,
                    "timestamp": msg.timestamp,
                    "metadata": msg.metadata,
                    "tool_call_id": msg.tool_call_id,
                    "tool_name": msg.tool_name
                }
                for msg in self.messages
            ],
            "turns": [
                {
                    "turn_number": turn.turn_number,
                    "user_content": turn.user_message.content,
                    "assistant_content": turn.assistant_message.content if turn.assistant_message else None,
                    "duration": turn.duration,
                    "tokens_used": turn.tokens_used,
                    "tool_calls": turn.tool_calls
                }
                for turn in self.turns
            ],
            "metadata": self.metadata
        }


class SystemPromptExtractor:
    """
    系统Prompt提取器

    支持多种agent的系统prompt格式：
    - Gemini: system_instruction参数
    - OpenAI: messages数组中的system role
    - Anthropic: system参数
    - 其他自定义格式
    """

    @staticmethod
    def extract_from_kwargs(kwargs: Dict[str, Any]) -> Optional[str]:
        """
        从kwargs中提取系统prompt

        支持多种格式：
        1. Gemini: system_instruction
        2. OpenAI: messages数组中的system消息
        3. Anthropic: system参数
        4. 通用: system_prompt参数
        """

        # 1. 尝试Gemini格式: system_instruction
        if 'system_instruction' in kwargs:
            system_inst = kwargs['system_instruction']

            # Gemini Content对象
            if hasattr(system_inst, 'parts'):
                parts = []
                for part in system_inst.parts:
                    if hasattr(part, 'text'):
                        parts.append(part.text)
                    else:
                        parts.append(str(part))
                return "\n".join(parts)

            # 字符串
            elif isinstance(system_inst, str):
                return system_inst

            # 字典格式
            elif isinstance(system_inst, dict):
                if 'parts' in system_inst:
                    parts = []
                    for part in system_inst['parts']:
                        if isinstance(part, dict) and 'text' in part:
                            parts.append(part['text'])
                        elif isinstance(part, str):
                            parts.append(part)
                    return "\n".join(parts)
                elif 'text' in system_inst:
                    return system_inst['text']

        # 2. 尝试OpenAI格式: messages数组中的system消息
        if 'messages' in kwargs:
            messages = kwargs['messages']
            if isinstance(messages, list):
                for msg in messages:
                    if isinstance(msg, dict):
                        if msg.get('role') == 'system':
                            return msg.get('content', '')
                    elif hasattr(msg, 'role') and msg.role == 'system':
                        if hasattr(msg, 'content'):
                            return msg.content

        # 3. 尝试Anthropic格式: system参数
        if 'system' in kwargs:
            system = kwargs['system']
            if isinstance(system, str):
                return system
            elif isinstance(system, list):
                # 可能是多个system message
                return "\n".join(str(s) for s in system)

        # 4. 通用格式: system_prompt参数
        if 'system_prompt' in kwargs:
            return str(kwargs['system_prompt'])

        return None

    @staticmethod
    def extract_from_messages(messages: List[Any]) -> Optional[str]:
        """从消息列表中提取系统prompt"""
        if not messages:
            return None

        for msg in messages:
            # 字典格式
            if isinstance(msg, dict):
                if msg.get('role') == 'system':
                    return msg.get('content', '')

            # 对象格式
            elif hasattr(msg, 'role'):
                if msg.role == 'system':
                    if hasattr(msg, 'content'):
                        return msg.content
                    elif hasattr(msg, 'parts'):
                        parts = []
                        for part in msg.parts:
                            if hasattr(part, 'text'):
                                parts.append(part.text)
                        return "\n".join(parts)

        return None

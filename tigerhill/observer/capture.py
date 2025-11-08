"""
Prompt Capture - 核心捕获功能

负责接收、存储和管理捕获的 prompt 数据。
支持多轮对话追踪和结构化历史记录。
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

from tigerhill.observer.conversation_models import (
    ConversationHistory,
    ConversationMessage,
    MessageRole
)

logger = logging.getLogger(__name__)


class PromptCapture:
    """
    Prompt 捕获管理器

    负责接收和存储从 observer SDK 捕获的数据。
    """

    def __init__(
        self,
        storage_path: str = "./prompt_captures",
        auto_save: bool = True,
        redact_patterns: Optional[List[Dict[str, str]]] = None
    ):
        """
        初始化 Prompt 捕获器

        Args:
            storage_path: 捕获数据存储路径
            auto_save: 是否自动保存到文件
            redact_patterns: 脱敏规则列表 [{"pattern": regex, "replacement": str}]
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.auto_save = auto_save
        self.redact_patterns = redact_patterns or []

        # 当前捕获会话
        self.captures: Dict[str, Dict[str, Any]] = {}

        # ✅ 新增：对话历史追踪
        self.conversations: Dict[str, ConversationHistory] = {}

        # ✅ 新增：request_id到conversation_id的映射
        self.request_conversation_map: Dict[str, str] = {}

        logger.info(f"PromptCapture initialized: {storage_path}")

    def start_capture(
        self,
        agent_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        开始新的捕获会话

        Args:
            agent_name: Agent 名称
            metadata: 额外元数据

        Returns:
            capture_id: 捕获会话 ID
        """
        capture_id = str(uuid.uuid4())

        self.captures[capture_id] = {
            "capture_id": capture_id,
            "agent_name": agent_name,
            "start_time": time.time(),
            "metadata": metadata or {},
            "requests": [],
            "responses": [],
            "tool_calls": [],
            "status": "active"
        }

        logger.info(f"Started capture: {capture_id} for agent: {agent_name}")
        return capture_id

    def capture_request(
        self,
        capture_id: str,
        request_data: Dict[str, Any],
        conversation_id: Optional[str] = None,
        turn_number: Optional[int] = None
    ) -> str:
        """
        捕获请求数据

        Args:
            capture_id: 捕获会话 ID
            request_data: 请求数据，包含：
                - model: 模型名称
                - prompt: 用户 prompt
                - system_prompt: 系统 prompt (可选)
                - messages: 结构化消息历史 (可选)
                - temperature: 温度参数 (可选)
                - max_tokens: 最大 token 数 (可选)
                - tools: 工具列表 (可选)
                - context: 上下文数据 (可选)
            conversation_id: 对话ID (可选，用于多轮对话追踪)
            turn_number: 对话轮次 (可选，从1开始)

        Returns:
            request_id: 生成的请求ID
        """
        if capture_id not in self.captures:
            logger.warning(f"Unknown capture_id: {capture_id}")
            return ""

        # 脱敏处理
        sanitized_data = self._sanitize(request_data)

        # 添加时间戳和request_id
        if "timestamp" not in sanitized_data:
            sanitized_data["timestamp"] = time.time()

        if "request_id" not in sanitized_data:
            sanitized_data["request_id"] = str(uuid.uuid4())

        request_id = sanitized_data["request_id"]

        # ✅ 新增：对话追踪元数据
        if conversation_id:
            sanitized_data["conversation_id"] = conversation_id
            sanitized_data["turn_number"] = turn_number or 1

            # 建立request_id到conversation_id的映射
            self.request_conversation_map[request_id] = conversation_id

            # 更新结构化对话历史
            self._update_conversation_history(
                capture_id,
                conversation_id,
                sanitized_data,
                turn_number or 1
            )

        # 存储
        self.captures[capture_id]["requests"].append(sanitized_data)

        logger.debug(f"Captured request for {capture_id}: model={sanitized_data.get('model')}, conv={conversation_id}, turn={turn_number}")

        return request_id

    def capture_response(
        self,
        capture_id: str,
        response_data: Dict[str, Any],
        request_id: Optional[str] = None
    ) -> None:
        """
        捕获响应数据

        Args:
            capture_id: 捕获会话 ID
            response_data: 响应数据，包含：
                - text: 响应文本
                - finish_reason: 完成原因
                - usage: token 使用情况
                - tool_calls: 工具调用 (可选)
            request_id: 关联的请求ID (可选，用于对话追踪)
        """
        if capture_id not in self.captures:
            logger.warning(f"Unknown capture_id: {capture_id}")
            return

        # 脱敏处理
        sanitized_data = self._sanitize(response_data)

        # 添加时间戳
        if "timestamp" not in sanitized_data:
            sanitized_data["timestamp"] = time.time()

        if "response_id" not in sanitized_data:
            sanitized_data["response_id"] = str(uuid.uuid4())

        # ✅ 新增：关联request_id
        if request_id:
            sanitized_data["request_id"] = request_id

            # 如果这个request属于某个conversation，更新对话历史
            if request_id in self.request_conversation_map:
                conversation_id = self.request_conversation_map[request_id]
                self._update_conversation_with_response(
                    capture_id,
                    conversation_id,
                    request_id,
                    sanitized_data
                )

        # 存储
        self.captures[capture_id]["responses"].append(sanitized_data)

        # 如果有工具调用，单独记录
        if "tool_calls" in sanitized_data and sanitized_data["tool_calls"]:
            self.captures[capture_id]["tool_calls"].extend(
                sanitized_data["tool_calls"]
            )

        logger.debug(f"Captured response for {capture_id}: {len(sanitized_data.get('text', ''))} chars, request_id={request_id}")

    def end_capture(self, capture_id: str) -> Dict[str, Any]:
        """
        结束捕获会话

        Args:
            capture_id: 捕获会话 ID

        Returns:
            完整的捕获数据
        """
        if capture_id not in self.captures:
            logger.warning(f"Unknown capture_id: {capture_id}")
            return {}

        capture = self.captures[capture_id]
        capture["end_time"] = time.time()
        capture["duration"] = capture["end_time"] - capture["start_time"]
        capture["status"] = "completed"

        # 统计信息
        capture["statistics"] = self._calculate_statistics(capture)

        # 自动保存
        if self.auto_save:
            self._save_capture(capture)

        logger.info(f"Ended capture: {capture_id}, duration: {capture['duration']:.2f}s")

        return capture

    def get_capture(self, capture_id: str) -> Optional[Dict[str, Any]]:
        """获取捕获数据"""
        return self.captures.get(capture_id)

    def list_captures(
        self,
        agent_name: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        列出捕获会话

        Args:
            agent_name: 过滤 agent 名称
            status: 过滤状态 (active/completed)

        Returns:
            捕获会话列表
        """
        captures = list(self.captures.values())

        if agent_name:
            captures = [c for c in captures if c["agent_name"] == agent_name]

        if status:
            captures = [c for c in captures if c["status"] == status]

        return captures

    def _sanitize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        脱敏处理

        移除或替换敏感信息（API keys, emails, etc.）
        """
        import re

        # 深拷贝避免修改原数据
        import copy
        sanitized = copy.deepcopy(data)

        # 默认脱敏规则
        default_patterns = [
            {
                "pattern": r"(AIza|sk-)[0-9A-Za-z-_]{20,}",
                "replacement": "<REDACTED_API_KEY>"
            },
            {
                "pattern": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                "replacement": "<REDACTED_EMAIL>"
            },
            {
                "pattern": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
                "replacement": "<REDACTED_CARD>"
            }
        ]

        all_patterns = default_patterns + self.redact_patterns

        # 递归应用脱敏规则
        def redact_recursive(obj):
            if isinstance(obj, str):
                for rule in all_patterns:
                    obj = re.sub(rule["pattern"], rule["replacement"], obj)
                return obj
            elif isinstance(obj, dict):
                return {k: redact_recursive(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [redact_recursive(item) for item in obj]
            else:
                return obj

        return redact_recursive(sanitized)

    def _calculate_statistics(self, capture: Dict[str, Any]) -> Dict[str, Any]:
        """计算统计信息"""
        stats = {
            "total_requests": len(capture["requests"]),
            "total_responses": len(capture["responses"]),
            "total_tool_calls": len(capture["tool_calls"]),
        }

        # Token 统计
        total_prompt_tokens = 0
        total_completion_tokens = 0

        for response in capture["responses"]:
            usage = response.get("usage", {})
            total_prompt_tokens += usage.get("prompt_tokens", 0)
            total_completion_tokens += usage.get("completion_tokens", 0)

        stats["total_prompt_tokens"] = total_prompt_tokens
        stats["total_completion_tokens"] = total_completion_tokens
        stats["total_tokens"] = total_prompt_tokens + total_completion_tokens

        # 平均长度
        if capture["responses"]:
            avg_response_length = sum(
                len(r.get("text", "")) for r in capture["responses"]
            ) / len(capture["responses"])
            stats["avg_response_length"] = avg_response_length

        return stats

    def _save_capture(self, capture: Dict[str, Any]) -> None:
        """保存捕获数据到文件"""
        capture_id = capture["capture_id"]
        timestamp = int(capture["start_time"])

        filename = f"capture_{capture_id}_{timestamp}.json"
        filepath = self.storage_path / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(capture, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved capture to: {filepath}")

    def load_capture(self, capture_id: str) -> Optional[Dict[str, Any]]:
        """从文件加载捕获数据"""
        # 查找匹配的文件
        pattern = f"capture_{capture_id}_*.json"
        files = list(self.storage_path.glob(pattern))

        if not files:
            logger.warning(f"No capture file found for: {capture_id}")
            return None

        # 加载最新的文件
        latest_file = max(files, key=lambda p: p.stat().st_mtime)

        with open(latest_file, "r", encoding="utf-8") as f:
            capture = json.load(f)

        # 加载到内存
        self.captures[capture_id] = capture

        logger.info(f"Loaded capture from: {latest_file}")
        return capture

    def export_to_trace_store(
        self,
        capture_id: str,
        trace_store: Any,
        agent_name: Optional[str] = None
    ) -> str:
        """
        导出到 TraceStore

        Args:
            capture_id: 捕获会话 ID
            trace_store: TraceStore 实例
            agent_name: 覆盖 agent 名称

        Returns:
            trace_id: 创建的 trace ID
        """
        capture = self.captures.get(capture_id)
        if not capture:
            # 尝试从文件加载
            capture = self.load_capture(capture_id)
            if not capture:
                raise ValueError(f"Capture not found: {capture_id}")

        # 创建 trace
        trace_id = trace_store.start_trace(
            agent_name=agent_name or capture["agent_name"],
            task_id=capture_id,
            metadata=capture.get("metadata", {})
        )

        # 写入请求事件
        for request in capture["requests"]:
            trace_store.write_event({
                "type": "prompt_request",
                "data": request
            })

        # 写入响应事件
        for response in capture["responses"]:
            trace_store.write_event({
                "type": "model_response",
                "text": response.get("text", ""),
                "data": response
            })

        # 写入工具调用
        for tool_call in capture.get("tool_calls", []):
            trace_store.write_event({
                "type": "tool_call",
                "data": tool_call
            })

        # 写入统计信息
        if "statistics" in capture:
            trace_store.write_event({
                "type": "statistics",
                "data": capture["statistics"]
            })

        # 结束 trace
        trace_store.end_trace(trace_id)

        logger.info(f"Exported capture {capture_id} to trace {trace_id}")
        return trace_id

    # ============================================================================
    # 对话追踪方法 (Phase 1新增)
    # ============================================================================

    def _update_conversation_history(
        self,
        capture_id: str,
        conversation_id: str,
        request_data: Dict[str, Any],
        turn_number: int
    ) -> None:
        """
        更新结构化对话历史（添加用户消息）

        Args:
            capture_id: 捕获会话ID
            conversation_id: 对话ID
            request_data: 请求数据
            turn_number: 对话轮次
        """
        # 确保对话存在
        if conversation_id not in self.conversations:
            capture = self.captures.get(capture_id, {})
            agent_name = capture.get("agent_name", "unknown")

            self.conversations[conversation_id] = ConversationHistory(
                conversation_id=conversation_id,
                agent_name=agent_name,
                started_at=request_data.get("timestamp", time.time())
            )

        conv = self.conversations[conversation_id]

        # 添加系统prompt（如果是第一轮且存在系统prompt）
        if turn_number == 1 and request_data.get("system_prompt"):
            conv.add_system_message(
                content=request_data["system_prompt"],
                metadata={"model": request_data.get("model")}
            )

        # 添加用户消息
        user_prompt = request_data.get("prompt", "")
        conv.add_user_message(
            content=user_prompt,
            turn_number=turn_number,
            metadata={
                "model": request_data.get("model"),
                "request_id": request_data.get("request_id"),
                "generation_config": request_data.get("generation_config"),
                "tools": request_data.get("tools")
            }
        )

        logger.debug(f"Updated conversation {conversation_id}: turn {turn_number}, user message added")

    def _update_conversation_with_response(
        self,
        capture_id: str,
        conversation_id: str,
        request_id: str,
        response_data: Dict[str, Any]
    ) -> None:
        """
        更新结构化对话历史（添加助手回复）

        Args:
            capture_id: 捕获会话ID
            conversation_id: 对话ID
            request_id: 请求ID
            response_data: 响应数据
        """
        if conversation_id not in self.conversations:
            logger.warning(f"Conversation {conversation_id} not found when adding response")
            return

        conv = self.conversations[conversation_id]

        # 找到对应的请求，确定turn_number
        capture = self.captures.get(capture_id, {})
        requests = capture.get("requests", [])

        turn_number = 1
        for req in requests:
            if req.get("request_id") == request_id:
                turn_number = req.get("turn_number", 1)
                break

        # 提取tokens使用情况
        tokens_used = None
        if "usage" in response_data:
            usage = response_data["usage"]
            tokens_used = {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0)
            }

        # 添加助手消息
        assistant_text = response_data.get("text", "")
        conv.add_assistant_message(
            content=assistant_text,
            turn_number=turn_number,
            metadata={
                "response_id": response_data.get("response_id"),
                "finish_reason": response_data.get("finish_reason"),
                "duration": response_data.get("duration")
            },
            tool_calls=response_data.get("tool_calls"),
            tokens_used=tokens_used
        )

        logger.debug(f"Updated conversation {conversation_id}: turn {turn_number}, assistant message added")

    def get_conversation_history(self, conversation_id: str) -> Optional[ConversationHistory]:
        """
        获取结构化对话历史

        Args:
            conversation_id: 对话ID

        Returns:
            ConversationHistory对象，如果不存在则返回None
        """
        return self.conversations.get(conversation_id)

    def list_conversations(
        self,
        capture_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        列出所有对话

        Args:
            capture_id: 可选的捕获会话ID，用于过滤

        Returns:
            对话列表
        """
        conversations = []

        for conv_id, conv in self.conversations.items():
            if capture_id:
                # 过滤：检查这个conversation是否属于指定的capture
                capture = self.captures.get(capture_id, {})
                if conv.agent_name != capture.get("agent_name"):
                    continue

            conversations.append({
                "conversation_id": conv.conversation_id,
                "agent_name": conv.agent_name,
                "total_turns": conv.total_turns,
                "message_count": len(conv.messages),
                "started_at": conv.started_at,
                "last_updated_at": conv.last_updated_at,
                "has_system_prompt": conv.system_prompt is not None
            })

        return conversations

    def export_conversation(self, conversation_id: str, output_path: str) -> None:
        """
        导出对话历史到JSON文件

        Args:
            conversation_id: 对话ID
            output_path: 输出文件路径
        """
        conv = self.conversations.get(conversation_id)
        if not conv:
            raise ValueError(f"Conversation {conversation_id} not found")

        # 导出为字典格式
        conv_data = conv.to_dict()

        # 写入文件
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(conv_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported conversation {conversation_id} to {output_path}")

    def get_conversation_summary(self, conversation_id: str) -> Dict[str, Any]:
        """
        获取对话摘要信息

        Args:
            conversation_id: 对话ID

        Returns:
            对话摘要字典
        """
        conv = self.conversations.get(conversation_id)
        if not conv:
            raise ValueError(f"Conversation {conversation_id} not found")

        return {
            "conversation_id": conv.conversation_id,
            "agent_name": conv.agent_name,
            "total_turns": conv.total_turns,
            "total_messages": len(conv.messages),
            "has_system_prompt": conv.system_prompt is not None,
            "system_prompt_preview": conv.system_prompt[:100] + "..." if conv.system_prompt and len(conv.system_prompt) > 100 else conv.system_prompt,
            "started_at": conv.started_at,
            "last_updated_at": conv.last_updated_at,
            "duration": conv.last_updated_at - conv.started_at,
            "total_tokens": conv.total_tokens,
            "turns": [
                {
                    "turn_number": turn.turn_number,
                    "user_preview": turn.user_message.content[:50] + "..." if len(turn.user_message.content) > 50 else turn.user_message.content,
                    "assistant_preview": (turn.assistant_message.content[:50] + "..." if turn.assistant_message and len(turn.assistant_message.content) > 50 else turn.assistant_message.content if turn.assistant_message else None),
                    "tokens": turn.tokens_used,
                    "duration": turn.duration,
                    "tool_calls_count": len(turn.tool_calls)
                }
                for turn in conv.turns
            ]
        }

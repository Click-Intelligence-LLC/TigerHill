"""
Python Observer - Google Generative AI SDK

为 Python 的 Google Generative AI SDK 提供 instrumentation。
支持多种LLM agent的系统prompt和对话历史追踪。
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Callable, Dict, Optional, List
import functools

from tigerhill.observer.conversation_models import SystemPromptExtractor

logger = logging.getLogger(__name__)


def wrap_generative_model(
    model_class: type,
    capture_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    capture_response: bool = True
):
    """
    包装 Google GenerativeModel 类

    Args:
        model_class: GenerativeModel 类
        capture_callback: 捕获回调函数，接收捕获的数据
        capture_response: 是否捕获响应

    Returns:
        包装后的模型类

    Example:
        >>> from google.generativeai import GenerativeModel
        >>> from tigerhill.observer import wrap_generative_model
        >>> from tigerhill.observer.capture import PromptCapture
        >>>
        >>> # 创建捕获器
        >>> capture = PromptCapture()
        >>> capture_id = capture.start_capture("my_agent")
        >>>
        >>> # 包装模型
        >>> WrappedModel = wrap_generative_model(
        ...     GenerativeModel,
        ...     capture_callback=lambda data: capture.capture_request(capture_id, data)
        ... )
        >>>
        >>> # 使用包装后的模型
        >>> model = WrappedModel('gemini-pro')
        >>> response = model.generate_content("Hello")
    """

    class WrappedGenerativeModel(model_class):
        """包装的 GenerativeModel"""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._tigerhill_callback = capture_callback
            self._tigerhill_capture_response = capture_response

            logger.info(f"Wrapped GenerativeModel: {self.model_name}")

        def generate_content(self, *args, **kwargs):
            """包装 generate_content 方法"""
            start_time = time.time()
            request_id = str(uuid.uuid4())

            # 提取所有prompt组件（包括system prompt）
            prompt_data = self._extract_prompt_with_system(args, kwargs)

            # 构建请求数据
            request_data = {
                "request_id": request_id,
                "model": self.model_name,
                "timestamp": start_time,

                # ✅ 新增：系统prompt
                "system_prompt": prompt_data.get("system_prompt"),

                # ✅ 新增：结构化的消息历史
                "messages": prompt_data.get("messages"),

                # 用户prompt（向后兼容）
                "prompt": prompt_data.get("user_prompt"),

                # 其他配置
                "generation_config": self._extract_generation_config(kwargs),
                "safety_settings": kwargs.get("safety_settings"),
                "tools": self._extract_tools(kwargs),
            }

            # 调用捕获回调
            if self._tigerhill_callback:
                try:
                    self._tigerhill_callback(request_data)
                except Exception as e:
                    logger.error(f"Capture callback failed: {e}")

            # 执行原始方法
            response = super().generate_content(*args, **kwargs)

            # 捕获响应
            if self._tigerhill_capture_response and self._tigerhill_callback:
                response_data = self._extract_response_data(response)
                response_data["request_id"] = request_id
                response_data["duration"] = time.time() - start_time
                try:
                    # 使用特殊的 response 标记
                    response_data["_is_response"] = True
                    self._tigerhill_callback(response_data)
                except Exception as e:
                    logger.error(f"Response capture failed: {e}")

            return response

        async def generate_content_async(self, *args, **kwargs):
            """包装异步 generate_content 方法"""
            start_time = time.time()
            request_id = str(uuid.uuid4())

            # 提取所有prompt组件（包括system prompt）
            prompt_data = self._extract_prompt_with_system(args, kwargs)

            # 构建请求数据
            request_data = {
                "request_id": request_id,
                "model": self.model_name,
                "timestamp": start_time,

                # ✅ 新增：系统prompt
                "system_prompt": prompt_data.get("system_prompt"),

                # ✅ 新增：结构化的消息历史
                "messages": prompt_data.get("messages"),

                # 用户prompt（向后兼容）
                "prompt": prompt_data.get("user_prompt"),

                # 其他配置
                "generation_config": self._extract_generation_config(kwargs),
                "safety_settings": kwargs.get("safety_settings"),
                "tools": self._extract_tools(kwargs),
            }

            # 调用捕获回调
            if self._tigerhill_callback:
                try:
                    self._tigerhill_callback(request_data)
                except Exception as e:
                    logger.error(f"Capture callback failed: {e}")

            # 执行原始方法
            response = await super().generate_content_async(*args, **kwargs)

            # 捕获响应
            if self._tigerhill_capture_response and self._tigerhill_callback:
                response_data = self._extract_response_data(response)
                response_data["request_id"] = request_id
                response_data["duration"] = time.time() - start_time
                try:
                    response_data["_is_response"] = True
                    self._tigerhill_callback(response_data)
                except Exception as e:
                    logger.error(f"Response capture failed: {e}")

            return response

        def _extract_prompt_with_system(self, args, kwargs) -> Dict[str, Any]:
            """
            提取完整的prompt组件，包括system prompt

            支持多种agent格式：
            - Gemini: system_instruction参数
            - OpenAI: messages数组中的system role
            - Anthropic: system参数
            - 其他通用格式

            Returns:
                {
                    "user_prompt": str,
                    "system_prompt": str | None,
                    "messages": List[Dict] | None
                }
            """
            result = {
                "user_prompt": "",
                "system_prompt": None,
                "messages": None
            }

            # 1. 提取系统prompt（使用通用提取器）
            result["system_prompt"] = SystemPromptExtractor.extract_from_kwargs(kwargs)

            # 2. 提取用户prompt和对话历史
            if args:
                content = args[0]
            else:
                content = kwargs.get("contents") or kwargs.get("content")

            # 处理不同格式的prompt
            if isinstance(content, str):
                # 简单字符串prompt
                result["user_prompt"] = content

            elif isinstance(content, list):
                # 多轮对话或消息数组
                formatted_messages = []

                for idx, c in enumerate(content):
                    formatted = self._format_content(c)
                    formatted_messages.append(formatted)

                    # 提取最后一条用户消息作为user_prompt
                    if isinstance(formatted, dict):
                        if formatted.get("role") == "user":
                            # 从parts中提取文本
                            parts = formatted.get("parts", [])
                            if parts:
                                if isinstance(parts[-1], str):
                                    result["user_prompt"] = parts[-1]
                                elif isinstance(parts[-1], dict) and "text" in parts[-1]:
                                    result["user_prompt"] = parts[-1]["text"]

                result["messages"] = formatted_messages

            else:
                result["user_prompt"] = str(content)

            # 3. 如果有OpenAI风格的messages参数，从中提取system prompt和用户消息
            if 'messages' in kwargs and isinstance(kwargs['messages'], list):
                messages = kwargs['messages']
                result["messages"] = messages

                # 提取system message（如果还没有从system_instruction提取）
                if not result["system_prompt"]:
                    result["system_prompt"] = SystemPromptExtractor.extract_from_messages(messages)

                # 提取最后一条用户消息
                for msg in reversed(messages):
                    if isinstance(msg, dict) and msg.get('role') == 'user':
                        result["user_prompt"] = msg.get('content', '')
                        break
                    elif hasattr(msg, 'role') and msg.role == 'user':
                        result["user_prompt"] = getattr(msg, 'content', '')
                        break

            return result

        def _extract_prompt(self, args, kwargs):
            """
            提取 prompt (旧方法，保留向后兼容)

            注意：这个方法已被 _extract_prompt_with_system 取代
            """
            if args:
                content = args[0]
            else:
                content = kwargs.get("contents") or kwargs.get("content")

            # 处理不同格式的 prompt
            if isinstance(content, str):
                return content
            elif isinstance(content, list):
                # 多轮对话
                return [self._format_content(c) for c in content]
            else:
                return str(content)

        def _format_content(self, content):
            """格式化 content 对象"""
            if isinstance(content, str):
                return {"role": "user", "parts": [content]}
            elif hasattr(content, "parts"):
                return {
                    "role": getattr(content, "role", "user"),
                    "parts": [str(p) for p in content.parts]
                }
            else:
                return str(content)

        def _extract_generation_config(self, kwargs):
            """提取生成配置"""
            config = kwargs.get("generation_config")
            if not config:
                return None

            if hasattr(config, "__dict__"):
                return {
                    k: v for k, v in config.__dict__.items()
                    if not k.startswith("_")
                }
            else:
                return config

        def _extract_tools(self, kwargs):
            """提取工具定义"""
            tools = kwargs.get("tools")
            if not tools:
                return None

            # 序列化工具定义
            try:
                if isinstance(tools, list):
                    return [self._format_tool(t) for t in tools]
                else:
                    return self._format_tool(tools)
            except Exception as e:
                logger.warning(f"Failed to extract tools: {e}")
                return None

        def _format_tool(self, tool):
            """格式化工具对象"""
            if hasattr(tool, "__dict__"):
                return {
                    k: v for k, v in tool.__dict__.items()
                    if not k.startswith("_")
                }
            else:
                return str(tool)

        def _extract_response_data(self, response):
            """提取响应数据"""
            try:
                data = {
                    "text": response.text if hasattr(response, "text") else str(response),
                    "finish_reason": None,
                    "usage": None,
                    "candidates": []
                }

                # 提取 finish_reason
                if hasattr(response, "candidates") and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, "finish_reason"):
                        data["finish_reason"] = str(candidate.finish_reason)

                    # 提取所有候选
                    data["candidates"] = [
                        {
                            "text": c.text if hasattr(c, "text") else str(c),
                            "finish_reason": str(c.finish_reason) if hasattr(c, "finish_reason") else None
                        }
                        for c in response.candidates
                    ]

                # 提取 usage
                if hasattr(response, "usage_metadata"):
                    usage = response.usage_metadata
                    data["usage"] = {
                        "prompt_tokens": getattr(usage, "prompt_token_count", 0),
                        "completion_tokens": getattr(usage, "candidates_token_count", 0),
                        "total_tokens": getattr(usage, "total_token_count", 0)
                    }

                # 提取工具调用（如果有）
                if hasattr(response, "candidates") and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                        tool_calls = []
                        for part in candidate.content.parts:
                            if hasattr(part, "function_call"):
                                fc = part.function_call
                                tool_calls.append({
                                    "name": fc.name,
                                    "arguments": dict(fc.args) if hasattr(fc, "args") else {}
                                })
                        if tool_calls:
                            data["tool_calls"] = tool_calls

                return data

            except Exception as e:
                logger.error(f"Failed to extract response data: {e}")
                return {"text": str(response)}

    return WrappedGenerativeModel


def create_observer_callback(capture: Any, capture_id: str):
    """
    创建观察回调函数

    Args:
        capture: PromptCapture 实例
        capture_id: 捕获会话 ID

    Returns:
        回调函数
    """
    def callback(data: Dict[str, Any]):
        # 区分请求和响应
        if data.get("_is_response"):
            # 移除标记
            data.pop("_is_response", None)

            # ✅ 新增：传递request_id以支持对话追踪
            request_id = data.get("request_id")
            capture.capture_response(capture_id, data, request_id=request_id)
        else:
            # ✅ 新增：支持对话ID和轮次追踪（可选）
            conversation_id = data.get("conversation_id")
            turn_number = data.get("turn_number")

            capture.capture_request(
                capture_id,
                data,
                conversation_id=conversation_id,
                turn_number=turn_number
            )

    return callback


# 便捷函数：自动创建捕获器和包装模型
def instrument_generative_ai(
    agent_name: str,
    storage_path: str = "./prompt_captures"
):
    """
    自动 instrument Google Generative AI

    Args:
        agent_name: Agent 名称
        storage_path: 捕获存储路径

    Returns:
        (capture, capture_id, wrapper_function)

    Example:
        >>> from google.generativeai import GenerativeModel
        >>> from tigerhill.observer import instrument_generative_ai
        >>>
        >>> # 自动 instrument
        >>> capture, capture_id, wrap_model = instrument_generative_ai("my_agent")
        >>>
        >>> # 包装模型
        >>> WrappedModel = wrap_model(GenerativeModel)
        >>> model = WrappedModel('gemini-pro')
        >>>
        >>> # 使用模型
        >>> response = model.generate_content("Hello")
        >>>
        >>> # 结束捕获
        >>> result = capture.end_capture(capture_id)
        >>> print(f"Captured {result['statistics']['total_requests']} requests")
    """
    from tigerhill.observer.capture import PromptCapture

    # 创建捕获器
    capture = PromptCapture(storage_path=storage_path)
    capture_id = capture.start_capture(agent_name)

    # 创建回调
    callback = create_observer_callback(capture, capture_id)

    # 创建包装函数
    def wrapper(model_class):
        return wrap_generative_model(model_class, capture_callback=callback)

    return capture, capture_id, wrapper

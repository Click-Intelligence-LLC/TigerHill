"""
Prompt component extraction from LLM requests with provider-specific adapters.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

try:
    import tiktoken
except Exception:  # pragma: no cover - optional dependency
    tiktoken = None


def _ensure_dict(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except Exception:
            return {}
    return {}


class GeminiAdapter:
    """Extract components from Gemini API format."""

    @staticmethod
    def extract_components(request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract PROMPT components only (exclude role=model responses).

        Responses are handled separately by response extractor.
        """
        # 🎯 Strategy: Check top-level first, then fallback to nested
        contents = None
        system_instruction = None
        tools = []

        # 1. Try top-level fields (actual Gemini CLI captures)
        if 'contents' in request and isinstance(request['contents'], list):
            contents = request['contents']

        if 'system_instruction' in request and isinstance(request['system_instruction'], dict):
            system_instruction = request['system_instruction']

        if 'tools' in request and isinstance(request['tools'], list):
            tools = request['tools']

        # 2. Fallback to nested raw_request structure
        if contents is None or system_instruction is None:
            body = request.get("raw_request") or request.get("body")
            if body:
                if isinstance(body, str):
                    body = _ensure_dict(body)

                # Extract from nested structure if not found at top level
                # Support both 2-level (raw_request.contents) and 3-level (raw_request.request.contents)
                if contents is None:
                    # Try 3-level nesting first (raw_request.request.contents)
                    if 'request' in body and isinstance(body['request'], dict):
                        contents = body['request'].get('contents', [])
                    # Fallback to 2-level (raw_request.contents)
                    if not contents:
                        contents = body.get('contents', [])

                if system_instruction is None:
                    # Try 3-level nesting first (raw_request.request.systemInstruction)
                    if 'request' in body and isinstance(body['request'], dict):
                        system_instruction = body['request'].get('systemInstruction')
                    # Fallback to 2-level (raw_request.systemInstruction)
                    if system_instruction is None:
                        system_instruction = body.get('systemInstruction')

                if not tools:
                    # Try 3-level nesting first (raw_request.request.tools)
                    if 'request' in body and isinstance(body['request'], dict):
                        tools = body['request'].get('tools', [])
                    # Fallback to 2-level (raw_request.tools)
                    if not tools:
                        tools = body.get('tools', [])

        components: List[Dict[str, Any]] = []

        # Extract system instruction
        if isinstance(system_instruction, dict):
            for part in system_instruction.get("parts", []):
                text = part.get("text")
                if text:
                    components.append(
                        {
                            "role": "system",
                            "content": text,
                            "source": "system_instruction",
                        }
                    )

        # Extract contents - role=user (prompts) and role=model (conversation history)
        # First, find the last user message index - this is the current input
        last_user_idx = -1
        for idx, content_item in enumerate(contents or []):
            if content_item.get("role") == "user":
                last_user_idx = idx

        # Collect conversation history (all messages except the last user message)
        history_items = []
        current_user_parts = []

        for idx, content_item in enumerate(contents or []):
            role = content_item.get("role", "user")
            is_current_input = (role == "user" and idx == last_user_idx)

            if is_current_input:
                # This is the current user input - extract separately
                for part in content_item.get("parts", []):
                    if "functionResponse" in part:
                        continue
                    if "text" in part:
                        current_user_parts.append(part["text"])
                    elif "functionCall" in part:
                        # Rare but possible: user provides function call structure
                        current_user_parts.append(f"[Function Call: {part['functionCall'].get('name', 'unknown')}]")
            else:
                # This is conversation history
                for part in content_item.get("parts", []):
                    if "functionResponse" in part:
                        continue
                    if "text" in part:
                        history_items.append({
                            "role": "assistant" if role == "model" else role,
                            "content": part["text"],
                            "type": "text"
                        })
                    elif "functionCall" in part:
                        history_items.append({
                            "role": "assistant" if role == "model" else role,
                            "content": part["functionCall"],
                            "type": "function_call"
                        })

        # Add merged conversation history as single component
        if history_items:
            components.append({
                "role": "system",  # History is system context
                "content_json": history_items,  # Store as structured JSON
                "source": "conversation_history",
                "_is_history": True
            })

        # Add current user input as separate component
        if current_user_parts:
            components.append({
                "role": "user",
                "content": "\n".join(current_user_parts),
                "source": "user_input",
            })

        # Extract tool definitions
        for tool in tools:
            components.append(
                {
                    "role": "system",
                    "content_json": tool,
                    "source": "tool_definition",
                    "_is_tool_def": True,
                }
            )

        return components


class AnthropicAdapter:
    """Extract components from Anthropic Messages API format."""

    @staticmethod
    def extract_components(request: Dict[str, Any]) -> List[Dict[str, Any]]:
        body = request.get("raw_request") or request.get("body") or request
        if isinstance(body, str):
            body = _ensure_dict(body)

        components: List[Dict[str, Any]] = []

        system_prompt = body.get("system")
        if isinstance(system_prompt, str):
            components.append(
                {"role": "system", "content": system_prompt, "source": "system"}
            )

        for message in body.get("messages", []):
            role = message.get("role", "user")
            content = message.get("content")
            if isinstance(content, list):
                for block in content:
                    block_type = block.get("type")
                    if block_type == "text":
                        components.append(
                            {
                                "role": role,
                                "content": block.get("text", ""),
                                "source": "messages",
                            }
                        )
                    elif block_type == "tool_use":
                        components.append(
                            {
                                "role": role,
                                "content_json": block,
                                "source": "tool_use",
                            }
                        )
            elif isinstance(content, str):
                components.append(
                    {"role": role, "content": content, "source": "messages"}
                )

        return components


class OpenAIAdapter:
    """Extract components from OpenAI-compatible Chat Completions format."""

    @staticmethod
    def extract_components(request: Dict[str, Any]) -> List[Dict[str, Any]]:
        body = request.get("raw_request") or request.get("body") or request
        if isinstance(body, str):
            body = _ensure_dict(body)

        components: List[Dict[str, Any]] = []

        for message in body.get("messages", []):
            role = message.get("role", "user")
            content = message.get("content")
            if isinstance(content, list):
                for part in content:
                    if part.get("type") == "text":
                        components.append(
                            {
                                "role": role,
                                "content": part.get("text", ""),
                                "source": "messages",
                            }
                        )
                    else:
                        components.append(
                            {
                                "role": role,
                                "content_json": part,
                                "source": "messages",
                            }
                        )
            elif isinstance(content, str):
                components.append(
                    {"role": role, "content": content, "source": "messages"}
                )

            if "tool_calls" in message:
                for call in message["tool_calls"]:
                    components.append(
                        {
                            "role": role,
                            "content_json": call,
                            "source": "tool_call",
                        }
                    )

        for fn in body.get("functions", []):
            components.append(
                {
                    "role": "system",
                    "content_json": fn,
                    "source": "function_definition",
                    "_is_tool_def": True,
                }
            )

        return components


class PromptComponentExtractor:
    """Extract and classify prompt components using provider adapters."""

    def __init__(self):
        self.adapters = {
            "gemini": GeminiAdapter(),
            "vertex": GeminiAdapter(),
            "anthropic": AnthropicAdapter(),
            "openai": OpenAIAdapter(),
            "openai_compatible": OpenAIAdapter(),
        }
        self._token_encoder = None

    def extract(
        self,
        request: Dict[str, Any],
        provider: str,
        protocol: str,
    ) -> List[Dict[str, Any]]:
        adapter = (
            self.adapters.get(provider)
            or self.adapters.get(protocol)
            or self.adapters.get("openai_compatible")
        )
        if not adapter:
            return []

        raw_components = adapter.extract_components(request)
        components: List[Dict[str, Any]] = []

        for idx, raw in enumerate(raw_components):
            component_type = self._classify_component(raw)

            # Build component metadata
            metadata = {}
            if raw.get("_is_history"):
                metadata["is_history"] = True

            components.append(
                {
                    "id": str(uuid.uuid4()),
                    "component_type": component_type,
                    "role": raw.get("role", "user"),
                    "content": raw.get("content"),
                    "content_json": raw.get("content_json"),
                    "order_index": idx,
                    "source": raw.get("source", "unknown"),
                    "token_count": self._estimate_tokens(raw),
                    "metadata": metadata,
                }
            )

        return components

    def _classify_component(self, raw: Dict[str, Any]) -> str:
        # Check source field first (explicit classification)
        source = raw.get("source", "")
        if source == "conversation_history":
            return "conversation_history"
        if source == "user_input":
            return "user"
        if source == "system_instruction":
            return "system"
        if source == "tool_definition":
            return "tool_definition"

        # Fallback to legacy logic
        if raw.get("_is_tool_def"):
            return "tool_definition"

        # Check if this is conversation history
        if raw.get("_is_history"):
            return "conversation_history"

        content = raw.get("content") or json.dumps(raw.get("content_json", {}))
        lowered = (content or "").lower()

        if self._looks_like_environment_desc(lowered):
            return "environment"
        if self._looks_like_context(lowered):
            return "context"
        if self._looks_like_example(lowered):
            return "example"

        role = raw.get("role", "").lower()
        if role in ("assistant", "model"):
            return "assistant"
        if role == "system":
            return "system"
        if role == "tool":
            return "tool_definition"
        return "user"

    @staticmethod
    def _looks_like_environment_desc(content: str) -> bool:
        if not content:
            return False
        keywords = ["environment", "runtime", "operating system", "dependencies"]
        return any(keyword in content for keyword in keywords)

    @staticmethod
    def _looks_like_context(content: str) -> bool:
        if not content:
            return False
        keywords = ["context:", "background", "reference", "knowledge base"]
        return any(keyword in content for keyword in keywords)

    @staticmethod
    def _looks_like_example(content: str) -> bool:
        if not content:
            return False
        return "example" in content or content.strip().startswith("input:")

    def _estimate_tokens(self, raw: Dict[str, Any]) -> Optional[int]:
        content = raw.get("content")
        if not content:
            return None

        if tiktoken:
            if self._token_encoder is None:
                self._token_encoder = tiktoken.get_encoding("cl100k_base")
            return len(self._token_encoder.encode(content))

        return max(1, len(content) // 4)

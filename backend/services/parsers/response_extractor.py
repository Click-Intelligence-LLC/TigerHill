"""
Response extraction from conversation history in LLM requests.

Gemini CLI captures include conversation history in each request's contents array.
Items with role=model contain AI responses (text and function calls).
Items with role=user containing functionResponse are tool execution results.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, Tuple


def _ensure_dict(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except Exception:
            return {}
    return {}


class GeminiResponseExtractor:
    """Extract responses from Gemini conversation history."""

    @staticmethod
    def extract_responses(request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract model responses from conversation history in contents array.

        Returns list of response dicts, each containing:
        - response_data: Basic response metadata
        - spans: List of response spans (text, tool_call, tool_result)
        """
        # Get contents array (same logic as component extractor)
        contents = None

        # 1. Try top-level first
        if 'contents' in request and isinstance(request['contents'], list):
            contents = request['contents']

        # 2. Fallback to nested
        if contents is None:
            body = request.get("raw_request") or request.get("body")
            if body:
                if isinstance(body, str):
                    body = _ensure_dict(body)

                if 'request' in body and isinstance(body['request'], dict):
                    contents = body['request'].get('contents', [])
                else:
                    contents = body.get('contents', [])

        if not contents:
            return []

        responses = []

        # Extract responses from contents
        for idx, content_item in enumerate(contents):
            role = content_item.get("role", "user")

            # Only process role=model (AI responses)
            if role != "model":
                continue

            # Build response data and spans
            response_data = {
                "conversation_index": idx,
                "role": role,
            }

            spans = []
            span_index = 0

            for part in content_item.get("parts", []):
                # Text span (AI's text response)
                if "text" in part:
                    spans.append({
                        "span_type": "text",
                        "content": part["text"],
                        "order_index": span_index,
                    })
                    span_index += 1

                # Tool call span (AI calling a tool)
                elif "functionCall" in part:
                    func_call = part["functionCall"]
                    spans.append({
                        "span_type": "tool_call",
                        "content_json": func_call,
                        "tool_name": func_call.get("name"),
                        "tool_input": func_call.get("args"),
                        "order_index": span_index,
                    })
                    span_index += 1

            # Only add if there are actual spans
            if spans:
                responses.append({
                    "response_data": response_data,
                    "spans": spans,
                })

        # Also extract tool results from role=user with functionResponse
        for idx, content_item in enumerate(contents):
            role = content_item.get("role", "user")

            if role != "user":
                continue

            for part in content_item.get("parts", []):
                if "functionResponse" in part:
                    func_response = part["functionResponse"]

                    # Create a pseudo-response for tool result
                    # (This represents the tool's output, which is part of the conversation flow)
                    spans = [{
                        "span_type": "tool_result",
                        "content_json": func_response,
                        "tool_name": func_response.get("name"),
                        "tool_output": func_response.get("response"),
                        "tool_call_id": func_response.get("id"),
                        "order_index": 0,
                    }]

                    responses.append({
                        "response_data": {
                            "conversation_index": idx,
                            "role": "tool",  # Mark as tool result
                            "is_tool_result": True,
                        },
                        "spans": spans,
                    })

        return responses


class ResponseExtractor:
    """Main response extractor with provider-specific adapters."""

    def __init__(self):
        self.adapters = {
            "gemini": GeminiResponseExtractor(),
            "vertex": GeminiResponseExtractor(),
            # Can add other providers later
        }

    def extract(
        self,
        request: Dict[str, Any],
        provider: str,
        protocol: str,
    ) -> List[Dict[str, Any]]:
        """
        Extract responses from request conversation history.

        Args:
            request: Request dict with contents/conversation history
            provider: Provider name
            protocol: Protocol name

        Returns:
            List of response dicts with response_data and spans
        """
        adapter = self.adapters.get(provider) or self.adapters.get(protocol)
        if not adapter:
            return []

        return adapter.extract_responses(request)

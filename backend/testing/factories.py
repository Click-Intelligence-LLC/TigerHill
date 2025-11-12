"""
Utilities for constructing realistic session payloads used by tests and tooling.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
import uuid
from typing import Any, Dict, List, Optional

ProviderName = str

PROVIDER_CONFIG: Dict[ProviderName, Dict[str, Any]] = {
    "gemini": {
        "model": "gemini-1.5-pro",
        "url": "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent",
    },
    "openai": {
        "model": "gpt-4o-mini",
        "url": "https://api.openai.com/v1/chat/completions",
    },
    "anthropic": {
        "model": "claude-3-sonnet-20240229",
        "url": "https://api.anthropic.com/v1/messages",
    },
}


def _now() -> datetime:
    return datetime.utcnow().replace(microsecond=0)


def _gemini_bodies(prompt: str) -> Dict[str, Any]:
    contents = [
        {"role": "system", "parts": [{"text": "You are TigerHill's debugging assistant."}]},
        {"role": "user", "parts": [{"text": prompt}]},
    ]
    raw_request = {
        "model": PROVIDER_CONFIG["gemini"]["model"],
        "contents": contents,
        "generationConfig": {"temperature": 0.25, "maxOutputTokens": 256, "stopSequences": ["END"]},
    }
    response = {
        "candidates": [
            {
                "finishReason": "STOP",
                "content": {
                    "role": "model",
                    "parts": [{"text": f"Gemini response for: {prompt}"}],
                },
            }
        ],
        "usageMetadata": {"promptTokenCount": 12, "candidatesTokenCount": 24, "totalTokenCount": 36},
    }
    return {"request": contents, "raw_request": raw_request, "response": response}


def _openai_bodies(prompt: str) -> Dict[str, Any]:
    messages = [
        {"role": "system", "content": "You are TigerHill assistant."},
        {"role": "user", "content": prompt},
    ]
    raw_request = {
        "model": PROVIDER_CONFIG["openai"]["model"],
        "temperature": 0.2,
        "messages": messages,
    }
    response = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": f"OpenAI response for: {prompt}"},
            }
        ],
        "usage": {"prompt_tokens": 11, "completion_tokens": 20, "total_tokens": 31},
    }
    return {"request": messages, "raw_request": raw_request, "response": response}


def _anthropic_bodies(prompt: str) -> Dict[str, Any]:
    messages = [
        {"role": "user", "content": [{"type": "text", "text": prompt}]},
    ]
    raw_request = {
        "model": PROVIDER_CONFIG["anthropic"]["model"],
        "temperature": 0.3,
        "max_tokens": 256,
        "messages": messages,
    }
    response = {
        "content": [{"type": "text", "text": f"Anthropic response for: {prompt}"}],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 15, "output_tokens": 18},
    }
    return {"request": messages, "raw_request": raw_request, "response": response}


BODY_BUILDERS = {
    "gemini": _gemini_bodies,
    "openai": _openai_bodies,
    "anthropic": _anthropic_bodies,
}


def _build_request(provider: ProviderName, prompt: str, timestamp: str, idx: int) -> Dict[str, Any]:
    builder = BODY_BUILDERS.get(provider)
    if not builder:
        raise ValueError(f"Unsupported provider {provider}")
    body = builder(prompt)
    request_id = f"{provider}-req-{idx}-{uuid.uuid4().hex[:6]}"
    return {
        "request_id": request_id,
        "timestamp": timestamp,
        "method": "POST",
        "url": PROVIDER_CONFIG[provider]["url"],
        "model": PROVIDER_CONFIG[provider]["model"],
        "headers": {"authorization": "Bearer test-token"},
        "raw_request": deepcopy(body["raw_request"]),
        "contents": deepcopy(body["request"]),
        "response": deepcopy(body["response"]),
        "response_timestamp": timestamp,
        "status_code": 200,
        "response_time_ms": 120 + idx * 5,
    }


def build_session_payload(
    session_id: Optional[str] = None,
    *,
    provider: ProviderName = "gemini",
    turns: int = 1,
    status: str = "success",
    prompts: Optional[List[str]] = None,
    start_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Create a Gemini CLI style session payload passed to DataImporter.
    """
    if provider not in PROVIDER_CONFIG:
        raise ValueError(f"Unknown provider {provider}")

    session_id = session_id or f"session-{uuid.uuid4().hex[:8]}"
    start_time = start_time or _now()
    prompts = prompts or [f"Prompt {i+1}" for i in range(turns)]

    payload: Dict[str, Any] = {
        "session_id": session_id,
        "agent_name": f"{provider}-agent",
        "start_time": start_time.isoformat(),
        "end_time": (start_time + timedelta(minutes=turns)).isoformat(),
        "status": status,
        "turns": [],
    }

    for idx in range(turns):
        prompt = prompts[idx % len(prompts)]
        turn_timestamp = (start_time + timedelta(seconds=idx * 10)).isoformat()
        request = _build_request(provider, prompt, turn_timestamp, idx)
        turn = {
            "turn_number": idx + 1,
            "timestamp": turn_timestamp,
            "requests": [request],
        }
        payload["turns"].append(turn)

    return payload


def build_mixed_session_set(count: int) -> List[Dict[str, Any]]:
    """
    Convenience helper that returns a list of session payloads with rotating providers.
    """
    providers = list(PROVIDER_CONFIG.keys())
    sessions = []
    for idx in range(count):
        provider = providers[idx % len(providers)]
        sessions.append(
            build_session_payload(
                session_id=f"session-{provider}-{idx}",
                provider=provider,
                turns=2,
                prompts=[
                    f"{provider} prompt #{idx}",
                    f"{provider} follow-up #{idx}",
                ],
            )
        )
    return sessions

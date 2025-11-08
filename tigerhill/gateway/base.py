from __future__ import annotations
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str
    content: str


class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]


class ModelResponse(BaseModel):
    text: str
    tool_calls: List[ToolCall] = Field(default_factory=list)


class LLMClient(ABC):
    @abstractmethod
    def chat(self, messages: List[Message], tools: Optional[List[Dict[str, Any]]] = None) -> ModelResponse:
        raise NotImplementedError

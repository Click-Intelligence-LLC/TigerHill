from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentOutput(BaseModel):
    text: str
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)


class Task(BaseModel):
    prompt: str
    setup: Optional[List[str]] = None
    assertions: List[Dict[str, Any]] = Field(default_factory=list)


class Environment(BaseModel):
    name: str
    agentbay_env_id: Optional[str] = None  # Reference to AgentBay environment ID
    agentbay_tool_set_id: Optional[str] = None # Reference to AgentBay tool set ID


class EvaluationResult(BaseModel):
    agent: str
    task: str
    environment: str
    assertion_results: List[Dict[str, Any]]
    metrics: Dict[str, Any] = Field(default_factory=dict)


class Agent(BaseModel):
    name: str

    def run(self, task: Task, env: Environment) -> AgentOutput:
        raise NotImplementedError

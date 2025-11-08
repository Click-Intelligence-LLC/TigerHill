"""
TigerHill Adapters - 跨语言 Agent 适配器

提供统一接口测试不同语言和协议的 Agent。
"""

from .multi_language import (
    AgentAdapter,
    HTTPAgentAdapter,
    CLIAgentAdapter,
    AgentBayAdapter,
    STDIOAgentAdapter,
    UniversalAgentTester
)

__all__ = [
    "AgentAdapter",
    "HTTPAgentAdapter",
    "CLIAgentAdapter",
    "AgentBayAdapter",
    "STDIOAgentAdapter",
    "UniversalAgentTester"
]

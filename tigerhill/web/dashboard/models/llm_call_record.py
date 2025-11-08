"""LLMCallRecord model for dashboard"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class LLMCallRecord:
    """单次LLM调用记录"""

    # 基本信息
    call_id: str                     # 调用ID
    trace_id: str                    # 所属追踪ID
    timestamp: datetime              # 调用时间
    sequence_number: int             # 在trace中的序号

    # LLM配置
    provider: str                    # 提供商: "openai", "anthropic", "google"
    model: str                       # 模型名称: "gpt-4", "claude-3-opus"

    # 请求数据
    prompt: str                      # 完整prompt
    system_prompt: Optional[str] = None     # 系统prompt（如果有）
    temperature: float = 0.7         # 温度参数
    max_tokens: int = 1000           # 最大token数
    request_params: Dict[str, Any] = None   # 其他请求参数

    # 响应数据
    response: str = ""               # 完整响应
    finish_reason: str = ""          # 结束原因: "stop", "length", "error"

    # Token统计
    prompt_tokens: int = 0           # prompt token数
    completion_tokens: int = 0       # 输出token数
    total_tokens: int = 0            # 总token数

    # 成本和性能
    cost_usd: float = 0.0            # 成本（美元）
    latency_seconds: float = 0.0     # 延迟（秒）

    # 工具调用（如果有）
    tool_calls: Optional[list] = None  # 工具调用记录

    def __post_init__(self):
        """初始化后处理"""
        if self.request_params is None:
            self.request_params = {}
        if self.tool_calls is None:
            self.tool_calls = []

    @property
    def tokens_per_second(self) -> float:
        """每秒生成token数"""
        return self.completion_tokens / self.latency_seconds if self.latency_seconds > 0 else 0

    @property
    def cost_per_1k_tokens(self) -> float:
        """每1k token成本"""
        return (self.cost_usd / self.total_tokens * 1000) if self.total_tokens > 0 else 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "call_id": self.call_id,
            "trace_id": self.trace_id,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            "sequence_number": self.sequence_number,
            "provider": self.provider,
            "model": self.model,
            "prompt": self.prompt,
            "system_prompt": self.system_prompt,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "request_params": self.request_params,
            "response": self.response,
            "finish_reason": self.finish_reason,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
            "latency_seconds": self.latency_seconds,
            "tool_calls": self.tool_calls
        }

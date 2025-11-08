"""TraceMetadata model for dashboard"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class TraceMetadata:
    """追踪元数据 - 用于列表展示和筛选"""

    # 基本信息
    trace_id: str                    # 追踪ID
    agent_name: str                  # Agent名称
    start_time: datetime             # 开始时间
    end_time: Optional[datetime]     # 结束时间
    duration_seconds: float          # 执行时长（秒）

    # 状态信息
    status: str                      # 状态: "running", "completed", "failed"
    total_events: int                # 事件总数

    # 统计信息（快速预览，无需加载完整数据）
    llm_calls_count: int             # LLM调用次数
    total_tokens: int                # 总token数
    total_cost_usd: float            # 总成本（美元）

    # 质量指标（来自 PromptAnalyzer）
    quality_score: Optional[float] = None   # 质量分数 0-100
    cost_efficiency: Optional[float] = None # 成本效率 0-100

    # 标签和分类
    tags: list = None                # 用户标签
    metadata: Dict[str, Any] = None  # 额外元数据

    def __post_init__(self):
        """初始化后处理"""
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}

    @property
    def avg_tokens_per_call(self) -> float:
        """平均每次调用的token数"""
        return self.total_tokens / self.llm_calls_count if self.llm_calls_count > 0 else 0

    @property
    def status_emoji(self) -> str:
        """状态表情符号"""
        return {
            "running": "🔄",
            "completed": "✅",
            "failed": "❌"
        }.get(self.status, "❓")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "trace_id": self.trace_id,
            "agent_name": self.agent_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "status": self.status,
            "total_events": self.total_events,
            "llm_calls_count": self.llm_calls_count,
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_usd,
            "quality_score": self.quality_score,
            "cost_efficiency": self.cost_efficiency,
            "tags": self.tags,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TraceMetadata":
        """从字典创建"""
        return cls(
            trace_id=data["trace_id"],
            agent_name=data["agent_name"],
            start_time=data["start_time"] if isinstance(data["start_time"], datetime) else datetime.fromisoformat(data["start_time"]),
            end_time=data["end_time"] if data["end_time"] is None or isinstance(data["end_time"], datetime) else datetime.fromisoformat(data["end_time"]),
            duration_seconds=data["duration_seconds"],
            status=data["status"],
            total_events=data["total_events"],
            llm_calls_count=data["llm_calls_count"],
            total_tokens=data["total_tokens"],
            total_cost_usd=data["total_cost_usd"],
            quality_score=data.get("quality_score"),
            cost_efficiency=data.get("cost_efficiency"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {})
        )

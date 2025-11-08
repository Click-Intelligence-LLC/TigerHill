"""AnalysisResult model for dashboard"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class AnalysisResult:
    """Prompt分析结果"""

    # 关联信息
    trace_id: str                    # 追踪ID
    analyzed_at: datetime            # 分析时间

    # 5大维度分数 (0-100)
    quality_score: float             # 质量分数
    cost_score: float                # 成本分数
    performance_score: float         # 性能分数
    security_score: float            # 安全分数
    compliance_score: float          # 合规分数

    # 总分
    overall_score: float             # 总分 (5个维度平均)

    # 详细指标 (22个子指标)
    metrics: Dict[str, float]        # 所有子指标

    # 问题和建议
    issues: list = None              # 发现的问题列表
    recommendations: list = None     # 优化建议

    # 对比数据（如果有）
    baseline_comparison: Optional[Dict[str, float]] = None  # 与基线对比

    def __post_init__(self):
        """初始化后处理"""
        if self.issues is None:
            self.issues = []
        if self.recommendations is None:
            self.recommendations = []

    @property
    def grade(self) -> str:
        """评级: A+, A, B, C, D, F"""
        score = self.overall_score
        if score >= 95: return "A+"
        if score >= 85: return "A"
        if score >= 75: return "B"
        if score >= 65: return "C"
        if score >= 55: return "D"
        return "F"

    @property
    def priority_issues(self) -> list:
        """高优先级问题"""
        return [i for i in self.issues if i.get("severity") in ["high", "critical"]]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "trace_id": self.trace_id,
            "analyzed_at": self.analyzed_at.isoformat() if isinstance(self.analyzed_at, datetime) else self.analyzed_at,
            "quality_score": self.quality_score,
            "cost_score": self.cost_score,
            "performance_score": self.performance_score,
            "security_score": self.security_score,
            "compliance_score": self.compliance_score,
            "overall_score": self.overall_score,
            "metrics": self.metrics,
            "issues": self.issues,
            "recommendations": self.recommendations,
            "baseline_comparison": self.baseline_comparison
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisResult":
        """从字典创建"""
        return cls(
            trace_id=data["trace_id"],
            analyzed_at=data["analyzed_at"] if isinstance(data["analyzed_at"], datetime) else datetime.fromisoformat(data["analyzed_at"]),
            quality_score=data["quality_score"],
            cost_score=data["cost_score"],
            performance_score=data["performance_score"],
            security_score=data["security_score"],
            compliance_score=data["compliance_score"],
            overall_score=data["overall_score"],
            metrics=data["metrics"],
            issues=data.get("issues", []),
            recommendations=data.get("recommendations", []),
            baseline_comparison=data.get("baseline_comparison")
        )

"""DashboardState model for dashboard"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


@dataclass
class DashboardState:
    """Streamlit Dashboard 全局状态"""

    # 数据源配置
    storage_path: str = "./test_traces"  # SQLite 数据库路径

    # 当前选中
    selected_trace_id: Optional[str] = None  # 当前选中的trace
    selected_call_id: Optional[str] = None   # 当前选中的LLM调用

    # 筛选条件
    filter_agent_name: Optional[str] = None  # 按agent名称筛选
    filter_status: list = field(default_factory=lambda: ["completed"])  # 按状态筛选
    filter_date_range: tuple = None          # 日期范围
    filter_min_cost: float = 0.0             # 最小成本
    filter_tags: list = field(default_factory=list)  # 标签筛选

    # 排序
    sort_by: str = "time"                    # 排序字段: "time", "cost", "tokens", "quality"
    sort_order: str = "desc"                 # 排序顺序: "asc", "desc"

    # 分页
    page_size: int = 20                      # 每页显示数量
    current_page: int = 1                    # 当前页码

    # 缓存数据
    cached_traces: list = field(default_factory=list)  # 缓存的trace列表
    cached_analysis: Dict[str, Any] = field(default_factory=dict)  # 缓存的分析结果

    # UI状态
    show_advanced_filters: bool = False      # 是否显示高级筛选
    active_tab: str = "overview"             # 当前激活标签页

    def __post_init__(self):
        """初始化后处理"""
        if self.filter_date_range is None:
            # 默认最近7天
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            self.filter_date_range = (start_date, end_date)

    def reset_filters(self):
        """重置筛选条件"""
        self.filter_agent_name = None
        self.filter_status = ["completed"]
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        self.filter_date_range = (start_date, end_date)
        self.filter_min_cost = 0.0
        self.filter_tags = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "storage_path": self.storage_path,
            "selected_trace_id": self.selected_trace_id,
            "selected_call_id": self.selected_call_id,
            "filter_agent_name": self.filter_agent_name,
            "filter_status": self.filter_status,
            "filter_date_range": self.filter_date_range,
            "filter_min_cost": self.filter_min_cost,
            "filter_tags": self.filter_tags,
            "sort_by": self.sort_by,
            "sort_order": self.sort_order,
            "page_size": self.page_size,
            "current_page": self.current_page,
            "show_advanced_filters": self.show_advanced_filters,
            "active_tab": self.active_tab
        }

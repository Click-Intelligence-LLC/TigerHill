"""Data processor for dashboard"""

from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd

from tigerhill.web.dashboard.models.trace_metadata import TraceMetadata
from tigerhill.web.dashboard.models.dashboard_state import DashboardState


def apply_filters(
    traces: List[TraceMetadata],
    state: DashboardState
) -> List[TraceMetadata]:
    """应用筛选条件

    Args:
        traces: TraceMetadata列表
        state: Dashboard状态

    Returns:
        筛选后的traces列表
    """
    filtered = traces

    # Agent名称筛选
    if state.filter_agent_name and state.filter_agent_name != "全部":
        filtered = [t for t in filtered if t.agent_name == state.filter_agent_name]

    # 状态筛选
    if state.filter_status:
        filtered = [t for t in filtered if t.status in state.filter_status]

    # 日期范围筛选
    if state.filter_date_range:
        start_date, end_date = state.filter_date_range

        # 确保是datetime对象
        if not isinstance(start_date, datetime):
            start_date = datetime.combine(start_date, datetime.min.time())
        if not isinstance(end_date, datetime):
            end_date = datetime.combine(end_date, datetime.max.time())

        filtered = [
            t for t in filtered
            if start_date <= t.start_time <= end_date
        ]

    # 成本筛选
    if state.filter_min_cost > 0:
        filtered = [t for t in filtered if t.total_cost_usd >= state.filter_min_cost]

    # 标签筛选
    if state.filter_tags:
        filtered = [
            t for t in filtered
            if any(tag in t.tags for tag in state.filter_tags)
        ]

    return filtered


def sort_traces(
    traces: List[TraceMetadata],
    sort_by: str,
    order: str = "desc"
) -> List[TraceMetadata]:
    """排序traces

    Args:
        traces: TraceMetadata列表
        sort_by: 排序字段
        order: 排序顺序 ("asc" 或 "desc")

    Returns:
        排序后的traces列表
    """
    key_map = {
        "time": lambda t: t.start_time,
        "cost": lambda t: t.total_cost_usd,
        "tokens": lambda t: t.total_tokens,
        "quality": lambda t: t.quality_score or 0
    }

    key_func = key_map.get(sort_by, key_map["time"])
    reverse = (order == "desc")

    return sorted(traces, key=key_func, reverse=reverse)


def calculate_metrics(traces: List[TraceMetadata]) -> Dict[str, Any]:
    """计算指标统计

    Args:
        traces: TraceMetadata列表

    Returns:
        指标统计字典
    """
    if not traces:
        return {
            "total_traces": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "avg_quality": 0.0,
            "traces_delta": 0,
            "tokens_delta": 0,
            "cost_delta": 0,
            "quality_delta": 0
        }

    # 当前周期统计
    current_total = len(traces)
    current_tokens = sum(t.total_tokens for t in traces)
    current_cost = sum(t.total_cost_usd for t in traces)

    # 计算平均质量分
    traces_with_quality = [t for t in traces if t.quality_score is not None]
    current_quality = (
        sum(t.quality_score for t in traces_with_quality) / len(traces_with_quality)
        if traces_with_quality else 0.0
    )

    # 上一周期统计（用于计算delta）
    # 简化版：这里假设没有历史数据对比
    prev_stats = {
        "total": current_total,
        "tokens": current_tokens,
        "cost": current_cost,
        "quality": current_quality
    }

    return {
        "total_traces": current_total,
        "total_tokens": current_tokens,
        "total_cost": current_cost,
        "avg_quality": current_quality,
        "traces_delta": calculate_delta(current_total, prev_stats["total"]),
        "tokens_delta": calculate_delta(current_tokens, prev_stats["tokens"]),
        "cost_delta": calculate_delta(current_cost, prev_stats["cost"]),
        "quality_delta": calculate_delta(current_quality, prev_stats["quality"])
    }


def calculate_delta(current: float, previous: float) -> float:
    """计算变化百分比

    Args:
        current: 当前值
        previous: 之前值

    Returns:
        变化百分比
    """
    if previous == 0:
        return 0.0
    return ((current - previous) / previous) * 100


def traces_to_dataframe(traces: List[TraceMetadata]) -> pd.DataFrame:
    """将trace列表转换为DataFrame

    Args:
        traces: TraceMetadata列表

    Returns:
        Pandas DataFrame
    """
    data = []
    for t in traces:
        data.append({
            "status": t.status_emoji,
            "agent_name": t.agent_name,
            "start_time": t.start_time,
            "duration": t.duration_seconds,
            "llm_calls": t.llm_calls_count,
            "total_tokens": t.total_tokens,
            "cost": t.total_cost_usd,
            "quality": t.quality_score if t.quality_score else 0
        })
    return pd.DataFrame(data)


def categorize_tokens(traces: List[TraceMetadata]) -> Dict[str, int]:
    """将traces按token范围分类

    Args:
        traces: TraceMetadata列表

    Returns:
        token范围分类统计
    """
    ranges = {
        "0-1k": 0,
        "1k-5k": 0,
        "5k-10k": 0,
        "10k-50k": 0,
        "50k+": 0
    }

    for trace in traces:
        tokens = trace.total_tokens
        if tokens < 1000:
            ranges["0-1k"] += 1
        elif tokens < 5000:
            ranges["1k-5k"] += 1
        elif tokens < 10000:
            ranges["5k-10k"] += 1
        elif tokens < 50000:
            ranges["10k-50k"] += 1
        else:
            ranges["50k+"] += 1

    return ranges


def prepare_time_series_data(
    traces: List[TraceMetadata],
    value_field: str
) -> pd.DataFrame:
    """准备时间序列数据

    Args:
        traces: TraceMetadata列表
        value_field: 值字段名

    Returns:
        时间序列DataFrame
    """
    data = []
    for trace in traces:
        data.append({
            "date": trace.start_time.date(),
            "value": getattr(trace, value_field, 0)
        })

    df = pd.DataFrame(data)
    if not df.empty:
        # 按日期分组求和
        df = df.groupby("date").sum().reset_index()
        df = df.sort_values("date")

    return df


def prepare_heatmap_data(traces: List[TraceMetadata]) -> Dict[str, Any]:
    """准备热力图数据

    Args:
        traces: TraceMetadata列表

    Returns:
        热力图数据字典
    """
    # 按agent和日期分组
    data_dict = {}
    agents = set()
    dates = set()

    for trace in traces:
        agent = trace.agent_name
        date = trace.start_time.date()
        quality = trace.quality_score or 0

        agents.add(agent)
        dates.add(date)

        key = (agent, date)
        if key not in data_dict:
            data_dict[key] = []
        data_dict[key].append(quality)

    # 转换为矩阵
    agents = sorted(list(agents))
    dates = sorted(list(dates))

    values = []
    for agent in agents:
        row = []
        for date in dates:
            key = (agent, date)
            if key in data_dict:
                # 取平均值
                row.append(sum(data_dict[key]) / len(data_dict[key]))
            else:
                row.append(0)
        values.append(row)

    return {
        "agents": agents,
        "dates": [d.isoformat() for d in dates],
        "values": values
    }

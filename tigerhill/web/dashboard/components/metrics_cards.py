"""Metrics cards component for dashboard"""

import streamlit as st
from typing import List

from tigerhill.web.dashboard.models.trace_metadata import TraceMetadata
from tigerhill.web.dashboard.data.processor import calculate_metrics


def render(traces: List[TraceMetadata]):
    """渲染指标卡片

    Args:
        traces: 筛选后的TraceMetadata列表
    """
    # 计算指标
    metrics = calculate_metrics(traces)

    # 渲染4个指标卡片
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="📊 总测试数",
            value=metrics["total_traces"],
            delta=f"{metrics['traces_delta']:+.1f}%" if metrics['traces_delta'] != 0 else None,
            help="已完成的测试追踪总数"
        )

    with col2:
        st.metric(
            label="🎯 总 Token 数",
            value=f"{metrics['total_tokens']:,}",
            delta=f"{metrics['tokens_delta']:+.1f}%" if metrics['tokens_delta'] != 0 else None,
            help="所有测试消耗的 token 总数"
        )

    with col3:
        st.metric(
            label="💰 总成本",
            value=f"${metrics['total_cost']:.4f}",
            delta=f"{metrics['cost_delta']:+.1f}%" if metrics['cost_delta'] != 0 else None,
            delta_color="inverse",  # 成本降低是好事
            help="所有测试的总成本（美元）"
        )

    with col4:
        st.metric(
            label="⭐ 平均质量分",
            value=f"{metrics['avg_quality']:.1f}",
            delta=f"{metrics['quality_delta']:+.1f}%" if metrics['quality_delta'] != 0 else None,
            help="所有测试的平均质量分数"
        )

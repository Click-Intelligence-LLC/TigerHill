"""Charts component for dashboard"""

import streamlit as st
from typing import List

from tigerhill.web.dashboard.models.trace_metadata import TraceMetadata
from tigerhill.web.dashboard.data.processor import categorize_tokens, prepare_time_series_data, prepare_heatmap_data


def render_token_distribution(traces: List[TraceMetadata]):
    """Token分布图

    Args:
        traces: TraceMetadata列表
    """
    st.subheader("📊 Token 分布")

    if not traces:
        st.info("没有数据")
        return

    # 数据准备
    token_ranges = categorize_tokens(traces)

    try:
        import plotly.express as px

        fig = px.bar(
            x=list(token_ranges.keys()),
            y=list(token_ranges.values()),
            labels={'x': 'Token范围', 'y': '测试数量'},
            color=list(token_ranges.values()),
            color_continuous_scale='Blues'
        )

        fig.update_layout(
            showlegend=False,
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    except ImportError:
        st.warning("⚠️ 需要安装 plotly: pip install plotly")
        # 备选方案：使用streamlit原生bar_chart
        st.bar_chart(token_ranges)


def render_cost_trend(traces: List[TraceMetadata]):
    """成本趋势图

    Args:
        traces: TraceMetadata列表
    """
    st.subheader("💰 成本趋势")

    if not traces:
        st.info("没有数据")
        return

    # 按时间分组
    df = prepare_time_series_data(traces, 'total_cost_usd')

    if df.empty:
        st.info("没有足够的数据")
        return

    try:
        import plotly.express as px

        fig = px.line(
            df,
            x='date',
            y='value',
            labels={'date': '日期', 'value': '成本 ($)'},
            markers=True
        )

        fig.update_layout(height=400)

        st.plotly_chart(fig, use_container_width=True)

    except ImportError:
        st.warning("⚠️ 需要安装 plotly: pip install plotly")
        # 备选方案：使用streamlit原生line_chart
        df_chart = df.set_index('date')
        st.line_chart(df_chart)


def render_quality_heatmap(traces: List[TraceMetadata]):
    """质量热力图

    Args:
        traces: TraceMetadata列表
    """
    st.subheader("🔥 质量热力图")

    if not traces:
        st.info("没有数据")
        return

    # 过滤有质量分数的traces
    traces_with_quality = [t for t in traces if t.quality_score is not None]

    if not traces_with_quality:
        st.info("没有质量分数数据")
        return

    # 按agent和时间聚合
    heatmap_data = prepare_heatmap_data(traces_with_quality)

    if not heatmap_data['agents'] or not heatmap_data['dates']:
        st.info("没有足够的数据生成热力图")
        return

    try:
        import plotly.graph_objects as go

        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data['values'],
            x=heatmap_data['dates'],
            y=heatmap_data['agents'],
            colorscale='RdYlGn',
            zmin=0,
            zmax=100
        ))

        fig.update_layout(
            xaxis_title='日期',
            yaxis_title='Agent',
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    except ImportError:
        st.warning("⚠️ 需要安装 plotly: pip install plotly")
        st.info("热力图需要 plotly 库支持")


def render_tokens_vs_cost(traces: List[TraceMetadata]):
    """Token vs 成本散点图

    Args:
        traces: TraceMetadata列表
    """
    st.subheader("🎯 Token数 vs 成本")

    if not traces:
        st.info("没有数据")
        return

    # 准备数据
    data = {
        'tokens': [t.total_tokens for t in traces],
        'cost': [t.total_cost_usd for t in traces],
        'agent': [t.agent_name for t in traces]
    }

    try:
        import plotly.express as px
        import pandas as pd

        df = pd.DataFrame(data)

        fig = px.scatter(
            df,
            x='tokens',
            y='cost',
            color='agent',
            labels={'tokens': 'Token数', 'cost': '成本 ($)', 'agent': 'Agent'},
            hover_data=['agent']
        )

        fig.update_layout(height=400)

        st.plotly_chart(fig, use_container_width=True)

    except ImportError:
        st.warning("⚠️ 需要安装 plotly: pip install plotly")
        st.info("散点图需要 plotly 库支持")


def render_llm_calls_distribution(traces: List[TraceMetadata]):
    """LLM调用次数分布

    Args:
        traces: TraceMetadata列表
    """
    st.subheader("📞 LLM 调用次数分布")

    if not traces:
        st.info("没有数据")
        return

    # 统计调用次数分布
    call_counts = {}
    for trace in traces:
        count = trace.llm_calls_count
        if count not in call_counts:
            call_counts[count] = 0
        call_counts[count] += 1

    # 排序
    sorted_counts = dict(sorted(call_counts.items()))

    try:
        import plotly.express as px

        fig = px.bar(
            x=list(sorted_counts.keys()),
            y=list(sorted_counts.values()),
            labels={'x': 'LLM调用次数', 'y': '测试数量'}
        )

        fig.update_layout(height=400)

        st.plotly_chart(fig, use_container_width=True)

    except ImportError:
        st.warning("⚠️ 需要安装 plotly: pip install plotly")
        st.bar_chart(sorted_counts)

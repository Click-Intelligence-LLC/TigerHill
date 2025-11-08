"""Sidebar component for dashboard"""

import streamlit as st
from datetime import datetime, timedelta
from typing import List
from pathlib import Path

from tigerhill.web.dashboard.models.trace_metadata import TraceMetadata


def render(traces: List[TraceMetadata]):
    """渲染侧边栏

    Args:
        traces: TraceMetadata列表
    """
    st.sidebar.title("🐯 TigerHill")
    st.sidebar.caption("AI Agent Testing Platform")

    # 数据源选择
    render_data_source_selector()

    st.sidebar.divider()

    # 筛选器
    render_filters(traces)

    st.sidebar.divider()

    # 排序选项
    render_sort_options()

    st.sidebar.divider()

    # 刷新按钮
    render_refresh_control()


def render_data_source_selector():
    """SQLite 数据源选择器"""
    st.sidebar.subheader("📁 数据源（SQLite）")

    state = st.session_state.dashboard_state

    # 文本输入：允许直接指定数据库路径
    db_input = st.sidebar.text_input(
        "数据库路径",
        value=state.storage_path,
        help="输入或粘贴 .db 文件路径，例如 ./swarm.db",
        key="db_path_input"
    ).strip()

    if db_input and db_input != state.storage_path:
        state.storage_path = db_input
        # 不设置data_refresh_needed，让load_data()通过路径变化自动检测
        st.rerun()

    st.sidebar.caption(f"当前: {Path(state.storage_path).name if state.storage_path else 'N/A'}")

    # 快速选择：展示当前目录下的所有 .db 文件
    db_files = sorted(Path(".").glob("*.db"))
    if db_files:
        st.sidebar.caption("快速选择：")
        for db_file in db_files:
            label = str(db_file.name)  # 只显示文件名
            if st.sidebar.button(label, key=f"quick_db_{label}"):
                resolved = str(db_file.resolve())
                if resolved != state.storage_path:
                    state.storage_path = resolved
                    st.rerun()


def render_filters(traces: List[TraceMetadata]):
    """渲染筛选器

    Args:
        traces: 用于获取可用选项
    """
    st.sidebar.subheader("🔍 筛选")

    state = st.session_state.dashboard_state

    # Agent名称筛选
    agent_names = sorted(list(set(t.agent_name for t in traces))) if traces else []
    selected_agent = st.sidebar.selectbox(
        "Agent",
        options=["全部"] + agent_names,
        index=0 if state.filter_agent_name is None else (
            agent_names.index(state.filter_agent_name) + 1
            if state.filter_agent_name in agent_names else 0
        ),
        key="agent_filter"
    )
    state.filter_agent_name = None if selected_agent == "全部" else selected_agent

    # 状态筛选
    status_options = ["completed", "running", "failed"]
    selected_statuses = st.sidebar.multiselect(
        "状态",
        options=status_options,
        default=state.filter_status,
        key="status_filter"
    )
    state.filter_status = selected_statuses

    # 日期范围
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input(
            "开始日期",
            value=state.filter_date_range[0] if state.filter_date_range else datetime.now() - timedelta(days=7),
            key="start_date_filter"
        )
    with col2:
        end_date = st.date_input(
            "结束日期",
            value=state.filter_date_range[1] if state.filter_date_range else datetime.now(),
            key="end_date_filter"
        )

    # 转换为datetime
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    state.filter_date_range = (start_datetime, end_datetime)

    # 高级筛选（可折叠）
    with st.sidebar.expander("🔧 高级筛选", expanded=state.show_advanced_filters):
        state.filter_min_cost = st.slider(
            "最小成本 (USD)",
            min_value=0.0,
            max_value=10.0,
            value=state.filter_min_cost,
            step=0.1,
            key="min_cost_filter"
        )

        # 获取所有标签
        all_tags = sorted(list(set(
            tag for trace in traces for tag in trace.tags
        ))) if traces else []

        state.filter_tags = st.multiselect(
            "标签",
            options=all_tags,
            default=state.filter_tags,
            key="tags_filter"
        )


def render_sort_options():
    """排序选项"""
    st.sidebar.subheader("⬆️ 排序")

    state = st.session_state.dashboard_state

    sort_options = [
        ("time", "时间"),
        ("cost", "成本"),
        ("tokens", "Token数"),
        ("quality", "质量分数")
    ]

    # 找到当前选项的索引
    current_index = 0
    for i, (key, _) in enumerate(sort_options):
        if key == state.sort_by:
            current_index = i
            break

    selected_sort = st.sidebar.selectbox(
        "排序字段",
        options=sort_options,
        index=current_index,
        format_func=lambda x: x[1],
        key="sort_by_select"
    )
    state.sort_by = selected_sort[0]

    order_options = [("desc", "降序 ↓"), ("asc", "升序 ↑")]
    selected_order = st.sidebar.selectbox(
        "排序顺序",
        options=order_options,
        index=0 if state.sort_order == "desc" else 1,
        format_func=lambda x: x[1],
        key="sort_order_select"
    )
    state.sort_order = selected_order[0]


def render_refresh_control():
    """刷新控制"""
    col1, col2 = st.sidebar.columns(2)

    with col1:
        if st.button("🔄 刷新", use_container_width=True, key="refresh_button"):
            # 清除缓存
            st.cache_data.clear()
            st.session_state.data_refresh_needed = True
            st.rerun()

    with col2:
        auto_refresh = st.checkbox("自动刷新", value=False, key="auto_refresh_checkbox")

    if auto_refresh:
        st.sidebar.caption("⏱️ 每30秒自动刷新")
        import time
        time.sleep(30)
        st.rerun()

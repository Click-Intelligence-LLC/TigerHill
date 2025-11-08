"""Trace list component for dashboard"""

import streamlit as st
from typing import List
from pathlib import Path

from tigerhill.web.dashboard.models.trace_metadata import TraceMetadata
from tigerhill.web.dashboard.data.processor import traces_to_dataframe
from tigerhill.web.dashboard.data.loader import DataLoader


def render(traces: List[TraceMetadata]):
    """渲染trace列表

    Args:
        traces: TraceMetadata列表
    """
    if not traces:
        st.info("📭 没有找到符合条件的测试记录")
        return

    state = st.session_state.dashboard_state

    # 分页控制
    total_pages = (len(traces) - 1) // state.page_size + 1 if traces else 1

    col1, col2, col3 = st.columns([2, 3, 2])
    with col1:
        st.caption(f"共 {len(traces)} 条记录")
    with col2:
        # 页码选择
        page_options = list(range(1, total_pages + 1))
        current_index = state.current_page - 1 if state.current_page <= total_pages else 0

        new_page = st.selectbox(
            "页码",
            options=page_options,
            index=current_index,
            format_func=lambda x: f"第 {x}/{total_pages} 页",
            label_visibility="collapsed",
            key="page_selector"
        )
        state.current_page = new_page

    with col3:
        # 每页显示数量
        page_size_options = [10, 20, 50, 100]
        current_size_index = page_size_options.index(state.page_size) if state.page_size in page_size_options else 1

        new_page_size = st.selectbox(
            "每页显示",
            options=page_size_options,
            index=current_size_index,
            format_func=lambda x: f"{x} 条/页",
            label_visibility="collapsed",
            key="page_size_selector"
        )

        # 如果页面大小改变，重置到第一页并触发刷新
        if new_page_size != state.page_size:
            state.page_size = new_page_size
            state.current_page = 1
            st.rerun()

    # 分页数据
    start_idx = (state.current_page - 1) * state.page_size
    end_idx = start_idx + state.page_size
    page_traces = traces[start_idx:end_idx]

    # 转换为DataFrame展示
    df = traces_to_dataframe(page_traces)

    if df.empty:
        st.info("📭 当前页没有数据")
        return

    # 使用dataframe展示，添加固定高度确保滚动条显示
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=400,  # 固定高度400像素，超出时自动显示滚动条
        column_config={
            "status": st.column_config.TextColumn(
                "状态",
                width="small"
            ),
            "agent_name": st.column_config.TextColumn(
                "Agent",
                width="medium"
            ),
            "start_time": st.column_config.DatetimeColumn(
                "开始时间",
                format="YYYY-MM-DD HH:mm:ss",
                width="medium"
            ),
            "duration": st.column_config.NumberColumn(
                "时长(秒)",
                format="%.2f",
                width="small"
            ),
            "llm_calls": st.column_config.NumberColumn(
                "LLM调用",
                width="small"
            ),
            "total_tokens": st.column_config.NumberColumn(
                "Token数",
                format="%d",
                width="small"
            ),
            "cost": st.column_config.NumberColumn(
                "成本($)",
                format="%.4f",
                width="small"
            ),
            "quality": st.column_config.ProgressColumn(
                "质量分",
                min_value=0,
                max_value=100,
                format="%.1f",
                width="small"
            )
        }
    )

    # 提供选择trace的功能 - 在列表下方显示详情
    st.divider()
    st.subheader("📝 选择测试记录查看详情")

    # 创建选择框
    trace_options = [
        f"{t.trace_id[:8]} - {t.agent_name} - {t.start_time.strftime('%Y-%m-%d %H:%M')}"
        for t in page_traces
    ]

    if trace_options:
        selected_option = st.selectbox(
            "选择一个测试记录",
            options=["请选择..."] + trace_options,
            key="trace_selector"
        )

        if selected_option != "请选择...":
            # 提取trace_id
            selected_idx = trace_options.index(selected_option)
            selected_trace = page_traces[selected_idx]
            state.selected_trace_id = selected_trace.trace_id

            # 直接在下方显示详情
            st.success(f"✅ 已选择: {selected_option}")

            render_trace_detail(selected_trace)


def render_trace_detail(trace_metadata: TraceMetadata):
    """渲染trace详情

    Args:
        trace_metadata: TraceMetadata对象
    """
    st.divider()
    st.subheader("🔍 Trace 详情")

    # 加载完整的trace数据
    state = st.session_state.dashboard_state
    raw_path = (state.storage_path or "").strip() or "./tigerhill.db"
    db_path = Path(raw_path).expanduser()

    if not db_path.exists():
        st.error(f"❌ 数据库不存在: {db_path}")
        return

    db_path = db_path.resolve()
    state.storage_path = str(db_path)

    loader = DataLoader(
        storage_path=str(db_path),
        use_database=True,
        db_path=str(db_path),
    )

    try:
        trace_obj = loader.load_trace_detail(trace_metadata.trace_id)

        if not trace_obj:
            st.error("❌ 无法加载trace详情")
            return

        # 如果是Trace对象，转换为字典
        if hasattr(trace_obj, 'to_dict'):
            trace_detail = trace_obj.to_dict()
        else:
            trace_detail = trace_obj

        # 显示基本信息
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Trace ID", trace_detail.get("trace_id", "N/A")[:20] + "...")
            st.metric("Agent", trace_detail.get("agent_name", "N/A"))

        with col2:
            st.metric("状态", trace_metadata.status_emoji + " " + trace_metadata.status)
            st.metric("事件数", len(trace_detail.get("events", [])))

        with col3:
            st.metric("开始时间", trace_metadata.start_time.strftime("%Y-%m-%d %H:%M:%S"))
            if trace_metadata.end_time:
                st.metric("结束时间", trace_metadata.end_time.strftime("%Y-%m-%d %H:%M:%S"))

        source_path = trace_detail.get("metadata", {}).get("source_path")
        if source_path:
            st.caption(f"数据来源: {source_path}")

        st.divider()

        # 显示事件列表
        st.subheader("📋 事件列表")

        events = trace_detail.get("events", [])

        if events:
            # 限制显示数量
            max_display = 20
            for i, event in enumerate(events[:max_display]):
                event_type = event.get("type", "unknown")
                timestamp = event.get("timestamp", "N/A")

                with st.expander(f"#{i+1} - {event_type} - {timestamp}", expanded=False):
                    st.json(event)

            if len(events) > max_display:
                st.info(f"显示了前{max_display}个事件，总共 {len(events)} 个事件")
        else:
            st.info("暂无事件数据")

    except Exception as e:
        st.error(f"❌ 加载详情失败: {str(e)}")
        import traceback
        with st.expander("查看错误详情"):
            st.code(traceback.format_exc())

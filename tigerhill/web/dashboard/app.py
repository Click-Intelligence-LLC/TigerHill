"""Streamlit Dashboard for TigerHill

Usage:
    streamlit run tigerhill/web/dashboard/app.py
"""

import streamlit as st
from pathlib import Path

# 组件导入 - 使用绝对导入
from tigerhill.web.dashboard.components import sidebar, metrics_cards, trace_list, charts
from tigerhill.web.dashboard.data.loader import DataLoader
from tigerhill.web.dashboard.data.processor import apply_filters, sort_traces
from tigerhill.web.dashboard.models.dashboard_state import DashboardState


def main():
    """主应用入口"""
    # 1. 页面配置
    st.set_page_config(
        page_title="🐯 TigerHill Dashboard",
        page_icon="🐯",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 2. 初始化状态
    initialize_state()

    # 3. 加载数据
    load_data()

    # 4. 获取筛选和排序后的数据
    filtered_traces = get_filtered_and_sorted_traces()

    # 5. 渲染 Sidebar
    sidebar.render(st.session_state.all_traces)

    # 6. 渲染 Main Content
    render_main_content(filtered_traces)


def initialize_state():
    """初始化 session state"""
    if "dashboard_state" not in st.session_state:
        st.session_state.dashboard_state = DashboardState()

    if "all_traces" not in st.session_state:
        st.session_state.all_traces = []

    if "data_refresh_needed" not in st.session_state:
        st.session_state.data_refresh_needed = True

    if "last_loaded_db_path" not in st.session_state:
        st.session_state.last_loaded_db_path = None


def load_data():
    """加载和缓存数据"""
    state = st.session_state.dashboard_state

    # 获取当前路径
    raw_path = (state.storage_path or "").strip() or "./tigerhill.db"
    db_path = Path(raw_path).expanduser()

    if not db_path.exists():
        db_path_str = str(db_path)
    else:
        db_path_str = str(db_path.resolve())

    # 检测路径是否改变
    path_changed = (st.session_state.last_loaded_db_path != db_path_str)

    # 如果需要刷新、路径变化、或没有数据
    if st.session_state.data_refresh_needed or path_changed or not st.session_state.all_traces:
        try:
            if not db_path.exists():
                st.warning(f"⚠️ 数据库不存在: {db_path}")
                st.info("💡 提示: 使用迁移脚本生成 .db 文件或更新路径")
                st.session_state.all_traces = []
                st.session_state.data_refresh_needed = False
                st.session_state.last_loaded_db_path = db_path_str
                return

            db_path = db_path.resolve()
            db_path_str = str(db_path)
            state.storage_path = db_path_str

            # 显示加载提示
            if path_changed:
                st.info(f"🔄 正在从 {Path(db_path_str).name} 加载数据...")

                # 关键修复：清除DatabaseManager单例，强制重新连接新数据库
                from tigerhill.storage.database import DatabaseManager
                DatabaseManager._instance = None
                if hasattr(DatabaseManager, '_initialized'):
                    DatabaseManager._initialized = False

            loader = DataLoader(
                storage_path=db_path_str,
                use_database=True,
                db_path=db_path_str,
            )
            st.session_state.all_traces = loader.load_traces(limit=1000)
            st.session_state.data_refresh_needed = False
            st.session_state.last_loaded_db_path = db_path_str

            if not st.session_state.all_traces:
                st.warning(f"⚠️ 数据库中未找到trace记录: {state.storage_path}")
                st.info("💡 提示: 确认迁移是否成功或数据库内容是否为空")
            elif path_changed:
                st.success(f"✅ 已加载 {len(st.session_state.all_traces)} 条测试记录")

        except Exception as e:
            st.error(f"❌ 数据加载失败: {str(e)}")
            st.session_state.all_traces = []
            import traceback
            with st.expander("查看错误详情"):
                st.code(traceback.format_exc())


def get_filtered_and_sorted_traces():
    """获取筛选和排序后的traces

    Returns:
        筛选和排序后的TraceMetadata列表
    """
    state = st.session_state.dashboard_state
    all_traces = st.session_state.all_traces

    # 应用筛选
    filtered = apply_filters(all_traces, state)

    # 应用排序
    sorted_traces = sort_traces(filtered, state.sort_by, state.sort_order)

    return sorted_traces


def render_main_content(filtered_traces):
    """渲染主内容区域

    Args:
        filtered_traces: 筛选和排序后的traces
    """
    # 标题
    st.title("🐯 TigerHill Dashboard")
    st.caption("AI Agent Testing & Analysis Platform")

    # 指标卡片
    metrics_cards.render(filtered_traces)

    st.divider()

    # Tab导航 - 只保留概览和趋势
    tab1, tab2 = st.tabs([
        "📊 测试记录", "📉 趋势分析"
    ])

    with tab1:
        render_overview_tab(filtered_traces)

    with tab2:
        render_trends_tab(filtered_traces)


def render_overview_tab(filtered_traces):
    """渲染概览标签页

    Args:
        filtered_traces: 筛选后的traces
    """
    # 渲染列表（包含详情展示）
    trace_list.render(filtered_traces)


def render_trends_tab(filtered_traces):
    """渲染趋势标签页

    Args:
        filtered_traces: 筛选后的traces
    """
    st.header("📉 趋势分析")

    if not filtered_traces:
        st.info("没有数据可显示")
        return

    # Token分布图
    charts.render_token_distribution(filtered_traces)

    st.divider()

    # 成本趋势和质量热力图
    col1, col2 = st.columns(2)

    with col1:
        charts.render_cost_trend(filtered_traces)

    with col2:
        charts.render_quality_heatmap(filtered_traces)

    st.divider()

    # 额外图表
    col3, col4 = st.columns(2)

    with col3:
        charts.render_tokens_vs_cost(filtered_traces)

    with col4:
        charts.render_llm_calls_distribution(filtered_traces)


if __name__ == "__main__":
    main()

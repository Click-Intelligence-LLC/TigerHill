"""Analysis panel component for dashboard"""

import streamlit as st
from typing import Optional

from tigerhill.web.dashboard.models.analysis_result import AnalysisResult


def render(trace_id: str, analysis: Optional[AnalysisResult] = None):
    """渲染分析面板

    Args:
        trace_id: 追踪ID
        analysis: 分析结果（如果已有）
    """
    if not analysis:
        st.warning("⚠️ 该trace尚未分析")
        st.info("💡 分析功能将在后续版本中提供")
        st.markdown("""
        分析功能将包括:
        - 🎯 5大维度质量评分
        - 📊 22个详细指标
        - ⚠️ 问题检测
        - 💡 优化建议
        - 📈 与基线对比
        """)

        if st.button("🔍 运行分析（即将推出）", type="primary", disabled=True):
            st.info("分析功能正在开发中...")
        return

    # 总分和评级
    render_overall_score(analysis)

    st.divider()

    # 5大维度展示
    col1, col2 = st.columns([1, 1])
    with col1:
        render_radar_chart(analysis)
    with col2:
        render_dimension_details(analysis)

    st.divider()

    # 问题和建议
    render_issues_and_recommendations(analysis)


def render_overall_score(analysis: AnalysisResult):
    """渲染总分

    Args:
        analysis: 分析结果
    """
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown(f"""
        <div style="text-align: center; padding: 20px;">
            <h1 style="font-size: 72px; margin: 0;">{analysis.overall_score:.1f}</h1>
            <h2 style="margin: 10px 0;">评级: {analysis.grade}</h2>
            <p style="color: gray;">综合质量分数</p>
        </div>
        """, unsafe_allow_html=True)


def render_radar_chart(analysis: AnalysisResult):
    """渲染雷达图

    Args:
        analysis: 分析结果
    """
    try:
        import plotly.graph_objects as go

        categories = ['质量', '成本', '性能', '安全', '合规']
        values = [
            analysis.quality_score,
            analysis.cost_score,
            analysis.performance_score,
            analysis.security_score,
            analysis.compliance_score
        ]

        fig = go.Figure()

        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name='当前'
        ))

        # 如果有基线对比
        if analysis.baseline_comparison:
            baseline_values = [
                analysis.baseline_comparison.get('quality', 0),
                analysis.baseline_comparison.get('cost', 0),
                analysis.baseline_comparison.get('performance', 0),
                analysis.baseline_comparison.get('security', 0),
                analysis.baseline_comparison.get('compliance', 0)
            ]
            fig.add_trace(go.Scatterpolar(
                r=baseline_values,
                theta=categories,
                fill='toself',
                name='基线',
                opacity=0.6
            ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )
            ),
            showlegend=True,
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    except ImportError:
        st.warning("⚠️ 需要安装 plotly: pip install plotly")
        render_dimension_bars(analysis)


def render_dimension_bars(analysis: AnalysisResult):
    """渲染维度条形图（备选方案）

    Args:
        analysis: 分析结果
    """
    dimensions = [
        ("质量", analysis.quality_score),
        ("成本", analysis.cost_score),
        ("性能", analysis.performance_score),
        ("安全", analysis.security_score),
        ("合规", analysis.compliance_score)
    ]

    for name, score in dimensions:
        st.progress(score / 100, text=f"{name}: {score:.1f}")


def render_dimension_details(analysis: AnalysisResult):
    """渲染维度详情

    Args:
        analysis: 分析结果
    """
    st.subheader("📊 维度详情")

    dimensions = [
        ("质量", analysis.quality_score, "🎯"),
        ("成本", analysis.cost_score, "💰"),
        ("性能", analysis.performance_score, "⚡"),
        ("安全", analysis.security_score, "🔒"),
        ("合规", analysis.compliance_score, "✅")
    ]

    for name, score, icon in dimensions:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.progress(score / 100, text=f"{icon} {name}")
        with col2:
            st.caption(f"{score:.1f}")


def render_issues_and_recommendations(analysis: AnalysisResult):
    """渲染问题和建议

    Args:
        analysis: 分析结果
    """
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("⚠️ 发现的问题")
        if analysis.priority_issues:
            for issue in analysis.priority_issues:
                severity = issue.get("severity", "info")
                severity_emoji = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢"
                }.get(severity, "ℹ️")

                with st.expander(f"{severity_emoji} {issue['title']}"):
                    st.write(issue['description'])
                    if 'location' in issue:
                        st.code(issue['location'])
        else:
            st.success("✅ 未发现严重问题")

    with col2:
        st.subheader("💡 优化建议")
        if analysis.recommendations:
            for i, rec in enumerate(analysis.recommendations, 1):
                st.markdown(f"{i}. {rec}")
        else:
            st.info("暂无优化建议")

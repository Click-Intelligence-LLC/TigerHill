"""Tests for dashboard data processor"""

import pytest
from datetime import datetime, timedelta

from tigerhill.web.dashboard.models.trace_metadata import TraceMetadata
from tigerhill.web.dashboard.models.dashboard_state import DashboardState
from tigerhill.web.dashboard.data.processor import (
    apply_filters,
    sort_traces,
    calculate_metrics,
    calculate_delta,
    categorize_tokens
)


def create_sample_traces():
    """创建示例traces"""
    base_time = datetime(2024, 1, 1, 12, 0, 0)

    traces = [
        TraceMetadata(
            trace_id="trace-1",
            agent_name="agent-a",
            start_time=base_time,
            end_time=base_time + timedelta(seconds=10),
            duration_seconds=10.0,
            status="completed",
            total_events=5,
            llm_calls_count=2,
            total_tokens=1000,
            total_cost_usd=0.05,
            quality_score=85.0,
            tags=["test"]
        ),
        TraceMetadata(
            trace_id="trace-2",
            agent_name="agent-b",
            start_time=base_time + timedelta(hours=1),
            end_time=base_time + timedelta(hours=1, seconds=20),
            duration_seconds=20.0,
            status="completed",
            total_events=10,
            llm_calls_count=4,
            total_tokens=2000,
            total_cost_usd=0.10,
            quality_score=90.0,
            tags=["production"]
        ),
        TraceMetadata(
            trace_id="trace-3",
            agent_name="agent-a",
            start_time=base_time + timedelta(hours=2),
            end_time=base_time + timedelta(hours=2, seconds=15),
            duration_seconds=15.0,
            status="failed",
            total_events=3,
            llm_calls_count=1,
            total_tokens=500,
            total_cost_usd=0.02,
            quality_score=60.0,
            tags=["test"]
        )
    ]

    return traces


class TestApplyFilters:
    """测试筛选功能"""

    def test_filter_by_agent_name(self):
        """测试按agent名称筛选"""
        traces = create_sample_traces()
        state = DashboardState()
        state.filter_agent_name = "agent-a"
        # 设置日期范围以包含测试数据
        state.filter_date_range = (
            datetime(2024, 1, 1, 0, 0, 0),
            datetime(2024, 1, 2, 0, 0, 0)
        )
        # 包含所有状态
        state.filter_status = ["completed", "failed"]

        filtered = apply_filters(traces, state)

        assert len(filtered) == 2
        assert all(t.agent_name == "agent-a" for t in filtered)

    def test_filter_by_status(self):
        """测试按状态筛选"""
        traces = create_sample_traces()
        state = DashboardState()
        state.filter_status = ["completed"]
        # 设置日期范围以包含测试数据
        state.filter_date_range = (
            datetime(2024, 1, 1, 0, 0, 0),
            datetime(2024, 1, 2, 0, 0, 0)
        )

        filtered = apply_filters(traces, state)

        assert len(filtered) == 2
        assert all(t.status == "completed" for t in filtered)

    def test_filter_by_min_cost(self):
        """测试按最小成本筛选"""
        traces = create_sample_traces()
        state = DashboardState()
        state.filter_min_cost = 0.05
        # 设置日期范围以包含测试数据
        state.filter_date_range = (
            datetime(2024, 1, 1, 0, 0, 0),
            datetime(2024, 1, 2, 0, 0, 0)
        )

        filtered = apply_filters(traces, state)

        assert len(filtered) == 2
        assert all(t.total_cost_usd >= 0.05 for t in filtered)

    def test_filter_by_tags(self):
        """测试按标签筛选"""
        traces = create_sample_traces()
        state = DashboardState()
        state.filter_tags = ["production"]
        # 设置日期范围以包含测试数据
        state.filter_date_range = (
            datetime(2024, 1, 1, 0, 0, 0),
            datetime(2024, 1, 2, 0, 0, 0)
        )

        filtered = apply_filters(traces, state)

        assert len(filtered) == 1
        assert "production" in filtered[0].tags

    def test_filter_by_date_range(self):
        """测试按日期范围筛选"""
        traces = create_sample_traces()
        state = DashboardState()

        # 只保留前1小时的数据
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        state.filter_date_range = (
            base_time,
            base_time + timedelta(minutes=30)
        )

        filtered = apply_filters(traces, state)

        assert len(filtered) == 1
        assert filtered[0].trace_id == "trace-1"


class TestSortTraces:
    """测试排序功能"""

    def test_sort_by_time_desc(self):
        """测试按时间降序排序"""
        traces = create_sample_traces()

        sorted_traces = sort_traces(traces, "time", "desc")

        assert sorted_traces[0].trace_id == "trace-3"
        assert sorted_traces[-1].trace_id == "trace-1"

    def test_sort_by_cost_asc(self):
        """测试按成本升序排序"""
        traces = create_sample_traces()

        sorted_traces = sort_traces(traces, "cost", "asc")

        assert sorted_traces[0].total_cost_usd == 0.02
        assert sorted_traces[-1].total_cost_usd == 0.10

    def test_sort_by_tokens(self):
        """测试按token数排序"""
        traces = create_sample_traces()

        sorted_traces = sort_traces(traces, "tokens", "desc")

        assert sorted_traces[0].total_tokens == 2000
        assert sorted_traces[-1].total_tokens == 500

    def test_sort_by_quality(self):
        """测试按质量分数排序"""
        traces = create_sample_traces()

        sorted_traces = sort_traces(traces, "quality", "desc")

        assert sorted_traces[0].quality_score == 90.0
        assert sorted_traces[-1].quality_score == 60.0


class TestCalculateMetrics:
    """测试指标计算"""

    def test_calculate_metrics_with_data(self):
        """测试计算指标（有数据）"""
        traces = create_sample_traces()

        metrics = calculate_metrics(traces)

        assert metrics["total_traces"] == 3
        assert metrics["total_tokens"] == 3500
        assert metrics["total_cost"] == 0.17
        assert metrics["avg_quality"] == pytest.approx(78.33, rel=0.1)

    def test_calculate_metrics_empty(self):
        """测试计算指标（无数据）"""
        traces = []

        metrics = calculate_metrics(traces)

        assert metrics["total_traces"] == 0
        assert metrics["total_tokens"] == 0
        assert metrics["total_cost"] == 0.0
        assert metrics["avg_quality"] == 0.0


class TestCalculateDelta:
    """测试变化百分比计算"""

    def test_calculate_delta_increase(self):
        """测试增长"""
        delta = calculate_delta(120, 100)
        assert delta == 20.0

    def test_calculate_delta_decrease(self):
        """测试减少"""
        delta = calculate_delta(80, 100)
        assert delta == -20.0

    def test_calculate_delta_zero_previous(self):
        """测试之前值为0"""
        delta = calculate_delta(100, 0)
        assert delta == 0.0


class TestCategorizeTokens:
    """测试token分类"""

    def test_categorize_tokens(self):
        """测试token范围分类"""
        traces = create_sample_traces()

        categories = categorize_tokens(traces)

        assert categories["0-1k"] == 1  # trace-3: 500 tokens
        assert categories["1k-5k"] == 2  # trace-1: 1000, trace-2: 2000
        assert categories["5k-10k"] == 0
        assert categories["10k-50k"] == 0
        assert categories["50k+"] == 0

    def test_categorize_tokens_empty(self):
        """测试空列表"""
        traces = []

        categories = categorize_tokens(traces)

        assert all(v == 0 for v in categories.values())

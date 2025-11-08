"""Tests for dashboard models"""

import pytest
from datetime import datetime, timedelta

from tigerhill.web.dashboard.models.trace_metadata import TraceMetadata
from tigerhill.web.dashboard.models.llm_call_record import LLMCallRecord
from tigerhill.web.dashboard.models.analysis_result import AnalysisResult
from tigerhill.web.dashboard.models.dashboard_state import DashboardState


class TestTraceMetadata:
    """测试TraceMetadata"""

    def test_create_trace_metadata(self):
        """测试创建TraceMetadata"""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=10)

        trace = TraceMetadata(
            trace_id="test-123",
            agent_name="test-agent",
            start_time=start_time,
            end_time=end_time,
            duration_seconds=10.0,
            status="completed",
            total_events=5,
            llm_calls_count=2,
            total_tokens=1000,
            total_cost_usd=0.05
        )

        assert trace.trace_id == "test-123"
        assert trace.agent_name == "test-agent"
        assert trace.status == "completed"
        assert trace.total_tokens == 1000

    def test_avg_tokens_per_call(self):
        """测试平均token计算"""
        trace = TraceMetadata(
            trace_id="test-123",
            agent_name="test-agent",
            start_time=datetime.now(),
            end_time=None,
            duration_seconds=10.0,
            status="completed",
            total_events=5,
            llm_calls_count=4,
            total_tokens=1000,
            total_cost_usd=0.05
        )

        assert trace.avg_tokens_per_call == 250.0

    def test_status_emoji(self):
        """测试状态表情符号"""
        trace = TraceMetadata(
            trace_id="test-123",
            agent_name="test-agent",
            start_time=datetime.now(),
            end_time=None,
            duration_seconds=10.0,
            status="completed",
            total_events=5,
            llm_calls_count=2,
            total_tokens=1000,
            total_cost_usd=0.05
        )

        assert trace.status_emoji == "✅"

    def test_to_dict_and_from_dict(self):
        """测试字典转换"""
        start_time = datetime.now()

        trace = TraceMetadata(
            trace_id="test-123",
            agent_name="test-agent",
            start_time=start_time,
            end_time=None,
            duration_seconds=10.0,
            status="completed",
            total_events=5,
            llm_calls_count=2,
            total_tokens=1000,
            total_cost_usd=0.05,
            tags=["test"],
            metadata={"key": "value"}
        )

        # 转换为字典
        trace_dict = trace.to_dict()
        assert trace_dict["trace_id"] == "test-123"
        assert trace_dict["agent_name"] == "test-agent"

        # 从字典创建
        trace2 = TraceMetadata.from_dict(trace_dict)
        assert trace2.trace_id == trace.trace_id
        assert trace2.agent_name == trace.agent_name


class TestLLMCallRecord:
    """测试LLMCallRecord"""

    def test_create_llm_call_record(self):
        """测试创建LLMCallRecord"""
        record = LLMCallRecord(
            call_id="call-123",
            trace_id="trace-123",
            timestamp=datetime.now(),
            sequence_number=1,
            provider="openai",
            model="gpt-4",
            prompt="Test prompt",
            response="Test response",
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            cost_usd=0.001,
            latency_seconds=1.5
        )

        assert record.call_id == "call-123"
        assert record.provider == "openai"
        assert record.model == "gpt-4"

    def test_tokens_per_second(self):
        """测试每秒token数计算"""
        record = LLMCallRecord(
            call_id="call-123",
            trace_id="trace-123",
            timestamp=datetime.now(),
            sequence_number=1,
            provider="openai",
            model="gpt-4",
            prompt="Test prompt",
            completion_tokens=100,
            latency_seconds=2.0
        )

        assert record.tokens_per_second == 50.0

    def test_cost_per_1k_tokens(self):
        """测试每1k token成本计算"""
        record = LLMCallRecord(
            call_id="call-123",
            trace_id="trace-123",
            timestamp=datetime.now(),
            sequence_number=1,
            provider="openai",
            model="gpt-4",
            prompt="Test prompt",
            total_tokens=1000,
            cost_usd=0.01
        )

        # 0.01 / 1000 * 1000 = 0.01
        assert record.cost_per_1k_tokens == 0.01


class TestAnalysisResult:
    """测试AnalysisResult"""

    def test_create_analysis_result(self):
        """测试创建AnalysisResult"""
        result = AnalysisResult(
            trace_id="trace-123",
            analyzed_at=datetime.now(),
            quality_score=85.0,
            cost_score=75.0,
            performance_score=90.0,
            security_score=80.0,
            compliance_score=70.0,
            overall_score=80.0,
            metrics={},
            issues=[],
            recommendations=[]
        )

        assert result.trace_id == "trace-123"
        assert result.quality_score == 85.0

    def test_grade_calculation(self):
        """测试评级计算"""
        # A+级别
        result1 = AnalysisResult(
            trace_id="trace-1",
            analyzed_at=datetime.now(),
            quality_score=95.0,
            cost_score=95.0,
            performance_score=95.0,
            security_score=95.0,
            compliance_score=95.0,
            overall_score=95.0,
            metrics={}
        )
        assert result1.grade == "A+"

        # B级别
        result2 = AnalysisResult(
            trace_id="trace-2",
            analyzed_at=datetime.now(),
            quality_score=75.0,
            cost_score=75.0,
            performance_score=75.0,
            security_score=75.0,
            compliance_score=75.0,
            overall_score=75.0,
            metrics={}
        )
        assert result2.grade == "B"

    def test_priority_issues(self):
        """测试高优先级问题筛选"""
        result = AnalysisResult(
            trace_id="trace-123",
            analyzed_at=datetime.now(),
            quality_score=85.0,
            cost_score=75.0,
            performance_score=90.0,
            security_score=80.0,
            compliance_score=70.0,
            overall_score=80.0,
            metrics={},
            issues=[
                {"severity": "low", "title": "Low issue"},
                {"severity": "high", "title": "High issue"},
                {"severity": "critical", "title": "Critical issue"}
            ]
        )

        priority = result.priority_issues
        assert len(priority) == 2
        assert priority[0]["severity"] == "high"
        assert priority[1]["severity"] == "critical"


class TestDashboardState:
    """测试DashboardState"""

    def test_create_dashboard_state(self):
        """测试创建DashboardState"""
        state = DashboardState()

        assert state.storage_path == "./test_traces"
        assert state.page_size == 20
        assert state.current_page == 1
        assert state.sort_by == "time"

    def test_reset_filters(self):
        """测试重置筛选器"""
        state = DashboardState()

        # 修改筛选条件
        state.filter_agent_name = "test-agent"
        state.filter_min_cost = 1.0
        state.filter_tags = ["tag1", "tag2"]

        # 重置
        state.reset_filters()

        assert state.filter_agent_name is None
        assert state.filter_min_cost == 0.0
        assert state.filter_tags == []

    def test_date_range_initialization(self):
        """测试日期范围初始化"""
        state = DashboardState()

        assert state.filter_date_range is not None
        start_date, end_date = state.filter_date_range

        # 应该是最近7天
        assert (end_date - start_date).days == 7

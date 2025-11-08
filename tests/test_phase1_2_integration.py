"""
Phase 1.2 集成测试
验证整个SQLite数据库系统的端到端功能
"""

import pytest
import tempfile
import time
from pathlib import Path

from tigerhill.storage.database import DatabaseManager
from tigerhill.storage.sqlite_trace_store import SQLiteTraceStore
from tigerhill.storage.trace_store import Trace, TraceEvent, EventType
from tigerhill.web.dashboard.data.loader import DataLoader


class TestPhase12Integration:
    """Phase 1.2 SQLite集成测试套件"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        # 重置单例
        DatabaseManager._instance = None

        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        yield db_path

        # 清理
        Path(db_path).unlink(missing_ok=True)
        DatabaseManager._instance = None

    def test_01_database_initialization(self, temp_db):
        """测试1: 数据库初始化"""
        db = DatabaseManager(temp_db)

        # 确保schema已创建
        schema_path = Path(__file__).parent.parent / "scripts" / "migrations" / "v1_initial_schema.sql"
        db.initialize_database(str(schema_path))

        # 验证表存在
        assert db.table_exists('traces')
        assert db.table_exists('events')
        assert db.table_exists('captures')
        assert db.table_exists('schema_version')

        # 验证schema版本
        version = db.get_schema_version()
        assert version == 1

    def test_02_sqlite_trace_store_basic_operations(self, temp_db):
        """测试2: SQLiteTraceStore基本操作"""
        store = SQLiteTraceStore(db_path=temp_db, auto_init=True)

        # 创建trace
        trace_id = store.start_trace(
            agent_name="test-agent",
            task_id="task-001",
            metadata={"test": True}
        )

        assert trace_id is not None

        # 写入events
        store.write_event(
            {"type": "prompt", "content": "test prompt", "total_tokens": 100, "cost_usd": 0.001},
            event_type=EventType.PROMPT
        )

        store.write_event(
            {"type": "model_response", "content": "test response", "total_tokens": 200, "cost_usd": 0.002},
            event_type=EventType.MODEL_RESPONSE
        )

        # 结束trace
        store.end_trace(trace_id)

        # 获取trace
        trace = store.get_trace(trace_id, include_events=True)
        assert trace is not None
        assert trace.trace_id == trace_id
        assert len(trace.events) == 2

        # 验证统计信息被正确计算
        assert trace.metadata['_db_total_events'] == 2
        assert trace.metadata['_db_llm_calls_count'] == 2
        assert trace.metadata['_db_total_tokens'] == 300
        assert trace.metadata['_db_total_cost_usd'] == 0.003
        assert trace.metadata['_db_status'] == 'completed'

    def test_03_query_and_filtering(self, temp_db):
        """测试3: 查询和筛选功能"""
        store = SQLiteTraceStore(db_path=temp_db, auto_init=True)

        # 创建多个traces
        for i in range(5):
            trace_id = store.start_trace(agent_name=f"agent-{i % 2}")
            store.write_event(
                {"type": "prompt", "total_tokens": (i + 1) * 100, "cost_usd": (i + 1) * 0.001},
                event_type=EventType.PROMPT
            )
            store.end_trace(trace_id)

        # 查询所有traces
        all_traces = store.query_traces()
        assert len(all_traces) == 5

        # 按agent_name筛选
        agent_0_traces = store.query_traces(agent_name="agent-0")
        assert len(agent_0_traces) == 3

        # 按成本筛选
        expensive_traces = store.query_traces(min_cost=0.003)
        assert len(expensive_traces) == 3

        # 分页
        page1 = store.query_traces(limit=2, offset=0)
        page2 = store.query_traces(limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].trace_id != page2[0].trace_id

        # 排序
        by_cost = store.query_traces(order_by="total_cost_usd", order_desc=True)
        assert by_cost[0].metadata['_db_total_cost_usd'] >= by_cost[-1].metadata['_db_total_cost_usd']

    def test_04_statistics(self, temp_db):
        """测试4: 统计功能"""
        store = SQLiteTraceStore(db_path=temp_db, auto_init=True)

        # 创建traces
        for i in range(3):
            trace_id = store.start_trace(agent_name="stats-agent")
            store.write_event(
                {"type": "prompt", "total_tokens": 100, "cost_usd": 0.001},
                event_type=EventType.PROMPT
            )
            store.end_trace(trace_id)

        # 获取统计信息
        stats = store.get_statistics()
        assert stats['total_traces'] == 3
        assert stats['total_events'] == 3
        assert stats['total_llm_calls'] == 3
        assert stats['total_tokens'] == 300
        assert stats['total_cost_usd'] == 0.003
        assert stats['status_counts']['completed'] == 3

    def test_05_dashboard_integration(self, temp_db):
        """测试5: Dashboard集成"""
        store = SQLiteTraceStore(db_path=temp_db, auto_init=True)

        # 创建测试数据
        for i in range(5):
            trace_id = store.start_trace(agent_name=f"dash-agent-{i}")
            store.write_event(
                {"type": "prompt", "total_tokens": 100},
                event_type=EventType.PROMPT
            )
            store.end_trace(trace_id)

        # 使用DataLoader加载
        loader = DataLoader(use_database=True, db_path=temp_db)
        assert loader.data_source_type == "SQLite Database"

        # 加载traces
        traces = loader.load_traces()
        assert len(traces) == 5

        # 验证metadata被正确提取
        for trace in traces:
            assert trace.trace_id is not None
            assert trace.agent_name.startswith("dash-agent-")
            assert trace.status == 'completed'
            assert trace.total_events == 1

        # 获取unique agent names
        agent_names = loader.get_unique_agent_names(traces)
        assert len(agent_names) == 5

    def test_06_concurrent_writes(self, temp_db):
        """测试6: 并发写入"""
        store = SQLiteTraceStore(db_path=temp_db, auto_init=True)

        # 同时创建多个traces
        trace_ids = []
        for i in range(5):
            trace_id = store.start_trace(agent_name=f"concurrent-agent-{i}")
            trace_ids.append(trace_id)

        # 为每个trace写入events
        for i, trace_id in enumerate(trace_ids):
            for j in range(3):
                store.write_event(
                    {"index": j, "trace_index": i},
                    trace_id=trace_id
                )

        # 结束所有traces
        for trace_id in trace_ids:
            store.end_trace(trace_id)

        # 验证所有traces都正确保存
        for i, trace_id in enumerate(trace_ids):
            trace = store.get_trace(trace_id, include_events=True)
            assert trace is not None
            assert len(trace.events) == 3
            assert trace.metadata['_db_total_events'] == 3

    def test_07_delete_and_cascade(self, temp_db):
        """测试7: 删除和级联"""
        store = SQLiteTraceStore(db_path=temp_db, auto_init=True)

        # 创建trace with events
        trace_id = store.start_trace(agent_name="delete-agent")
        for i in range(3):
            store.write_event({"index": i})
        store.end_trace(trace_id)

        # 验证events存在
        events = store.get_events(trace_id)
        assert len(events) == 3

        # 删除trace
        assert store.delete_trace(trace_id) is True

        # 验证trace被删除
        assert store.get_trace(trace_id) is None

        # 验证events被级联删除
        events = store.get_events(trace_id)
        assert len(events) == 0

    def test_08_end_to_end_workflow(self, temp_db):
        """测试8: 端到端工作流"""
        store = SQLiteTraceStore(db_path=temp_db, auto_init=True)

        # 模拟完整的agent执行流程
        trace_id = store.start_trace(
            agent_name="e2e-agent",
            task_id="e2e-task-001",
            metadata={"priority": "high", "tags": ["production", "test"]}
        )

        # 模拟多个LLM调用
        for i in range(3):
            # Prompt
            store.write_event(
                {
                    "type": "prompt",
                    "content": f"Prompt {i}",
                    "total_tokens": 100,
                    "cost_usd": 0.001
                },
                event_type=EventType.PROMPT
            )

            # Response
            store.write_event(
                {
                    "type": "model_response",
                    "content": f"Response {i}",
                    "total_tokens": 200,
                    "cost_usd": 0.002
                },
                event_type=EventType.MODEL_RESPONSE
            )

            # Tool call (optional)
            if i % 2 == 0:
                store.write_event(
                    {"type": "tool_call", "tool": "calculator"},
                    event_type=EventType.TOOL_CALL
                )

        # 结束trace
        time.sleep(0.01)  # 确保有duration
        store.end_trace(trace_id)

        # 验证完整trace
        trace = store.get_trace(trace_id, include_events=True)
        assert trace is not None
        assert trace.agent_name == "e2e-agent"
        assert trace.task_id == "e2e-task-001"
        assert len(trace.events) == 8  # 3 prompts + 3 responses + 2 tool calls
        assert trace.end_time > trace.start_time

        # 验证统计信息
        assert trace.metadata['_db_total_events'] == 8
        assert trace.metadata['_db_llm_calls_count'] == 6  # 3 prompts + 3 responses
        assert trace.metadata['_db_total_tokens'] == 900  # (100 + 200) * 3
        assert abs(trace.metadata['_db_total_cost_usd'] - 0.009) < 0.0001  # 浮点数比较
        assert trace.metadata['_db_status'] == 'completed'

        # 获取摘要
        summary = store.get_summary(trace_id)
        assert summary is not None
        assert summary['total_events'] == 8
        assert summary['llm_calls_count'] == 6
        assert summary['event_counts']['prompt'] == 3
        assert summary['event_counts']['model_response'] == 3
        assert summary['event_counts']['tool_call'] == 2

        # Dashboard加载
        loader = DataLoader(use_database=True, db_path=temp_db)
        traces = loader.load_traces()
        assert len(traces) == 1
        loaded_trace = traces[0]
        assert loaded_trace.trace_id == trace_id
        assert loaded_trace.total_events == 8
        assert loaded_trace.llm_calls_count == 6
        assert loaded_trace.total_tokens == 900
        assert abs(loaded_trace.total_cost_usd - 0.009) < 0.0001


def test_run_all_integration_tests():
    """运行所有集成测试"""
    pytest.main([__file__, "-v", "-s"])


if __name__ == "__main__":
    test_run_all_integration_tests()

"""
端到端自动化验证测试
验证完整流程：Agent执行 → 存储 → 查询 → Dashboard
"""

import pytest
import tempfile
import time
from pathlib import Path

from tigerhill.storage.sqlite_trace_store import SQLiteTraceStore
from tigerhill.storage.trace_store import EventType
from tigerhill.storage.database import DatabaseManager
from tigerhill.web.dashboard.data.loader import DataLoader


class TestEndToEndValidation:
    """端到端验证测试套件"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        # 重置单例
        DatabaseManager._instance = None

        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        yield db_path

        Path(db_path).unlink(missing_ok=True)
        DatabaseManager._instance = None

    def test_complete_workflow(self, temp_db):
        """测试完整工作流：Agent执行 → 存储 → 查询 → Dashboard"""

        # === 步骤1: 初始化TraceStore ===
        store = SQLiteTraceStore(db_path=temp_db, auto_init=True)

        # === 步骤2: 模拟Agent执行 ===
        trace_ids = []

        for task_num in range(3):
            # 开始trace
            trace_id = store.start_trace(
                agent_name="e2e-validation-agent",
                task_id=f"task-{task_num}",
                metadata={"task_number": task_num, "tags": ["validation", "e2e"]}
            )
            trace_ids.append(trace_id)

            # 模拟LLM调用
            for call_num in range(3):
                # Prompt
                store.write_event(
                    {
                        "type": "prompt",
                        "content": f"Prompt {call_num}",
                        "total_tokens": 100,
                        "cost_usd": 0.003
                    },
                    trace_id=trace_id,
                    event_type=EventType.PROMPT
                )

                # Response
                store.write_event(
                    {
                        "type": "model_response",
                        "content": f"Response {call_num}",
                        "total_tokens": 200,
                        "cost_usd": 0.006
                    },
                    trace_id=trace_id,
                    event_type=EventType.MODEL_RESPONSE
                )

            # 模拟工具调用
            store.write_event(
                {"type": "tool_call", "tool": "calculator"},
                trace_id=trace_id,
                event_type=EventType.TOOL_CALL
            )

            # 结束trace
            time.sleep(0.01)
            store.end_trace(trace_id)

        # === 步骤3: 验证存储 ===

        # 3.1 验证traces数量
        all_traces = store.query_traces()
        assert len(all_traces) == 3, f"Expected 3 traces, got {len(all_traces)}"

        # 3.2 验证统计信息
        stats = store.get_statistics()
        assert stats['total_traces'] == 3
        assert stats['total_events'] == 21  # (3 prompts + 3 responses + 1 tool) * 3 tasks
        assert stats['total_llm_calls'] == 18  # (3 prompts + 3 responses) * 3 tasks
        assert stats['total_tokens'] == 2700  # (100 + 200) * 3 * 3
        assert abs(stats['total_cost_usd'] - 0.081) < 0.001  # (0.003 + 0.006) * 3 * 3
        assert stats['status_counts']['completed'] == 3

        # 3.3 验证每个trace
        for trace_id in trace_ids:
            trace = store.get_trace(trace_id, include_events=True)
            assert trace is not None
            assert trace.agent_name == "e2e-validation-agent"
            assert len(trace.events) == 7  # 3 prompts + 3 responses + 1 tool
            assert trace.metadata['_db_status'] == 'completed'
            assert trace.metadata['_db_total_events'] == 7
            assert trace.metadata['_db_llm_calls_count'] == 6
            assert trace.metadata['_db_total_tokens'] == 900
            assert abs(trace.metadata['_db_total_cost_usd'] - 0.027) < 0.001

        # === 步骤4: 验证查询功能 ===

        # 4.1 按agent_name查询
        agent_traces = store.query_traces(agent_name="e2e-validation-agent")
        assert len(agent_traces) == 3

        # 4.2 按状态查询
        completed_traces = store.query_traces(status="completed")
        assert len(completed_traces) == 3

        # 4.3 按成本范围查询
        expensive_traces = store.query_traces(min_cost=0.025)
        assert len(expensive_traces) == 3

        # 4.4 排序查询
        by_cost = store.query_traces(order_by="total_cost_usd", order_desc=True)
        assert len(by_cost) == 3
        assert by_cost[0].metadata['_db_total_cost_usd'] >= by_cost[-1].metadata['_db_total_cost_usd']

        # 4.5 分页查询
        page1 = store.query_traces(limit=2, offset=0)
        page2 = store.query_traces(limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 1

        # === 步骤5: 验证Dashboard集成 ===

        # 5.1 创建DataLoader
        loader = DataLoader(use_database=True, db_path=temp_db)
        assert loader.data_source_type == "SQLite Database"

        # 5.2 加载traces
        dashboard_traces = loader.load_traces()
        assert len(dashboard_traces) == 3

        # 5.3 验证TraceMetadata
        for trace_meta in dashboard_traces:
            assert trace_meta.agent_name == "e2e-validation-agent"
            assert trace_meta.status == "completed"
            assert trace_meta.total_events == 7
            assert trace_meta.llm_calls_count == 6
            assert trace_meta.total_tokens == 900
            assert abs(trace_meta.total_cost_usd - 0.027) < 0.001

        # 5.4 获取unique agent names
        agent_names = loader.get_unique_agent_names(dashboard_traces)
        assert len(agent_names) == 1
        assert agent_names[0] == "e2e-validation-agent"

        # 5.5 加载trace详情
        trace_detail = loader.load_trace_detail(trace_ids[0])
        assert trace_detail is not None

        # === 步骤6: 验证摘要功能 ===
        for trace_id in trace_ids:
            summary = store.get_summary(trace_id)
            assert summary is not None
            assert summary['trace_id'] == trace_id
            assert summary['agent_name'] == "e2e-validation-agent"
            assert summary['status'] == 'completed'
            assert summary['total_events'] == 7
            assert summary['llm_calls_count'] == 6
            assert summary['event_counts']['prompt'] == 3
            assert summary['event_counts']['model_response'] == 3
            assert summary['event_counts']['tool_call'] == 1

        print("\n" + "=" * 60)
        print("✅ 端到端验证测试通过！")
        print("=" * 60)
        print(f"验证项目:")
        print(f"  ✅ Agent执行和Trace记录")
        print(f"  ✅ 数据存储到SQLite")
        print(f"  ✅ 统计信息计算")
        print(f"  ✅ 查询和筛选功能")
        print(f"  ✅ Dashboard集成")
        print(f"  ✅ Trace摘要生成")
        print("=" * 60)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

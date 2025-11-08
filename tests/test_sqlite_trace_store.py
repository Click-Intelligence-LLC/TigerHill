"""
测试SQLiteTraceStore
"""

import pytest
import tempfile
import time
from pathlib import Path

from tigerhill.storage.sqlite_trace_store import SQLiteTraceStore
from tigerhill.storage.trace_store import EventType


@pytest.fixture
def temp_store():
    """临时SQLiteTraceStore fixture"""
    # 重置单例
    from tigerhill.storage.database import DatabaseManager
    DatabaseManager._instance = None

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    store = SQLiteTraceStore(db_path=db_path, auto_init=True)

    yield store

    # 清理
    store.db.close_connection()
    Path(db_path).unlink(missing_ok=True)

    # 再次重置单例
    DatabaseManager._instance = None


def test_start_trace(temp_store):
    """测试启动trace"""
    trace_id = temp_store.start_trace(
        agent_name="test-agent",
        task_id="task-001",
        metadata={"key": "value"}
    )

    assert trace_id is not None
    assert temp_store._current_trace_id == trace_id

    # 验证trace已插入数据库
    trace = temp_store.get_trace(trace_id, include_events=False)
    assert trace is not None
    assert trace.trace_id == trace_id
    assert trace.agent_name == "test-agent"
    assert trace.task_id == "task-001"
    assert trace.end_time is None


def test_end_trace(temp_store):
    """测试结束trace"""
    trace_id = temp_store.start_trace(agent_name="test-agent")

    # 等待一小段时间
    time.sleep(0.01)

    temp_store.end_trace(trace_id)

    # 验证trace已更新
    trace = temp_store.get_trace(trace_id, include_events=False)
    assert trace.end_time is not None
    assert trace.end_time > trace.start_time
    assert trace.metadata['_db_status'] in ['completed', 'running', 'failed']


def test_write_event(temp_store):
    """测试写入事件"""
    trace_id = temp_store.start_trace(agent_name="test-agent")

    # 写入事件
    event_id = temp_store.write_event(
        event_data={"type": "prompt", "content": "test prompt"},
        event_type=EventType.PROMPT
    )

    assert event_id is not None

    # 获取事件
    events = temp_store.get_events(trace_id)
    assert len(events) == 1
    assert events[0].event_id == event_id
    assert events[0].event_type == EventType.PROMPT
    assert events[0].data["content"] == "test prompt"


def test_write_multiple_events(temp_store):
    """测试写入多个事件"""
    trace_id = temp_store.start_trace(agent_name="test-agent")

    # 写入3个事件
    for i in range(3):
        temp_store.write_event(
            event_data={"type": "custom", "index": i},
            event_type=EventType.CUSTOM
        )

    # 验证
    events = temp_store.get_events(trace_id)
    assert len(events) == 3

    # 验证sequence_number正确
    for i, event in enumerate(events):
        assert event.data["index"] == i


def test_write_event_without_active_trace(temp_store):
    """测试在没有active trace时写入事件"""
    with pytest.raises(ValueError, match="No active trace"):
        temp_store.write_event({"data": "test"})


def test_get_trace(temp_store):
    """测试获取trace"""
    # 创建trace和事件
    trace_id = temp_store.start_trace(agent_name="test-agent")
    temp_store.write_event({"type": "prompt", "msg": "test"}, event_type=EventType.PROMPT)
    temp_store.write_event({"type": "model_response", "msg": "response"}, event_type=EventType.MODEL_RESPONSE)
    temp_store.end_trace()

    # 获取trace（包含events）
    trace = temp_store.get_trace(trace_id, include_events=True)
    assert trace is not None
    assert trace.trace_id == trace_id
    assert len(trace.events) == 2

    # 获取trace（不包含events）
    trace = temp_store.get_trace(trace_id, include_events=False)
    assert trace is not None
    assert len(trace.events) == 0


def test_get_trace_not_found(temp_store):
    """测试获取不存在的trace"""
    trace = temp_store.get_trace("nonexistent-id")
    assert trace is None


def test_get_all_traces(temp_store):
    """测试获取所有traces"""
    # 创建3个traces
    for i in range(3):
        trace_id = temp_store.start_trace(agent_name=f"agent-{i}")
        temp_store.write_event({"index": i})
        temp_store.end_trace(trace_id)

    # 获取所有traces
    traces = temp_store.get_all_traces(include_events=False)
    assert len(traces) == 3

    # 验证按start_time降序排序
    for i in range(len(traces) - 1):
        assert traces[i].start_time >= traces[i + 1].start_time


def test_get_events_filtered(temp_store):
    """测试按类型筛选事件"""
    trace_id = temp_store.start_trace(agent_name="test-agent")

    # 写入不同类型的事件
    temp_store.write_event({"type": "prompt"}, event_type=EventType.PROMPT)
    temp_store.write_event({"type": "model_response"}, event_type=EventType.MODEL_RESPONSE)
    temp_store.write_event({"type": "prompt"}, event_type=EventType.PROMPT)
    temp_store.write_event({"type": "error"}, event_type=EventType.ERROR)

    # 筛选PROMPT类型
    prompt_events = temp_store.get_events(trace_id, event_type=EventType.PROMPT)
    assert len(prompt_events) == 2

    # 获取所有事件
    all_events = temp_store.get_events(trace_id)
    assert len(all_events) == 4


def test_query_traces_by_agent_name(temp_store):
    """测试按agent_name查询"""
    temp_store.start_trace(agent_name="agent-a")
    temp_store.end_trace()

    temp_store.start_trace(agent_name="agent-b")
    temp_store.end_trace()

    temp_store.start_trace(agent_name="agent-a")
    temp_store.end_trace()

    # 查询agent-a
    traces = temp_store.query_traces(agent_name="agent-a")
    assert len(traces) == 2
    assert all(t.agent_name == "agent-a" for t in traces)


def test_query_traces_by_status(temp_store):
    """测试按status查询"""
    # 创建completed trace
    trace_id = temp_store.start_trace(agent_name="test-agent")
    temp_store.end_trace(trace_id)

    # 创建running trace
    temp_store.start_trace(agent_name="test-agent")

    # 创建failed trace
    trace_id = temp_store.start_trace(agent_name="test-agent")
    temp_store.write_event({"type": "error"}, event_type=EventType.ERROR)
    temp_store.end_trace(trace_id)

    # 查询completed
    traces = temp_store.query_traces(status="completed")
    assert len(traces) == 1
    assert traces[0].metadata['_db_status'] == 'completed'

    # 查询running
    traces = temp_store.query_traces(status="running")
    assert len(traces) == 1

    # 查询failed
    traces = temp_store.query_traces(status="failed")
    assert len(traces) == 1


def test_query_traces_with_pagination(temp_store):
    """测试分页查询"""
    # 创建10个traces
    for i in range(10):
        trace_id = temp_store.start_trace(agent_name="test-agent")
        temp_store.end_trace(trace_id)

    # 第1页（5条）
    page1 = temp_store.query_traces(limit=5, offset=0)
    assert len(page1) == 5

    # 第2页（5条）
    page2 = temp_store.query_traces(limit=5, offset=5)
    assert len(page2) == 5

    # 验证没有重复
    page1_ids = {t.trace_id for t in page1}
    page2_ids = {t.trace_id for t in page2}
    assert len(page1_ids & page2_ids) == 0


def test_query_traces_with_time_filter(temp_store):
    """测试时间范围筛选"""
    # 创建3个traces，间隔时间
    start_times = []
    for i in range(3):
        trace_id = temp_store.start_trace(agent_name="test-agent")
        trace = temp_store.get_trace(trace_id, include_events=False)
        start_times.append(trace.start_time)
        temp_store.end_trace(trace_id)
        time.sleep(0.01)

    # 查询第2个trace之后开始的
    traces = temp_store.query_traces(start_after=start_times[1])
    assert len(traces) >= 1


def test_query_traces_with_cost_filter(temp_store):
    """测试成本筛选"""
    # 创建不同成本的traces
    for cost in [0.001, 0.005, 0.01]:
        trace_id = temp_store.start_trace(agent_name="test-agent")
        temp_store.write_event(
            {"type": "prompt", "cost_usd": cost},
            event_type=EventType.PROMPT
        )
        temp_store.end_trace(trace_id)

    # 查询成本 >= 0.005的
    traces = temp_store.query_traces(min_cost=0.005)
    assert len(traces) == 2

    # 查询成本 <= 0.005的
    traces = temp_store.query_traces(max_cost=0.005)
    assert len(traces) == 2


def test_query_traces_order_by(temp_store):
    """测试排序"""
    # 创建不同tokens的traces
    for tokens in [100, 50, 200]:
        trace_id = temp_store.start_trace(agent_name="test-agent")
        temp_store.write_event(
            {"type": "prompt", "total_tokens": tokens},
            event_type=EventType.PROMPT
        )
        temp_store.end_trace(trace_id)

    # 按tokens升序
    traces = temp_store.query_traces(order_by="total_tokens", order_desc=False)
    assert len(traces) == 3
    assert traces[0].metadata['_db_total_tokens'] <= traces[1].metadata['_db_total_tokens']

    # 按tokens降序
    traces = temp_store.query_traces(order_by="total_tokens", order_desc=True)
    assert len(traces) == 3
    assert traces[0].metadata['_db_total_tokens'] >= traces[1].metadata['_db_total_tokens']


def test_delete_trace(temp_store):
    """测试删除trace"""
    trace_id = temp_store.start_trace(agent_name="test-agent")
    temp_store.write_event({"data": "test"})
    temp_store.end_trace(trace_id)

    # 验证存在
    assert temp_store.get_trace(trace_id) is not None

    # 删除
    result = temp_store.delete_trace(trace_id)
    assert result is True

    # 验证已删除
    assert temp_store.get_trace(trace_id) is None

    # Events应该被级联删除
    events = temp_store.get_events(trace_id)
    assert len(events) == 0


def test_delete_nonexistent_trace(temp_store):
    """测试删除不存在的trace"""
    result = temp_store.delete_trace("nonexistent-id")
    assert result is False


def test_clear(temp_store):
    """测试清空所有数据"""
    # 创建多个traces
    for i in range(3):
        trace_id = temp_store.start_trace(agent_name=f"agent-{i}")
        temp_store.write_event({"index": i})
        temp_store.end_trace(trace_id)

    # 清空
    temp_store.clear()

    # 验证
    traces = temp_store.get_all_traces()
    assert len(traces) == 0


def test_get_summary(temp_store):
    """测试获取trace摘要"""
    trace_id = temp_store.start_trace(agent_name="test-agent", task_id="task-001")

    # 写入不同类型的事件
    temp_store.write_event({"type": "prompt"}, event_type=EventType.PROMPT)
    temp_store.write_event({"type": "model_response"}, event_type=EventType.MODEL_RESPONSE)
    temp_store.write_event({"type": "tool_call"}, event_type=EventType.TOOL_CALL)

    temp_store.end_trace(trace_id)

    # 获取摘要
    summary = temp_store.get_summary(trace_id)

    assert summary is not None
    assert summary['trace_id'] == trace_id
    assert summary['agent_name'] == "test-agent"
    assert summary['task_id'] == "task-001"
    assert summary['total_events'] == 3
    assert summary['status'] == 'completed'
    assert 'event_counts' in summary
    assert summary['event_counts']['prompt'] == 1
    assert summary['event_counts']['model_response'] == 1
    assert summary['event_counts']['tool_call'] == 1


def test_get_summary_not_found(temp_store):
    """测试获取不存在trace的摘要"""
    summary = temp_store.get_summary("nonexistent-id")
    assert summary is None


def test_get_statistics(temp_store):
    """测试获取统计信息"""
    # 创建多个traces
    for i in range(5):
        trace_id = temp_store.start_trace(agent_name=f"agent-{i}")
        temp_store.write_event(
            {"type": "prompt", "total_tokens": 100, "cost_usd": 0.001},
            event_type=EventType.PROMPT
        )
        temp_store.end_trace(trace_id)

    # 创建1个运行中的trace
    temp_store.start_trace(agent_name="agent-running")

    # 获取统计
    stats = temp_store.get_statistics()

    assert stats['total_traces'] == 6
    assert stats['total_events'] >= 5
    assert stats['total_llm_calls'] >= 5
    assert stats['total_tokens'] >= 500
    assert stats['total_cost_usd'] >= 0.005
    assert 'status_counts' in stats
    assert stats['status_counts']['completed'] == 5
    assert stats['status_counts']['running'] == 1


def test_interface_compatibility(temp_store):
    """测试接口与原TraceStore兼容"""
    # 验证所有TraceStore方法都存在
    required_methods = [
        'start_trace',
        'end_trace',
        'write_event',
        'get_trace',
        'get_all_traces',
        'get_events',
        'query_traces',
        'clear',
        'get_summary'
    ]

    for method in required_methods:
        assert hasattr(temp_store, method)
        assert callable(getattr(temp_store, method))


def test_concurrent_traces(temp_store):
    """测试并发创建多个traces"""
    trace_ids = []

    # 同时创建3个traces
    for i in range(3):
        trace_id = temp_store.start_trace(agent_name=f"agent-{i}")
        trace_ids.append(trace_id)

    # 为每个trace写入事件（不使用current_trace_id）
    for i, trace_id in enumerate(trace_ids):
        temp_store.write_event(
            {"index": i},
            trace_id=trace_id
        )

    # 结束每个trace
    for trace_id in trace_ids:
        temp_store.end_trace(trace_id)

    # 验证
    for i, trace_id in enumerate(trace_ids):
        trace = temp_store.get_trace(trace_id)
        assert trace is not None
        assert len(trace.events) == 1
        assert trace.events[0].data['index'] == i

"""
测试Trace和TraceEvent的数据库序列化/反序列化
"""

import pytest
import json
import time

from tigerhill.storage.trace_store import Trace, TraceEvent, EventType


def test_trace_event_to_db_dict():
    """测试TraceEvent.to_db_dict()"""
    event = TraceEvent(
        event_id="event-001",
        trace_id="trace-001",
        event_type=EventType.PROMPT,
        timestamp=1234567890.5,
        data={"prompt": "test prompt", "model": "gpt-4"},
        metadata={"user": "test_user"}
    )

    db_dict = event.to_db_dict(sequence_number=0)

    assert db_dict['trace_id'] == "trace-001"
    assert db_dict['event_type'] == "prompt"
    assert db_dict['timestamp'] == 1234567890.5
    assert db_dict['sequence_number'] == 0

    # Data should be JSON string
    assert isinstance(db_dict['data'], str)

    # Parse and verify data content
    data = json.loads(db_dict['data'])
    assert data['event_id'] == "event-001"
    assert data['event_type'] == "prompt"
    assert data['data'] == {"prompt": "test prompt", "model": "gpt-4"}
    assert data['metadata'] == {"user": "test_user"}


def test_trace_event_from_db_dict():
    """测试TraceEvent.from_db_dict()"""
    db_data = {
        'trace_id': 'trace-001',
        'event_type': 'prompt',
        'timestamp': 1234567890.5,
        'sequence_number': 0,
        'data': json.dumps({
            'event_id': 'event-001',
            'event_type': 'prompt',
            'data': {'prompt': 'test prompt', 'model': 'gpt-4'},
            'metadata': {'user': 'test_user'}
        })
    }

    event = TraceEvent.from_db_dict(db_data)

    assert event.event_id == "event-001"
    assert event.trace_id == "trace-001"
    assert event.event_type == EventType.PROMPT
    assert event.timestamp == 1234567890.5
    assert event.data == {'prompt': 'test prompt', 'model': 'gpt-4'}
    assert event.metadata == {'user': 'test_user'}


def test_trace_event_round_trip():
    """测试TraceEvent序列化和反序列化的完整流程"""
    original = TraceEvent(
        event_id="event-001",
        trace_id="trace-001",
        event_type=EventType.MODEL_RESPONSE,
        timestamp=time.time(),
        data={"response": "test response", "tokens": 100},
        metadata={"cost_usd": 0.002}
    )

    # 序列化到数据库格式
    db_dict = original.to_db_dict(sequence_number=5)

    # 反序列化回对象
    restored = TraceEvent.from_db_dict(db_dict)

    # 验证数据一致
    assert restored.event_id == original.event_id
    assert restored.trace_id == original.trace_id
    assert restored.event_type == original.event_type
    assert restored.timestamp == original.timestamp
    assert restored.data == original.data
    assert restored.metadata == original.metadata


def test_trace_to_db_dict_running():
    """测试Trace.to_db_dict() - running状态"""
    trace = Trace(
        trace_id="trace-001",
        agent_name="test-agent",
        task_id="task-001",
        start_time=1234567890.0,
        end_time=None,  # Running
        events=[],
        metadata={"tags": ["test", "demo"]}
    )

    db_dict = trace.to_db_dict()

    assert db_dict['trace_id'] == "trace-001"
    assert db_dict['agent_name'] == "test-agent"
    assert db_dict['task_id'] == "task-001"
    assert db_dict['start_time'] == 1234567890.0
    assert db_dict['end_time'] is None
    assert db_dict['duration_seconds'] is None
    assert db_dict['status'] == 'running'
    assert db_dict['total_events'] == 0
    assert db_dict['llm_calls_count'] == 0
    assert db_dict['total_tokens'] == 0
    assert db_dict['total_cost_usd'] == 0.0

    # Tags should be JSON string
    assert db_dict['tags'] == json.dumps(["test", "demo"])


def test_trace_to_db_dict_completed():
    """测试Trace.to_db_dict() - completed状态"""
    events = [
        TraceEvent(
            event_id="e1",
            trace_id="trace-001",
            event_type=EventType.PROMPT,
            timestamp=1234567890.0,
            data={"total_tokens": 50, "cost_usd": 0.001}
        ),
        TraceEvent(
            event_id="e2",
            trace_id="trace-001",
            event_type=EventType.MODEL_RESPONSE,
            timestamp=1234567891.0,
            data={"total_tokens": 100, "cost_usd": 0.002}
        ),
        TraceEvent(
            event_id="e3",
            trace_id="trace-001",
            event_type=EventType.TOOL_CALL,
            timestamp=1234567892.0,
            data={"tool": "calculator"}
        )
    ]

    trace = Trace(
        trace_id="trace-001",
        agent_name="test-agent",
        task_id="task-001",
        start_time=1234567890.0,
        end_time=1234567900.0,
        events=events,
        metadata={
            "tags": ["test"],
            "quality_score": 85.5,
            "cost_efficiency": 90.0
        }
    )

    db_dict = trace.to_db_dict()

    assert db_dict['status'] == 'completed'
    assert db_dict['duration_seconds'] == 10.0
    assert db_dict['total_events'] == 3
    assert db_dict['llm_calls_count'] == 2  # 2 LLM events
    assert db_dict['total_tokens'] == 150  # 50 + 100
    assert db_dict['total_cost_usd'] == 0.003  # 0.001 + 0.002
    assert db_dict['quality_score'] == 85.5
    assert db_dict['cost_efficiency'] == 90.0


def test_trace_to_db_dict_failed():
    """测试Trace.to_db_dict() - failed状态"""
    events = [
        TraceEvent(
            event_id="e1",
            trace_id="trace-001",
            event_type=EventType.PROMPT,
            timestamp=1234567890.0,
            data={}
        ),
        TraceEvent(
            event_id="e2",
            trace_id="trace-001",
            event_type=EventType.ERROR,
            timestamp=1234567891.0,
            data={"error": "Connection timeout"}
        )
    ]

    trace = Trace(
        trace_id="trace-001",
        agent_name="test-agent",
        task_id=None,
        start_time=1234567890.0,
        end_time=1234567891.0,
        events=events,
        metadata=None
    )

    db_dict = trace.to_db_dict()

    assert db_dict['status'] == 'failed'
    assert db_dict['total_events'] == 2


def test_trace_from_db_dict():
    """测试Trace.from_db_dict()"""
    db_data = {
        'trace_id': 'trace-001',
        'agent_name': 'test-agent',
        'task_id': 'task-001',
        'start_time': 1234567890.0,
        'end_time': 1234567900.0,
        'duration_seconds': 10.0,
        'status': 'completed',
        'total_events': 3,
        'llm_calls_count': 2,
        'total_tokens': 150,
        'total_cost_usd': 0.003,
        'quality_score': 85.5,
        'cost_efficiency': 90.0,
        'tags': json.dumps(["test", "demo"]),
        'metadata': json.dumps({"custom_field": "value"})
    }

    trace = Trace.from_db_dict(db_data)

    assert trace.trace_id == "trace-001"
    assert trace.agent_name == "test-agent"
    assert trace.task_id == "task-001"
    assert trace.start_time == 1234567890.0
    assert trace.end_time == 1234567900.0
    assert trace.events == []  # No events provided

    # Check metadata
    assert trace.metadata is not None
    assert trace.metadata['tags'] == ["test", "demo"]
    assert trace.metadata['quality_score'] == 85.5
    assert trace.metadata['cost_efficiency'] == 90.0
    assert trace.metadata['custom_field'] == "value"

    # Check database fields in metadata
    assert trace.metadata['_db_status'] == 'completed'
    assert trace.metadata['_db_total_events'] == 3
    assert trace.metadata['_db_llm_calls_count'] == 2
    assert trace.metadata['_db_total_tokens'] == 150
    assert trace.metadata['_db_total_cost_usd'] == 0.003


def test_trace_from_db_dict_with_events():
    """测试Trace.from_db_dict()带事件"""
    db_data = {
        'trace_id': 'trace-001',
        'agent_name': 'test-agent',
        'task_id': None,
        'start_time': 1234567890.0,
        'end_time': 1234567900.0,
        'status': 'completed',
        'total_events': 2,
        'llm_calls_count': 0,
        'total_tokens': 0,
        'total_cost_usd': 0.0,
        'quality_score': None,
        'cost_efficiency': None,
        'tags': None,
        'metadata': None
    }

    events = [
        TraceEvent(
            event_id="e1",
            trace_id="trace-001",
            event_type=EventType.CUSTOM,
            timestamp=1234567890.0,
            data={"message": "event 1"}
        ),
        TraceEvent(
            event_id="e2",
            trace_id="trace-001",
            event_type=EventType.CUSTOM,
            timestamp=1234567891.0,
            data={"message": "event 2"}
        )
    ]

    trace = Trace.from_db_dict(db_data, events=events)

    assert len(trace.events) == 2
    assert trace.events[0].event_id == "e1"
    assert trace.events[1].event_id == "e2"


def test_trace_round_trip():
    """测试Trace序列化和反序列化的完整流程"""
    original_events = [
        TraceEvent(
            event_id="e1",
            trace_id="trace-001",
            event_type=EventType.PROMPT,
            timestamp=1234567890.0,
            data={"prompt": "test", "total_tokens": 50, "cost_usd": 0.001}
        ),
        TraceEvent(
            event_id="e2",
            trace_id="trace-001",
            event_type=EventType.MODEL_RESPONSE,
            timestamp=1234567891.0,
            data={"response": "result", "total_tokens": 100, "cost_usd": 0.002}
        )
    ]

    original = Trace(
        trace_id="trace-001",
        agent_name="test-agent",
        task_id="task-001",
        start_time=1234567890.0,
        end_time=1234567900.0,
        events=original_events,
        metadata={
            "tags": ["test"],
            "quality_score": 85.5,
            "custom": "value"
        }
    )

    # 序列化到数据库格式
    db_dict = original.to_db_dict()

    # 反序列化回对象（不包含events，因为events存在另一个表）
    restored = Trace.from_db_dict(db_dict, events=original_events)

    # 验证核心字段
    assert restored.trace_id == original.trace_id
    assert restored.agent_name == original.agent_name
    assert restored.task_id == original.task_id
    assert restored.start_time == original.start_time
    assert restored.end_time == original.end_time

    # 验证metadata中的原始字段
    assert restored.metadata['tags'] == original.metadata['tags']
    assert restored.metadata['quality_score'] == original.metadata['quality_score']
    assert restored.metadata['custom'] == original.metadata['custom']

    # 验证添加的数据库字段
    assert restored.metadata['_db_status'] == 'completed'
    assert restored.metadata['_db_total_events'] == 2
    assert restored.metadata['_db_llm_calls_count'] == 2
    assert restored.metadata['_db_total_tokens'] == 150
    assert restored.metadata['_db_total_cost_usd'] == 0.003


def test_trace_to_db_dict_no_metadata():
    """测试没有metadata的Trace序列化"""
    trace = Trace(
        trace_id="trace-001",
        agent_name="test-agent",
        task_id=None,
        start_time=1234567890.0,
        end_time=1234567900.0,
        events=[],
        metadata=None
    )

    db_dict = trace.to_db_dict()

    assert db_dict['tags'] is None
    assert db_dict['quality_score'] is None
    assert db_dict['cost_efficiency'] is None
    assert db_dict['metadata'] is None


def test_trace_from_db_dict_null_fields():
    """测试从包含NULL字段的数据库数据反序列化"""
    db_data = {
        'trace_id': 'trace-001',
        'agent_name': 'test-agent',
        'task_id': None,
        'start_time': 1234567890.0,
        'end_time': None,
        'duration_seconds': None,
        'status': 'running',
        'total_events': 0,
        'llm_calls_count': 0,
        'total_tokens': 0,
        'total_cost_usd': 0.0,
        'quality_score': None,
        'cost_efficiency': None,
        'tags': None,
        'metadata': None
    }

    trace = Trace.from_db_dict(db_data)

    assert trace.trace_id == "trace-001"
    assert trace.agent_name == "test-agent"
    assert trace.task_id is None
    assert trace.end_time is None
    assert trace.events == []

    # Metadata should contain database fields even if original metadata was None
    assert trace.metadata is not None
    assert trace.metadata['_db_status'] == 'running'


def test_trace_event_from_db_dict_invalid_json():
    """测试从无效JSON的数据库数据反序列化TraceEvent"""
    db_data = {
        'trace_id': 'trace-001',
        'event_type': 'custom',
        'timestamp': 1234567890.0,
        'sequence_number': 0,
        'data': 'invalid json string'
    }

    # Should not raise, but use fallback
    event = TraceEvent.from_db_dict(db_data)

    assert event.trace_id == "trace-001"
    assert event.event_type == EventType.CUSTOM
    assert event.timestamp == 1234567890.0
    assert event.data == {}  # Fallback to empty dict

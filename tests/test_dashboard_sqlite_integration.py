"""
测试Dashboard与SQLite集成
"""

import pytest
from pathlib import Path

from tigerhill.web.dashboard.data.loader import DataLoader


def test_data_loader_jsonl():
    """测试使用JSONL数据源"""
    loader = DataLoader(storage_path="./test_traces", use_database=False)

    assert loader.data_source_type == "JSONL Files"
    assert loader.trace_store is not None

    # 加载traces
    traces = loader.load_traces(limit=10)
    assert len(traces) > 0
    assert traces[0].trace_id is not None
    assert traces[0].agent_name is not None


def test_data_loader_sqlite():
    """测试使用SQLite数据源"""
    # 确保数据库文件存在
    db_path = "./tigerhill.db"
    if not Path(db_path).exists():
        pytest.skip(f"Database file {db_path} does not exist. Run migration first.")

    loader = DataLoader(use_database=True, db_path=db_path)

    assert loader.data_source_type == "SQLite Database"
    assert loader.trace_store is not None

    # 加载traces
    traces = loader.load_traces(limit=10)
    assert len(traces) > 0
    assert traces[0].trace_id is not None
    assert traces[0].agent_name is not None

    # 验证数据库字段被正确提取
    trace = traces[0]
    assert trace.status in ['running', 'completed', 'failed']
    assert trace.total_events >= 0


def test_data_loader_sqlite_load_trace_detail():
    """测试从SQLite加载trace详情"""
    db_path = "./tigerhill.db"
    if not Path(db_path).exists():
        pytest.skip(f"Database file {db_path} does not exist. Run migration first.")

    loader = DataLoader(use_database=True, db_path=db_path)

    # 先获取一个trace_id
    traces = loader.load_traces(limit=1)
    assert len(traces) > 0

    trace_id = traces[0].trace_id

    # 加载详情
    trace_detail = loader.load_trace_detail(trace_id)
    assert trace_detail is not None


def test_data_loader_sqlite_get_unique_agent_names():
    """测试获取唯一agent名称"""
    db_path = "./tigerhill.db"
    if not Path(db_path).exists():
        pytest.skip(f"Database file {db_path} does not exist. Run migration first.")

    loader = DataLoader(use_database=True, db_path=db_path)

    traces = loader.load_traces()
    agent_names = loader.get_unique_agent_names(traces)

    assert len(agent_names) > 0
    assert all(isinstance(name, str) for name in agent_names)


def test_data_loader_comparison():
    """对比JSONL和SQLite加载的数据"""
    db_path = "./tigerhill.db"
    if not Path(db_path).exists():
        pytest.skip(f"Database file {db_path} does not exist. Run migration first.")

    # 从JSONL加载
    jsonl_loader = DataLoader(storage_path="./test_traces", use_database=False)
    jsonl_traces = jsonl_loader.load_traces()
    jsonl_trace_ids = {t.trace_id for t in jsonl_traces}

    # 从SQLite加载
    sqlite_loader = DataLoader(use_database=True, db_path=db_path)
    sqlite_traces = sqlite_loader.load_traces()
    sqlite_trace_ids = {t.trace_id for t in sqlite_traces}

    # 验证两者包含相同的trace_id
    assert jsonl_trace_ids == sqlite_trace_ids

    # 验证数量一致
    assert len(jsonl_traces) == len(sqlite_traces)

    print(f"\n✅ JSONL和SQLite数据一致性验证通过:")
    print(f"  - JSONL traces: {len(jsonl_traces)}")
    print(f"  - SQLite traces: {len(sqlite_traces)}")
    print(f"  - 共同的trace_ids: {len(jsonl_trace_ids & sqlite_trace_ids)}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])

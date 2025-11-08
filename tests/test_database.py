"""
测试数据库管理器
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
import threading
import time

from tigerhill.storage.database import DatabaseManager, get_db_manager


@pytest.fixture
def temp_db():
    """临时数据库fixture"""
    # 重置单例以避免测试间相互影响
    DatabaseManager._instance = None

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    # 创建新的DatabaseManager实例
    db = DatabaseManager(db_path)

    # 初始化数据库
    schema_path = Path(__file__).parent.parent / "scripts" / "migrations" / "v1_initial_schema.sql"
    db.initialize_database(str(schema_path))

    yield db

    # 清理
    db.close_connection()
    Path(db_path).unlink(missing_ok=True)

    # 再次重置单例
    DatabaseManager._instance = None


def test_singleton_pattern():
    """测试单例模式"""
    db1 = DatabaseManager()
    db2 = DatabaseManager()
    assert db1 is db2


def test_connection_creation(temp_db):
    """测试连接创建"""
    conn = temp_db.get_connection()
    assert conn is not None
    assert isinstance(conn, sqlite3.Connection)


def test_foreign_keys_enabled(temp_db):
    """测试外键约束是否启用"""
    result = temp_db.fetch_one("PRAGMA foreign_keys")
    assert result['foreign_keys'] == 1


def test_wal_mode_enabled(temp_db):
    """测试WAL模式是否启用"""
    result = temp_db.fetch_one("PRAGMA journal_mode")
    assert result['journal_mode'].upper() == 'WAL'


def test_table_exists(temp_db):
    """测试表存在性检查"""
    assert temp_db.table_exists('traces') is True
    assert temp_db.table_exists('events') is True
    assert temp_db.table_exists('captures') is True
    assert temp_db.table_exists('nonexistent_table') is False


def test_get_schema_version(temp_db):
    """测试获取Schema版本"""
    version = temp_db.get_schema_version()
    assert version == 1


def test_insert_record(temp_db):
    """测试插入记录"""
    data = {
        'trace_id': 'test-trace-001',
        'agent_name': 'test-agent',
        'start_time': time.time(),
        'status': 'running'
    }

    record_id = temp_db.insert('traces', data)
    assert record_id > 0

    # 验证记录已插入
    result = temp_db.fetch_one("SELECT * FROM traces WHERE trace_id = ?", ('test-trace-001',))
    assert result is not None
    assert result['trace_id'] == 'test-trace-001'
    assert result['agent_name'] == 'test-agent'
    assert result['status'] == 'running'


def test_update_record(temp_db):
    """测试更新记录"""
    # 先插入
    data = {
        'trace_id': 'test-trace-002',
        'agent_name': 'test-agent',
        'start_time': time.time(),
        'status': 'running'
    }
    temp_db.insert('traces', data)

    # 更新
    update_data = {
        'status': 'completed',
        'end_time': time.time()
    }
    rows_affected = temp_db.update('traces', update_data, 'trace_id = ?', ('test-trace-002',))
    assert rows_affected == 1

    # 验证
    result = temp_db.fetch_one("SELECT * FROM traces WHERE trace_id = ?", ('test-trace-002',))
    assert result['status'] == 'completed'
    assert result['end_time'] is not None


def test_delete_record(temp_db):
    """测试删除记录"""
    # 先插入
    data = {
        'trace_id': 'test-trace-003',
        'agent_name': 'test-agent',
        'start_time': time.time(),
        'status': 'running'
    }
    temp_db.insert('traces', data)

    # 删除
    rows_affected = temp_db.delete('traces', 'trace_id = ?', ('test-trace-003',))
    assert rows_affected == 1

    # 验证
    result = temp_db.fetch_one("SELECT * FROM traces WHERE trace_id = ?", ('test-trace-003',))
    assert result is None


def test_fetch_one(temp_db):
    """测试查询单条记录"""
    # 插入测试数据
    data = {
        'trace_id': 'test-trace-004',
        'agent_name': 'test-agent',
        'start_time': time.time(),
        'status': 'running'
    }
    temp_db.insert('traces', data)

    # 查询
    result = temp_db.fetch_one("SELECT * FROM traces WHERE trace_id = ?", ('test-trace-004',))
    assert result is not None
    assert result['trace_id'] == 'test-trace-004'

    # 查询不存在的记录
    result = temp_db.fetch_one("SELECT * FROM traces WHERE trace_id = ?", ('nonexistent',))
    assert result is None


def test_fetch_all(temp_db):
    """测试查询多条记录"""
    # 插入多条测试数据
    for i in range(5):
        data = {
            'trace_id': f'test-trace-{i:03d}',
            'agent_name': 'test-agent',
            'start_time': time.time(),
            'status': 'running'
        }
        temp_db.insert('traces', data)

    # 查询所有
    results = temp_db.fetch_all("SELECT * FROM traces WHERE agent_name = ?", ('test-agent',))
    assert len(results) >= 5

    # 验证返回的是字典列表
    for result in results:
        assert isinstance(result, dict)
        assert 'trace_id' in result


def test_execute_many(temp_db):
    """测试批量执行"""
    # 批量插入
    params_list = [
        ('test-trace-batch-001', 'batch-agent', time.time(), 'running'),
        ('test-trace-batch-002', 'batch-agent', time.time(), 'running'),
        ('test-trace-batch-003', 'batch-agent', time.time(), 'running'),
    ]

    sql = "INSERT INTO traces (trace_id, agent_name, start_time, status) VALUES (?, ?, ?, ?)"
    temp_db.execute_many(sql, params_list)

    # 验证
    results = temp_db.fetch_all("SELECT * FROM traces WHERE agent_name = ?", ('batch-agent',))
    assert len(results) == 3


def test_transaction_commit(temp_db):
    """测试事务提交"""
    with temp_db.transaction():
        temp_db.execute(
            "INSERT INTO traces (trace_id, agent_name, start_time, status) VALUES (?, ?, ?, ?)",
            ('test-trace-tx-001', 'tx-agent', time.time(), 'running')
        )

    # 验证事务已提交
    result = temp_db.fetch_one("SELECT * FROM traces WHERE trace_id = ?", ('test-trace-tx-001',))
    assert result is not None


def test_transaction_rollback(temp_db):
    """测试事务回滚"""
    try:
        with temp_db.transaction():
            temp_db.execute(
                "INSERT INTO traces (trace_id, agent_name, start_time, status) VALUES (?, ?, ?, ?)",
                ('test-trace-tx-002', 'tx-agent', time.time(), 'running')
            )
            # 故意触发错误
            raise ValueError("Test rollback")
    except ValueError:
        pass

    # 验证事务已回滚
    result = temp_db.fetch_one("SELECT * FROM traces WHERE trace_id = ?", ('test-trace-tx-002',))
    assert result is None


def test_foreign_key_cascade(temp_db):
    """测试外键级联删除"""
    # 插入trace
    trace_data = {
        'trace_id': 'test-trace-fk-001',
        'agent_name': 'fk-agent',
        'start_time': time.time(),
        'status': 'running'
    }
    temp_db.insert('traces', trace_data)

    # 插入events
    for i in range(3):
        event_data = {
            'trace_id': 'test-trace-fk-001',
            'event_type': 'test_event',
            'timestamp': time.time(),
            'sequence_number': i,
            'data': '{"test": true}'
        }
        temp_db.insert('events', event_data)

    # 验证events已插入
    events = temp_db.fetch_all("SELECT * FROM events WHERE trace_id = ?", ('test-trace-fk-001',))
    assert len(events) == 3

    # 删除trace
    temp_db.delete('traces', 'trace_id = ?', ('test-trace-fk-001',))

    # 验证events被级联删除
    events = temp_db.fetch_all("SELECT * FROM events WHERE trace_id = ?", ('test-trace-fk-001',))
    assert len(events) == 0


def test_trigger_event_count(temp_db):
    """测试事件计数触发器"""
    # 插入trace
    trace_data = {
        'trace_id': 'test-trace-trigger-001',
        'agent_name': 'trigger-agent',
        'start_time': time.time(),
        'status': 'running'
    }
    temp_db.insert('traces', trace_data)

    # 初始total_events应该为0
    result = temp_db.fetch_one("SELECT total_events FROM traces WHERE trace_id = ?", ('test-trace-trigger-001',))
    assert result['total_events'] == 0

    # 插入3个events
    for i in range(3):
        event_data = {
            'trace_id': 'test-trace-trigger-001',
            'event_type': 'test_event',
            'timestamp': time.time(),
            'sequence_number': i,
            'data': '{"test": true}'
        }
        temp_db.insert('events', event_data)

    # total_events应该自动增加到3
    result = temp_db.fetch_one("SELECT total_events FROM traces WHERE trace_id = ?", ('test-trace-trigger-001',))
    assert result['total_events'] == 3

    # 删除1个event
    temp_db.execute("DELETE FROM events WHERE trace_id = ? AND sequence_number = ?", ('test-trace-trigger-001', 0))

    # total_events应该自动减少到2
    result = temp_db.fetch_one("SELECT total_events FROM traces WHERE trace_id = ?", ('test-trace-trigger-001',))
    assert result['total_events'] == 2


def test_thread_safety(temp_db):
    """测试线程安全"""
    results = []
    errors = []

    def insert_records(thread_id):
        try:
            for i in range(10):
                data = {
                    'trace_id': f'test-trace-thread-{thread_id}-{i:03d}',
                    'agent_name': f'thread-agent-{thread_id}',
                    'start_time': time.time(),
                    'status': 'running'
                }
                temp_db.insert('traces', data)
            results.append(thread_id)
        except Exception as e:
            errors.append((thread_id, str(e)))

    # 创建5个线程并发插入
    threads = []
    for i in range(5):
        t = threading.Thread(target=insert_records, args=(i,))
        threads.append(t)
        t.start()

    # 等待所有线程完成
    for t in threads:
        t.join()

    # 验证没有错误
    assert len(errors) == 0, f"Errors occurred: {errors}"
    assert len(results) == 5

    # 验证所有记录都已插入
    all_records = temp_db.fetch_all("SELECT * FROM traces WHERE agent_name LIKE 'thread-agent-%'")
    assert len(all_records) == 50  # 5 threads * 10 records


def test_get_db_manager():
    """测试全局数据库管理器函数"""
    db1 = get_db_manager()
    db2 = get_db_manager()
    assert db1 is db2


def test_constraint_check_status(temp_db):
    """测试CHECK约束 - status字段"""
    # 合法的status值
    for status in ['running', 'completed', 'failed']:
        data = {
            'trace_id': f'test-trace-status-{status}',
            'agent_name': 'test-agent',
            'start_time': time.time(),
            'status': status
        }
        record_id = temp_db.insert('traces', data)
        assert record_id > 0

    # 非法的status值应该抛出异常
    with pytest.raises(sqlite3.IntegrityError):
        data = {
            'trace_id': 'test-trace-status-invalid',
            'agent_name': 'test-agent',
            'start_time': time.time(),
            'status': 'invalid_status'
        }
        temp_db.insert('traces', data)


def test_constraint_check_non_negative(temp_db):
    """测试CHECK约束 - 非负数字段"""
    # 合法的total_events值
    data = {
        'trace_id': 'test-trace-nonneg-001',
        'agent_name': 'test-agent',
        'start_time': time.time(),
        'status': 'running',
        'total_events': 0
    }
    record_id = temp_db.insert('traces', data)
    assert record_id > 0

    # 负数应该抛出异常
    with pytest.raises(sqlite3.IntegrityError):
        data = {
            'trace_id': 'test-trace-nonneg-002',
            'agent_name': 'test-agent',
            'start_time': time.time(),
            'status': 'running',
            'total_events': -1
        }
        temp_db.insert('traces', data)


def test_unique_constraint(temp_db):
    """测试UNIQUE约束"""
    # 插入第一条记录
    data = {
        'trace_id': 'test-trace-unique-001',
        'agent_name': 'test-agent',
        'start_time': time.time(),
        'status': 'running'
    }
    temp_db.insert('traces', data)

    # 尝试插入相同trace_id应该抛出异常
    with pytest.raises(sqlite3.IntegrityError):
        temp_db.insert('traces', data)

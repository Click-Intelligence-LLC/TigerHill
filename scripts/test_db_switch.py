#!/usr/bin/env python3
"""
测试数据库切换是否正常工作
验证DatabaseManager单例清除机制
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tigerhill.storage.database import DatabaseManager
from tigerhill.storage.sqlite_trace_store import SQLiteTraceStore

def test_database_switch():
    """测试数据库切换"""

    print("=" * 60)
    print("测试1: 连接第一个数据库 (swarm.db)")
    print("=" * 60)

    # 第一次连接
    store1 = SQLiteTraceStore(db_path="./swarm.db", auto_init=False)
    traces1 = store1.query_traces()
    print(f"✅ 第一个数据库: swarm.db")
    print(f"   Traces数量: {len(traces1)}")
    print(f"   DatabaseManager实例ID: {id(store1.db)}")
    print(f"   DatabaseManager路径: {store1.db.db_path}")

    print("\n" + "=" * 60)
    print("测试2: 不清除单例，切换到第二个数据库 (tigerhill.db)")
    print("=" * 60)

    # 不清除单例，直接创建新store
    store2 = SQLiteTraceStore(db_path="./tigerhill.db", auto_init=False)
    traces2 = store2.query_traces()
    print(f"✅ 第二个数据库: tigerhill.db")
    print(f"   Traces数量: {len(traces2)}")
    print(f"   DatabaseManager实例ID: {id(store2.db)}")
    print(f"   DatabaseManager路径: {store2.db.db_path}")

    if id(store1.db) == id(store2.db):
        print(f"⚠️  警告: 两个store使用同一个DatabaseManager实例！")
        print(f"   这就是为什么数据不更新的原因！")

    if len(traces2) == len(traces1):
        print(f"❌ 错误: traces数量相同，数据没有更新！")
    else:
        print(f"✅ 正确: traces数量不同")

    print("\n" + "=" * 60)
    print("测试3: 清除单例，重新连接")
    print("=" * 60)

    # 清除单例
    DatabaseManager._instance = None

    # 重新创建store
    store3 = SQLiteTraceStore(db_path="./tigerhill.db", auto_init=False)
    traces3 = store3.query_traces()
    print(f"✅ 第三个数据库: tigerhill.db (清除单例后)")
    print(f"   Traces数量: {len(traces3)}")
    print(f"   DatabaseManager实例ID: {id(store3.db)}")
    print(f"   DatabaseManager路径: {store3.db.db_path}")

    if id(store3.db) != id(store1.db):
        print(f"✅ 正确: 创建了新的DatabaseManager实例")

    print("\n" + "=" * 60)
    print("测试4: 切换回第一个数据库")
    print("=" * 60)

    # 清除单例
    DatabaseManager._instance = None

    # 切换回swarm.db
    store4 = SQLiteTraceStore(db_path="./swarm.db", auto_init=False)
    traces4 = store4.query_traces()
    print(f"✅ 第四个数据库: swarm.db (清除单例后)")
    print(f"   Traces数量: {len(traces4)}")
    print(f"   DatabaseManager实例ID: {id(store4.db)}")
    print(f"   DatabaseManager路径: {store4.db.db_path}")

    if len(traces4) == len(traces1):
        print(f"✅ 正确: 切换回原数据库，数据一致")

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"swarm.db traces: {len(traces1)}")
    print(f"tigerhill.db traces (不清除单例): {len(traces2)}")
    print(f"tigerhill.db traces (清除单例): {len(traces3)}")
    print(f"swarm.db traces (清除单例): {len(traces4)}")

    if len(traces1) != len(traces3):
        print(f"\n✅ 测试通过: 清除单例后能够正确切换数据库")
        return True
    else:
        print(f"\n❌ 测试失败: 数据仍然不正确")
        return False

if __name__ == "__main__":
    try:
        success = test_database_switch()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

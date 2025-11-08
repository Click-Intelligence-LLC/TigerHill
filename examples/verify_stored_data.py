#!/usr/bin/env python3
"""
验证存储的数据
查看SQLite数据库中的数据
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from tigerhill.storage.sqlite_trace_store import SQLiteTraceStore


def main():
    db_path = "./tigerhill_validation.db"

    if not Path(db_path).exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        print("请先运行: python3 examples/demo_agent_with_tracing.py")
        return

    print("=" * 60)
    print("验证存储的数据")
    print("=" * 60)
    print()

    # 连接数据库
    store = SQLiteTraceStore(db_path=db_path, auto_init=False)

    # 查询所有traces
    traces = store.query_traces()
    print(f"✅ 找到 {len(traces)} 个traces\n")

    for i, trace in enumerate(traces, 1):
        print(f"{i}. Trace ID: {trace.trace_id[:8]}...")
        print(f"   Agent: {trace.agent_name}")
        print(f"   状态: {trace.metadata['_db_status']}")
        print(f"   Events: {trace.metadata['_db_total_events']}")
        print(f"   Tokens: {trace.metadata['_db_total_tokens']}")
        print(f"   成本: ${trace.metadata['_db_total_cost_usd']:.4f}")
        print()

    # 查看第一个trace的详情
    if traces:
        print("=" * 60)
        print("详细查看第一个Trace")
        print("=" * 60)
        trace_id = traces[0].trace_id
        trace = store.get_trace(trace_id, include_events=True)

        print(f"Trace ID: {trace_id}")
        print(f"Agent: {trace.agent_name}")
        print(f"开始时间: {trace.start_time}")
        print(f"结束时间: {trace.end_time}")
        print(f"Events数量: {len(trace.events)}")
        print()

        print("Events列表:")
        for i, event in enumerate(trace.events, 1):
            print(f"  {i}. {event.event_type.value} @ {event.timestamp}")
            if hasattr(event.data, 'get'):
                content = event.data.get('content', '')
                if content:
                    print(f"     内容: {content[:50]}...")
        print()

    print("=" * 60)
    print("✅ 验证完成")
    print("=" * 60)


if __name__ == "__main__":
    main()

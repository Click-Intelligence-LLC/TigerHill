#!/usr/bin/env python3
"""
演示Agent - 完整的Trace记录示例
展示如何在实际Agent中集成TigerHill Trace记录
"""

import time
import random
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from tigerhill.storage.sqlite_trace_store import SQLiteTraceStore
from tigerhill.storage.trace_store import EventType


class DemoLLMAgent:
    """模拟的LLM Agent - 展示Trace集成"""

    def __init__(self, name: str, trace_store: SQLiteTraceStore):
        self.name = name
        self.store = trace_store

    def run_task(self, task: str, simulate_llm_calls: int = 3):
        """执行任务并记录trace

        Args:
            task: 任务描述
            simulate_llm_calls: 模拟的LLM调用次数
        """
        # 1. 开始trace
        trace_id = self.store.start_trace(
            agent_name=self.name,
            task_id=f"task-{int(time.time())}",
            metadata={
                "task_description": task,
                "tags": ["demo", "validation"],
                "priority": "high"
            }
        )

        print(f"✅ 开始任务: {task}")
        print(f"   Trace ID: {trace_id}")

        try:
            # 2. 模拟多次LLM调用
            for i in range(simulate_llm_calls):
                self._simulate_llm_call(trace_id, i)

            # 3. 模拟工具调用
            self._simulate_tool_calls(trace_id)

            print(f"✅ 任务完成")

        except Exception as e:
            # 记录错误
            self.store.write_event(
                {
                    "type": "error",
                    "error_message": str(e),
                    "error_type": type(e).__name__
                },
                trace_id=trace_id,
                event_type=EventType.ERROR
            )
            print(f"❌ 任务失败: {e}")

        finally:
            # 4. 结束trace
            self.store.end_trace(trace_id)

        return trace_id

    def _simulate_llm_call(self, trace_id: str, call_index: int):
        """模拟LLM调用"""
        # 模拟Prompt
        prompt_tokens = random.randint(50, 200)
        prompt = f"This is prompt #{call_index + 1} for the task"

        self.store.write_event(
            {
                "type": "prompt",
                "content": prompt,
                "model": "gpt-4",
                "temperature": 0.7,
                "total_tokens": prompt_tokens,
                "cost_usd": prompt_tokens * 0.00003  # $0.03 per 1K tokens
            },
            trace_id=trace_id,
            event_type=EventType.PROMPT
        )

        # 模拟处理时间
        time.sleep(0.1)

        # 模拟Response
        completion_tokens = random.randint(100, 300)
        response = f"This is response #{call_index + 1} from the model"

        self.store.write_event(
            {
                "type": "model_response",
                "content": response,
                "model": "gpt-4",
                "finish_reason": "stop",
                "total_tokens": completion_tokens,
                "cost_usd": completion_tokens * 0.00006  # $0.06 per 1K tokens
            },
            trace_id=trace_id,
            event_type=EventType.MODEL_RESPONSE
        )

        print(f"   📝 LLM调用 #{call_index + 1}: {prompt_tokens + completion_tokens} tokens")

    def _simulate_tool_calls(self, trace_id: str):
        """模拟工具调用"""
        tools = ["calculator", "search", "database_query"]

        for tool in random.sample(tools, k=2):
            # 工具调用
            self.store.write_event(
                {
                    "type": "tool_call",
                    "tool_name": tool,
                    "arguments": {"query": f"test {tool}"}
                },
                trace_id=trace_id,
                event_type=EventType.TOOL_CALL
            )

            time.sleep(0.05)

            # 工具结果
            self.store.write_event(
                {
                    "type": "tool_result",
                    "tool_name": tool,
                    "result": f"Result from {tool}",
                    "success": True
                },
                trace_id=trace_id,
                event_type=EventType.TOOL_RESULT
            )

            print(f"   🔧 工具调用: {tool}")


def main():
    """主函数 - 运行演示"""
    print("=" * 60)
    print("TigerHill 端到端验证 - Agent执行演示")
    print("=" * 60)
    print()

    # 1. 初始化TraceStore（使用SQLite）
    db_path = "./tigerhill_validation.db"
    store = SQLiteTraceStore(db_path=db_path, auto_init=True)
    print(f"✅ 初始化TraceStore: {db_path}")
    print()

    # 2. 创建Agent
    agent = DemoLLMAgent(name="validation-agent", trace_store=store)

    # 3. 运行多个任务
    tasks = [
        "分析用户反馈并生成报告",
        "总结技术文档的关键点",
        "生成测试用例"
    ]

    trace_ids = []
    for i, task in enumerate(tasks, 1):
        print(f"--- 任务 {i}/{len(tasks)} ---")
        trace_id = agent.run_task(task, simulate_llm_calls=random.randint(2, 4))
        trace_ids.append(trace_id)
        print()
        time.sleep(0.2)

    # 4. 显示统计信息
    print("=" * 60)
    print("执行统计")
    print("=" * 60)
    stats = store.get_statistics()
    print(f"总Traces: {stats['total_traces']}")
    print(f"总Events: {stats['total_events']}")
    print(f"LLM调用: {stats['total_llm_calls']}")
    print(f"总Tokens: {stats['total_tokens']}")
    print(f"总成本: ${stats['total_cost_usd']:.4f}")
    print(f"状态分布: {stats['status_counts']}")
    print()

    # 5. 显示每个trace的摘要
    print("=" * 60)
    print("Trace摘要")
    print("=" * 60)
    for i, trace_id in enumerate(trace_ids, 1):
        summary = store.get_summary(trace_id)
        print(f"{i}. {summary['trace_id'][:8]}...")
        print(f"   Agent: {summary['agent_name']}")
        print(f"   状态: {summary['status']}")
        print(f"   Events: {summary['total_events']}")
        print(f"   LLM调用: {summary['llm_calls_count']}")
        print(f"   Tokens: {summary['total_tokens']}")
        print(f"   成本: ${summary['total_cost_usd']:.4f}")
        print(f"   事件类型: {summary['event_counts']}")
        print()

    print("=" * 60)
    print("✅ 演示完成！")
    print("=" * 60)
    print()
    print("下一步:")
    print("1. 数据已保存到: ./tigerhill_validation.db")
    print("2. 运行Dashboard查看: PYTHONPATH=. streamlit run tigerhill/web/dashboard/app.py")
    print("3. 在Dashboard中:")
    print("   - 侧边栏选择 'SQLite Database'")
    print("   - 数据库路径填写: ./tigerhill_validation.db")
    print("   - 查看traces列表和详情")
    print()


if __name__ == "__main__":
    main()

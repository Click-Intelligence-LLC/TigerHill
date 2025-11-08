"""
TigerHill Trace Viewer - 友好的追踪查看工具

提供格式化的 trace 查看，清晰展示 prompt、response 和评估结果。
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class TraceViewer:
    """Trace 查看器，提供格式化的追踪展示"""

    def __init__(self, storage_path: str = "./traces"):
        """
        初始化 Trace 查看器

        Args:
            storage_path: Trace 存储路径
        """
        self.storage_path = Path(storage_path)

    def list_traces(self, agent_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出所有 trace

        Args:
            agent_name: 过滤特定 agent（可选）

        Returns:
            Trace 列表，包含基本信息
        """
        traces = []

        if not self.storage_path.exists():
            return traces

        for trace_file in self.storage_path.glob("**/*.json"):
            try:
                with open(trace_file, "r", encoding="utf-8") as f:
                    trace = json.load(f)

                if agent_name and trace.get("agent_name") != agent_name:
                    continue

                traces.append({
                    "trace_id": trace.get("trace_id"),
                    "agent_name": trace.get("agent_name"),
                    "task_id": trace.get("task_id"),
                    "start_time": trace.get("start_time"),
                    "duration": trace.get("end_time", 0) - trace.get("start_time", 0),
                    "num_events": len(trace.get("events", [])),
                    "file_path": str(trace_file)
                })
            except Exception as e:
                print(f"Warning: Failed to read {trace_file}: {e}")

        # 按时间倒序排序
        traces.sort(key=lambda x: x.get("start_time", 0), reverse=True)
        return traces

    def view_trace(self, trace_id: str, verbose: bool = False) -> None:
        """
        查看单个 trace 的详细信息

        Args:
            trace_id: Trace ID
            verbose: 是否显示详细的事件数据
        """
        trace_file = self._find_trace_file(trace_id)
        if not trace_file:
            print(f"❌ Trace {trace_id} not found")
            return

        with open(trace_file, "r", encoding="utf-8") as f:
            trace = json.load(f)

        self._print_trace_summary(trace)
        self._print_trace_events(trace, verbose)

    def view_conversation(self, trace_id: str, verbose: bool = False) -> None:
        """
        以对话格式查看 trace（只显示 prompt 和 response）

        Args:
            trace_id: Trace ID
            verbose: 是否显示完整输出
        """
        trace_file = self._find_trace_file(trace_id)
        if not trace_file:
            print(f"❌ Trace {trace_id} not found")
            return

        with open(trace_file, "r", encoding="utf-8") as f:
            trace = json.load(f)

        print("=" * 80)
        print(f"📝 Conversation View - {trace.get('agent_name', 'Unknown')}")
        print(f"🆔 Trace ID: {trace.get('trace_id')}")
        print(f"🕐 Time: {self._format_timestamp(trace.get('start_time'))}")
        print("=" * 80)
        print()

        for event in trace.get("events", []):
            event_type = event.get("event_type")
            data = event.get("data", {})

            if event_type == "prompt":
                print("🤔 USER PROMPT:")
                print("-" * 80)
                print(data.get("content", ""))
                print()

            elif event_type == "model_response":
                print("🤖 AGENT RESPONSE:")
                print("-" * 80)
                response_text = data.get("text", "")
                # 限制输出长度，避免过长
                if len(response_text) > 2000 and not verbose:
                    print(response_text[:2000])
                    print(f"\n... [truncated, total {len(response_text)} chars]")
                else:
                    print(response_text)
                print()

            elif event_type == "custom" and data.get("type") == "evaluation":
                print("📊 EVALUATION RESULTS:")
                print("-" * 80)
                print(f"✅ Passed: {data.get('passed')}/{data.get('total')}")
                print(f"⏱️  Duration: {data.get('duration_seconds', 0):.2f}s")
                print()

    def _find_trace_file(self, trace_id: str) -> Optional[Path]:
        """查找 trace 文件"""
        for trace_file in self.storage_path.glob(f"**/trace_{trace_id}_*.json"):
            return trace_file
        return None

    def _print_trace_summary(self, trace: Dict[str, Any]) -> None:
        """打印 trace 摘要"""
        print("=" * 80)
        print("📊 TRACE SUMMARY")
        print("=" * 80)
        print(f"🆔 Trace ID:    {trace.get('trace_id')}")
        print(f"🤖 Agent:       {trace.get('agent_name')}")
        print(f"📝 Task ID:     {trace.get('task_id', 'N/A')}")
        print(f"🕐 Start:       {self._format_timestamp(trace.get('start_time'))}")
        print(f"🕐 End:         {self._format_timestamp(trace.get('end_time'))}")

        duration = trace.get("end_time", 0) - trace.get("start_time", 0)
        print(f"⏱️  Duration:    {duration:.2f}s")
        print(f"📦 Events:      {len(trace.get('events', []))}")
        print("=" * 80)
        print()

    def _print_trace_events(self, trace: Dict[str, Any], verbose: bool) -> None:
        """打印 trace 事件"""
        print("📋 EVENTS")
        print("=" * 80)

        for i, event in enumerate(trace.get("events", []), 1):
            event_type = event.get("event_type")
            data = event.get("data", {})

            print(f"\n[{i}] {event_type.upper()}")
            print(f"    Timestamp: {self._format_timestamp(event.get('timestamp'))}")

            if event_type == "prompt":
                content = data.get("content", "")
                print(f"    Content: {content[:100]}..." if len(content) > 100 else f"    Content: {content}")

            elif event_type == "model_response":
                text = data.get("text", "")
                adapter = data.get("adapter_type", "Unknown")
                print(f"    Adapter: {adapter}")
                print(f"    Length: {len(text)} chars")
                if verbose:
                    print(f"    Text: {text}")

            elif event_type == "custom":
                if verbose:
                    print(f"    Data: {json.dumps(data, indent=2)}")
                else:
                    print(f"    Data: {list(data.keys())}")

            elif event_type == "error":
                print(f"    ❌ Error: {data.get('error')}")
                print(f"    Type: {data.get('error_type')}")

        print()

    def _format_timestamp(self, timestamp: Optional[float]) -> str:
        """格式化时间戳"""
        if not timestamp:
            return "N/A"
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def main():
    """命令行接口"""
    import argparse

    parser = argparse.ArgumentParser(description="TigerHill Trace Viewer")
    parser.add_argument("--storage", default="./test_traces/gemini_cli", help="Trace 存储路径")
    parser.add_argument("--list", action="store_true", help="列出所有 trace")
    parser.add_argument("--view", help="查看指定 trace (trace_id)")
    parser.add_argument("--conversation", help="以对话格式查看 trace (trace_id)")
    parser.add_argument("--agent", help="过滤特定 agent")
    parser.add_argument("--verbose", action="store_true", help="显示详细信息")

    args = parser.parse_args()

    viewer = TraceViewer(storage_path=args.storage)

    if args.list:
        traces = viewer.list_traces(agent_name=args.agent)
        print(f"\n📊 Found {len(traces)} trace(s):\n")
        for trace in traces:
            print(f"🆔 {trace['trace_id'][:8]}... | "
                  f"🤖 {trace['agent_name']:<15} | "
                  f"📝 {trace.get('task_id', 'N/A'):<10} | "
                  f"⏱️  {trace['duration']:.1f}s | "
                  f"📦 {trace['num_events']} events")
        print()

    elif args.view:
        viewer.view_trace(args.view, verbose=args.verbose)

    elif args.conversation:
        viewer.view_conversation(args.conversation, verbose=args.verbose)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

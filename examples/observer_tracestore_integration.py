"""
TigerHill Observer SDK - TraceStore Integration Example

演示如何将 Observer 捕获的数据导出到 TigerHill TraceStore，
实现 Debug Mode 与 Test Mode 的无缝集成。

使用场景：
- 开发阶段使用 Observer 捕获 prompt/response
- 将捕获数据导出为测试用例
- 在 CI/CD 中重放和验证

使用步骤：
1. 先运行 observer_python_basic.py 生成捕获数据
2. 运行: python examples/observer_tracestore_integration.py
"""

import json
from pathlib import Path
from tigerhill.observer import PromptCapture
from tigerhill.trace_store import TraceStore


def load_latest_capture(storage_path="./prompt_captures"):
    """加载最新的捕获文件"""
    capture_dir = Path(storage_path)
    if not capture_dir.exists():
        print(f"Error: {storage_path} does not exist")
        return None, None

    capture_files = list(capture_dir.glob("capture_*.json"))
    if not capture_files:
        print(f"Error: No capture files found in {storage_path}")
        return None, None

    latest_file = max(capture_files, key=lambda p: p.stat().st_mtime)
    print(f"📂 Loading capture from: {latest_file}")

    with open(latest_file, "r", encoding="utf-8") as f:
        capture_data = json.load(f)

    return capture_data, capture_data["capture_id"]


def main():
    print("=" * 80)
    print("🔄 TigerHill Observer → TraceStore Integration")
    print("=" * 80)

    # 1. 加载捕获数据
    print("\n[Step 1] Loading captured data...")
    capture_data, capture_id = load_latest_capture()
    if not capture_data:
        print("\n❌ No capture data found. Please run observer_python_basic.py first.")
        return

    print(f"✅ Loaded capture: {capture_id}")
    print(f"   Agent: {capture_data['agent_name']}")
    print(f"   Requests: {len(capture_data['requests'])}")
    print(f"   Responses: {len(capture_data['responses'])}")
    print(f"   Duration: {capture_data['duration']:.2f}s")

    # 2. 创建 TraceStore
    print("\n[Step 2] Creating TraceStore...")
    trace_store = TraceStore(storage_path="./traces_from_observer")
    print(f"✅ TraceStore created at: ./traces_from_observer")

    # 3. 创建 PromptCapture 并加载数据
    print("\n[Step 3] Preparing export...")
    capture = PromptCapture(storage_path="./prompt_captures")
    capture.captures[capture_id] = capture_data

    # 4. 导出到 TraceStore
    print("\n[Step 4] Exporting to TraceStore...")
    trace_id = capture.export_to_trace_store(
        capture_id=capture_id,
        trace_store=trace_store,
        agent_name=capture_data['agent_name']
    )

    print(f"✅ Exported to trace: {trace_id}")

    # 5. 验证导出的 trace
    print("\n[Step 5] Verifying exported trace...")
    trace = trace_store.get_trace(trace_id)

    if trace:
        print(f"✅ Trace verified:")
        print(f"   Trace ID: {trace['trace_id']}")
        print(f"   Agent: {trace['agent_name']}")
        print(f"   Task ID: {trace['task_id']}")
        print(f"   Events: {len(trace['events'])}")

        # 统计事件类型
        event_types = {}
        for event in trace['events']:
            event_type = event.get('type', 'unknown')
            event_types[event_type] = event_types.get(event_type, 0) + 1

        print(f"   Event types:")
        for event_type, count in event_types.items():
            print(f"     - {event_type}: {count}")

    # 6. 演示如何查询导出的 traces
    print("\n[Step 6] Querying traces...")
    all_traces = trace_store.query_traces(agent_name=capture_data['agent_name'])
    print(f"✅ Found {len(all_traces)} traces for agent '{capture_data['agent_name']}'")

    # 7. 生成测试用例建议
    print("\n[Step 7] Generating test case recommendations...")
    print("\n" + "=" * 80)
    print("🧪 Test Case Generation Recommendations:")
    print("=" * 80)

    for i, request in enumerate(capture_data['requests'], 1):
        print(f"\n[Test Case {i}]")
        print(f"Input prompt: {request.get('prompt', 'N/A')[:80]}...")
        print(f"Model: {request.get('model', 'N/A')}")

        # 找到对应的响应
        if i <= len(capture_data['responses']):
            response = capture_data['responses'][i - 1]
            print(f"Expected output: {response.get('text', 'N/A')[:80]}...")

            # 建议的断言
            print(f"\nSuggested assertions:")
            print(f"  - response_length_min: {len(response.get('text', ''))}")
            print(f"  - contains: [<key concepts from response>]")

            if response.get('usage'):
                usage = response['usage']
                print(f"  - token_usage_max: {usage.get('total_tokens', 0) * 1.2:.0f}")

    # 8. 使用示例
    print("\n" + "=" * 80)
    print("📝 Usage in TigerHill Tests:")
    print("=" * 80)
    print("""
Example test configuration:

```python
from tigerhill.adapters import UniversalAgentTester
from tigerhill.trace_store import TraceStore

# Load trace
trace_store = TraceStore(storage_path="./traces_from_observer")
trace = trace_store.get_trace("{trace_id}")

# Create test case from trace
test_case = {{
    "name": "test_from_observer_capture",
    "input": trace['events'][0]['data']['prompt'],
    "expected": {{
        "contains": ["key", "concepts"],
        "response_length_min": 100,
        "response_time_max": 10.0
    }}
}}

# Run test
tester = UniversalAgentTester(adapter=your_adapter, trace_store=trace_store)
result = tester.test(test_case)
```
""".format(trace_id=trace_id))

    # 9. 总结
    print("\n" + "=" * 80)
    print("✅ Integration Complete!")
    print("=" * 80)
    print(f"""
Summary:
- Captured data: ./prompt_captures/capture_{capture_id}_*.json
- Trace data: ./traces_from_observer/{trace_id}.json
- Total requests: {len(capture_data['requests'])}
- Total responses: {len(capture_data['responses'])}

Next Steps:
1. Review the exported trace data
2. Create test cases based on captured prompts/responses
3. Integrate into your CI/CD pipeline
4. Use for regression testing

Benefits:
✨ No manual test case creation needed
✨ Real production prompts captured
✨ Automatic trace generation
✨ Seamless debug-to-test workflow
""")

    print("=" * 80)


if __name__ == "__main__":
    main()

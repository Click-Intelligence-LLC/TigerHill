"""
TigerHill Observer SDK - Demo (无需 API key)

演示 Observer SDK 的核心功能，不需要真实的 Google API key。
使用 Mock 数据展示完整的捕获、分析和优化建议流程。
"""

from tigerhill.observer import PromptCapture, PromptAnalyzer


def create_mock_capture_data():
    """创建模拟的捕获数据用于演示"""
    return {
        "capture_id": "demo-12345",
        "agent_name": "demo_agent",
        "start_time": 1234567890.0,
        "end_time": 1234567895.5,
        "duration": 5.5,
        "metadata": {
            "task": "generate_fibonacci",
            "version": "1.0"
        },
        "requests": [
            {
                "request_id": "req-001",
                "timestamp": 1234567890.5,
                "model": "gemini-2.5-flash",
                "prompt": "Write a Python function to calculate fibonacci numbers",
                "system_prompt": "You are a helpful coding assistant",
                "temperature": 0.7,
                "tools": [
                    {"name": "search", "description": "Search documentation"},
                    {"name": "calculator", "description": "Calculate numbers"}
                ]
            },
            {
                "request_id": "req-002",
                "timestamp": 1234567893.0,
                "model": "gemini-2.5-flash",
                "prompt": "Can you optimize the fibonacci function with memoization?"
            }
        ],
        "responses": [
            {
                "response_id": "res-001",
                "timestamp": 1234567892.0,
                "text": """Here is a fibonacci function:

```python
def fib(n):
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)
```

This function uses recursion to calculate fibonacci numbers.""",
                "finish_reason": "stop",
                "usage": {
                    "prompt_tokens": 50,
                    "completion_tokens": 100,
                    "total_tokens": 150
                },
                "tool_calls": [
                    {"name": "search", "arguments": {"query": "fibonacci algorithm"}}
                ]
            },
            {
                "response_id": "res-002",
                "timestamp": 1234567895.0,
                "text": """Sure! Here's an optimized version with memoization:

```python
def fib(n, memo={}):
    if n <= 1:
        return n
    if n not in memo:
        memo[n] = fib(n-1, memo) + fib(n-2, memo)
    return memo[n]
```

This version caches results to avoid redundant calculations.""",
                "finish_reason": "stop",
                "usage": {
                    "prompt_tokens": 80,
                    "completion_tokens": 120,
                    "total_tokens": 200
                }
            }
        ],
        "tool_calls": [
            {"name": "search", "arguments": {"query": "fibonacci algorithm"}}
        ],
        "statistics": {
            "total_requests": 2,
            "total_responses": 2,
            "total_tool_calls": 1,
            "total_tokens": 350,
            "total_prompt_tokens": 130,
            "total_completion_tokens": 220
        },
        "status": "completed"
    }


def main():
    print("=" * 80)
    print("🐯 TigerHill Observer SDK - 功能演示")
    print("=" * 80)
    print("\n本演示使用模拟数据，无需 Google API key\n")

    # 1. 创建模拟数据
    print("📦 [Step 1] 创建模拟捕获数据...")
    capture_data = create_mock_capture_data()
    print(f"✅ 已创建模拟数据：")
    print(f"   - Agent: {capture_data['agent_name']}")
    print(f"   - 请求数: {len(capture_data['requests'])}")
    print(f"   - 响应数: {len(capture_data['responses'])}")
    print(f"   - 持续时间: {capture_data['duration']:.2f}s")

    # 2. 创建分析器
    print(f"\n🔍 [Step 2] 创建 PromptAnalyzer...")
    analyzer = PromptAnalyzer(capture_data)
    print("✅ 分析器已创建")

    # 3. 执行完整分析
    print(f"\n📊 [Step 3] 执行完整分析...")
    report = analyzer.analyze_all()
    print("✅ 分析完成！\n")

    # 4. 显示分析报告
    print("=" * 80)
    print("📈 分析报告详情")
    print("=" * 80)

    # 摘要
    print("\n[1] 📋 摘要信息")
    summary = report["summary"]
    print(f"    - 总请求数: {summary['total_requests']}")
    print(f"    - 总响应数: {summary['total_responses']}")
    print(f"    - 使用的 Agent: {', '.join(summary['agents'])}")
    print(f"    - 使用的模型: {', '.join(summary['models'])}")

    # Token 分析
    print("\n[2] 💰 Token 使用分析")
    tokens = report["token_analysis"]
    print(f"    - 总 Token 数: {tokens['total_tokens']:,}")
    print(f"    - Prompt Tokens: {tokens['total_prompt_tokens']:,}")
    print(f"    - Completion Tokens: {tokens['total_completion_tokens']:,}")
    print(f"    - 平均每请求: {tokens['avg_tokens_per_request']:.0f} tokens")
    print(f"    - Token 效率比: {tokens['token_efficiency_ratio']:.2f} (输出/输入)")

    # 效率评估
    if tokens['token_efficiency_ratio'] < 0.5:
        print("    ⚠️  效率较低：输出相对输入较少")
    elif tokens['token_efficiency_ratio'] > 2.0:
        print("    ✅ 效率良好：输出相对输入较多")

    # Prompt 质量
    print("\n[3] ✨ Prompt 质量分析")
    quality = report["prompt_quality"]
    print(f"    - 清晰度评分: {quality['clarity_score']:.2f}/1.0", end="")
    if quality['clarity_score'] >= 0.8:
        print(" ✅ 优秀")
    elif quality['clarity_score'] >= 0.6:
        print(" 🟡 良好")
    else:
        print(" ⚠️  需要改进")

    print(f"    - 系统 Prompt 使用率: {quality['has_system_prompt_ratio']*100:.1f}%")
    print(f"    - 平均 Prompt 长度: {quality['avg_prompt_length']:.0f} 字符")

    if quality['detected_issues']:
        print(f"    - 检测到的问题: {len(quality['detected_issues'])} 个")
        for issue in quality['detected_issues'][:2]:
            print(f"      • {issue['type']}: {issue['description']}")

    # 性能分析
    print("\n[4] ⚡ 性能分析")
    perf = report["performance"]
    print(f"    - 平均响应时间: {perf['avg_duration']:.2f}s")
    print(f"    - 最长响应时间: {perf['max_duration']:.2f}s")
    print(f"    - 最短响应时间: {perf['min_duration']:.2f}s")

    if perf['avg_duration'] > 10:
        print("    ⚠️  响应时间较长，建议优化")
    else:
        print("    ✅ 响应时间良好")

    # 工具使用
    print("\n[5] 🛠️  工具使用分析")
    tools = report["tool_usage"]
    print(f"    - 定义的工具数: {tools['total_tools_defined']}")
    print(f"    - 实际调用的工具: {tools['total_tool_calls']}")
    print(f"    - 工具使用率: {tools['tool_usage_rate']*100:.1f}%")

    if tools['most_used_tools']:
        print(f"    - 最常用工具: {tools['most_used_tools'][0][0]} ({tools['most_used_tools'][0][1]} 次)")

    if tools['tools_defined_but_not_used']:
        print(f"    - 未使用的工具: {', '.join(tools['tools_defined_but_not_used'])}")
        print("    💡 建议移除未使用的工具以减少上下文")

    # 优化建议
    print("\n[6] 💡 优化建议")
    recommendations = report["recommendations"]
    if recommendations:
        print(f"    共有 {len(recommendations)} 条建议：\n")
        for i, rec in enumerate(recommendations[:5], 1):
            severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec["severity"], "⚪")
            print(f"    [{i}] {severity_emoji} {rec['title']} ({rec['category']})")
            print(f"        描述: {rec['description']}")
            print(f"        建议: {rec['suggestion']}\n")
    else:
        print("    ✅ 没有发现问题，Prompt 质量良好！")

    print("=" * 80)

    # 5. 演示打印报告
    print("\n📄 [Step 4] 生成格式化报告...\n")
    analyzer.print_report(report)

    # 6. 总结
    print("\n" + "=" * 80)
    print("🎉 演示完成！")
    print("=" * 80)
    print("""
这个演示展示了 Observer SDK 的核心功能：

✅ 自动捕获：记录 prompt、response、工具调用
✅ 智能分析：5 维度、22 个指标
✅ Token 分析：使用量、效率、成本优化
✅ 质量评估：清晰度评分、问题检测
✅ 性能监控：响应时间统计
✅ 工具分析：使用率、未使用检测
✅ 优化建议：自动生成可操作建议

下一步：
1. 查看完整文档: cat OBSERVER_SDK_DOCUMENTATION.md
2. 使用真实 API: python examples/observer_python_basic.py
   (需要设置: export GOOGLE_API_KEY=your_key)
3. 运行分析示例: python examples/observer_python_analysis.py
4. 集成到项目: 参考文档的"使用指南"部分

文档链接：
- 快速参考: OBSERVER_SDK_QUICK_SUMMARY.md
- 完整文档: OBSERVER_SDK_DOCUMENTATION.md
- 示例指南: examples/README.md
""")
    print("=" * 80)


if __name__ == "__main__":
    main()

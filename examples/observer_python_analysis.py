"""
TigerHill Observer SDK - Python Analysis Example

演示如何使用 PromptAnalyzer 自动分析捕获的数据，获取优化建议。

使用步骤：
1. 先运行 observer_python_basic.py 生成捕获数据
2. 运行: python examples/observer_python_analysis.py
"""

import json
from pathlib import Path
from tigerhill.observer import PromptCapture, PromptAnalyzer


def load_latest_capture(storage_path="./prompt_captures"):
    """加载最新的捕获文件"""
    capture_dir = Path(storage_path)
    if not capture_dir.exists():
        print(f"Error: {storage_path} does not exist")
        print("Please run observer_python_basic.py first to generate capture data")
        return None

    # 查找所有捕获文件
    capture_files = list(capture_dir.glob("capture_*.json"))
    if not capture_files:
        print(f"Error: No capture files found in {storage_path}")
        print("Please run observer_python_basic.py first to generate capture data")
        return None

    # 获取最新的文件
    latest_file = max(capture_files, key=lambda p: p.stat().st_mtime)
    print(f"📂 Loading capture from: {latest_file}")

    with open(latest_file, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    # 1. 加载捕获数据
    capture_data = load_latest_capture()
    if not capture_data:
        return

    print(f"\n✅ Loaded capture: {capture_data['capture_id']}")
    print(f"   Agent: {capture_data['agent_name']}")
    print(f"   Requests: {len(capture_data['requests'])}")
    print(f"   Responses: {len(capture_data['responses'])}")

    # 2. 创建分析器
    print("\n🔍 Creating analyzer...")
    analyzer = PromptAnalyzer(capture_data)

    # 3. 执行完整分析
    print("\n📊 Analyzing captured data...")
    report = analyzer.analyze_all()

    # 4. 打印报告
    analyzer.print_report(report)

    # 5. 详细展示建议
    if report["recommendations"]:
        print("\n" + "=" * 80)
        print("💡 Detailed Recommendations:")
        print("=" * 80)

        for i, rec in enumerate(report["recommendations"], 1):
            severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec["severity"], "⚪")
            print(f"\n[{i}] {severity_emoji} {rec['title']} ({rec['category']})")
            print(f"    Severity: {rec['severity'].upper()}")
            print(f"    Description: {rec['description']}")
            print(f"    Suggestion: {rec['suggestion']}")
    else:
        print("\n✅ No issues detected! Your prompts look good.")

    # 6. 保存分析报告
    report_file = f"./prompt_captures/analysis_{capture_data['capture_id']}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n📄 Analysis report saved to: {report_file}")

    # 7. 提供操作建议
    print("\n" + "=" * 80)
    print("🎯 Action Items:")
    print("=" * 80)

    # Token 优化建议
    token_analysis = report["token_analysis"]
    if token_analysis["avg_prompt_tokens"] > 2000:
        print("1. ⚠️  Reduce prompt length to save costs")
        print("   - Current avg: {:.0f} tokens".format(token_analysis["avg_prompt_tokens"]))
        print("   - Target: < 2000 tokens")

    if token_analysis["token_efficiency_ratio"] < 0.5:
        print("2. ⚠️  Improve token efficiency")
        print("   - Current ratio: {:.2f}".format(token_analysis["token_efficiency_ratio"]))
        print("   - Consider requesting more detailed outputs")

    # 质量建议
    quality = report["prompt_quality"]
    if quality["has_system_prompt_ratio"] < 0.8:
        print("3. ⚠️  Add system prompts for better control")
        print("   - Current: {:.0f}% of requests have system prompt".format(
            quality["has_system_prompt_ratio"] * 100
        ))
        print("   - Target: > 80%")

    if quality["clarity_score"] < 0.7:
        print("4. ⚠️  Improve prompt clarity")
        print("   - Current score: {:.2f}/1.0".format(quality["clarity_score"]))
        print("   - Add specific instructions and examples")

    # 工具使用建议
    tool_usage = report["tool_usage"]
    if tool_usage["tools_defined_but_not_used"]:
        print("5. 💡 Remove unused tools:")
        for tool in tool_usage["tools_defined_but_not_used"][:3]:
            print(f"   - {tool}")

    # 性能建议
    performance = report["performance"]
    if performance["avg_duration"] > 10:
        print("6. ⚠️  Optimize response time")
        print("   - Current avg: {:.2f}s".format(performance["avg_duration"]))
        print("   - Consider using faster models or simpler prompts")

    print("\n" + "=" * 80)
    print("✨ Analysis complete! Use these insights to optimize your prompts.")
    print("=" * 80)


if __name__ == "__main__":
    main()

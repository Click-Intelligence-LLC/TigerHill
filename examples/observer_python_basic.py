"""
TigerHill Observer SDK - Python Basic Example

演示如何使用 TigerHill Observer SDK 捕获 Google Generative AI 的 prompt 和响应。

使用步骤：
1. 安装依赖: pip install google-generativeai
2. 设置环境变量: export GOOGLE_API_KEY=your_api_key
3. 运行: python examples/observer_python_basic.py
"""

import os
from tigerhill.observer import PromptCapture, wrap_python_model
from tigerhill.observer.python_observer import create_observer_callback

try:
    import google.generativeai as genai
except ImportError:
    print("Error: Please install google-generativeai: pip install google-generativeai")
    exit(1)


def main():
    # 检查 API key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: Please set GOOGLE_API_KEY environment variable")
        print("Example: export GOOGLE_API_KEY=your_api_key")
        exit(1)

    # 配置 API
    genai.configure(api_key=api_key)

    # 1. 创建捕获器
    capture = PromptCapture(
        storage_path="./prompt_captures",
        auto_save=True  # 自动保存到文件
    )

    # 2. 开始捕获会话
    capture_id = capture.start_capture(
        agent_name="code_assistant",
        metadata={
            "task": "generate_fibonacci",
            "version": "1.0"
        }
    )

    print(f"🎯 Started capture session: {capture_id}")

    # 3. 创建观察回调
    callback = create_observer_callback(capture, capture_id)

    # 4. 包装 GenerativeModel
    WrappedModel = wrap_python_model(
        genai.GenerativeModel,
        capture_callback=callback,
        capture_response=True
    )

    # 5. 使用包装后的模型
    print("\n📝 Creating model and generating content...")

    # 尝试不同的模型名称（按优先级）
    model_names = [
        "gemini-2.5-flash",     # 最新版本（优先）
        "gemini-2.0-flash-exp", # Gemini 2.0 实验版本
        "gemini-1.5-flash",     # 1.5 Flash
        "gemini-pro",           # 稳定版本
        "gemini-1.0-pro",       # 旧版本
    ]

    model = None
    for model_name in model_names:
        try:
            print(f"   Trying model: {model_name}...")
            model = WrappedModel(model_name)
            print(f"   ✅ Successfully created model: {model_name}")
            break
        except Exception as e:
            print(f"   ❌ Failed: {str(e)[:80]}")
            continue

    if model is None:
        print("\n❌ Error: Could not create any model.")
        print("Please check:")
        print("  1. GOOGLE_API_KEY is set correctly")
        print("  2. API key has access to Gemini models")
        print("  3. Run: gcloud auth application-default login")
        exit(1)

    # 第一个请求
    print("\n[Request 1] Asking for fibonacci function...")
    response1 = model.generate_content("Write a Python function to calculate fibonacci numbers")
    print(f"✅ Response 1 received: {len(response1.text)} characters")

    # 第二个请求
    print("\n[Request 2] Asking for optimization...")
    response2 = model.generate_content("Can you optimize the fibonacci function with memoization?")
    print(f"✅ Response 2 received: {len(response2.text)} characters")

    # 6. 结束捕获
    print("\n📊 Ending capture session...")
    result = capture.end_capture(capture_id)

    # 7. 显示统计信息
    print("\n" + "=" * 60)
    print("📈 Capture Statistics:")
    print("=" * 60)
    print(f"Agent: {result['agent_name']}")
    print(f"Duration: {result['duration']:.2f} seconds")
    print(f"Total Requests: {result['statistics']['total_requests']}")
    print(f"Total Responses: {result['statistics']['total_responses']}")
    print(f"Total Tokens: {result['statistics']['total_tokens']:,}")
    print(f"  - Prompt Tokens: {result['statistics']['total_prompt_tokens']:,}")
    print(f"  - Completion Tokens: {result['statistics']['total_completion_tokens']:,}")

    if result['statistics']['total_tokens'] > 0:
        avg_tokens = result['statistics']['total_tokens'] / result['statistics']['total_requests']
        print(f"Average Tokens per Request: {avg_tokens:.0f}")

    print("=" * 60)
    print(f"\n✅ Capture saved to: ./prompt_captures/capture_{capture_id}_*.json")
    print("\n💡 Next steps:")
    print("   - Use PromptAnalyzer to analyze the captured data")
    print("   - Export to TraceStore for integration with TigerHill testing")
    print("   - Review and optimize your prompts based on captured data")


if __name__ == "__main__":
    main()

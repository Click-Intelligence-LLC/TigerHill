"""
Phase 1 增强功能演示

演示系统Prompt捕获和多轮对话追踪功能
"""

import json
from tigerhill.observer import PromptCapture
from tigerhill.observer.conversation_models import SystemPromptExtractor

def demonstrate_system_prompt_extraction():
    """演示从多种格式提取系统prompt"""
    print("=" * 80)
    print("演示 1：系统Prompt提取（支持多种agent格式）")
    print("=" * 80)

    # 1. Gemini格式
    print("\n1️⃣ Gemini格式 (system_instruction):")
    gemini_kwargs = {
        'system_instruction': "You are a helpful AI assistant specialized in Python programming."
    }
    system_prompt = SystemPromptExtractor.extract_from_kwargs(gemini_kwargs)
    print(f"   提取结果: {system_prompt}")

    # 2. OpenAI格式
    print("\n2️⃣  OpenAI格式 (messages数组中的system role):")
    openai_kwargs = {
        'messages': [
            {'role': 'system', 'content': 'You are an expert code reviewer.'},
            {'role': 'user', 'content': 'Review my code'}
        ]
    }
    system_prompt = SystemPromptExtractor.extract_from_kwargs(openai_kwargs)
    print(f"   提取结果: {system_prompt}")

    # 3. Anthropic格式
    print("\n3️⃣ Anthropic格式 (system参数):")
    anthropic_kwargs = {
        'system': 'You are Claude, a helpful AI assistant.'
    }
    system_prompt = SystemPromptExtractor.extract_from_kwargs(anthropic_kwargs)
    print(f"   提取结果: {system_prompt}")

    print("\n✅ 系统Prompt提取演示完成！")


def demonstrate_multiturn_conversation():
    """演示多轮对话追踪"""
    print("\n" + "=" * 80)
    print("演示 2：多轮对话追踪")
    print("=" * 80)

    # 创建捕获器
    capture = PromptCapture(storage_path="./prompt_captures/phase1_demo")
    capture_id = capture.start_capture("demo_agent")

    # 模拟多轮对话
    conversation_id = "demo_conversation_001"

    print(f"\n📝 对话ID: {conversation_id}")
    print("-" * 80)

    # Turn 1
    print("\n🔵 Turn 1:")
    print("   User: 什么是Python？")
    request_id_1 = capture.capture_request(
        capture_id,
        {
            "model": "gemini-2.0-flash-exp",
            "prompt": "什么是Python？",
            "system_prompt": "你是一个编程教学助手，擅长解释编程概念。"
        },
        conversation_id=conversation_id,
        turn_number=1
    )

    capture.capture_response(
        capture_id,
        {
            "text": "Python是一种高级编程语言，以其简洁易读的语法而闻名。",
            "usage": {
                "prompt_tokens": 25,
                "completion_tokens": 30,
                "total_tokens": 55
            }
        },
        request_id=request_id_1
    )
    print("   Assistant: Python是一种高级编程语言，以其简洁易读的语法而闻名。")
    print("   📊 Tokens: 55")

    # Turn 2
    print("\n🔵 Turn 2:")
    print("   User: 它有什么特点？")
    request_id_2 = capture.capture_request(
        capture_id,
        {
            "model": "gemini-2.0-flash-exp",
            "prompt": "它有什么特点？"
        },
        conversation_id=conversation_id,
        turn_number=2
    )

    capture.capture_response(
        capture_id,
        {
            "text": "Python的主要特点包括：1）易学易用 2）丰富的标准库 3）强大的社区支持 4）跨平台兼容性好。",
            "usage": {
                "prompt_tokens": 30,
                "completion_tokens": 45,
                "total_tokens": 75
            }
        },
        request_id=request_id_2
    )
    print("   Assistant: Python的主要特点包括：1）易学易用 2）丰富的标准库 3）强大的社区支持...")
    print("   📊 Tokens: 75")

    # Turn 3
    print("\n🔵 Turn 3:")
    print("   User: 适合初学者吗？")
    request_id_3 = capture.capture_request(
        capture_id,
        {
            "model": "gemini-2.0-flash-exp",
            "prompt": "适合初学者吗？"
        },
        conversation_id=conversation_id,
        turn_number=3
    )

    capture.capture_response(
        capture_id,
        {
            "text": "非常适合！Python的语法接近自然语言，是最适合编程初学者的语言之一。",
            "usage": {
                "prompt_tokens": 20,
                "completion_tokens": 35,
                "total_tokens": 55
            }
        },
        request_id=request_id_3
    )
    print("   Assistant: 非常适合！Python的语法接近自然语言，是最适合编程初学者的语言之一。")
    print("   📊 Tokens: 55")

    print("\n" + "-" * 80)

    # 获取对话历史
    conv_history = capture.get_conversation_history(conversation_id)

    print("\n📊 对话统计:")
    print(f"   • 总轮次: {conv_history.total_turns}")
    print(f"   • 消息总数: {len(conv_history.messages)}")
    print(f"   • 系统prompt: {'✓ 已设置' if conv_history.system_prompt else '✗ 未设置'}")
    print(f"   • 总Token消耗: {conv_history.total_tokens['total_tokens']}")

    print("\n📝 消息结构:")
    for msg in conv_history.messages:
        role_icon = {
            'system': '🔧',
            'user': '👤',
            'assistant': '🤖'
        }.get(msg.role, '•')

        content_preview = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
        print(f"   {role_icon} [{msg.role:10s}] Turn {msg.turn_number}: {content_preview}")

    # 获取对话摘要
    print("\n📋 对话摘要:")
    summary = capture.get_conversation_summary(conversation_id)
    print(f"   • 系统prompt预览: {summary['system_prompt_preview'][:60]}...")
    print(f"   • 对话时长: {summary['duration']:.2f}秒")
    print(f"   • Token统计: {summary['total_tokens']}")

    print("\n💾 导出对话历史...")
    export_path = "./prompt_captures/phase1_demo/conversation_demo.json"
    capture.export_conversation(conversation_id, export_path)
    print(f"   ✅ 已保存到: {export_path}")

    # 结束捕获
    result = capture.end_capture(capture_id)
    print(f"\n✅ 多轮对话追踪演示完成！")
    print(f"   捕获了 {result['statistics']['total_requests']} 个请求")
    print(f"   捕获了 {result['statistics']['total_responses']} 个响应")


def demonstrate_conversation_structure():
    """演示对话结构查询"""
    print("\n" + "=" * 80)
    print("演示 3：对话结构查询")
    print("=" * 80)

    capture = PromptCapture(storage_path="./prompt_captures/phase1_demo")
    capture_id = capture.start_capture("structure_demo")

    # 创建两个不同的对话
    conversations = [
        ("conv_python_basics", [
            ("Turn 1", "Python是什么？", "Python是一种编程语言"),
            ("Turn 2", "如何学习？", "从基础语法开始学习")
        ]),
        ("conv_data_structures", [
            ("Turn 1", "什么是列表？", "列表是Python中的一种数据结构"),
            ("Turn 2", "如何使用？", "可以用[]创建列表")
        ])
    ]

    for conv_id, turns in conversations:
        for turn_num, (_, user_msg, assistant_msg) in enumerate(turns, 1):
            req_id = capture.capture_request(
                capture_id,
                {"model": "test", "prompt": user_msg},
                conversation_id=conv_id,
                turn_number=turn_num
            )
            capture.capture_response(
                capture_id,
                {"text": assistant_msg},
                request_id=req_id
            )

    # 列出所有对话
    print("\n📋 当前会话中的对话列表:")
    conversations_list = capture.list_conversations()
    for idx, conv in enumerate(conversations_list, 1):
        print(f"\n{idx}. 对话ID: {conv['conversation_id']}")
        print(f"   • Agent: {conv['agent_name']}")
        print(f"   • 轮次数: {conv['total_turns']}")
        print(f"   • 消息数: {conv['message_count']}")
        print(f"   • 开始时间: {conv['started_at']}")

    print("\n✅ 对话结构查询演示完成！")


def main():
    """主函数"""
    print("\n" + "🚀" * 40)
    print("TigerHill Observer SDK - Phase 1 增强功能演示")
    print("🚀" * 40)

    # 演示1：系统prompt提取
    demonstrate_system_prompt_extraction()

    # 演示2：多轮对话追踪
    demonstrate_multiturn_conversation()

    # 演示3：对话结构查询
    demonstrate_conversation_structure()

    print("\n" + "=" * 80)
    print("🎉 所有演示完成！")
    print("=" * 80)

    print("\n💡 Phase 1 增强功能总结:")
    print("   ✅ 支持从Gemini、OpenAI、Anthropic等多种格式提取系统prompt")
    print("   ✅ 结构化对话历史追踪（包含角色、turn_number等）")
    print("   ✅ 自动conversation_id生成和管理")
    print("   ✅ 完整的对话统计和摘要功能")
    print("   ✅ 对话历史导出功能")

    print("\n🎯 支持的使用场景:")
    print("   • gemini-cli 多轮对话追踪")
    print("   • 其他CLI agent的对话捕获")
    print("   • LLM API的请求/响应完整记录")
    print("   • 系统prompt质量分析")
    print("   • 多轮对话coherence分析")

    print("\n📚 查看更多:")
    print("   • 测试文件: tests/test_observer_phase1_enhancements.py")
    print("   • 文档: OBSERVER_SDK_CAPABILITIES_ANALYSIS.md")
    print()


if __name__ == "__main__":
    main()

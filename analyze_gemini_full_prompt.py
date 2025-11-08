#!/usr/bin/env python3
"""
深入分析 Gemini CLI 拦截到的完整 prompt
"""

import json
from pathlib import Path

# 读取最新的 session 文件
session_files = sorted(Path("prompt_captures/gemini_cli").glob("session_*.json"))
latest = session_files[-1]

print(f"分析文件: {latest.name}")
print("=" * 80)

with open(latest) as f:
    data = json.load(f)

print(f"\n📋 Session 信息")
print(f"  Session ID: {data['session_id']}")
print(f"  Agent: {data['agent_name']}")
print(f"  Turns: {len(data['turns'])}")
print(f"  开始时间: {data['start_time']}")

# 分析每一个 turn
for turn_idx, turn in enumerate(data['turns'], 1):
    print(f"\n" + "=" * 80)
    print(f"🔄 Turn {turn_idx}")
    print("=" * 80)

    print(f"\n📤 Requests: {len(turn['requests'])}")

    # 分析每个请求
    for req_idx, req in enumerate(turn['requests'], 1):
        print(f"\n  --- Request {req_idx} ---")
        print(f"  URL: {req['url']}")

        # 只分析 generateContent 请求（真正的 LLM 调用）
        if 'generateContent' not in req['url']:
            print(f"  (跳过: 不是 generateContent)")
            continue

        print(f"  Model: {req.get('model', 'N/A')}")
        print(f"\n  === 完整 Prompt 分析 ===")

        # 1. 系统提示词
        print(f"\n  1️⃣ 系统提示词 (System Instruction)")

        if 'system_instruction' in req:
            sys_inst = req['system_instruction']
            if isinstance(sys_inst, dict) and 'parts' in sys_inst:
                text = sys_inst['parts'][0].get('text', '')
                print(f"     长度: {len(text):,} 字符")
                print(f"     行数: {len(text.splitlines()):,}")
                print(f"     估算 tokens: {len(text) // 4:,}")
                print(f"\n     前 20 行:")
                for i, line in enumerate(text.splitlines()[:20], 1):
                    print(f"       {i:2d}. {line}")
                print(f"       ...")
            else:
                print(f"     值: {sys_inst}")
        elif 'system_prompt' in req:
            sys_prompt = req['system_prompt']
            print(f"     长度: {len(sys_prompt):,} 字符")
            print(f"     行数: {len(sys_prompt.splitlines()):,}")
            print(f"     估算 tokens: {len(sys_prompt) // 4:,}")
            print(f"\n     前 20 行:")
            for i, line in enumerate(sys_prompt.splitlines()[:20], 1):
                print(f"       {i:2d}. {line}")
            print(f"       ...")
        else:
            print(f"     ❌ 未找到系统提示词")

        # 2. Input Messages / Contents
        print(f"\n  2️⃣ 输入内容 (Contents/Messages)")

        contents = req.get('contents', [])
        print(f"     数量: {len(contents)} 个 message")

        for msg_idx, msg in enumerate(contents, 1):
            role = msg.get('role', 'unknown')
            parts = msg.get('parts', [])

            print(f"\n     Message {msg_idx}: role={role}")

            for part_idx, part in enumerate(parts, 1):
                if 'text' in part:
                    text = part['text']
                    print(f"       Part {part_idx} [text]:")
                    print(f"         长度: {len(text):,} 字符")
                    print(f"         行数: {len(text.splitlines()):,}")
                    print(f"         估算 tokens: {len(text) // 4:,}")

                    # 显示内容预览
                    if len(text) < 500:
                        # 短内容：完整显示
                        print(f"         完整内容:")
                        for line in text.splitlines():
                            print(f"           {line}")
                    else:
                        # 长内容：显示前10行和分析
                        print(f"         前 10 行:")
                        for i, line in enumerate(text.splitlines()[:10], 1):
                            print(f"           {i:2d}. {line}")
                        print(f"           ...")

                        # 分析内容类型
                        if "This is the Gemini CLI" in text:
                            print(f"         内容类型: 上下文设置（Context Setup）")
                        elif "<user_instructions>" in text:
                            print(f"         内容类型: 项目指令（AGENTS.md）")
                        elif "<environment_context>" in text:
                            print(f"         内容类型: 环境上下文")
                        else:
                            print(f"         内容类型: 用户输入")

                elif 'thought' in part:
                    print(f"       Part {part_idx} [thought]:")
                    print(f"         (思考内容)")

                else:
                    print(f"       Part {part_idx}: {list(part.keys())}")

        # 3. Generation Config
        print(f"\n  3️⃣ 生成配置 (Generation Config)")

        if 'generation_config' in req:
            config = req['generation_config']
            print(f"     {json.dumps(config, indent=6)}")
        elif 'generationConfig' in req:
            config = req['generationConfig']
            print(f"     {json.dumps(config, indent=6)}")
        else:
            print(f"     ❌ 未找到生成配置")

        # 4. 其他字段
        print(f"\n  4️⃣ 其他字段")

        extra_fields = [
            'user_input',
            'conversation_length',
            'tools',
            'tool_config',
            'safety_settings'
        ]

        for field in extra_fields:
            if field in req:
                value = req[field]
                if isinstance(value, str):
                    print(f"     {field}: {value[:100]}...")
                elif isinstance(value, (int, float, bool)):
                    print(f"     {field}: {value}")
                elif isinstance(value, (list, dict)):
                    print(f"     {field}: {type(value).__name__} with {len(value)} items")
                else:
                    print(f"     {field}: {type(value).__name__}")

        # 5. Token 估算
        print(f"\n  5️⃣ Token 估算（粗略：4字符≈1token）")

        total_chars = 0

        # 系统提示词
        if 'system_instruction' in req:
            sys_inst = req['system_instruction']
            if isinstance(sys_inst, dict) and 'parts' in sys_inst:
                text = sys_inst['parts'][0].get('text', '')
                total_chars += len(text)
                print(f"     系统提示词: {len(text):,} chars → ~{len(text) // 4:,} tokens")
        elif 'system_prompt' in req:
            total_chars += len(req['system_prompt'])
            print(f"     系统提示词: {len(req['system_prompt']):,} chars → ~{len(req['system_prompt']) // 4:,} tokens")

        # Contents
        for msg in contents:
            for part in msg.get('parts', []):
                if 'text' in part:
                    text = part['text']
                    total_chars += len(text)

        print(f"     所有 contents: {total_chars - (len(req.get('system_prompt', '')) or len(req.get('system_instruction', {}).get('parts', [{}])[0].get('text', ''))):,} chars")
        print(f"     总计: {total_chars:,} chars → ~{total_chars // 4:,} tokens")

    # 分析响应
    print(f"\n📥 Responses: {len(turn['responses'])}")

    for resp_idx, resp in enumerate(turn['responses'], 1):
        print(f"\n  --- Response {resp_idx} ---")
        print(f"  Status: {resp.get('status_code', 'N/A')}")
        print(f"  Duration: {resp.get('duration_ms', 0):.0f} ms")

        if 'text' in resp:
            text = resp['text']
            print(f"  Response 文本长度: {len(text)} chars")
            print(f"  Response 内容: \"{text}\"")

        if 'usage' in resp:
            usage = resp['usage']
            print(f"  Token 使用:")
            print(f"    Prompt: {usage.get('prompt_tokens', 0):,}")
            print(f"    Completion: {usage.get('completion_tokens', 0):,}")
            print(f"    Total: {usage.get('total_tokens', 0):,}")

        if 'finish_reason' in resp:
            print(f"  Finish Reason: {resp['finish_reason']}")

print("\n" + "=" * 80)
print("✅ 分析完成")

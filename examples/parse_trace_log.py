#!/usr/bin/env python3
"""
从 RUST_LOG=trace 日志中提取完整的 API 请求

直接解析已有的 trace 日志文件
"""

import json
import re
import sys
from pathlib import Path


def parse_trace_log(log_content: str) -> dict:
    """
    从 trace 日志中解析完整的 API 请求
    """

    # 查找 TRACE codex_core::client: POST ... 行
    # 格式: TRACE codex_core::client: POST to URL: "JSON..."
    # 使用更宽松的模式匹配
    pattern = r'TRACE codex_core::client: POST to.+?: "(.+?)"(?:\s|$)'

    # 搜索所有匹配
    matches = []
    for line in log_content.split('\n'):
        # 先查找 TRACE codex_core::client: POST
        if 'TRACE codex_core::client: POST' in line:
            # 提取 JSON 部分（在第一个 " 到最后一个 " 之间）
            start = line.find('": "')
            if start != -1:
                start += 4  # 跳过 ": "
                # 找到行尾的引号（但不是转义的）
                json_part = line[start:]
                # 去掉最后的引号
                if json_part.endswith('"'):
                    json_part = json_part[:-1]
                matches.append(json_part)

    if not matches:
        return None

    # 取第一个匹配（通常是用户的实际请求）
    json_str = matches[0]

    try:
        # JSON 是转义的，需要解转义
        # 替换: \\" → "
        #       \\n → \n
        json_str = json_str.replace('\\"', '"')
        json_str = json_str.replace('\\n', '\n')
        json_str = json_str.replace('\\\\', '\\')

        # 解析 JSON
        request = json.loads(json_str)
        return request

    except json.JSONDecodeError as e:
        print(f"JSON 解析错误: {e}")
        print(f"原始字符串前 500 字符: {json_str[:500]}")
        return None


def display_request_summary(request: dict):
    """
    显示请求摘要
    """

    print("\n" + "="*70)
    print("📋 完整 API 请求分析")
    print("="*70 + "\n")

    # 1. Model
    print("1️⃣  Model")
    print(f"  {request.get('model', 'N/A')}\n")

    # 2. System Instructions
    instructions = request.get('instructions', '')
    if instructions:
        print("2️⃣  系统提示词 (System Instructions)")
        print(f"  长度: {len(instructions):,} 字符")
        print(f"  行数: {len(instructions.split(chr(10))):,}")
        print(f"\n  前 10 行:")

        lines = instructions.split('\n')[:10]
        for line in lines:
            print(f"    {line}")

        if len(instructions.split('\n')) > 10:
            print(f"    ... (共 {len(instructions.split(chr(10)))} 行)\n")

    # 3. Input Messages
    input_msgs = request.get('input', [])
    if input_msgs:
        print(f"3️⃣  Input Messages (共 {len(input_msgs)} 条)\n")

        for i, msg in enumerate(input_msgs, 1):
            role = msg.get('role', 'unknown')
            msg_type = msg.get('type', 'message')
            content = msg.get('content', [])

            print(f"  Message {i}: type={msg_type}, role={role}")

            for item in content:
                item_type = item.get('type', 'unknown')

                if item_type == 'input_text':
                    text = item.get('text', '')
                    preview = text[:150].replace('\n', ' ')
                    if len(text) > 150:
                        preview += f"... ({len(text):,} 字符)"
                    print(f"    📝 {item_type}: {preview}")

                elif item_type == 'input_file':
                    path = item.get('path', '')
                    content_preview = item.get('content', '')[:100]
                    print(f"    📄 {item_type}: {path}")
                    if content_preview:
                        print(f"       内容预览: {content_preview}...")

                else:
                    print(f"    🔹 {item_type}")

            print()

    # 4. 统计
    print("4️⃣  统计信息")

    total_chars = len(instructions)
    for msg in input_msgs:
        for item in msg.get('content', []):
            if 'text' in item:
                total_chars += len(item['text'])
            if 'content' in item:
                total_chars += len(item['content'])

    estimated_tokens = total_chars // 4

    print(f"  总字符数: {total_chars:,}")
    print(f"  估算 tokens: {estimated_tokens:,} (粗略: 4 字符 ≈ 1 token)")

    print("\n" + "="*70 + "\n")


def main():
    """
    演示：从实际的 trace 日志中提取和显示完整请求
    """

    if len(sys.argv) > 1:
        log_file = sys.argv[1]
    else:
        # 使用演示数据（从之前捕获的日志）
        print("使用演示数据...")
        print("提示：你可以提供 trace 日志文件作为参数\n")
        print(f"用法: {sys.argv[0]} path/to/trace.log\n")

        # 演示：显示如何提取
        demo_log = '''
2025-11-06T23:56:33.029306Z TRACE codex_core::client: POST to https://chatgpt.com/backend-api/codex/responses: "{\\"model\\":\\"gpt-5-codex\\",\\"instructions\\":\\"You are Codex, based on GPT-5. You are running as a coding agent in the Codex CLI.\\\\n\\\\n## General\\\\n\\\\n- Use `rg` for searching...\\",\\"input\\":[{\\"type\\":\\"message\\",\\"role\\":\\"user\\",\\"content\\":[{\\"type\\":\\"input_text\\",\\"text\\":\\"<user_instructions>\\\\n\\\\nProject-specific instructions here\\\\n\\\\n</user_instructions>\\"}]}],\\"stream\\":true}"
'''

        request = parse_trace_log(demo_log)
        if request:
            print("✓ 成功解析演示数据\n")
            display_request_summary(request)

        print("\n💡 实际使用示例:")
        print("  1. 运行 Codex 并启用 trace 日志:")
        print("     export RUST_LOG=trace")
        print("     codex exec --json --skip-git-repo-check \"your prompt\" 2>trace.log")
        print()
        print("  2. 解析日志:")
        print(f"     python3 {sys.argv[0]} trace.log")
        print()
        print("  3. 保存为 JSON:")
        print(f"     python3 {sys.argv[0]} trace.log --json > request.json")

        return

    # 读取并解析日志文件
    log_content = Path(log_file).read_text()

    request = parse_trace_log(log_content)

    if not request:
        print("⚠️  未找到 API 请求数据")
        print("确保日志是使用 RUST_LOG=trace 生成的")
        return

    # 如果有 --json 参数，输出 JSON
    if '--json' in sys.argv:
        print(json.dumps(request, indent=2, ensure_ascii=False))
    else:
        display_request_summary(request)


if __name__ == "__main__":
    main()

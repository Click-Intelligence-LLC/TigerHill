#!/usr/bin/env python3
"""
分析 Codex CLI 发送给 LLM 的完整请求

通过 RUST_LOG=trace 捕获并解析完整的 API 请求，包括：
- 系统提示词
- 完整的 messages 数组
- 上下文和历史对话
"""

import json
import os
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path


def capture_with_trace_logs(prompt: str, working_dir: str = ".") -> dict:
    """
    使用 RUST_LOG=trace 运行 Codex CLI 并捕获完整日志
    """

    print(f"\n{'='*70}")
    print(f"捕获完整 LLM 请求")
    print(f"{'='*70}\n")

    # 创建临时脚本
    script_content = f'''
const {{ Codex }} = require('@openai/codex-sdk');

async function run() {{
    const codex = new Codex();

    const thread = await codex.startThread();

    for await (const event of codex.runStreamed({{
        threadId: thread.threadId,
        prompt: {json.dumps(prompt)},
        workingDirectory: {json.dumps(working_dir)},
        skipGitRepoCheck: true,
    }})) {{
        // 只输出 JSONL 事件
        console.log(JSON.stringify(event));
    }}
}}

run().catch(console.error);
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write(script_content)
        script_path = f.name

    try:
        # 设置环境变量启用 trace 日志
        env = os.environ.copy()
        env['RUST_LOG'] = 'trace'  # 或 'codex_core=trace'

        print(f"运行 Codex CLI (RUST_LOG=trace)...")
        print(f"Prompt: {prompt}\n")

        # 执行并捕获所有输出
        result = subprocess.run(
            ['node', script_path],
            env=env,
            capture_output=True,
            text=True,
            timeout=120
        )

        stdout = result.stdout
        stderr = result.stderr

        # 保存原始日志
        log_dir = Path("./prompt_captures/codex_cli/logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"trace_{timestamp}.log"

        with open(log_file, 'w') as f:
            f.write("=== STDOUT ===\n")
            f.write(stdout)
            f.write("\n\n=== STDERR ===\n")
            f.write(stderr)

        print(f"✓ 原始日志已保存: {log_file}")

        # 解析完整请求
        full_request = parse_full_request(stderr)

        if full_request:
            request_file = log_dir / f"request_{timestamp}.json"
            with open(request_file, 'w') as f:
                json.dump(full_request, f, indent=2, ensure_ascii=False)
            print(f"✓ 完整请求已保存: {request_file}\n")

        return {
            'stdout': stdout,
            'stderr': stderr,
            'log_file': str(log_file),
            'full_request': full_request
        }

    finally:
        if os.path.exists(script_path):
            os.unlink(script_path)


def parse_full_request(stderr: str) -> dict:
    """
    从 trace 日志中解析完整的 API 请求
    """

    # 查找 TRACE codex_core::client: POST ... 行
    pattern = r'TRACE codex_core::client: POST to [^:]+: "(.+?)"(?:\s|$)'

    matches = re.findall(pattern, stderr, re.MULTILINE)

    if not matches:
        print("⚠️  未找到 API 请求日志")
        return None

    # 取第一个匹配（用户 turn 的请求）
    request_json_str = matches[0]

    # 解析转义的 JSON
    try:
        # 替换转义字符
        request_json_str = request_json_str.replace('\\"', '"')
        request_json_str = request_json_str.replace('\\n', '\n')

        # 解析 JSON
        request_data = json.loads(request_json_str)

        return request_data

    except json.JSONDecodeError as e:
        print(f"⚠️  JSON 解析失败: {e}")
        return {
            'raw_json': request_json_str[:500] + "...",
            'error': str(e)
        }


def display_full_request(request: dict):
    """
    显示完整请求的关键部分
    """

    if not request:
        return

    print(f"{'='*70}")
    print(f"📋 完整 LLM 请求分析")
    print(f"{'='*70}\n")

    # 1. Model
    if 'model' in request:
        print(f"1️⃣  Model")
        print(f"  {request['model']}\n")

    # 2. System Instructions (系统提示词)
    if 'instructions' in request:
        instructions = request['instructions']
        print(f"2️⃣  系统提示词 (System Instructions)")
        print(f"  长度: {len(instructions)} 字符")
        print(f"  预览:")

        # 显示前几行
        lines = instructions.split('\n')[:10]
        for line in lines:
            print(f"    {line}")

        if len(instructions.split('\n')) > 10:
            print(f"    ... ({len(instructions.split('\n'))} 行总计)\n")

    # 3. Input Messages
    if 'input' in request:
        messages = request['input']
        print(f"3️⃣  Input Messages (共 {len(messages)} 条)")

        for i, msg in enumerate(messages, 1):
            role = msg.get('role', 'unknown')
            content = msg.get('content', [])

            print(f"\n  Message {i}: role={role}")

            # 显示content
            if isinstance(content, list):
                for item in content:
                    item_type = item.get('type', 'unknown')

                    if item_type == 'input_text':
                        text = item.get('text', '')
                        preview = text[:200]
                        if len(text) > 200:
                            preview += f"... ({len(text)} 字符总计)"
                        print(f"    📝 {item_type}: {preview}")

                    elif item_type == 'input_file':
                        path = item.get('path', '')
                        print(f"    📄 {item_type}: {path}")

                    else:
                        print(f"    🔹 {item_type}")

    # 4. 其他参数
    print(f"\n4️⃣  其他参数")
    for key in ['temperature', 'max_tokens', 'top_p', 'stream']:
        if key in request:
            print(f"  {key}: {request[key]}")

    # 5. 统计
    print(f"\n5️⃣  统计信息")

    # 计算总 token 数（粗略估算）
    total_chars = 0
    if 'instructions' in request:
        total_chars += len(request['instructions'])
    if 'input' in request:
        for msg in request['input']:
            for item in msg.get('content', []):
                if 'text' in item:
                    total_chars += len(item['text'])

    estimated_tokens = total_chars // 4  # 粗略估算：4 字符 ≈ 1 token

    print(f"  总字符数: {total_chars:,}")
    print(f"  估算 tokens: {estimated_tokens:,}")

    print(f"\n{'='*70}\n")


def main():
    """主函数"""

    # 捕获一个简单的请求
    result = capture_with_trace_logs(
        prompt="列出当前目录下的所有 Python 文件",
        working_dir="."
    )

    # 显示完整请求
    if result['full_request']:
        display_full_request(result['full_request'])

    print("\n💡 提示:")
    print("  - 完整的系统提示词已被捕获")
    print("  - 所有 input messages 已被捕获")
    print("  - 上下文文件内容已被捕获")
    print("  - 可以查看保存的 JSON 文件获取完整数据")

    print(f"\n📂 查看完整数据:")
    if result['full_request']:
        print(f"  cat {result.get('log_file', 'N/A').replace('trace_', 'request_').replace('.log', '.json')}")


if __name__ == "__main__":
    main()

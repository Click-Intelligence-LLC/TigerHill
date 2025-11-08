#!/usr/bin/env python3
"""
TigerHill 捕获文件查看工具 - 快速查看最新捕获
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def format_timestamp(ts: float) -> str:
    """格式化时间戳"""
    return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

def view_capture(filepath: str):
    """查看捕获文件"""

    print("=" * 70)
    print("TigerHill 捕获文件查看")
    print("=" * 70)
    print()

    # 读取文件
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ 文件未找到: {filepath}")
        return
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        return

    # 基本信息
    print("📋 基本信息")
    print("-" * 70)
    print(f"Session ID:     {data.get('session_id', 'N/A')[:40]}...")
    print(f"Agent:          {data.get('agent_name', 'N/A')}")
    print(f"Interceptor:    {data.get('metadata', {}).get('interceptor', 'N/A')} v{data.get('metadata', {}).get('version', 'N/A')}")
    print(f"开始时间:       {format_timestamp(data.get('start_time', 0))}")
    if data.get('end_time'):
        print(f"结束时间:       {format_timestamp(data['end_time'])}")
        print(f"持续时间:       {data.get('duration', 0):.2f} 秒")
    print()

    # 统计信息
    stats = data.get('statistics', {})
    print("📊 统计信息")
    print("-" * 70)
    print(f"总轮次:         {stats.get('total_turns', 0)}")
    print(f"总请求:         {stats.get('total_requests', 0)}")
    print(f"总响应:         {stats.get('total_responses', 0)}")
    print(f"总 Tokens:      {stats.get('total_tokens', 0):,}")

    conv_stats = stats.get('conversation_statistics', {})
    if conv_stats:
        print(f"总消息数:       {conv_stats.get('total_messages', 0)}")
        print(f"  系统消息:     {conv_stats.get('system_messages', 0)}")
        print(f"  用户消息:     {conv_stats.get('user_messages', 0)}")
        print(f"  助手消息:     {conv_stats.get('assistant_messages', 0)}")
        print(f"系统 Prompt:    {'✓ 有' if conv_stats.get('has_system_prompt') else '✗ 无'}")
    print()

    # 错误检测
    turns = data.get('turns', [])
    errors = []
    success_count = 0

    for i, turn in enumerate(turns, 1):
        for response in turn.get('responses', []):
            status = response.get('status_code')
            if status == 200:
                success_count += 1
            elif status:
                errors.append({
                    'turn': i,
                    'status': status,
                    'error': response.get('parse_error') or response.get('raw_text', '')[:100]
                })

    if errors:
        print("⚠️  错误检测")
        print("-" * 70)
        print(f"成功响应: {success_count}")
        print(f"失败响应: {len(errors)}")
        print()

        for err in errors:
            print(f"Turn #{err['turn']}: HTTP {err['status']}")
            if err['status'] == 429:
                print("  ⚠️  原因: API 限流 (Rate Limiting)")
                print("     说明: 这是 Google API 的配额限制，不是 TigerHill 的问题")
                print("     解决: 等待几分钟后重试，或升级到付费账户")
            elif err['status'] == 404:
                print("  ❌ 原因: 资源未找到")
            else:
                print(f"  ❌ 错误: {err['error'][:80]}...")
            print()
    else:
        print("✅ 所有响应成功 (无错误)")
        print()

    # 对话历史
    print("💬 对话历史")
    print("-" * 70)

    messages = data.get('conversation_history', {}).get('messages', [])
    if not messages:
        print("(无对话记录 - 可能所有请求都失败了)")
        print()
    else:
        for msg in messages:
            role = msg['role'].upper()
            content = msg['content']
            turn = msg.get('turn_number', 0)

            # 角色标签
            if role == 'SYSTEM':
                label = f"[系统]"
                emoji = "⚙️ "
            elif role == 'USER':
                label = f"[用户 Turn#{turn}]"
                emoji = "👤 "
            else:
                label = f"[助手 Turn#{turn}]"
                emoji = "🤖 "

            # 截断长文本
            if len(content) > 200:
                content = content[:200] + "..."

            print(f"{emoji}{label}")
            # 缩进显示内容
            for line in content.split('\n'):
                if line.strip():
                    print(f"  {line}")

            # 显示 token 信息
            if msg.get('tokens_used'):
                tokens = msg['tokens_used']
                print(f"  → Tokens: {tokens.get('total_tokens', 0)} " +
                      f"(prompt: {tokens.get('prompt_tokens', 0)}, " +
                      f"completion: {tokens.get('completion_tokens', 0)})")

            print()

    print("=" * 70)
    print(f"文件: {filepath}")
    print("=" * 70)

def main():
    """主函数"""

    if len(sys.argv) > 1:
        # 命令行指定文件
        filepath = sys.argv[1]
    else:
        # 自动查找最新文件
        capture_dir = Path("./prompt_captures/gemini_cli")

        if not capture_dir.exists():
            # 尝试其他可能的目录
            alt_dirs = [
                Path("./prompt_captures/gemini_cli_fixed"),
                Path("./prompt_captures/gemini_cli_test"),
            ]

            for alt_dir in alt_dirs:
                if alt_dir.exists():
                    capture_dir = alt_dir
                    break
            else:
                print("❌ 捕获目录不存在")
                print()
                print("尝试的目录:")
                print(f"  - ./prompt_captures/gemini_cli")
                for alt_dir in alt_dirs:
                    print(f"  - {alt_dir}")
                print()
                print("使用方法:")
                print(f"  {sys.argv[0]} <捕获文件路径>")
                return

        # 查找所有 session 文件
        session_files = list(capture_dir.glob("session_*.json"))

        if not session_files:
            print(f"❌ 未找到捕获文件: {capture_dir}")
            print()
            print("提示:")
            print("  1. 确保已运行 Gemini CLI 并进行了对话")
            print("  2. 确保使用了 TigerHill interceptor")
            print("  3. 检查是否有 [TigerHill] 日志输出")
            return

        # 按修改时间排序，取最新的
        filepath = max(session_files, key=lambda p: p.stat().st_mtime)

        print(f"📁 自动选择最新文件: {filepath.name}")
        print(f"   目录: {capture_dir}")
        print()

    view_capture(str(filepath))

if __name__ == '__main__':
    main()

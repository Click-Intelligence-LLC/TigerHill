#!/usr/bin/env python3
"""
分析Gemini CLI多轮对话捕获数据 V2
处理gzip压缩的响应数据
"""

import json
import glob
import os
import gzip
import io
from datetime import datetime

def decompress_if_needed(data):
    """如果数据是gzip压缩的，解压缩它"""
    if isinstance(data, str):
        try:
            # 尝试作为UTF-8字符串解码
            return data
        except:
            pass

    # 尝试gzip解压
    try:
        if isinstance(data, str):
            # 字符串转bytes
            data_bytes = data.encode('latin1')
        else:
            data_bytes = data

        decompressed = gzip.decompress(data_bytes)
        return decompressed.decode('utf-8')
    except:
        return None

def analyze_session_file(filepath):
    """分析单个会话文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    session_info = {
        'file': os.path.basename(filepath),
        'session_id': data.get('session_id', 'unknown'),
        'start_time': data.get('start_time'),
        'duration': data.get('duration', 0),
        'total_turns': len(data.get('turns', [])),
        'turns_analysis': []
    }

    # 分析每个turn
    for turn_idx, turn in enumerate(data.get('turns', []), 1):
        turn_info = {
            'turn_number': turn_idx,
            'timestamp': turn.get('timestamp'),
            'user_input': None,
            'system_instruction_length': 0,
            'ai_response': None,
            'ai_response_length': 0,
            'tokens': {
                'prompt': 0,
                'completion': 0,
                'total': 0
            }
        }

        # 分析请求 - 查找包含body的POST请求
        for req in turn.get('requests', []):
            if req.get('method') == 'POST':
                # 检查是否有请求体（可能在headers里或单独字段）
                url = req.get('url', '')

                # 如果URL包含generateContent,尝试查找下一个请求
                if 'generateContent' in url:
                    # 请求体可能在后续的请求中
                    pass

        # 分析响应
        for resp in turn.get('responses', []):
            raw_text = resp.get('raw_text', '')
            if raw_text:
                # 尝试解压
                decompressed = decompress_if_needed(raw_text)

                if decompressed:
                    try:
                        resp_json = json.loads(decompressed)

                        # 提取AI响应文本
                        if 'candidates' in resp_json:
                            for candidate in resp_json['candidates']:
                                content = candidate.get('content', {})
                                parts = content.get('parts', [])
                                if parts and 'text' in parts[0]:
                                    turn_info['ai_response'] = parts[0]['text']
                                    turn_info['ai_response_length'] = len(parts[0]['text'])

                        # 提取token统计
                        if 'usageMetadata' in resp_json:
                            usage = resp_json['usageMetadata']
                            turn_info['tokens'] = {
                                'prompt': usage.get('promptTokenCount', 0),
                                'completion': usage.get('candidatesTokenCount', 0),
                                'total': usage.get('totalTokenCount', 0)
                            }
                    except json.JSONDecodeError:
                        # 可能是其他类型的响应
                        pass

        session_info['turns_analysis'].append(turn_info)

    return session_info

def print_detailed_analysis(sessions):
    """打印详细分析"""
    print("=" * 100)
    print("  TigerHill Gemini CLI 多轮对话测试 - 详细分析报告")
    print("=" * 100)
    print()

    total_tokens = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_turns = 0
    total_response_chars = 0

    for session_idx, session in enumerate(sessions, 1):
        print(f"╔═══════════════════════════════════════════════════════════════════════════════════════╗")
        print(f"║ 会话 {session_idx}/{len(sessions)}")
        print(f"╠═══════════════════════════════════════════════════════════════════════════════════════╣")
        print(f"║ Session ID: {session['session_id'][:40]}...")
        print(f"║ 持续时间: {session['duration']:.2f} 秒")
        print(f"║ 轮次数: {session['total_turns']}")
        print(f"╚═══════════════════════════════════════════════════════════════════════════════════════╝")
        print()

        for turn in session['turns_analysis']:
            total_turns += 1

            print(f"  ┌─ Turn {turn['turn_number']} ────────────────────────────────────────────────")
            print(f"  │")

            if turn['user_input']:
                user_preview = turn['user_input'][:150].replace('\n', ' ')
                print(f"  │ 👤 用户输入:")
                print(f"  │    {user_preview}...")

            if turn['ai_response']:
                ai_preview = turn['ai_response'][:300].replace('\n', ' ')
                print(f"  │")
                print(f"  │ 🤖 AI响应 ({turn['ai_response_length']} 字符):")
                lines = [turn['ai_response'][i:i+80] for i in range(0, min(len(turn['ai_response']), 320), 80)]
                for line in lines[:4]:
                    print(f"  │    {line}")
                if turn['ai_response_length'] > 320:
                    print(f"  │    ...")

                total_response_chars += turn['ai_response_length']

            if turn['tokens']['total'] > 0:
                print(f"  │")
                print(f"  │ 📊 Token统计:")
                print(f"  │    Prompt: {turn['tokens']['prompt']:,} tokens")
                print(f"  │    Completion: {turn['tokens']['completion']:,} tokens")
                print(f"  │    Total: {turn['tokens']['total']:,} tokens")

                total_tokens += turn['tokens']['total']
                total_prompt_tokens += turn['tokens']['prompt']
                total_completion_tokens += turn['tokens']['completion']

            print(f"  │")
            print(f"  └────────────────────────────────────────────────────────────")
            print()

    # 总体统计
    print("=" * 100)
    print("📊 总体统计")
    print("=" * 100)
    print(f"总会话数: {len(sessions)}")
    print(f"总轮次数: {total_turns}")
    print(f"总 Token 数: {total_tokens:,}")
    print(f"  - Prompt Tokens: {total_prompt_tokens:,}")
    print(f"  - Completion Tokens: {total_completion_tokens:,}")
    if total_turns > 0:
        print(f"平均每轮 Tokens: {total_tokens / total_turns:.1f}")
    print(f"总响应字符数: {total_response_chars:,}")
    if total_turns > 0:
        print(f"平均响应长度: {total_response_chars / total_turns:.0f} 字符")
    print()

    # 成本估算
    prompt_cost = (total_prompt_tokens / 1000) * 0.00025
    completion_cost = (total_completion_tokens / 1000) * 0.0005
    total_cost = prompt_cost + completion_cost

    print("💰 成本估算 (Gemini 2.0 Flash 定价)")
    print("=" * 100)
    print(f"Prompt 成本: ${prompt_cost:.6f}")
    print(f"Completion 成本: ${completion_cost:.6f}")
    print(f"总成本: ${total_cost:.6f}")
    print()

    print("=" * 100)
    print("分析完成！")
    print("=" * 100)

def main():
    capture_dir = "/Users/yinaruto/MyProjects/ChatLLM/TigerHill/prompt_captures/multiturn_test"

    # 查找所有会话文件
    session_files = sorted(glob.glob(f"{capture_dir}/session_*.json"))

    if not session_files:
        print("❌ 未找到会话文件")
        return

    print(f"找到 {len(session_files)} 个会话文件")
    print()

    # 分析所有会话
    sessions = []
    for filepath in session_files:
        try:
            session_info = analyze_session_file(filepath)
            sessions.append(session_info)
        except Exception as e:
            print(f"⚠️  分析文件失败: {filepath}")
            print(f"   错误: {e}")
            import traceback
            traceback.print_exc()
            continue

    # 打印详细分析
    print_detailed_analysis(sessions)

if __name__ == "__main__":
    main()

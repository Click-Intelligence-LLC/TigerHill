#!/usr/bin/env python3
"""
分析Gemini CLI多轮对话捕获数据
"""

import json
import glob
import os
from datetime import datetime
from collections import defaultdict

def analyze_session_file(filepath):
    """分析单个会话文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    session_info = {
        'file': os.path.basename(filepath),
        'session_id': data.get('session_id', 'unknown'),
        'start_time': data.get('start_time'),
        'tool': data.get('metadata', {}).get('tool', 'unknown'),
        'total_turns': len(data.get('turns', [])),
        'processes': data.get('metadata', {}).get('processes', []),
        'turns': []
    }

    # 分析每个turn
    for turn_idx, turn in enumerate(data.get('turns', []), 1):
        turn_info = {
            'turn_number': turn_idx,
            'conversation_length': turn.get('conversation_length', 0),
            'timestamp': turn.get('timestamp'),
            'requests': [],
            'responses': [],
            'statistics': {}
        }

        # 分析请求
        for req in turn.get('requests', []):
            if req.get('type') == 'gemini_request':
                request_data = req.get('data', {})
                contents = request_data.get('contents', [])

                # 提取用户输入
                user_input = None
                for content in contents:
                    if content.get('role') == 'user':
                        parts = content.get('parts', [])
                        if parts and 'text' in parts[0]:
                            user_input = parts[0]['text']
                            break

                # 提取系统指令
                system_instruction = request_data.get('systemInstruction', {})
                system_text = None
                if system_instruction:
                    parts = system_instruction.get('parts', [])
                    if parts and 'text' in parts[0]:
                        system_text = parts[0]['text']

                turn_info['requests'].append({
                    'user_input': user_input,
                    'system_instruction_length': len(system_text) if system_text else 0,
                    'model': request_data.get('model'),
                    'timestamp': req.get('timestamp')
                })

        # 分析响应
        for resp in turn.get('responses', []):
            if resp.get('type') == 'gemini_response':
                response_data = resp.get('data', {})
                candidates = response_data.get('candidates', [])

                response_text = None
                if candidates:
                    content = candidates[0].get('content', {})
                    parts = content.get('parts', [])
                    if parts and 'text' in parts[0]:
                        response_text = parts[0]['text']

                # Token使用统计
                usage = response_data.get('usageMetadata', {})

                turn_info['responses'].append({
                    'text_length': len(response_text) if response_text else 0,
                    'text_preview': response_text[:200] if response_text else None,
                    'prompt_tokens': usage.get('promptTokenCount', 0),
                    'candidates_tokens': usage.get('candidatesTokenCount', 0),
                    'total_tokens': usage.get('totalTokenCount', 0),
                    'timestamp': resp.get('timestamp')
                })

                turn_info['statistics'] = {
                    'prompt_tokens': usage.get('promptTokenCount', 0),
                    'completion_tokens': usage.get('candidatesTokenCount', 0),
                    'total_tokens': usage.get('totalTokenCount', 0)
                }

        session_info['turns'].append(turn_info)

    return session_info

def calculate_overall_statistics(sessions):
    """计算总体统计"""
    stats = {
        'total_sessions': len(sessions),
        'total_turns': 0,
        'total_tokens': 0,
        'total_prompt_tokens': 0,
        'total_completion_tokens': 0,
        'avg_tokens_per_turn': 0,
        'avg_response_length': 0,
        'total_response_chars': 0
    }

    turn_count = 0
    response_lengths = []

    for session in sessions:
        stats['total_turns'] += len(session['turns'])
        for turn in session['turns']:
            turn_count += 1
            if turn['statistics']:
                stats['total_tokens'] += turn['statistics'].get('total_tokens', 0)
                stats['total_prompt_tokens'] += turn['statistics'].get('prompt_tokens', 0)
                stats['total_completion_tokens'] += turn['statistics'].get('completion_tokens', 0)

            for resp in turn['responses']:
                if resp['text_length']:
                    response_lengths.append(resp['text_length'])
                    stats['total_response_chars'] += resp['text_length']

    if turn_count > 0:
        stats['avg_tokens_per_turn'] = stats['total_tokens'] / turn_count

    if response_lengths:
        stats['avg_response_length'] = sum(response_lengths) / len(response_lengths)

    return stats

def print_analysis(sessions, overall_stats):
    """打印分析结果"""
    print("=" * 80)
    print("  TigerHill 多轮对话分析报告")
    print("=" * 80)
    print()

    print("📊 总体统计")
    print("-" * 80)
    print(f"总会话数: {overall_stats['total_sessions']}")
    print(f"总轮次数: {overall_stats['total_turns']}")
    print(f"总 Token 数: {overall_stats['total_tokens']:,}")
    print(f"  - Prompt Tokens: {overall_stats['total_prompt_tokens']:,}")
    print(f"  - Completion Tokens: {overall_stats['total_completion_tokens']:,}")
    print(f"平均每轮 Tokens: {overall_stats['avg_tokens_per_turn']:.1f}")
    print(f"平均响应长度: {overall_stats['avg_response_length']:.0f} 字符")
    print(f"总响应字符数: {overall_stats['total_response_chars']:,}")
    print()

    # 估算成本（基于Gemini Pro定价）
    # Gemini Pro: $0.00025 per 1K prompt tokens, $0.0005 per 1K completion tokens
    prompt_cost = (overall_stats['total_prompt_tokens'] / 1000) * 0.00025
    completion_cost = (overall_stats['total_completion_tokens'] / 1000) * 0.0005
    total_cost = prompt_cost + completion_cost

    print("💰 成本估算 (Gemini Pro 定价)")
    print("-" * 80)
    print(f"Prompt 成本: ${prompt_cost:.6f}")
    print(f"Completion 成本: ${completion_cost:.6f}")
    print(f"总成本: ${total_cost:.6f}")
    print()

    # 按会话详细分析
    print("📝 各轮次详细分析")
    print("=" * 80)
    print()

    for idx, session in enumerate(sessions, 1):
        print(f"会话 {idx}/{len(sessions)}")
        print(f"Session ID: {session['session_id'][:30]}...")
        print(f"文件: {session['file']}")
        print(f"轮次数: {session['total_turns']}")
        print()

        for turn in session['turns']:
            print(f"  ┌─ Turn {turn['turn_number']}")
            print(f"  │")

            # 用户输入
            for req in turn['requests']:
                if req['user_input']:
                    input_preview = req['user_input'][:100].replace('\n', ' ')
                    print(f"  │ 👤 用户输入: {input_preview}...")
                    if req['system_instruction_length']:
                        print(f"  │    系统指令长度: {req['system_instruction_length']} 字符")

            # AI响应
            for resp in turn['responses']:
                if resp['text_preview']:
                    preview = resp['text_preview'][:100].replace('\n', ' ')
                    print(f"  │ 🤖 AI响应: {preview}...")
                    print(f"  │    响应长度: {resp['text_length']} 字符")
                    print(f"  │    Tokens: {resp['total_tokens']} (提示: {resp['prompt_tokens']}, 完成: {resp['candidates_tokens']})")

            print(f"  │")

        print(f"  └─────────────────────────────────────────")
        print()

    print("=" * 80)
    print("分析完成！")
    print("=" * 80)

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
            continue

    # 计算总体统计
    overall_stats = calculate_overall_statistics(sessions)

    # 打印分析结果
    print_analysis(sessions, overall_stats)

    # 保存分析报告
    report_file = f"{capture_dir}/analysis_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'sessions': sessions,
            'overall_statistics': overall_stats,
            'generated_at': datetime.now().isoformat()
        }, f, indent=2, ensure_ascii=False)

    print()
    print(f"📄 详细报告已保存到: {report_file}")

if __name__ == "__main__":
    main()

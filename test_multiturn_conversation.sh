#!/bin/bash

# TigerHill 多轮对话测试脚本

set -e

echo "=========================================="
echo "TigerHill 多轮对话捕获测试"
echo "=========================================="
echo ""

# 配置
CAPTURE_PATH="/Users/yinaruto/MyProjects/ChatLLM/TigerHill/prompt_captures/multiturn_test"
INTERCEPTOR="/Users/yinaruto/MyProjects/ChatLLM/TigerHill/tigerhill/observer/gemini_session_interceptor.cjs"

mkdir -p "$CAPTURE_PATH"

echo "捕获路径: $CAPTURE_PATH"
echo "拦截器: gemini_session_interceptor.cjs"
echo ""

# 清理旧文件
echo "清理旧的捕获文件..."
rm -f "$CAPTURE_PATH"/*.json
echo ""

# 创建测试对话脚本
CONVERSATION_SCRIPT="$CAPTURE_PATH/conversation.txt"
cat > "$CONVERSATION_SCRIPT" << 'EOF'
什么是斐波那契数列？
请用Python实现一个计算斐波那契数列的函数
现在用动态规划优化这个函数
这个优化的时间复杂度是多少？
EOF

echo "======================================"
echo "测试场景 1: 交互式多轮对话"
echo "======================================"
echo ""
echo "将模拟以下对话："
cat "$CONVERSATION_SCRIPT"
echo ""
echo "按 Ctrl+C 结束对话"
echo ""

# 使用 expect 进行交互（如果没有 expect，使用手动方式）
if command -v expect &> /dev/null; then
    expect << 'EXPECT_SCRIPT'
set timeout 60

# 启动 gemini-cli
spawn env NODE_OPTIONS="--require /Users/yinaruto/MyProjects/ChatLLM/TigerHill/tigerhill/observer/gemini_session_interceptor.cjs" TIGERHILL_CAPTURE_PATH="/Users/yinaruto/MyProjects/ChatLLM/TigerHill/prompt_captures/multiturn_test" node /Users/yinaruto/MyProjects/ChatLLM/gemini-cli/bundle/gemini.js

expect "Ready for your command."

# 第一轮
send "什么是斐波那契数列？\r"
expect "Ready for your command." { send "请用Python实现一个计算斐波那契数列的函数\r" }

# 第二轮
expect "Ready for your command." { send "现在用动态规划优化这个函数\r" }

# 第三轮
expect "Ready for your command." { send "这个优化的时间复杂度是多少？\r" }

# 第四轮（退出）
expect "Ready for your command." { send "exit\r" }

expect eof
EXPECT_SCRIPT
else
    echo "⚠️  未安装 expect，请手动测试"
    echo ""
    echo "请运行以下命令，然后逐个输入测试对话："
    echo ""
    echo "NODE_OPTIONS=\"--require $INTERCEPTOR\" \\"
    echo "  TIGERHILL_CAPTURE_PATH=\"$CAPTURE_PATH\" \\"
    echo "  node /Users/yinaruto/MyProjects/ChatLLM/gemini-cli/bundle/gemini.js"
    echo ""
    echo "然后输入："
    cat "$CONVERSATION_SCRIPT"
    echo ""
    read -p "完成后按 Enter 继续..."
fi

echo ""
echo "======================================"
echo "测试场景 2: 单命令多轮对话"
echo "======================================"
echo ""

# 测试：单个复杂任务
echo "测试：让AI执行一个需要多步骤的复杂任务"
NODE_OPTIONS="--require $INTERCEPTOR" \
  TIGERHILL_CAPTURE_PATH="$CAPTURE_PATH" \
  node /Users/yinaruto/MyProjects/ChatLLM/gemini-cli/bundle/gemini.js -p "创建一个计算器程序：1) 先设计接口；2) 实现基本运算；3) 添加错误处理；4) 写单元测试"

echo ""
echo "======================================"
echo "分析捕获结果"
echo "======================================"
echo ""

# 等待文件写入
sleep 2

# 列出捕获的文件
echo "捕获的文件："
ls -lh "$CAPTURE_PATH"/*.json 2>/dev/null | grep -v ".session_store" || echo "没有捕获文件"
echo ""

# 分析会话存储
if [ -f "$CAPTURE_PATH/.session_store.json" ]; then
    echo "会话存储内容："
    cat "$CAPTURE_PATH/.session_store.json" | python3 -m json.tool | head -50
    echo ""
fi

# 分析捕获文件
for capture_file in "$CAPTURE_PATH"/session_*.json; do
    if [ -f "$capture_file" ]; then
        echo "======================================"
        echo "分析: $(basename $capture_file)"
        echo "======================================"

        python3 << EOF
import json
import sys

try:
    with open('$capture_file', 'r') as f:
        data = json.load(f)

    print(f"会话 ID: {data.get('session_id', 'N/A')}")
    print(f"持续时间: {data.get('duration', 0):.2f}秒")
    print(f"涉及进程: {len(data.get('metadata', {}).get('processes', []))}")
    print()

    # 分析每一轮
    turns = data.get('turns', [])
    print(f"对话轮数: {len(turns)}")
    print()

    for i, turn in enumerate(turns, 1):
        print(f"--- 第 {i} 轮 ---")
        print(f"时间: {turn.get('timestamp', 0)}")
        print(f"请求数: {len(turn.get('requests', []))}")
        print(f"响应数: {len(turn.get('responses', []))}")

        # 显示用户输入
        for req in turn.get('requests', []):
            if 'user_input' in req:
                user_input = req['user_input']
                # 只显示最后的用户输入（跳过上下文设置）
                if not user_input.startswith('This is the Gemini CLI'):
                    print(f"用户: {user_input[:100]}...")
                    break

        # 显示AI响应
        for resp in turn.get('responses', []):
            if 'text' in resp:
                print(f"AI: {resp['text'][:100]}...")
                if 'usage' in resp:
                    usage = resp['usage']
                    print(f"Tokens: {usage.get('total_tokens', 0)} total")
                break

        print()

    # 统计信息
    stats = data.get('statistics', {})
    if stats:
        print("=== 统计信息 ===")
        print(f"总请求数: {stats.get('total_requests', 0)}")
        print(f"总响应数: {stats.get('total_responses', 0)}")
        print(f"总Token数: {stats.get('total_tokens', 0)}")

except Exception as e:
    print(f"分析失败: {e}", file=sys.stderr)
EOF

        echo ""
    fi
done

# 生成测试报告
REPORT_FILE="$CAPTURE_PATH/test_report.md"
cat > "$REPORT_FILE" << 'REPORT_EOF'
# 多轮对话捕获测试报告

## 测试日期
REPORT_EOF
date >> "$REPORT_FILE"

cat >> "$REPORT_FILE" << 'REPORT_EOF'

## 测试场景

### 场景1: 交互式多轮对话
测试连续多轮对话时的捕获能力

### 场景2: 单命令复杂任务
测试单个命令触发的多步骤交互

## 测试结果

REPORT_EOF

# 添加捕获文件列表
echo "### 捕获的文件" >> "$REPORT_FILE"
echo '```' >> "$REPORT_FILE"
ls -lh "$CAPTURE_PATH"/*.json 2>/dev/null | grep -v ".session_store" >> "$REPORT_FILE" || echo "无捕获文件" >> "$REPORT_FILE"
echo '```' >> "$REPORT_FILE"

echo "" >> "$REPORT_FILE"
echo "## 详细分析" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "详细分析结果见上方终端输出" >> "$REPORT_FILE"

echo ""
echo "======================================"
echo "测试完成！"
echo "======================================"
echo ""
echo "测试报告: $REPORT_FILE"
echo "捕获文件目录: $CAPTURE_PATH"
echo ""
echo "后续步骤："
echo "1. 检查是否正确捕获了所有对话轮次"
echo "2. 验证会话ID是否一致"
echo "3. 检查对话历史是否完整"
echo "4. 验证token统计是否准确"

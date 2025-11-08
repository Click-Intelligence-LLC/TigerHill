#!/bin/bash

# TigerHill Gemini CLI Capture - 修复版本测试脚本

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  TigerHill Gemini CLI Capture - Fixed Version Test            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 检查 Gemini CLI 路径
GEMINI_CLI_PATH="../gemini-cli/bundle/gemini.js"
if [ ! -f "$GEMINI_CLI_PATH" ]; then
    echo -e "${RED}❌ Error: Gemini CLI not found at $GEMINI_CLI_PATH${NC}"
    echo ""
    echo "Please update GEMINI_CLI_PATH in this script."
    echo "Example: GEMINI_CLI_PATH=\"/path/to/gemini-cli/bundle/gemini.js\""
    exit 1
fi

echo -e "${BLUE}📁 Gemini CLI Path:${NC} $GEMINI_CLI_PATH"
echo ""

# 设置捕获目录
CAPTURE_DIR="./prompt_captures/gemini_cli_fixed"
mkdir -p "$CAPTURE_DIR"

echo -e "${BLUE}📂 Capture Directory:${NC} $CAPTURE_DIR"
echo ""

# 显示问题说明
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}问题说明${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "❌ 旧版本 interceptor 的问题:"
echo "   • 直接消费了 HTTP 响应流 (res.on('data'))"
echo "   • 导致 Gemini CLI 无法读取响应数据"
echo "   • 结果: 'Requested entity was not found' 错误"
echo ""
echo "✅ 修复版本的改进:"
echo "   • 使用透明代理模式，包装 res.emit 方法"
echo "   • 复制数据副本给 TigerHill，同时保持原始流完整"
echo "   • Gemini CLI 能正常接收和处理响应"
echo ""

# 显示将要执行的命令
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}将要执行的命令${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}环境变量:${NC}"
echo "  TIGERHILL_CAPTURE_PATH=\"$CAPTURE_DIR\""
echo "  TIGERHILL_DEBUG=\"true\""
echo "  TIGERHILL_SAVE_RAW=\"true\""
echo "  NODE_OPTIONS=\"--require ./tigerhill/observer/gemini_session_interceptor.cjs\""
echo ""
echo -e "${BLUE}命令:${NC}"
echo "  node $GEMINI_CLI_PATH"
echo ""

# 提示用户
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}测试步骤${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "1. 按回车启动 Gemini CLI (修复版 interceptor)"
echo "2. 在 Gemini CLI 中输入测试 prompt，例如:"
echo "   ${BLUE}> 给我创建一个 HTML 页面${NC}"
echo "   ${BLUE}> 添加一些 CSS 样式${NC}"
echo "3. 验证 Gemini CLI 是否正常响应 (不应该有错误)"
echo "4. 输入 ${BLUE}/quit${NC} 退出"
echo "5. 检查捕获的文件"
echo ""

read -p "按 Enter 开始测试 (Ctrl+C 取消)..."
echo ""

# 启动 Gemini CLI (使用修复版 interceptor)
echo -e "${GREEN}▶ 启动 Gemini CLI (修复版 interceptor)...${NC}"
echo ""

TIGERHILL_CAPTURE_PATH="$CAPTURE_DIR" \
TIGERHILL_DEBUG="true" \
TIGERHILL_SAVE_RAW="true" \
NODE_OPTIONS="--require ./tigerhill/observer/gemini_session_interceptor.cjs" \
node "$GEMINI_CLI_PATH"

EXIT_CODE=$?

# 测试完成后的分析
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}测试完成${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Gemini CLI 正常退出 (exit code: $EXIT_CODE)${NC}"
else
    echo -e "${YELLOW}⚠ Gemini CLI 退出码: $EXIT_CODE${NC}"
fi

echo ""
echo -e "${BLUE}📊 捕获文件:${NC}"
ls -lh "$CAPTURE_DIR"/*.json 2>/dev/null | tail -5

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠ 没有找到捕获文件${NC}"
else
    echo ""
    echo -e "${BLUE}📈 最新捕获文件统计:${NC}"
    LATEST_FILE=$(ls -t "$CAPTURE_DIR"/session_*.json 2>/dev/null | head -1)

    if [ -n "$LATEST_FILE" ]; then
        echo -e "  文件: ${YELLOW}$(basename $LATEST_FILE)${NC}"

        # 使用 Python 提取统计信息
        python3 -c "
import json
import sys

try:
    with open('$LATEST_FILE') as f:
        data = json.load(f)

    stats = data.get('statistics', {})
    conv_stats = stats.get('conversation_statistics', {})

    print(f\"  Session ID: {data.get('session_id', 'N/A')}\")
    print(f\"  Total turns: {stats.get('total_turns', 0)}\")
    print(f\"  Total tokens: {stats.get('total_tokens', 0)}\")
    print(f\"  Total messages: {conv_stats.get('total_messages', 0)}\")
    print(f\"  User messages: {conv_stats.get('user_messages', 0)}\")
    print(f\"  Assistant messages: {conv_stats.get('assistant_messages', 0)}\")

    # 检查是否有响应数据
    if data.get('turns'):
        has_responses = any(turn.get('responses') for turn in data['turns'])
        if has_responses:
            print(f\"  ✅ 成功捕获响应数据\")
        else:
            print(f\"  ❌ 没有捕获到响应数据\")
except Exception as e:
    print(f\"  ⚠ 无法解析文件: {e}\", file=sys.stderr)
" 2>/dev/null

        if [ $? -ne 0 ]; then
            echo -e "${YELLOW}  ⚠ 无法解析统计信息 (需要 Python 3)${NC}"
        fi
    fi
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}下一步${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "1. 查看捕获内容:"
echo "   ${BLUE}cat $CAPTURE_DIR/session_*.json | python -m json.tool | less${NC}"
echo ""
echo "2. 对比旧版本测试:"
echo "   ${BLUE}./scripts/test_gemini_capture.sh${NC}"
echo "   (应该会出现 'Requested entity was not found' 错误)"
echo ""
echo "3. 永久使用修复版本:"
echo "   ${BLUE}NODE_OPTIONS=\"--require ./tigerhill/observer/gemini_session_interceptor.cjs\"${NC}"
echo "   (当前仓库已默认包含修复后的拦截器)"
echo ""
echo -e "${YELLOW}💡 如果测试成功（没有错误），说明修复有效！${NC}"
echo ""

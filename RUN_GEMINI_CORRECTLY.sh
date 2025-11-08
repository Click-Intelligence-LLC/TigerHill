#!/bin/bash

# ============================================================================
# TigerHill + Gemini CLI 正确运行方式
# ============================================================================

# 设置颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  TigerHill + Gemini CLI - 正确启动方式                      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 配置路径
GEMINI_CLI_PATH="../gemini-cli/bundle/gemini.js"
CAPTURE_DIR="./prompt_captures/gemini_cli"
INTERCEPTOR_PATH="./tigerhill/observer/gemini_session_interceptor.cjs"

# 检查文件
if [ ! -f "$GEMINI_CLI_PATH" ]; then
    echo -e "${YELLOW}⚠ Gemini CLI 未找到: $GEMINI_CLI_PATH${NC}"
    echo ""
    echo "请修改此脚本中的 GEMINI_CLI_PATH 变量指向正确路径"
    exit 1
fi

if [ ! -f "$INTERCEPTOR_PATH" ]; then
    echo -e "${YELLOW}⚠ Interceptor 未找到: $INTERCEPTOR_PATH${NC}"
    exit 1
fi

# 创建捕获目录
mkdir -p "$CAPTURE_DIR"

echo -e "${BLUE}配置信息:${NC}"
echo "  Gemini CLI: $GEMINI_CLI_PATH"
echo "  Interceptor: $INTERCEPTOR_PATH"
echo "  捕获目录: $CAPTURE_DIR"
echo ""

echo -e "${BLUE}环境变量:${NC}"
echo "  TIGERHILL_CAPTURE_PATH=\"$CAPTURE_DIR\""
echo "  TIGERHILL_DEBUG=\"true\""
echo "  TIGERHILL_SAVE_RAW=\"true\""
echo "  NODE_OPTIONS=\"--require $INTERCEPTOR_PATH\""
echo ""

echo -e "${YELLOW}重要提示:${NC}"
echo "  1. 如果看到 429 错误，这是 Google API 限流，不是 TigerHill 的问题"
echo "  2. 遇到 429 时，请等待几分钟后再试"
echo "  3. 使用简单的问题测试，避免复杂任务"
echo "  4. 应该看到 ${GREEN}[TigerHill Session Interceptor] Active${NC} 日志"
echo ""

read -p "按 Enter 启动 Gemini CLI..."

echo ""
echo -e "${GREEN}>>> 启动中...${NC}"
echo ""

# ============================================================================
# 正确的命令格式 - 所有环境变量在一行
# ============================================================================

TIGERHILL_CAPTURE_PATH="$CAPTURE_DIR" \
TIGERHILL_DEBUG="true" \
TIGERHILL_SAVE_RAW="true" \
NODE_OPTIONS="--require $INTERCEPTOR_PATH" \
node "$GEMINI_CLI_PATH"

# ============================================================================

EXIT_CODE=$?

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Gemini CLI 已退出 (退出码: $EXIT_CODE)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# 显示捕获文件
echo -e "${BLUE}捕获文件:${NC}"
SESSION_COUNT=$(ls -1 "$CAPTURE_DIR"/session_*.json 2>/dev/null | wc -l | tr -d ' ')

if [ "$SESSION_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ 找到 $SESSION_COUNT 个会话文件${NC}"
    echo ""
    ls -lht "$CAPTURE_DIR"/session_*.json | head -5
    echo ""

    # 显示最新文件统计
    LATEST_FILE=$(ls -t "$CAPTURE_DIR"/session_*.json 2>/dev/null | head -1)
    if [ -n "$LATEST_FILE" ]; then
        echo -e "${BLUE}最新会话统计:${NC}"
        python3 -c "
import json
try:
    with open('$LATEST_FILE') as f:
        data = json.load(f)
    print(f\"  文件: $(basename $LATEST_FILE)\")
    print(f\"  Session ID: {data.get('session_id', 'N/A')[:20]}...\")
    stats = data.get('statistics', {})
    print(f\"  Total turns: {stats.get('total_turns', 0)}\")
    print(f\"  Total tokens: {stats.get('total_tokens', 0)}\")
except Exception as e:
    print(f\"  无法解析: {e}\")
" 2>/dev/null || echo "  (需要 Python 3 查看统计)"
    fi
else
    echo -e "${YELLOW}⚠ 没有找到捕获文件${NC}"
    echo ""
    echo "可能的原因："
    echo "  1. Interceptor 未正确加载"
    echo "  2. 没有成功的 API 请求（都失败了）"
    echo "  3. 遇到 429 错误，请求被拒绝"
    echo ""
    echo "建议："
    echo "  • 运行诊断脚本: ./scripts/diagnose_gemini.sh"
    echo "  • 查看 429 错误文档: cat GEMINI_429_ERROR.md"
fi

echo ""
echo -e "${BLUE}查看捕获内容:${NC}"
echo "  cat $CAPTURE_DIR/session_*.json | python -m json.tool | less"
echo ""

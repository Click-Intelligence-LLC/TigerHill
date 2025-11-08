#!/bin/bash

# TigerHill Gemini CLI 诊断脚本

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  TigerHill Gemini CLI 诊断工具                              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 检查文件路径
GEMINI_CLI_PATH="../gemini-cli/bundle/gemini.js"
INTERCEPTOR_PATH="./tigerhill/observer/gemini_session_interceptor.cjs"

echo -e "${BLUE}[1/5] 检查文件存在性${NC}"
echo ""

if [ -f "$GEMINI_CLI_PATH" ]; then
    echo -e "  ${GREEN}✓${NC} Gemini CLI: $GEMINI_CLI_PATH"
else
    echo -e "  ${RED}✗${NC} Gemini CLI 未找到: $GEMINI_CLI_PATH"
    echo ""
    echo "请更新脚本中的 GEMINI_CLI_PATH 变量指向正确的路径"
    exit 1
fi

if [ -f "$INTERCEPTOR_PATH" ]; then
    echo -e "  ${GREEN}✓${NC} Interceptor: $INTERCEPTOR_PATH"
else
    echo -e "  ${RED}✗${NC} Interceptor 不存在: $INTERCEPTOR_PATH"
    exit 1
fi

echo ""
echo -e "${BLUE}[2/5] 检查 Node.js 版本${NC}"
echo ""

NODE_VERSION=$(node --version 2>/dev/null)
if [ $? -eq 0 ]; then
    echo -e "  ${GREEN}✓${NC} Node.js: $NODE_VERSION"
else
    echo -e "  ${RED}✗${NC} Node.js 未安装"
    exit 1
fi

echo ""
echo -e "${BLUE}[3/5] 测试不带 interceptor 的 Gemini CLI${NC}"
echo ""
echo "这将启动 Gemini CLI 但不加载 TigerHill interceptor"
echo "用于验证 Gemini CLI 本身是否正常工作"
echo ""
read -p "按 Enter 开始测试 (输入一个简单问题后立即 /quit，Ctrl+C 跳过)..."

# 清理之前的错误报告
rm -f /var/folders/*/gemini-client-error-*.json 2>/dev/null

# 不带 interceptor 运行
echo ""
echo -e "${YELLOW}>>> 不带 interceptor 启动 Gemini CLI${NC}"
echo ""

timeout 60 node "$GEMINI_CLI_PATH" 2>&1 | tee /tmp/gemini_no_interceptor.log &
GEMINI_PID=$!

wait $GEMINI_PID
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ Gemini CLI 正常退出${NC}"
elif [ $EXIT_CODE -eq 124 ]; then
    echo -e "${YELLOW}⚠ 测试超时（60秒）${NC}"
else
    echo -e "${YELLOW}⚠ Gemini CLI 退出码: $EXIT_CODE${NC}"
fi

# 检查错误日志
if grep -q "429" /tmp/gemini_no_interceptor.log 2>/dev/null; then
    echo -e "${RED}✗ 检测到 429 错误 (API 限流)${NC}"
    echo ""
    echo "  这是 Google Gemini API 的配额限制问题，不是 TigerHill 的问题。"
    echo "  解决方法："
    echo "    1. 等待几分钟再试"
    echo "    2. 检查你的 Google Cloud 配额"
    echo "    3. 切换到不同的 Google 账户"
    echo ""
    read -p "是否继续测试 interceptor？(y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

if grep -q "Requested entity was not found" /tmp/gemini_no_interceptor.log 2>/dev/null; then
    echo -e "${RED}✗ 检测到 'Requested entity was not found' 错误${NC}"
    echo ""
    echo "  即使不使用 interceptor，Gemini CLI 也有错误。"
    echo "  这可能是 Gemini CLI 自身的问题，不是 TigerHill 的问题。"
    echo ""
fi

echo ""
echo -e "${BLUE}[4/5] 测试修复版 interceptor${NC}"
echo ""
echo "这将启动 Gemini CLI 并加载 TigerHill 修复版 interceptor"
echo ""

# 设置捕获目录
CAPTURE_DIR="./prompt_captures/gemini_cli_test"
mkdir -p "$CAPTURE_DIR"

echo -e "${YELLOW}配置:${NC}"
echo "  TIGERHILL_CAPTURE_PATH: $CAPTURE_DIR"
echo "  TIGERHILL_DEBUG: true"
echo "  NODE_OPTIONS: --require $INTERCEPTOR_PATH"
echo ""

read -p "按 Enter 开始测试 (输入一个简单问题后立即 /quit，Ctrl+C 跳过)..."

echo ""
echo -e "${YELLOW}>>> 启动 Gemini CLI (修复版 interceptor)${NC}"
echo ""

# 正确的单行命令
TIGERHILL_CAPTURE_PATH="$CAPTURE_DIR" \
TIGERHILL_DEBUG="true" \
TIGERHILL_SAVE_RAW="true" \
NODE_OPTIONS="--require $INTERCEPTOR_PATH" \
timeout 60 node "$GEMINI_CLI_PATH" 2>&1 | tee /tmp/gemini_with_interceptor.log &

GEMINI_PID=$!
wait $GEMINI_PID
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ Gemini CLI 正常退出${NC}"
elif [ $EXIT_CODE -eq 124 ]; then
    echo -e "${YELLOW}⚠ 测试超时（60秒）${NC}"
else
    echo -e "${YELLOW}⚠ Gemini CLI 退出码: $EXIT_CODE${NC}"
fi

echo ""
echo -e "${BLUE}[5/5] 分析结果${NC}"
echo ""

# 检查是否看到 TigerHill 日志
if grep -q "\[TigerHill" /tmp/gemini_with_interceptor.log; then
    echo -e "${GREEN}✓ TigerHill interceptor 已加载${NC}"

    # 检查是否拦截了请求
    if grep -q "Intercepting Gemini API request" /tmp/gemini_with_interceptor.log; then
        echo -e "${GREEN}✓ TigerHill 成功拦截 API 请求${NC}"
    else
        echo -e "${YELLOW}⚠ TigerHill 已加载但没有拦截到请求${NC}"
        echo "  可能是因为："
        echo "    1. 没有发送任何请求"
        echo "    2. 请求失败（429 错误等）"
    fi
else
    echo -e "${RED}✗ TigerHill interceptor 未加载${NC}"
    echo ""
    echo "  可能的原因："
    echo "    1. NODE_OPTIONS 环境变量未正确设置"
    echo "    2. interceptor 文件路径错误"
    echo "    3. Node.js 版本不兼容"
    echo ""
    echo "  调试建议："
    echo "    1. 检查 interceptor 文件: ls -l $INTERCEPTOR_PATH"
    echo "    2. 手动测试加载:"
    echo "       node --require $INTERCEPTOR_PATH -e \"console.log('loaded')\""
fi

# 检查捕获文件
echo ""
echo -e "${BLUE}捕获文件:${NC}"
SESSION_FILES=$(ls -1 "$CAPTURE_DIR"/session_*.json 2>/dev/null | wc -l)

if [ "$SESSION_FILES" -gt 0 ]; then
    echo -e "${GREEN}✓ 找到 $SESSION_FILES 个捕获文件${NC}"
    echo ""
    ls -lh "$CAPTURE_DIR"/session_*.json | tail -3
    echo ""

    # 显示最新文件的统计
    LATEST_FILE=$(ls -t "$CAPTURE_DIR"/session_*.json 2>/dev/null | head -1)
    if [ -n "$LATEST_FILE" ]; then
        echo -e "${BLUE}最新捕获文件统计:${NC}"
        python3 -c "
import json
try:
    with open('$LATEST_FILE') as f:
        data = json.load(f)
    stats = data.get('statistics', {})
    print(f\"  Total turns: {stats.get('total_turns', 0)}\")
    print(f\"  Total tokens: {stats.get('total_tokens', 0)}\")
    print(f\"  Total requests: {stats.get('total_requests', 0)}\")
    print(f\"  Total responses: {stats.get('total_responses', 0)}\")
except Exception as e:
    print(f\"  Error: {e}\")
" 2>/dev/null || echo "  (需要 Python 3 查看统计)"
    fi
else
    echo -e "${YELLOW}⚠ 没有找到捕获文件${NC}"
    echo "  可能是因为："
    echo "    1. Interceptor 未加载"
    echo "    2. 没有成功的 API 请求"
    echo "    3. 所有请求都失败了（429 等错误）"
fi

# 检查 429 错误
echo ""
if grep -q "429" /tmp/gemini_with_interceptor.log 2>/dev/null; then
    echo -e "${RED}⚠ 检测到 API 限流错误 (429)${NC}"
    echo ""
    echo "  ${YELLOW}这是 Google Gemini API 的配额问题，不是 TigerHill 的 bug。${NC}"
    echo ""
    echo "  解决方法："
    echo "    1. 等待几分钟（限流会自动恢复）"
    echo "    2. 检查 Google Cloud 配额: https://console.cloud.google.com/iam-admin/quotas"
    echo "    3. 使用不同的 Google 账户或 API key"
    echo "    4. 升级到付费账户获得更高配额"
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}诊断完成${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# 清理
echo -e "${BLUE}日志文件:${NC}"
echo "  不带 interceptor: /tmp/gemini_no_interceptor.log"
echo "  带 interceptor: /tmp/gemini_with_interceptor.log"
echo ""
echo "查看完整日志："
echo "  ${YELLOW}cat /tmp/gemini_with_interceptor.log${NC}"
echo ""

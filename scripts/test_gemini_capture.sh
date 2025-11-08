#!/bin/bash

# TigerHill Gemini CLI Capture Test Script
# 正确的方式来捕获 Gemini CLI 交互

# 设置颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== TigerHill Gemini CLI Capture Test ===${NC}\n"

# 检查 Gemini CLI 是否存在
GEMINI_CLI_PATH="../gemini-cli/bundle/gemini.js"
if [ ! -f "$GEMINI_CLI_PATH" ]; then
    echo -e "${RED}Error: Gemini CLI not found at $GEMINI_CLI_PATH${NC}"
    echo "Please update GEMINI_CLI_PATH in this script to point to your Gemini CLI location"
    exit 1
fi

# 设置捕获目录
CAPTURE_DIR="./prompt_captures/gemini_cli"
mkdir -p "$CAPTURE_DIR"

echo -e "${YELLOW}Capture directory:${NC} $CAPTURE_DIR"
echo -e "${YELLOW}Gemini CLI path:${NC} $GEMINI_CLI_PATH"
echo ""

# 方式 1: 交互模式（不带初始 prompt）
echo -e "${GREEN}[Method 1] Interactive Mode${NC}"
echo "This will start Gemini CLI in interactive mode with TigerHill capture enabled."
echo "You can chat with Gemini, and all interactions will be captured."
echo ""
echo -e "${YELLOW}Command:${NC}"
echo "TIGERHILL_CAPTURE_PATH=\"$CAPTURE_DIR\" \\"
echo "TIGERHILL_DEBUG=\"true\" \\"
echo "TIGERHILL_SAVE_RAW=\"true\" \\"
echo "NODE_OPTIONS=\"--require ./tigerhill/observer/gemini_session_interceptor.cjs\" \\"
echo "node $GEMINI_CLI_PATH"
echo ""

read -p "Press Enter to start interactive mode (or Ctrl+C to skip)..."

TIGERHILL_CAPTURE_PATH="$CAPTURE_DIR" \
TIGERHILL_DEBUG="true" \
TIGERHILL_SAVE_RAW="true" \
NODE_OPTIONS="--require ./tigerhill/observer/gemini_session_interceptor.cjs" \
node "$GEMINI_CLI_PATH"

echo ""
echo -e "${GREEN}=== Interactive session ended ===${NC}"
echo ""

# 显示捕获的文件
echo -e "${GREEN}Captured files:${NC}"
ls -lh "$CAPTURE_DIR"/*.json 2>/dev/null || echo "No capture files found"

echo ""
echo -e "${GREEN}=== Test Complete ===${NC}"
echo ""
echo -e "${YELLOW}Tips:${NC}"
echo "1. All captured sessions are saved in: $CAPTURE_DIR"
echo "2. You can analyze captures with: python examples/analyze_codex_capture.py"
echo "3. To disable debug output, remove TIGERHILL_DEBUG=\"true\""
echo "4. To reduce file size, remove TIGERHILL_SAVE_RAW=\"true\""

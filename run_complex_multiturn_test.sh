#!/bin/bash

# 复杂多轮对话测试脚本
# 测试场景：让AI完成一个完整的编程任务（设计->实现->优化->解释）

set -e

GEMINI_CLI="/Users/yinaruto/MyProjects/ChatLLM/gemini-cli/bundle/gemini.js"
INTERCEPTOR="/Users/yinaruto/MyProjects/ChatLLM/TigerHill/tigerhill/observer/gemini_session_interceptor.cjs"
CAPTURE_PATH="/Users/yinaruto/MyProjects/ChatLLM/TigerHill/prompt_captures/multiturn_test"

echo "========================================="
echo "  TigerHill 复杂多轮对话测试"
echo "========================================="
echo ""
echo "测试场景: 完整的编程任务（设计->实现->优化->解释）"
echo "捕获路径: $CAPTURE_PATH"
echo ""

# 清理旧的捕获文件
rm -f "$CAPTURE_PATH"/*.json
rm -f .session_store.json

# 轮次1: 设计一个算法
echo "=== 轮次 1: 设计算法 ==="
NODE_OPTIONS="--require $INTERCEPTOR" \
  TIGERHILL_CAPTURE_PATH="$CAPTURE_PATH" \
  node "$GEMINI_CLI" -p "请设计一个Python函数来计算斐波那契数列的第n项，要求使用动态规划方法。只需要给出算法设计思路，不要写代码。"

echo ""
echo "等待2秒..."
sleep 2

# 轮次2: 实现代码
echo ""
echo "=== 轮次 2: 实现代码 ==="
NODE_OPTIONS="--require $INTERCEPTOR" \
  TIGERHILL_CAPTURE_PATH="$CAPTURE_PATH" \
  node "$GEMINI_CLI" -p "很好！现在请根据刚才的设计思路，用Python实现这个函数，包括完整的代码和注释。"

echo ""
echo "等待2秒..."
sleep 2

# 轮次3: 优化代码
echo ""
echo "=== 轮次 3: 优化性能 ==="
NODE_OPTIONS="--require $INTERCEPTOR" \
  TIGERHILL_CAPTURE_PATH="$CAPTURE_PATH" \
  node "$GEMINI_CLI" -p "这个实现很好。请分析一下时间复杂度和空间复杂度，并建议如何进一步优化。"

echo ""
echo "等待2秒..."
sleep 2

# 轮次4: 添加测试
echo ""
echo "=== 轮次 4: 添加测试用例 ==="
NODE_OPTIONS="--require $INTERCEPTOR" \
  TIGERHILL_CAPTURE_PATH="$CAPTURE_PATH" \
  node "$GEMINI_CLI" -p "请为这个函数编写完整的单元测试，包括边界条件测试。使用pytest框架。"

echo ""
echo ""
echo "========================================="
echo "  测试完成！"
echo "========================================="
echo ""
echo "捕获文件已保存到:"
ls -lh "$CAPTURE_PATH"/*.json 2>/dev/null || echo "未找到捕获文件"
echo ""
echo "会话存储:"
ls -lh .session_store.json 2>/dev/null || echo "未找到会话存储"
echo ""

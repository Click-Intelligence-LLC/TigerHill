#!/usr/bin/env bash
set -euo pipefail

# Run Gemini CLI with TigerHill HTTP interceptor using a complex evaluation prompt.
#
# Usage:
#   scripts/run_gemini_complex.sh "自定义问题"
#   TIGERHILL_CAPTURE_PATH=./captures scripts/run_gemini_complex.sh
#
# If no prompt is provided, a default architecture scenario prompt is used.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DEFAULT_PROMPT="你是一名资深云架构师，请用表格和步骤详细说明如何在全球三地区部署一套支持多租户、实时分析的SaaS平台。回答应包含：
1. 系统架构分层与关键组件（包括消息总线、CDC 管道、实时计算引擎、长周期数仓）
2. 数据隔离策略（行级/列级、工作区、VPC）以及多租户权限模型
3. 成本优化与自动扩缩策略
4. 可观测性与回滚预案
5. 关键风险与待验证项
请最后输出一个 30/60/90 天的落地 roadmap。"

PROMPT="${1:-$DEFAULT_PROMPT}"

CAPTURE_ROOT="${TIGERHILL_CAPTURE_PATH:-"$REPO_ROOT/prompt_captures/gemini_cli_complex"}"
mkdir -p "$CAPTURE_ROOT"

INTERCEPTOR="$REPO_ROOT/tigerhill/observer/gemini_http_interceptor.cjs"
CLI_BUNDLE="$REPO_ROOT/../gemini-cli/bundle/gemini.js"

if [[ ! -f "$CLI_BUNDLE" ]]; then
  echo "Gemini CLI bundle not found at $CLI_BUNDLE" >&2
  echo "Update the script with the correct path to gemini.js." >&2
  exit 1
fi

echo "Running Gemini CLI complex test..."
echo "Capture path: $CAPTURE_ROOT"
echo

NODE_OPTIONS="--require $INTERCEPTOR" \
TIGERHILL_CAPTURE_PATH="$CAPTURE_ROOT" \
node "$CLI_BUNDLE" -p "$PROMPT"

echo
echo "Run complete. Captures saved under: $CAPTURE_ROOT"

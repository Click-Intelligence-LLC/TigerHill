#!/bin/bash

# 测试 TigerHill HTTP Interceptor

echo "======================================"
echo "TigerHill Gemini CLI Interceptor Test"
echo "======================================"
echo ""

# 设置捕获路径
CAPTURE_PATH="/Users/yinaruto/MyProjects/ChatLLM/TigerHill/prompt_captures/gemini_cli"
mkdir -p "$CAPTURE_PATH"

echo "Capture path: $CAPTURE_PATH"
echo ""

# 清理旧的捕获文件（可选）
echo "Cleaning old captures..."
rm -f "$CAPTURE_PATH"/capture_*.json
echo ""

# 使用新的 Fetch API 拦截器运行 gemini-cli
echo "Running gemini-cli with Fetch API interceptor..."
echo "Command: 什么是机器学习？"
echo ""

NODE_OPTIONS="--require /Users/yinaruto/MyProjects/ChatLLM/TigerHill/tigerhill/observer/gemini_fetch_interceptor.cjs" \
  TIGERHILL_CAPTURE_PATH="$CAPTURE_PATH" \
  node /Users/yinaruto/MyProjects/ChatLLM/gemini-cli/bundle/gemini.js -p "什么是机器学习？"

echo ""
echo "======================================"
echo "Checking captured files..."
echo "======================================"
echo ""

# 列出捕获的文件
captured_files=$(ls -t "$CAPTURE_PATH"/capture_*.json 2>/dev/null | head -1)

if [ -z "$captured_files" ]; then
    echo "❌ No capture files found!"
    echo ""
    echo "Expected location: $CAPTURE_PATH/capture_*.json"
    exit 1
else
    echo "✅ Found capture file: $captured_files"
    echo ""
    echo "File size: $(du -h "$captured_files" | cut -f1)"
    echo ""

    echo "======================================"
    echo "Capture Summary:"
    echo "======================================"

    # 使用 python 解析 JSON（如果有的话）
    if command -v python3 &> /dev/null; then
        python3 << 'EOF'
import json
import sys
import os

capture_file = os.popen('ls -t /Users/yinaruto/MyProjects/ChatLLM/TigerHill/prompt_captures/gemini_cli/capture_*.json 2>/dev/null | head -1').read().strip()

if capture_file:
    with open(capture_file, 'r') as f:
        data = json.load(f)

    print(f"Capture ID: {data.get('capture_id', 'N/A')}")
    print(f"Agent: {data.get('agent_name', 'N/A')}")
    print(f"Duration: {data.get('duration', 0):.2f}s")
    print(f"")
    print(f"Requests: {len(data.get('requests', []))}")
    print(f"Responses: {len(data.get('responses', []))}")
    print(f"")

    # 显示第一个请求的信息
    if data.get('requests'):
        req = data['requests'][0]
        print("First Request:")
        print(f"  Model: {req.get('model', 'N/A')}")
        print(f"  Prompt (first 100 chars): {str(req.get('prompt_text', 'N/A'))[:100]}...")

        if req.get('system_prompt'):
            print(f"  System Prompt (first 100 chars): {req.get('system_prompt', '')[:100]}...")
        print(f"")

    # 显示第一个响应的信息
    if data.get('responses'):
        resp = data['responses'][0]
        print("First Response:")
        print(f"  Status: {resp.get('status_code', 'N/A')}")
        if resp.get('text'):
            print(f"  Text (first 200 chars): {resp.get('text', '')[:200]}...")
        if resp.get('usage'):
            usage = resp['usage']
            print(f"  Tokens: {usage.get('prompt_tokens', 0)} prompt + {usage.get('completion_tokens', 0)} completion = {usage.get('total_tokens', 0)} total")
EOF
    else
        # 如果没有 python，使用 jq（如果有的话）
        if command -v jq &> /dev/null; then
            jq '{ capture_id, agent_name, duration, request_count: (.requests | length), response_count: (.responses | length) }' "$captured_files"
        else
            echo "Install python3 or jq to see detailed summary"
            echo ""
            echo "Preview (first 50 lines):"
            head -50 "$captured_files"
        fi
    fi
fi

echo ""
echo "======================================"
echo "Test complete!"
echo "======================================"

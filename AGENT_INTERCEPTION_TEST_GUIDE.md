# Agent 拦截测试指南

## 快速开始

本指南提供了针对不同类型 Agent 的测试验证流程。

---

## 测试 1: Gemini CLI 单轮对话

### 目标
验证基本的 prompt 和响应捕获功能

### 步骤

1. **准备环境**
   ```bash
   export TIGERHILL_CAPTURE_PATH="./test_captures/gemini_single"
   mkdir -p "$TIGERHILL_CAPTURE_PATH"
   ```

2. **运行测试**
   ```bash
   NODE_OPTIONS="--require ./tigerhill/observer/gemini_http_interceptor.cjs" \
     TIGERHILL_CAPTURE_PATH="$TIGERHILL_CAPTURE_PATH" \
     node /path/to/gemini-cli/bundle/gemini.js -p "什么是机器学习？"
   ```

3. **验证结果**
   ```bash
   # 查看捕获文件
   ls -lh "$TIGERHILL_CAPTURE_PATH"/*.json

   # 检查内容
   cat "$TIGERHILL_CAPTURE_PATH"/capture_*.json | python3 -m json.tool | less
   ```

4. **检查项**
   - [ ] 捕获文件存在且非空
   - [ ] `systemInstruction` 字段包含路由 prompt
   - [ ] `contents` 包含用户输入"什么是机器学习？"
   - [ ] `responses` 包含 AI 回复
   - [ ] `usage` 字段有 token 统计

---

## 测试 2: Gemini CLI 多轮对话

### 目标
验证会话追踪和多轮对话捕获

### 步骤

1. **使用会话感知拦截器**
   ```bash
   export TIGERHILL_CAPTURE_PATH="./test_captures/gemini_multiturn"
   mkdir -p "$TIGERHILL_CAPTURE_PATH"

   NODE_OPTIONS="--require ./tigerhill/observer/gemini_session_interceptor.cjs" \
     TIGERHILL_CAPTURE_PATH="$TIGERHILL_CAPTURE_PATH" \
     node /path/to/gemini-cli/bundle/gemini.js -p "写一个Python快速排序"
   ```

2. **继续对话**（在同一会话中）
   ```bash
   # 如果 CLI 支持交互模式，继续输入：
   # - "解释一下这个算法的时间复杂度"
   # - "能优化吗？"
   # - "exit"
   ```

3. **验证结果**
   ```bash
   # 查看会话文件
   cat "$TIGERHILL_CAPTURE_PATH"/session_*.json | python3 << 'EOF'
   import json, sys
   data = json.load(sys.stdin)
   print(f"Session ID: {data['session_id']}")
   print(f"Total turns: {len(data['turns'])}")
   for i, turn in enumerate(data['turns'], 1):
       print(f"\nTurn {i}:")
       for req in turn['requests']:
           if 'user_input' in req:
               print(f"  User: {req['user_input'][:50]}...")
       for resp in turn['responses']:
           if 'text' in resp:
               print(f"  AI: {resp['text'][:50]}...")
   EOF
   ```

4. **检查项**
   - [ ] `session_id` 在所有轮次中一致
   - [ ] `turns` 数组包含所有对话轮次
   - [ ] 每轮的 `conversation_length` 递增
   - [ ] 对话历史正确累积

---

## 测试 3: Python OpenAI Agent

### 目标
验证 Python Observer SDK 对 OpenAI 的支持

### 步骤

1. **创建测试脚本** (`test_openai_agent.py`)
   ```python
   from tigerhill.observer import wrap_openai_client, start_capture
   from openai import OpenAI
   import os

   # 启动捕获
   capture = start_capture(
       agent_name="openai_test",
       task="Test OpenAI integration",
       export_path="./test_captures/openai"
   )

   # 包装客户端
   client = wrap_openai_client(OpenAI())

   # 单轮对话
   print("Testing single-turn conversation...")
   response = client.chat.completions.create(
       model="gpt-4",
       messages=[
           {"role": "system", "content": "You are a helpful assistant."},
           {"role": "user", "content": "Explain quantum computing in one sentence."}
       ]
   )
   print(f"Response: {response.choices[0].message.content}")

   # 多轮对话
   print("\nTesting multi-turn conversation...")
   messages = [
       {"role": "system", "content": "You are a coding tutor."}
   ]

   for user_input in [
       "What is a closure in Python?",
       "Can you show me an example?",
       "Explain the benefits"
   ]:
       messages.append({"role": "user", "content": user_input})
       response = client.chat.completions.create(
           model="gpt-4",
           messages=messages
       )
       assistant_msg = response.choices[0].message.content
       messages.append({"role": "assistant", "content": assistant_msg})
       print(f"Turn: {user_input[:30]}... -> {assistant_msg[:50]}...")

   # 结束捕获
   capture.end()
   print(f"\nCapture saved to: {capture.export_path}")
   ```

2. **运行测试**
   ```bash
   python test_openai_agent.py
   ```

3. **验证结果**
   ```bash
   # 查看捕获文件
   ls -lh test_captures/openai/

   # 分析内容
   python << 'EOF'
   import json
   import glob

   for file in glob.glob('test_captures/openai/capture_*.json'):
       with open(file) as f:
           data = json.load(f)
       print(f"File: {file}")
       print(f"  Agent: {data['agent_name']}")
       print(f"  Requests: {len(data['requests'])}")
       print(f"  Has system prompt: {'system_prompt' in data['requests'][0] if data['requests'] else False}")
       print()
   EOF
   ```

4. **检查项**
   - [ ] 单轮和多轮对话都被捕获
   - [ ] 系统 prompt 正确记录
   - [ ] 对话历史完整
   - [ ] Token 使用统计准确

---

## 测试 4: Python Anthropic Agent

### 目标
验证 Anthropic Claude API 的支持

### 步骤

1. **创建测试脚本** (`test_anthropic_agent.py`)
   ```python
   from tigerhill.observer import wrap_anthropic_client, start_capture
   from anthropic import Anthropic

   capture = start_capture(
       agent_name="claude_test",
       task="Test Claude integration",
       export_path="./test_captures/anthropic"
   )

   client = wrap_anthropic_client(Anthropic())

   response = client.messages.create(
       model="claude-3-5-sonnet-20241022",
       max_tokens=1024,
       system="You are a helpful coding assistant.",
       messages=[
           {"role": "user", "content": "Write a Python function to calculate factorial"}
       ]
   )

   print(response.content[0].text)
   capture.end()
   ```

2. **运行并验证**
   ```bash
   python test_anthropic_agent.py
   ls -lh test_captures/anthropic/
   ```

3. **检查项**
   - [ ] 系统 prompt 被捕获
   - [ ] 用户消息完整
   - [ ] Claude 响应包含代码
   - [ ] Token 使用记录正确

---

## 测试 5: Node.js 通用 Agent

### 目标
验证 Node.js HTTP 拦截器对不同 LLM 的支持

### 步骤

1. **创建 OpenAI 测试** (`test_nodejs_openai.js`)
   ```javascript
   const OpenAI = require('openai');

   async function main() {
       const client = new OpenAI();

       const completion = await client.chat.completions.create({
           model: "gpt-4",
           messages: [
               {role: "system", content: "You are helpful."},
               {role: "user", content: "What is async/await?"}
           ]
       });

       console.log(completion.choices[0].message.content);
   }

   main();
   ```

2. **运行测试**
   ```bash
   NODE_OPTIONS="--require ./tigerhill/observer/gemini_http_interceptor.cjs" \
     TIGERHILL_CAPTURE_PATH="./test_captures/nodejs_openai" \
     node test_nodejs_openai.js
   ```

3. **验证**（需要先更新拦截器以支持 api.openai.com）
   ```bash
   # 检查是否捕获到 OpenAI 请求
   cat test_captures/nodejs_openai/capture_*.json | grep -i openai
   ```

---

## 测试 6: HTTP Adapter Agent

### 目标
验证通过 HTTP Adapter 测试自定义 API 的 agent

### 步骤

1. **创建测试脚本** (`test_http_adapter.py`)
   ```python
   from tigerhill import HTTPAdapter, TraceStore

   # 假设有一个本地 LLM 服务
   adapter = HTTPAdapter(
       base_url="http://localhost:11434",  # Ollama
       endpoint="/api/generate",
       method="POST"
   )

   store = TraceStore()
   trace = store.start_trace(agent_name="ollama_test", task="Test Ollama")

   response = adapter.send_message(
       "Why is the sky blue?",
       trace,
       json_payload={
           "model": "llama2",
           "prompt": "Why is the sky blue?",
           "stream": False
       }
   )

   print(response)
   store.save_trace(trace)
   ```

2. **运行测试**
   ```bash
   # 确保 Ollama 在运行
   # ollama serve

   python test_http_adapter.py
   ```

3. **检查项**
   - [ ] HTTP 请求被正确构造
   - [ ] Trace 包含请求和响应
   - [ ] 自定义 JSON payload 正确传递

---

## 测试 7: STDIO Adapter Agent

### 目标
测试通过 STDIN/STDOUT 交互的 CLI 工具

### 步骤

1. **创建测试脚本** (`test_stdio_adapter.py`)
   ```python
   from tigerhill import STDIOAdapter, TraceStore

   # 测试一个简单的 CLI（例如 bc 计算器）
   adapter = STDIOAdapter(
       command=["bc", "-l"],
       prompt_prefix="",
       response_delimiter="\n"
   )

   store = TraceStore()
   trace = store.start_trace(agent_name="bc_calculator", task="Test bc")

   # 发送计算
   result = adapter.send_message("2 + 2", trace)
   print(f"Result: {result}")

   result = adapter.send_message("sqrt(16)", trace)
   print(f"Result: {result}")

   adapter.close()
   store.save_trace(trace)
   ```

2. **运行测试**
   ```bash
   python test_stdio_adapter.py
   ```

3. **检查项**
   - [ ] CLI 工具正确启动
   - [ ] 输入/输出被捕获
   - [ ] 多次交互都记录在 trace 中

---

## 测试总结检查清单

### Gemini CLI
- [ ] 单轮对话捕获完整
- [ ] 多轮对话会话追踪正确
- [ ] 系统 prompt 完整
- [ ] 上下文信息（文件树等）完整
- [ ] Token 统计准确

### Python Agents
- [ ] OpenAI 集成正常
- [ ] Anthropic 集成正常
- [ ] Gemini 集成正常
- [ ] Observer SDK 正确捕获
- [ ] 与 TraceStore 集成无缝

### Node.js Agents
- [ ] HTTP 拦截器工作正常
- [ ] 支持多种 LLM 提供商
- [ ] 无需代码修改即可使用

### 通用 Adapters
- [ ] HTTPAdapter 支持自定义 API
- [ ] STDIOAdapter 支持 CLI 工具
- [ ] 所有 adapter 与 TraceStore 集成

---

## 故障排除

### 问题: 没有生成捕获文件

**检查**:
1. 确认环境变量设置正确
2. 确认捕获目录有写入权限
3. 查看控制台是否有 `[TigerHill]` 日志

**解决**:
```bash
# 查看详细日志
NODE_OPTIONS="--require ./tigerhill/observer/gemini_http_interceptor.cjs" \
  TIGERHILL_CAPTURE_PATH="./test_captures" \
  node your-agent.js 2>&1 | grep -i tigerhill
```

### 问题: 捕获文件为空或不完整

**原因**: 可能是多进程问题

**解决**: 检查所有生成的捕获文件，实际内容可能在另一个文件中

```bash
# 查看所有捕获文件
for file in test_captures/*.json; do
    echo "=== $file ==="
    jq '.statistics' "$file" 2>/dev/null || echo "Empty or invalid"
done
```

### 问题: Python Observer SDK 导入失败

**解决**:
```bash
# 确保安装了 tigerhill
pip install -e .

# 或者使用完整路径
PYTHONPATH=/path/to/TigerHill python test_script.py
```

---

## 自动化测试套件

创建一个自动化测试脚本 (`run_all_tests.sh`):

```bash
#!/bin/bash

set -e

echo "Running TigerHill Agent Interception Tests..."
echo ""

# 测试1: Gemini CLI 单轮
echo "Test 1: Gemini CLI Single Turn"
NODE_OPTIONS="--require ./tigerhill/observer/gemini_http_interceptor.cjs" \
  TIGERHILL_CAPTURE_PATH="./test_captures/gemini_single" \
  node /path/to/gemini-cli/bundle/gemini.js -p "Test query"
echo "✓ Test 1 passed"
echo ""

# 测试2: Python OpenAI (如果有 API key)
if [ -n "$OPENAI_API_KEY" ]; then
    echo "Test 2: Python OpenAI Agent"
    python test_openai_agent.py
    echo "✓ Test 2 passed"
else
    echo "⊘ Test 2 skipped (no OPENAI_API_KEY)"
fi
echo ""

# 测试3: Python Anthropic (如果有 API key)
if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo "Test 3: Python Anthropic Agent"
    python test_anthropic_agent.py
    echo "✓ Test 3 passed"
else
    echo "⊘ Test 3 skipped (no ANTHROPIC_API_KEY)"
fi
echo ""

# 测试4: STDIO Adapter
echo "Test 4: STDIO Adapter"
python test_stdio_adapter.py
echo "✓ Test 4 passed"
echo ""

echo "All tests completed!"
```

运行:
```bash
chmod +x run_all_tests.sh
./run_all_tests.sh
```

---

## 下一步

1. 根据实际 agent 架构选择合适的拦截方法
2. 运行相应的测试验证
3. 根据测试结果调整配置
4. 集成到 CI/CD 流程

如需支持新的 agent 类型，参考 `UNIVERSAL_AGENT_INTERCEPTION.md` 中的实现指南。

# Gemini CLI Interceptor 使用指南

## 概述

TigerHill 提供了一个 HTTP 拦截器，可以捕获 Gemini CLI 的完整交互，包括系统 prompt、上下文、用户输入和 AI 响应。

## 问题背景

### 原始方案的局限性

最初尝试使用的方案（包装 `@google/generative-ai` SDK）无法工作，因为：

1. **Bundle 打包**：gemini-cli 使用 esbuild 将所有代码打包成单一文件 (`bundle/gemini.js`)
2. **依赖内联**：所有 npm 包（包括 `@google/genai` SDK）都被编译成内联代码
3. **无法 Hook**：`Module._load` 无法拦截已打包的代码

### 成功方案：HTTP 层拦截

通过调试发现，gemini-cli 使用：
- **SDK**: `@google/genai` (不是 `@google/generative-ai`)
- **HTTP 客户端**: Node.js 原生的 `https.request`
- **API 端点**: `cloudcode-pa.googleapis.com` (不是 `generativelanguage.googleapis.com`)

因此，我们通过 hook `https.request` 成功拦截了所有 API 调用。

## 使用方法

### 1. 基本用法

```bash
NODE_OPTIONS="--require /path/to/TigerHill/tigerhill/observer/gemini_http_interceptor.cjs" \
  TIGERHILL_CAPTURE_PATH="/path/to/captures" \
  gemini -p "你的问题"
```

### 2. 完整示例

```bash
# 设置捕获路径
export TIGERHILL_CAPTURE_PATH="$HOME/gemini_captures"
mkdir -p "$TIGERHILL_CAPTURE_PATH"

# 运行 gemini-cli 并捕获
NODE_OPTIONS="--require /Users/yinaruto/MyProjects/ChatLLM/TigerHill/tigerhill/observer/gemini_http_interceptor.cjs" \
  TIGERHILL_CAPTURE_PATH="$TIGERHILL_CAPTURE_PATH" \
  gemini -p "解释什么是量子计算"
```

### 3. 配置选项

#### 环境变量

- `TIGERHILL_CAPTURE_PATH`: 捕获文件保存路径（默认：`./prompt_captures`）
- `TIGERHILL_SAVE_RAW`: 设为 `true` 以保存完整的原始请求/响应（用于调试）

#### 示例：保存原始数据

```bash
NODE_OPTIONS="--require /path/to/gemini_http_interceptor.cjs" \
  TIGERHILL_CAPTURE_PATH="./captures" \
  TIGERHILL_SAVE_RAW="true" \
  gemini -p "你的问题"
```

## 捕获的数据结构

### JSON 文件格式

```json
{
  "capture_id": "uuid",
  "agent_name": "gemini_cli",
  "start_time": 1234567890.123,
  "end_time": 1234567920.456,
  "duration": 30.333,
  "metadata": {
    "tool": "gemini-cli",
    "interceptor": "http",
    "version": "1.0"
  },
  "requests": [
    {
      "request_id": "uuid",
      "timestamp": 1234567890.5,
      "method": "POST",
      "url": "https://cloudcode-pa.googleapis.com/v1internal:generateContent",
      "headers": { ... },
      "raw_request": {
        "model": "gemini-2.5-pro",
        "project": "...",
        "request": {
          "contents": [
            {
              "role": "user",
              "parts": [
                {
                  "text": "完整的上下文设置和用户输入"
                }
              ]
            }
          ],
          "systemInstruction": {
            "role": "user",
            "parts": [
              {
                "text": "完整的系统 prompt"
              }
            ]
          },
          "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 1024,
            "responseMimeType": "application/json"
          }
        }
      }
    }
  ],
  "responses": [
    {
      "request_id": "uuid",
      "timestamp": 1234567895.5,
      "duration_ms": 5000,
      "status_code": 200,
      "text": "AI 的回复文本",
      "usage": {
        "prompt_tokens": 1000,
        "completion_tokens": 500,
        "total_tokens": 1500
      },
      "finish_reason": "STOP"
    }
  ],
  "statistics": {
    "total_requests": 4,
    "total_responses": 4,
    "total_tokens": 35000
  }
}
```

### 捕获内容详解

#### 1. System Instruction（系统指令）

Gemini CLI 使用一个复杂的路由系统 prompt 来决定使用哪个模型：

```text
You are a specialized Task Routing AI. Your sole function is to analyze
the user's request and classify its complexity. Choose between `flash`
(SIMPLE) or `pro` (COMPLEX).
```

这个 prompt 包含：
- 复杂度评估标准
- 示例场景
- JSON 输出格式要求

#### 2. Context Setup（上下文设置）

每次对话开始时，CLI 会注入：
- 当前日期和时间
- 操作系统信息
- 工作目录
- 完整的文件目录树（最多 200 项）

示例：
```text
This is the Gemini CLI. We are setting up the context for our chat.
Today's date is Saturday, November 1, 2025
My operating system is: darwin
I'm currently working in the directory: /Users/yinaruto/MyProjects/...
Here is the folder structure of the current working directories:
[完整的目录树]
```

#### 3. User Input（用户输入）

用户的实际问题，例如：
```text
简单解释一下量子计算
```

#### 4. Generation Config（生成配置）

包括：
- `temperature`: 0
- `maxOutputTokens`: 1024
- `responseMimeType`: "application/json"
- `responseJsonSchema`: 结构化输出定义
- `thinkingConfig`: 思考预算（512 tokens）

## 分析捕获数据

### 使用 Python 分析

```python
import json

# 读取捕获文件
with open('capture_xxx.json', 'r') as f:
    data = json.load(f)

# 提取系统 prompt
for req in data['requests']:
    if 'raw_request' in req and 'systemInstruction' in req['raw_request']['request']:
        sys_inst = req['raw_request']['request']['systemInstruction']
        if 'parts' in sys_inst:
            for part in sys_inst['parts']:
                if 'text' in part:
                    print("System Prompt:")
                    print(part['text'])
                    print()

# 提取用户输入
for req in data['requests']:
    if 'raw_request' in req and 'contents' in req['raw_request']['request']:
        for content in req['raw_request']['request']['contents']:
            if content.get('role') == 'user':
                print(f"\n[USER]")
                for part in content['parts']:
                    if 'text' in part:
                        print(part['text'])

# 提取响应和 token 统计
for resp in data['responses']:
    if 'text' in resp:
        print(f"\n[ASSISTANT]")
        print(resp['text'][:200] + "...")

        if 'usage' in resp:
            usage = resp['usage']
            print(f"\nTokens: {usage['total_tokens']} total")
            print(f"  - Prompt: {usage['prompt_tokens']}")
            print(f"  - Completion: {usage['completion_tokens']}")
```

### 使用命令行工具

```bash
# 查看最新捕获文件
ls -lt captures/ | head -5

# 美化打印 JSON
cat captures/capture_xxx.json | python3 -m json.tool | less

# 提取系统 prompt
cat captures/capture_xxx.json | jq '.requests[].raw_request.request.systemInstruction.parts[].text' -r

# 提取用户输入
cat captures/capture_xxx.json | jq '.requests[].raw_request.request.contents[] | select(.role=="user") | .parts[].text' -r

# 统计 token 使用
cat captures/capture_xxx.json | jq '.statistics'
```

## 高级用法

### 1. 批量捕获

创建一个脚本来批量运行和分析：

```bash
#!/bin/bash

QUESTIONS=(
    "什么是机器学习？"
    "解释量子纠缠"
    "写一个快速排序算法"
)

for question in "${QUESTIONS[@]}"; do
    echo "Processing: $question"
    NODE_OPTIONS="--require /path/to/gemini_http_interceptor.cjs" \
      TIGERHILL_CAPTURE_PATH="./batch_captures" \
      gemini -p "$question"
    sleep 2
done
```

### 2. 与 TigerHill TraceStore 集成

```python
from tigerhill import TraceStore
import json
import glob

# 初始化 TraceStore
store = TraceStore()

# 导入所有捕获文件
for capture_file in glob.glob('captures/*.json'):
    with open(capture_file, 'r') as f:
        data = json.load(f)

    # 转换为 TraceStore 格式
    trace = store.start_trace(
        agent_name="gemini_cli",
        task=data['requests'][0]['raw_request']['request']['contents'][-1]['parts'][0]['text'][:100]
    )

    # 添加请求和响应
    for req, resp in zip(data['requests'], data['responses']):
        if 'raw_request' in req:
            trace.log_request(req['raw_request'])
            trace.log_response(resp.get('text', ''))

    trace.end(status='completed')
    store.save_trace(trace)

print(f"Imported {len(glob.glob('captures/*.json'))} captures to TraceStore")
```

### 3. 实时监控

```bash
# 在一个终端窗口运行 gemini-cli
NODE_OPTIONS="--require /path/to/gemini_http_interceptor.cjs" \
  TIGERHILL_CAPTURE_PATH="./captures" \
  gemini

# 在另一个终端窗口实时监控
watch -n 1 'ls -lt captures/ | head -5 && echo && tail -20 captures/$(ls -t captures/ | head -1) | python3 -m json.tool'
```

## 故障排除

### 问题：没有捕获到数据

**检查项**：
1. 确认 `NODE_OPTIONS` 环境变量正确设置
2. 确认拦截器文件路径正确
3. 检查是否有权限写入捕获目录
4. 查看控制台是否有 `[TigerHill]` 日志

**解决方法**：
```bash
# 查看完整日志
NODE_OPTIONS="--require /path/to/gemini_http_interceptor.cjs" \
  TIGERHILL_CAPTURE_PATH="./captures" \
  gemini -p "test" 2>&1 | grep TigerHill
```

### 问题：捕获文件为空

这可能是因为 gemini-cli 启动了多个进程。查看日志中的进程 ID：

```
[TigerHill HTTP Interceptor] Active
[TigerHill HTTP Interceptor] Capture file: capture_xxx.json
```

检查是否有多个捕获文件生成，实际的 API 调用可能在另一个文件中。

### 问题：只捕获到部分数据

如果只捕获到 `loadCodeAssist` 请求而没有 `generateContent`，检查：
1. 是否有 API 配额限制
2. 是否有网络错误
3. 查看响应的 status_code

## 技术细节

### 支持的 API 端点

拦截器监控以下主机的请求：
- `cloudcode-pa.googleapis.com` (Gemini CLI 主要端点)
- `generativelanguage.googleapis.com` (标准 Gemini API)
- `aiplatform.googleapis.com` (Vertex AI)
- `content-aiplatform.googleapis.com`

### Gemini CLI 的请求流程

1. **认证**: 请求 `oauth2.googleapis.com` 获取 token
2. **初始化**: 调用 `loadCodeAssist` 加载配置
3. **路由决策**: 使用 `gemini-2.5-flash-lite` 分析复杂度
4. **生成内容**: 根据决策使用 `flash` 或 `pro` 模型
5. **流式响应**: 使用 SSE（Server-Sent Events）返回结果

### 文件命名规则

捕获文件命名格式：
```
capture_{UUID}_{timestamp}.json
```

示例：
```
capture_53acecf2-8807-41eb-8419-73a23940fbea_1761923192964.json
```

## 相关文件

- **拦截器实现**: `tigerhill/observer/gemini_http_interceptor.cjs`
- **调试工具**: `tigerhill/observer/gemini_debug_interceptor.cjs`
- **测试脚本**: `test_gemini_interceptor.sh`

## 致谢

这个拦截器是通过系统性调试开发的：

1. 首先尝试了 Module Hook（失败 - bundle 问题）
2. 然后尝试了 Fetch Hook（失败 - 使用了 https.request）
3. 创建了诊断工具发现真实的 HTTP 调用
4. 最终通过 HTTPS Hook 成功捕获

## 许可证

Apache-2.0 License

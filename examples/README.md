# TigerHill Observer SDK - Examples

这个目录包含 TigerHill Observer SDK 的使用示例，展示如何在 Debug Mode 下捕获、分析和优化 LLM prompts。

## 📋 示例列表

### 1. Python Basic Example (`observer_python_basic.py`)

**功能**: 演示如何使用 Observer SDK 捕获 Google Generative AI 的 prompt 和响应

**使用场景**:
- 开发阶段捕获 LLM 交互
- 记录 prompt 和响应用于后续分析
- 自动保存捕获数据到文件

**前置条件**:
```bash
pip install google-generativeai
export GOOGLE_API_KEY=your_api_key
```

**运行**:
```bash
python examples/observer_python_basic.py
```

**输出**:
- 控制台显示捕获过程和统计信息
- 自动保存 JSON 文件到 `./prompt_captures/`

---

### 2. Python Analysis Example (`observer_python_analysis.py`)

**功能**: 使用 PromptAnalyzer 自动分析捕获的数据，获取优化建议

**使用场景**:
- 分析 token 使用情况
- 评估 prompt 质量
- 获取性能优化建议
- 识别未使用的工具

**前置条件**:
```bash
# 先运行 basic example 生成数据
python examples/observer_python_basic.py
```

**运行**:
```bash
python examples/observer_python_analysis.py
```

**输出**:
- 完整的分析报告（控制台）
- Token 使用统计
- Prompt 质量评分
- 优化建议列表
- 保存分析报告到 JSON 文件

**分析维度**:
1. **Token Analysis** - 使用量、效率比率
2. **Prompt Quality** - 清晰度评分、系统 prompt 使用率
3. **Performance** - 响应时间、延迟分析
4. **Tool Usage** - 工具定义和调用统计
5. **Recommendations** - 自动生成的优化建议

---

### 3. TraceStore Integration Example (`observer_tracestore_integration.py`)

**功能**: 将 Observer 捕获的数据导出到 TigerHill TraceStore

**使用场景**:
- Debug Mode → Test Mode 无缝转换
- 从实际使用中生成测试用例
- 集成到 CI/CD 流程
- 回归测试自动化

**前置条件**:
```bash
# 先运行 basic example 生成数据
python examples/observer_python_basic.py
```

**运行**:
```bash
python examples/observer_tracestore_integration.py
```

**输出**:
- 导出的 trace 数据到 `./traces_from_observer/`
- 测试用例生成建议
- 集成代码示例

**工作流程**:
```
Observer Capture → TraceStore → Test Cases → CI/CD
     (Debug)         (Export)    (Generate)   (Automate)
```

---

### 4. Node.js Basic Example (`observer_nodejs_basic.js`)

**功能**: 演示 Node.js 环境下的 Observer SDK 使用

**使用场景**:
- Node.js 应用的 LLM 交互捕获
- 跨语言 Agent 测试
- Stream 模式支持

**前置条件**:
```bash
npm install @google/generative-ai
export GOOGLE_API_KEY=your_api_key
```

**运行**:
```bash
node examples/observer_nodejs_basic.js
```

**特性**:
- 自动导出到 JSON 文件
- Stream 响应支持
- 回调函数自定义
- 可选的远程端点发送

**Auto-Instrumentation (可选)**:
```javascript
// 使用 shim 自动注入
const { createShim } = require('./tigerhill/observer/node_observer');
createShim('./tigerhill-shim.js');

// 然后运行：
// NODE_OPTIONS="--require ./tigerhill-shim.js" node your_script.js
```

---

## 🎯 完整工作流程

### 开发阶段 (Debug Mode)

1. **集成 Observer SDK**
   ```python
   from tigerhill.observer import PromptCapture, wrap_python_model

   capture = PromptCapture(storage_path="./captures")
   capture_id = capture.start_capture("my_agent")
   ```

2. **包装模型**
   ```python
   WrappedModel = wrap_python_model(
       GenerativeModel,
       capture_callback=callback
   )
   ```

3. **使用模型**
   ```python
   model = WrappedModel("gemini-pro")
   response = model.generate_content(prompt)
   ```

4. **结束捕获**
   ```python
   result = capture.end_capture(capture_id)
   ```

### 分析阶段

5. **运行分析**
   ```bash
   python examples/observer_python_analysis.py
   ```

6. **查看建议**
   - Token 优化
   - Prompt 改进
   - 性能优化
   - 工具使用优化

### 测试阶段

7. **导出到 TraceStore**
   ```bash
   python examples/observer_tracestore_integration.py
   ```

8. **创建测试用例**
   ```python
   # 基于捕获数据生成
   test_case = {
       "input": captured_prompt,
       "expected": {
           "contains": ["key", "concepts"],
           "response_length_min": 100
       }
   }
   ```

9. **运行测试**
   ```python
   tester = UniversalAgentTester(adapter, trace_store)
   result = tester.test(test_case)
   ```

### CI/CD 阶段

10. **集成测试**
    ```yaml
    # .github/workflows/test.yml
    - name: Run Agent Tests
      run: |
        python -m pytest tests/
        python scripts/run_observer_tests.py
    ```

---

## 📊 数据结构

### 捕获数据格式 (`capture_*.json`)

```json
{
  "capture_id": "uuid",
  "agent_name": "code_assistant",
  "start_time": 1234567890.0,
  "end_time": 1234567895.5,
  "duration": 5.5,
  "requests": [
    {
      "request_id": "uuid",
      "timestamp": 1234567890.5,
      "model": "gemini-pro",
      "prompt": "Write a function...",
      "system_prompt": "You are...",
      "generation_config": {...},
      "tools": [...]
    }
  ],
  "responses": [
    {
      "response_id": "uuid",
      "timestamp": 1234567893.0,
      "text": "Here is the function...",
      "finish_reason": "stop",
      "usage": {
        "prompt_tokens": 50,
        "completion_tokens": 100,
        "total_tokens": 150
      },
      "tool_calls": [...]
    }
  ],
  "statistics": {
    "total_requests": 2,
    "total_responses": 2,
    "total_tokens": 300,
    "total_prompt_tokens": 100,
    "total_completion_tokens": 200
  }
}
```

### 分析报告格式 (`analysis_*.json`)

```json
{
  "summary": {
    "total_captures": 1,
    "total_requests": 2,
    "unique_agents": 1,
    "unique_models": 1
  },
  "token_analysis": {
    "total_tokens": 300,
    "avg_tokens_per_request": 150,
    "token_efficiency_ratio": 2.0
  },
  "prompt_quality": {
    "clarity_score": 0.8,
    "has_system_prompt_ratio": 0.5
  },
  "recommendations": [
    {
      "category": "token_optimization",
      "severity": "medium",
      "title": "Token 效率较低",
      "suggestion": "..."
    }
  ]
}
```

---

## 🔒 隐私保护

Observer SDK 自动脱敏敏感信息：

- **API Keys**: `AIza...` → `<REDACTED_API_KEY>`
- **Emails**: `user@example.com` → `<REDACTED_EMAIL>`
- **Credit Cards**: `1234 5678 9012 3456` → `<REDACTED_CARD>`

### 自定义脱敏规则

```python
custom_patterns = [
    {
        "pattern": r"SECRET-\d{6}",
        "replacement": "<SECRET>"
    }
]

capture = PromptCapture(
    storage_path="./captures",
    redact_patterns=custom_patterns
)
```

---

## 💡 最佳实践

### 1. 开发环境集成

```python
# 在开发环境启用捕获
if os.getenv("TIGERHILL_CAPTURE", "false") == "true":
    from tigerhill.observer import instrument_generative_ai
    capture, capture_id, wrap_model = instrument_generative_ai("my_agent")
    GenerativeModel = wrap_model(GenerativeModel)
```

### 2. 定期分析

```bash
# 定时任务分析捕获数据
0 0 * * * cd /path/to/project && python examples/observer_python_analysis.py
```

### 3. 自动化测试生成

```python
# 从捕获数据自动生成测试
captures = load_all_captures()
for capture in captures:
    test_cases = generate_test_cases(capture)
    save_test_suite(test_cases)
```

### 4. 持续优化

```python
# 跟踪 token 使用趋势
def track_token_usage(capture_id):
    analyzer = PromptAnalyzer(capture)
    report = analyzer.analyze_all()

    # 记录到监控系统
    metrics.record("token_usage", report["token_analysis"])
```

---

## 🚀 高级用法

### Stream 响应捕获 (Node.js)

```javascript
async function* captureStream() {
    for await (const chunk of model.generateContentStream(prompt)) {
        // 自动捕获每个 chunk
        yield chunk;
    }
}
```

### 异步捕获 (Python)

```python
async def capture_async():
    response = await model.generate_content_async(prompt)
    # 自动捕获异步响应
    return response
```

### 批量分析

```python
# 分析多个捕获会话
captures = [load_capture(id) for id in capture_ids]
analyzer = PromptAnalyzer(captures)
combined_report = analyzer.analyze_all()
```

### 远程捕获服务

```python
# 发送到远程服务器
capture = PromptCapture(
    storage_path="./captures",
    capture_endpoint="http://tigerhill-server:8000/api/capture"
)
```

---

## 📚 相关文档

- [TigerHill 主文档](../README.md)
- [Observer SDK API](../docs/observer_api.md)
- [PromptAnalyzer 使用指南](../docs/analyzer_guide.md)
- [TraceStore 集成](../docs/tracestore_integration.md)

---

## ❓ 常见问题

**Q: Observer SDK 会影响性能吗？**

A: 影响很小。捕获操作是异步的，不会阻塞主流程。建议只在开发/测试环境启用。

**Q: 如何处理大量捕获数据？**

A: 使用 `auto_save=False` 禁用自动保存，手动控制保存时机。或定期清理旧数据。

**Q: 可以捕获其他 LLM SDK 吗？**

A: 可以！参考 `python_observer.py` 创建自定义包装器。支持 OpenAI、Anthropic 等。

**Q: 捕获数据安全吗？**

A: Observer SDK 自动脱敏敏感信息。建议不要提交捕获文件到版本控制。

---

## 🤝 贡献

欢迎贡献更多示例！请查看 [CONTRIBUTING.md](../CONTRIBUTING.md)

---

## 📄 许可证

MIT License - 详见 [LICENSE](../LICENSE)

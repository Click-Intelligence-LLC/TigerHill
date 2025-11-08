# TigerHill 存储目录说明

TigerHill 使用两个不同的目录来存储不同类型的数据。本文档解释它们的区别和用途。

---

## 📂 两个存储目录

### 1. `test_traces/` - TraceStore 追踪数据

**用途**: 存储完整的Agent测试执行追踪记录

**文件格式**: `trace_<uuid>_<timestamp>.json`

**内容结构**:
```json
{
  "trace_id": "09b2813c-bee3-4f7e-8f6d-88a24445dcbd",
  "agent_name": "my_agent",
  "task_id": "task_001",
  "start_time": 1761735238.993592,
  "end_time": 1761735238.993618,
  "status": "success",
  "events": [
    {
      "event_id": "...",
      "event_type": "prompt",
      "timestamp": 1761735238.993597,
      "data": {
        "type": "prompt",
        "content": "用户输入"
      }
    },
    {
      "event_type": "model_response",
      "data": {
        "text": "AI响应",
        "adapter_type": "Mock"
      }
    },
    {
      "event_type": "evaluation",
      "data": {
        "passed": 5,
        "total": 5
      }
    }
  ],
  "metadata": {}
}
```

**包含的信息**:
- ✅ 完整的测试执行流程
- ✅ 所有事件的时间线（prompt、响应、工具调用、评估等）
- ✅ 测试结果和断言
- ✅ Agent名称和任务ID
- ✅ 执行状态和元数据

**何时使用**:
```python
from tigerhill.storage.trace_store import TraceStore

# 创建TraceStore
store = TraceStore(storage_path="./test_traces")

# 开始追踪
trace_id = store.start_trace(
    agent_name="my_agent",
    task_id="test_001"
)

# 记录事件
store.write_event({"type": "prompt", "content": "..."})
store.write_event({"type": "model_response", "text": "..."})

# 结束追踪
store.end_trace(trace_id)

# 自动保存到: test_traces/trace_<id>_<timestamp>.json
```

---

### 2. `prompt_captures/` - Observer SDK 捕获数据

**用途**: 存储原始LLM API请求和响应，用于调试和优化

**文件格式**:
- `capture_<uuid>_<timestamp>.json` (单次捕获)
- `session_<uuid>_<timestamp>.json` (会话追踪)

**内容结构**:
```json
{
  "capture_id": "7a874eee-b8a4-4b4e-8e54-f3c38d93b286",
  "agent_name": "code_assistant",
  "start_time": 1761823414.479209,
  "metadata": {
    "task": "generate_fibonacci",
    "version": "1.0"
  },
  "requests": [
    {
      "model": "models/gemini-2.5-flash",
      "prompt": "Write a Python function...",
      "generation_config": null,
      "timestamp": 1761823414.4793751,
      "request_id": "..."
    }
  ],
  "responses": [
    {
      "text": "完整的AI响应...",
      "timestamp": 1761823441.9490292,
      "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 2579,
        "total_tokens": 4024
      }
    }
  ],
  "statistics": {
    "total_requests": 2,
    "total_tokens": 8553,
    "avg_response_time": 13.23
  }
}
```

**包含的信息**:
- ✅ 原始LLM API请求参数
- ✅ 完整的AI响应文本
- ✅ Token使用统计
- ✅ 响应时间
- ✅ 成本估算数据
- ✅ 多轮对话历史

**何时使用**:

#### 方式1: Python Observer SDK
```python
from tigerhill.observer import PromptCapture

# 创建捕获器
capture = PromptCapture(
    storage_path="./prompt_captures",  # 保存到此目录
    auto_export=True
)

# 开始捕获
capture_id = capture.start_capture("my_agent")

# ... 执行LLM调用 ...

# 结束捕获
result = capture.end_capture(capture_id)
# 自动保存到: prompt_captures/capture_<id>_<timestamp>.json
```

#### 方式2: Node.js 拦截器
```bash
# 使用HTTP拦截器
NODE_OPTIONS="--require ./tigerhill/observer/gemini_http_interceptor.cjs" \
  TIGERHILL_CAPTURE_PATH="./prompt_captures/gemini_cli" \
  node your-agent.js

# 自动保存到: prompt_captures/gemini_cli/capture_<id>_<timestamp>.json
```

#### 方式3: Session 拦截器（多轮对话）
```bash
NODE_OPTIONS="--require ./tigerhill/observer/gemini_session_interceptor.cjs" \
  TIGERHILL_CAPTURE_PATH="./prompt_captures/session_test" \
  node your-agent.js

# 自动保存到: prompt_captures/session_test/session_<id>_<timestamp>.json
```

---

## 🔄 两者的关系

### 功能对比

| 特性 | test_traces/ | prompt_captures/ |
|------|-------------|-----------------|
| **数据来源** | TraceStore API | Observer SDK / 拦截器 |
| **数据类型** | 测试执行追踪 | LLM交互原始数据 |
| **粒度** | 完整测试流程 | LLM请求/响应 |
| **主要用途** | 测试验证、回归测试 | 调试、优化、成本分析 |
| **事件类型** | prompt, response, tool_call, evaluation | requests, responses, usage |
| **断言结果** | ✅ 包含 | ❌ 不包含 |
| **Token统计** | ⚠️ 可选 | ✅ 详细 |
| **多轮对话** | ✅ 完整追踪 | ✅ Session追踪 |

### 使用场景对比

#### 场景1: 测试Agent功能
**使用**: `test_traces/` (TraceStore)

```python
# 验证Agent是否正确执行任务
store = TraceStore(storage_path="./test_traces")
trace_id = store.start_trace("math_agent")

# 执行Agent
output = agent.run("计算 2+2")

# 记录和验证
store.write_event({"type": "model_response", "text": output})
results = run_assertions(output, [{"type": "contains", "expected": "4"}])

store.end_trace(trace_id)
```

#### 场景2: 优化Prompt和降低成本
**使用**: `prompt_captures/` (Observer SDK)

```python
# 捕获LLM交互以分析token使用
capture = PromptCapture(storage_path="./prompt_captures")
capture_id = capture.start_capture("code_gen")

# 执行LLM调用
model.generate_content("写一个Python函数...")

# 分析token使用和成本
result = capture.end_capture(capture_id)
analyzer = PromptAnalyzer(result)
report = analyzer.analyze_all()
# 获得优化建议
```

#### 场景3: 调试Gemini CLI
**使用**: `prompt_captures/` (拦截器)

```bash
# 捕获完整的API请求以调试问题
NODE_OPTIONS="--require ./tigerhill/observer/gemini_http_interceptor.cjs" \
  TIGERHILL_CAPTURE_PATH="./prompt_captures/debug" \
  node gemini-cli -p "测试问题"

# 查看捕获的请求和响应
cat prompt_captures/debug/capture_*.json
```

---

## 🔗 集成使用

### Observer SDK 导出到 TraceStore

你可以将捕获的LLM交互导出为TraceStore格式：

```python
from tigerhill.observer import PromptCapture
from tigerhill.storage.trace_store import TraceStore

# 1. 捕获LLM交互
capture = PromptCapture(storage_path="./prompt_captures")
capture_id = capture.start_capture("my_agent")

# ... LLM调用 ...

# 2. 导出到TraceStore
store = TraceStore(storage_path="./test_traces")
trace_id = capture.export_to_trace_store(
    capture_id=capture_id,
    trace_store=store,
    agent_name="my_agent"
)

# 现在数据在两个地方都有：
# - prompt_captures/capture_<id>.json  (原始LLM数据)
# - test_traces/trace_<id>.json        (转换后的Trace格式)
```

---

## 📊 目录结构示例

```
TigerHill/
├── test_traces/                    # TraceStore数据
│   ├── calculator/                 # 按agent组织
│   │   ├── trace_abc123_1761735238.json
│   │   └── trace_def456_1761735240.json
│   ├── code_gen/
│   │   └── trace_ghi789_1761735250.json
│   └── trace_jkl012_1761735260.json  # 也可以放在根目录
│
└── prompt_captures/                # Observer SDK数据
    ├── gemini_cli/                 # Gemini CLI捕获
    │   ├── capture_aaa111_1761823414.json
    │   └── session_bbb222_1761823500.json
    ├── session_test/               # 会话测试
    │   └── session_ccc333_1761998714.json
    └── multiturn_test/            # 多轮对话测试
        ├── session_ddd444_1761998728.json
        ├── session_eee555_1761998745.json
        └── analysis_report.json   # 分析报告
```

---

## 🎯 选择指南

### 何时使用 test_traces/ (TraceStore)

✅ **使用场景**:
- 编写Agent单元测试
- 回归测试
- 性能基准测试
- CI/CD集成测试
- 需要完整事件时间线
- 需要验证测试断言

✅ **优势**:
- 结构化的测试数据
- 支持查询和过滤
- 完整的执行上下文
- 内置断言支持

### 何时使用 prompt_captures/ (Observer SDK)

✅ **使用场景**:
- 调试LLM交互
- 优化Prompt
- 降低Token成本
- 分析响应质量
- 捕获Gemini CLI交互
- 多轮对话分析

✅ **优势**:
- 原始LLM数据
- 详细的Token统计
- 自动成本估算
- 无侵入式捕获
- 支持多种LLM

---

## 🔧 配置和管理

### 更改TraceStore路径

```python
# 方法1: 初始化时指定
store = TraceStore(storage_path="./my_custom_traces")

# 方法2: 使用环境变量
import os
os.environ['TIGERHILL_TRACE_PATH'] = "./my_custom_traces"
store = TraceStore()
```

### 更改Capture路径

```python
# Python Observer SDK
capture = PromptCapture(storage_path="./my_captures")

# Node.js 拦截器
# 使用环境变量
export TIGERHILL_CAPTURE_PATH="./my_captures"
```

### 清理旧数据

```bash
# 清理超过30天的trace
find ./test_traces -name "trace_*.json" -mtime +30 -delete

# 清理超过7天的capture
find ./prompt_captures -name "*.json" -mtime +7 -delete
```

---

## 📖 相关文档

- **TraceStore详细文档**: `USER_GUIDE.md` 第2节
- **Observer SDK详细文档**: `OBSERVER_SDK_DOCUMENTATION.md`
- **拦截器使用指南**: `GEMINI_CLI_INTERCEPTOR_GUIDE.md`
- **跨语言测试**: `CROSS_LANGUAGE_TESTING.md`

---

## ❓ 常见问题

### Q: 我应该提交这些目录到Git吗？

**A**: 通常**不应该**。建议添加到 `.gitignore`:

```gitignore
# TigerHill数据目录
test_traces/
prompt_captures/

# 但保留示例数据（如果有）
!test_traces/.gitkeep
!test_traces/examples/
!prompt_captures/.gitkeep
```

### Q: 两个目录的数据可以互相转换吗？

**A**:
- ✅ `prompt_captures` → `test_traces`: 支持，使用 `export_to_trace_store()`
- ❌ `test_traces` → `prompt_captures`: 不支持（信息不完整）

### Q: 如果我只需要测试，是否可以只使用一个目录？

**A**:
- 如果只需要**功能测试**：使用 `test_traces/` 即可
- 如果需要**调试和优化**：两个都需要
- 如果使用**Observer SDK**: 会自动创建 `prompt_captures/`

### Q: 数据会占用很多空间吗？

**A**:
- `test_traces/`: 通常很小（1-10KB/trace）
- `prompt_captures/`: 较大（50-500KB/capture），取决于响应长度
- 建议定期清理或压缩旧数据

---

**文档版本**: 1.0
**更新日期**: 2025-11-01

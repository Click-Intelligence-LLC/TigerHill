# TigerHill Observer SDK - 完整文档

## 📖 目录

- [概述](#概述)
- [快速开始](#快速开始)
- [核心概念](#核心概念)
- [API 参考](#api-参考)
- [使用指南](#使用指南)
- [最佳实践](#最佳实践)
- [故障排除](#故障排除)

---

## 概述

TigerHill Observer SDK 是一个**无侵入式的 LLM 调试工具**，用于在开发阶段捕获、分析和优化 prompt 和响应。

### 🎯 核心功能

1. **Prompt 捕获** - 自动记录所有 LLM 请求和响应
2. **自动分析** - Token 使用、质量评估、性能分析
3. **隐私保护** - 自动脱敏敏感信息（API keys、邮箱等）
4. **TraceStore 集成** - 无缝转换为测试用例
5. **跨语言支持** - Python 和 Node.js

### 🏗️ 架构设计

```
┌─────────────────────────────────────────────────┐
│           Your Application Code                 │
│                                                 │
│  model.generate_content("prompt")              │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│         TigerHill Observer SDK                  │
│                                                 │
│  ┌──────────────┐  ┌──────────────┐           │
│  │   Wrapper    │→ │   Capture    │           │
│  │   (透明包装)  │  │   (数据捕获)  │           │
│  └──────────────┘  └──────┬───────┘           │
│                            │                    │
│                            ▼                    │
│  ┌──────────────┐  ┌──────────────┐           │
│  │  Sanitizer   │→ │   Storage    │           │
│  │  (脱敏处理)   │  │   (持久化)    │           │
│  └──────────────┘  └──────────────┘           │
└─────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│           Google Generative AI                  │
│                                                 │
│  Gemini API → Response                         │
└─────────────────────────────────────────────────┘
```

### 🔑 设计原则

- **无侵入**: 通过包装器模式，不修改原始代码
- **透明化**: 自动捕获，开发者无感知
- **安全性**: 自动脱敏，保护隐私
- **可扩展**: 支持自定义回调和规则

---

## 快速开始

### Python - 5 分钟上手

#### 1. 安装依赖

```bash
pip install google-generativeai
```

#### 2. 基础使用

```python
import os
from tigerhill.observer import PromptCapture, wrap_python_model
from tigerhill.observer.python_observer import create_observer_callback
import google.generativeai as genai

# 配置 API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# 创建捕获器
capture = PromptCapture(storage_path="./captures")
capture_id = capture.start_capture("my_agent")

# 创建回调
callback = create_observer_callback(capture, capture_id)

# 包装模型
WrappedModel = wrap_python_model(
    genai.GenerativeModel,
    capture_callback=callback
)

# 使用包装后的模型（完全透明）
model = WrappedModel("gemini-pro")
response = model.generate_content("Hello!")

# 结束捕获
result = capture.end_capture(capture_id)
print(f"Captured {result['statistics']['total_requests']} requests")
```

#### 3. 运行分析

```python
from tigerhill.observer import PromptAnalyzer

analyzer = PromptAnalyzer(result)
report = analyzer.analyze_all()
analyzer.print_report(report)
```

### Node.js - 5 分钟上手

#### 1. 安装依赖

```bash
npm install @google/generative-ai
```

#### 2. 基础使用

```javascript
const { GoogleGenerativeAI } = require('@google/generative-ai');
const { wrapGenerativeModel } = require('./tigerhill/observer/node_observer');

// 包装模型类
const WrappedModel = wrapGenerativeModel(GoogleGenerativeAI, {
    onRequest: (data) => console.log('Request:', data),
    onResponse: (data) => console.log('Response:', data),
    autoExport: true,
    exportPath: './captures'
});

// 使用
const genAI = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY);
const model = genAI.getGenerativeModel({ model: 'gemini-pro' });

const result = await model.generateContent('Hello!');
```

---

## 核心概念

### 1. Capture (捕获)

捕获是 Observer SDK 的核心功能，记录 LLM 交互的完整生命周期。

#### Capture 对象

```python
capture = PromptCapture(
    storage_path="./captures",    # 存储路径
    auto_save=True,                # 自动保存
    redact_patterns=[]             # 自定义脱敏规则
)
```

#### Capture Session

每个 capture session 包含：

- **capture_id**: 唯一标识符
- **agent_name**: Agent 名称
- **metadata**: 自定义元数据
- **requests**: 请求列表
- **responses**: 响应列表
- **tool_calls**: 工具调用列表
- **statistics**: 统计信息

#### 生命周期

```python
# 1. 开始捕获
capture_id = capture.start_capture("agent_name")

# 2. 捕获请求
capture.capture_request(capture_id, request_data)

# 3. 捕获响应
capture.capture_response(capture_id, response_data)

# 4. 结束捕获
result = capture.end_capture(capture_id)
```

### 2. Observer (观察器)

Observer 是透明的包装器，自动捕获 LLM SDK 的调用。

#### Python Observer

```python
WrappedModel = wrap_python_model(
    model_class,              # 要包装的模型类
    capture_callback,         # 捕获回调函数
    capture_response=True     # 是否捕获响应
)
```

**支持的方法**:
- `generate_content()` - 同步生成
- `generate_content_async()` - 异步生成

**自动提取**:
- Prompt (文本/多轮对话)
- System prompt
- Generation config
- Tools
- Safety settings
- Usage metadata
- Tool calls

#### Node.js Observer

```javascript
WrappedModel = wrapGenerativeModel(ModelClass, {
    onRequest: callback,       // 请求回调
    onResponse: callback,      // 响应回调
    captureEndpoint: url,      // 远程端点
    autoExport: true,          // 自动导出
    exportPath: path           // 导出路径
});
```

**支持的方法**:
- `generateContent()` - 常规生成
- `generateContentStream()` - 流式生成

### 3. Analyzer (分析器)

Analyzer 提供自动分析和优化建议。

#### 创建分析器

```python
analyzer = PromptAnalyzer(capture_data)
```

支持的输入格式：
- `PromptCapture` 实例
- 单个捕获数据字典
- 捕获数据列表

#### 分析维度

1. **Token Analysis** - Token 使用分析
   ```python
   token_report = analyzer.analyze_tokens()
   # 返回：total, avg, efficiency_ratio, max, min
   ```

2. **Prompt Quality** - 质量评估
   ```python
   quality_report = analyzer.analyze_prompt_quality()
   # 返回：clarity_score, system_prompt_ratio, issues
   ```

3. **Performance** - 性能分析
   ```python
   perf_report = analyzer.analyze_performance()
   # 返回：avg_duration, max, min, total
   ```

4. **Tool Usage** - 工具使用
   ```python
   tool_report = analyzer.analyze_tool_usage()
   # 返回：defined, called, unused, most_used
   ```

5. **Recommendations** - 优化建议
   ```python
   recommendations = analyzer.generate_recommendations()
   # 返回：category, severity, title, suggestion
   ```

#### 完整分析

```python
report = analyzer.analyze_all()
analyzer.print_report(report)
```

### 4. Sanitization (脱敏)

自动保护敏感信息。

#### 默认规则

| 类型 | 正则表达式 | 替换值 |
|------|-----------|--------|
| API Keys | `(AIza\|sk-)[0-9A-Za-z-_]{20,}` | `<REDACTED_API_KEY>` |
| Emails | `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}` | `<REDACTED_EMAIL>` |
| Credit Cards | `\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}` | `<REDACTED_CARD>` |

#### 自定义规则

```python
custom_patterns = [
    {
        "pattern": r"SECRET-\d{6}",
        "replacement": "<SECRET>"
    },
    {
        "pattern": r"TOKEN_[A-Z0-9]{32}",
        "replacement": "<TOKEN>"
    }
]

capture = PromptCapture(redact_patterns=custom_patterns)
```

### 5. TraceStore Integration

将捕获数据导出为测试用例。

```python
trace_id = capture.export_to_trace_store(
    capture_id=capture_id,
    trace_store=trace_store,
    agent_name="my_agent"
)
```

**导出内容**:
- `prompt_request` 事件
- `model_response` 事件
- `tool_call` 事件
- `statistics` 事件

---

## API 参考

### PromptCapture

#### 构造函数

```python
PromptCapture(
    storage_path: str = "./prompt_captures",
    auto_save: bool = True,
    redact_patterns: Optional[List[Dict[str, str]]] = None
)
```

#### 方法

##### `start_capture(agent_name, metadata=None) -> str`

开始新的捕获会话。

**参数**:
- `agent_name` (str): Agent 名称
- `metadata` (dict, optional): 自定义元数据

**返回**: capture_id (str)

**示例**:
```python
capture_id = capture.start_capture(
    "code_assistant",
    metadata={"version": "1.0", "task": "refactor"}
)
```

##### `capture_request(capture_id, request_data) -> None`

捕获请求数据。

**参数**:
- `capture_id` (str): 捕获会话 ID
- `request_data` (dict): 请求数据
  - `model` (str): 模型名称
  - `prompt` (str|list): Prompt 内容
  - `system_prompt` (str, optional): 系统 prompt
  - `temperature` (float, optional): 温度参数
  - `tools` (list, optional): 工具列表

**示例**:
```python
capture.capture_request(capture_id, {
    "model": "gemini-pro",
    "prompt": "Write a function...",
    "system_prompt": "You are a coding assistant",
    "temperature": 0.7,
    "tools": [{"name": "search"}]
})
```

##### `capture_response(capture_id, response_data) -> None`

捕获响应数据。

**参数**:
- `capture_id` (str): 捕获会话 ID
- `response_data` (dict): 响应数据
  - `text` (str): 响应文本
  - `finish_reason` (str): 完成原因
  - `usage` (dict): Token 使用
  - `tool_calls` (list, optional): 工具调用

**示例**:
```python
capture.capture_response(capture_id, {
    "text": "Here is the function...",
    "finish_reason": "stop",
    "usage": {
        "prompt_tokens": 50,
        "completion_tokens": 100,
        "total_tokens": 150
    }
})
```

##### `end_capture(capture_id) -> Dict[str, Any]`

结束捕获会话并返回完整数据。

**参数**:
- `capture_id` (str): 捕获会话 ID

**返回**: 完整的捕获数据，包含统计信息

**示例**:
```python
result = capture.end_capture(capture_id)
print(f"Duration: {result['duration']:.2f}s")
print(f"Total tokens: {result['statistics']['total_tokens']}")
```

##### `get_capture(capture_id) -> Optional[Dict[str, Any]]`

获取指定的捕获数据。

##### `list_captures(agent_name=None, status=None) -> List[Dict[str, Any]]`

列出捕获会话。

**参数**:
- `agent_name` (str, optional): 按 agent 过滤
- `status` (str, optional): 按状态过滤 (active/completed)

##### `load_capture(capture_id) -> Optional[Dict[str, Any]]`

从文件加载捕获数据。

##### `export_to_trace_store(capture_id, trace_store, agent_name=None) -> str`

导出到 TraceStore。

**返回**: trace_id

---

### PromptAnalyzer

#### 构造函数

```python
PromptAnalyzer(capture)
```

**参数**:
- `capture`: PromptCapture 实例、字典或列表

#### 方法

##### `analyze_all() -> Dict[str, Any]`

执行完整分析，返回完整报告。

**返回**:
```python
{
    "summary": {...},
    "token_analysis": {...},
    "prompt_quality": {...},
    "performance": {...},
    "tool_usage": {...},
    "recommendations": [...]
}
```

##### `get_summary() -> Dict[str, Any]`

获取摘要信息。

**返回**:
```python
{
    "total_captures": 1,
    "total_requests": 2,
    "total_responses": 2,
    "unique_agents": 1,
    "unique_models": 1,
    "agents": ["agent1"],
    "models": ["gemini-pro"]
}
```

##### `analyze_tokens() -> Dict[str, Any]`

分析 Token 使用。

**返回**:
```python
{
    "total_tokens": 1000,
    "total_prompt_tokens": 400,
    "total_completion_tokens": 600,
    "avg_tokens_per_request": 500,
    "token_efficiency_ratio": 1.5,
    "max_tokens": 700,
    "min_tokens": 300
}
```

##### `analyze_prompt_quality() -> Dict[str, Any]`

分析 Prompt 质量。

**返回**:
```python
{
    "total_prompts": 2,
    "avg_prompt_length": 150,
    "has_system_prompt_ratio": 0.5,
    "clarity_score": 0.75,
    "detected_issues": [...]
}
```

##### `analyze_performance() -> Dict[str, Any]`

分析性能指标。

##### `analyze_tool_usage() -> Dict[str, Any]`

分析工具使用。

##### `generate_recommendations() -> List[Dict[str, Any]]`

生成优化建议。

**建议格式**:
```python
{
    "category": "token_optimization",
    "severity": "medium",  # high/medium/low
    "title": "Prompt 过长",
    "description": "平均 prompt tokens: 2500",
    "suggestion": "考虑简化 prompt..."
}
```

##### `print_report(report=None) -> None`

打印格式化的分析报告。

---

### Python Observer

#### `wrap_python_model(model_class, capture_callback, capture_response=True)`

包装 Python 模型类。

**参数**:
- `model_class` (type): 要包装的模型类
- `capture_callback` (callable): 捕获回调函数
- `capture_response` (bool): 是否捕获响应

**返回**: 包装后的模型类

**示例**:
```python
WrappedModel = wrap_python_model(
    GenerativeModel,
    capture_callback=my_callback,
    capture_response=True
)
```

#### `create_observer_callback(capture, capture_id)`

创建观察回调函数。

**参数**:
- `capture`: PromptCapture 实例
- `capture_id` (str): 捕获会话 ID

**返回**: 回调函数

**示例**:
```python
callback = create_observer_callback(capture, capture_id)
```

#### `instrument_generative_ai(agent_name, storage_path="./prompt_captures")`

自动 instrument Google Generative AI。

**参数**:
- `agent_name` (str): Agent 名称
- `storage_path` (str): 存储路径

**返回**: (capture, capture_id, wrapper_function)

**示例**:
```python
capture, capture_id, wrap_model = instrument_generative_ai("my_agent")

WrappedModel = wrap_model(GenerativeModel)
model = WrappedModel("gemini-pro")

# ... 使用模型 ...

result = capture.end_capture(capture_id)
```

---

### Node.js Observer

#### `wrapGenerativeModel(ModelClass, options)`

包装 Node.js 模型类。

**参数**:
- `ModelClass` (function): 模型类
- `options` (object): 配置选项
  - `onRequest` (function): 请求回调
  - `onResponse` (function): 响应回调
  - `captureEndpoint` (string): 远程端点
  - `autoExport` (boolean): 自动导出
  - `exportPath` (string): 导出路径

**返回**: 包装后的模型类

**示例**:
```javascript
const WrappedModel = wrapGenerativeModel(GoogleGenerativeAI, {
    onRequest: (data) => {
        console.log('Request:', data.prompt);
    },
    onResponse: (data) => {
        console.log('Response:', data.text);
    },
    autoExport: true,
    exportPath: './captures'
});
```

#### `createShim(outputPath)`

创建自动注入 shim 文件。

**参数**:
- `outputPath` (string): Shim 文件路径

**示例**:
```javascript
createShim('./tigerhill-shim.js');

// 然后运行：
// NODE_OPTIONS="--require ./tigerhill-shim.js" node app.js
```

---

## 使用指南

### 场景 1: 基础捕获

**目标**: 记录 LLM 交互用于调试

```python
from tigerhill.observer import PromptCapture, wrap_python_model
from tigerhill.observer.python_observer import create_observer_callback
import google.generativeai as genai

# 设置
genai.configure(api_key=api_key)
capture = PromptCapture()
capture_id = capture.start_capture("debug_session")
callback = create_observer_callback(capture, capture_id)

# 包装
WrappedModel = wrap_python_model(genai.GenerativeModel, callback)
model = WrappedModel("gemini-pro")

# 使用
response = model.generate_content("Debug this code...")

# 结束
result = capture.end_capture(capture_id)
```

### 场景 2: Token 优化

**目标**: 分析和优化 Token 使用

```python
# 1. 捕获数据
# ... (同场景 1)

# 2. 分析
from tigerhill.observer import PromptAnalyzer

analyzer = PromptAnalyzer(result)
token_report = analyzer.analyze_tokens()

# 3. 检查效率
if token_report["token_efficiency_ratio"] < 0.5:
    print("⚠️ Token efficiency is low")
    print(f"Current: {token_report['token_efficiency_ratio']:.2f}")
    print("Consider requesting more detailed outputs")

# 4. 检查成本
avg_tokens = token_report["avg_tokens_per_request"]
if avg_tokens > 2000:
    print(f"⚠️ High token usage: {avg_tokens:.0f}")
    print("Consider simplifying prompts")
```

### 场景 3: 质量评估

**目标**: 评估 prompt 质量并改进

```python
analyzer = PromptAnalyzer(result)
quality_report = analyzer.analyze_prompt_quality()

# 检查清晰度
if quality_report["clarity_score"] < 0.7:
    print("⚠️ Low clarity score")
    issues = quality_report["detected_issues"]
    for issue in issues:
        print(f"  - {issue['type']}: {issue['suggestion']}")

# 检查系统 prompt
if quality_report["has_system_prompt_ratio"] < 0.8:
    print("💡 Add system prompts for better control")
```

### 场景 4: 性能监控

**目标**: 监控和优化响应时间

```python
analyzer = PromptAnalyzer(result)
perf_report = analyzer.analyze_performance()

if perf_report["avg_duration"] > 5.0:
    print(f"⚠️ Slow response: {perf_report['avg_duration']:.2f}s")
    print("Consider:")
    print("  - Using faster models")
    print("  - Simplifying prompts")
    print("  - Reducing output length")

# 记录到监控系统
metrics.record("llm_response_time", perf_report["avg_duration"])
```

### 场景 5: 工具使用优化

**目标**: 优化工具定义和使用

```python
analyzer = PromptAnalyzer(result)
tool_report = analyzer.analyze_tool_usage()

# 检查未使用的工具
unused = tool_report["tools_defined_but_not_used"]
if unused:
    print("⚠️ Unused tools detected:")
    for tool in unused:
        print(f"  - {tool}")
    print("Consider removing them to reduce context size")

# 检查使用率
usage_rate = tool_report["tool_usage_rate"]
if usage_rate < 0.1:
    print(f"⚠️ Low tool usage: {usage_rate*100:.1f}%")
    print("Tools may not be well-designed or necessary")
```

### 场景 6: 批量分析

**目标**: 分析多个会话的趋势

```python
# 收集多个捕获
captures = []
for capture_file in Path("./captures").glob("capture_*.json"):
    with open(capture_file) as f:
        captures.append(json.load(f))

# 批量分析
analyzer = PromptAnalyzer(captures)
report = analyzer.analyze_all()

# 趋势分析
print(f"Total sessions: {report['summary']['total_captures']}")
print(f"Total tokens: {report['token_analysis']['total_tokens']:,}")
print(f"Avg efficiency: {report['token_analysis']['token_efficiency_ratio']:.2f}")
```

### 场景 7: CI/CD 集成

**目标**: 在 CI/CD 中自动分析

```python
# ci_check_prompts.py
import sys
from pathlib import Path
from tigerhill.observer import PromptAnalyzer

def check_prompts():
    # 加载最新捕获
    captures = load_recent_captures(hours=24)
    analyzer = PromptAnalyzer(captures)
    report = analyzer.analyze_all()

    # 检查阈值
    failures = []

    # Token 使用
    avg_tokens = report["token_analysis"]["avg_tokens_per_request"]
    if avg_tokens > 3000:
        failures.append(f"High token usage: {avg_tokens:.0f} > 3000")

    # 质量评分
    clarity = report["prompt_quality"]["clarity_score"]
    if clarity < 0.6:
        failures.append(f"Low clarity score: {clarity:.2f} < 0.6")

    # 性能
    avg_duration = report["performance"]["avg_duration"]
    if avg_duration > 10:
        failures.append(f"Slow response: {avg_duration:.2f}s > 10s")

    # 报告
    if failures:
        print("❌ Prompt quality check failed:")
        for failure in failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print("✅ Prompt quality check passed")

if __name__ == "__main__":
    check_prompts()
```

**GitHub Actions 配置**:
```yaml
# .github/workflows/prompt-check.yml
name: Prompt Quality Check

on: [push, pull_request]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
      - name: Check prompts
        run: python ci_check_prompts.py
```

### 场景 8: 从捕获生成测试

**目标**: 自动生成测试用例

```python
from tigerhill.observer import PromptCapture
from tigerhill.trace_store import TraceStore

def generate_tests_from_captures(capture_dir="./captures"):
    """从捕获数据生成测试用例"""
    capture = PromptCapture()
    trace_store = TraceStore(storage_path="./tests/traces")

    for capture_file in Path(capture_dir).glob("capture_*.json"):
        # 加载捕获
        with open(capture_file) as f:
            capture_data = json.load(f)

        capture_id = capture_data["capture_id"]
        capture.captures[capture_id] = capture_data

        # 导出到 TraceStore
        trace_id = capture.export_to_trace_store(
            capture_id,
            trace_store,
            agent_name=capture_data["agent_name"]
        )

        print(f"✅ Generated test from {capture_file.name}")
        print(f"   Trace ID: {trace_id}")

        # 生成测试代码
        generate_test_code(trace_id, capture_data)

def generate_test_code(trace_id, capture_data):
    """生成测试代码"""
    test_code = f'''
def test_from_capture_{trace_id[:8]}():
    """Auto-generated from capture"""
    tester = UniversalAgentTester(adapter, trace_store)

'''
    for i, request in enumerate(capture_data["requests"], 1):
        response = capture_data["responses"][i-1] if i <= len(capture_data["responses"]) else None

        test_code += f'''
    # Test case {i}
    result = tester.test({{
        "name": "capture_{trace_id[:8]}_case_{i}",
        "input": {repr(request["prompt"])},
        "expected": {{
            "response_length_min": {len(response["text"]) if response else 0},
            "response_time_max": 10.0
        }}
    }})
    assert result.passed
'''

    # 保存测试文件
    test_file = Path(f"tests/test_capture_{trace_id[:8]}.py")
    test_file.write_text(test_code)
    print(f"   Test code: {test_file}")
```

---

## 最佳实践

### 1. 开发环境集成

#### 环境变量控制

```python
import os

# 只在开发环境启用
ENABLE_CAPTURE = os.getenv("TIGERHILL_CAPTURE", "false") == "true"

if ENABLE_CAPTURE:
    from tigerhill.observer import instrument_generative_ai
    capture, capture_id, wrap_model = instrument_generative_ai("my_agent")
    GenerativeModel = wrap_model(GenerativeModel)
```

#### IDE 集成

在 VS Code 中添加调试配置：

```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: With Capture",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "env": {
                "TIGERHILL_CAPTURE": "true",
                "TIGERHILL_CAPTURE_PATH": "./debug_captures"
            }
        }
    ]
}
```

### 2. 捕获策略

#### 采样捕获

不是所有请求都需要捕获，可以采样：

```python
import random

class SamplingCapture:
    def __init__(self, capture, sample_rate=0.1):
        self.capture = capture
        self.sample_rate = sample_rate
        self.capture_id = None

    def should_capture(self):
        return random.random() < self.sample_rate

    def start_if_needed(self, agent_name):
        if self.should_capture():
            self.capture_id = self.capture.start_capture(agent_name)
        return self.capture_id

# 使用
sampling = SamplingCapture(capture, sample_rate=0.1)  # 10% 采样
```

#### 条件捕获

只在特定条件下捕获：

```python
def conditional_capture(request_data):
    # 只捕获长 prompt
    if len(request_data.get("prompt", "")) > 1000:
        return True

    # 只捕获使用工具的请求
    if request_data.get("tools"):
        return True

    return False
```

### 3. 性能优化

#### 异步捕获

```python
import asyncio
from queue import Queue
from threading import Thread

class AsyncCapture:
    def __init__(self, capture):
        self.capture = capture
        self.queue = Queue()
        self.worker = Thread(target=self._process_queue, daemon=True)
        self.worker.start()

    def capture_async(self, capture_id, data, is_response=False):
        self.queue.put((capture_id, data, is_response))

    def _process_queue(self):
        while True:
            capture_id, data, is_response = self.queue.get()
            if is_response:
                self.capture.capture_response(capture_id, data)
            else:
                self.capture.capture_request(capture_id, data)
            self.queue.task_done()
```

#### 批量保存

```python
class BatchCapture:
    def __init__(self, capture, batch_size=10):
        self.capture = capture
        self.batch_size = batch_size
        self.buffer = []

    def capture_request(self, capture_id, data):
        self.buffer.append(("request", capture_id, data))
        if len(self.buffer) >= self.batch_size:
            self.flush()

    def flush(self):
        for type, capture_id, data in self.buffer:
            if type == "request":
                self.capture.capture_request(capture_id, data)
            else:
                self.capture.capture_response(capture_id, data)
        self.buffer.clear()
```

### 4. 数据管理

#### 自动清理

```python
from datetime import datetime, timedelta
from pathlib import Path

def cleanup_old_captures(capture_dir="./captures", days=7):
    """删除超过 N 天的捕获数据"""
    cutoff = datetime.now() - timedelta(days=days)

    for capture_file in Path(capture_dir).glob("capture_*.json"):
        mtime = datetime.fromtimestamp(capture_file.stat().st_mtime)
        if mtime < cutoff:
            capture_file.unlink()
            print(f"Deleted old capture: {capture_file.name}")
```

#### 压缩存储

```python
import gzip
import json

def compress_capture(capture_file):
    """压缩捕获文件"""
    with open(capture_file) as f:
        data = json.load(f)

    compressed_file = capture_file.with_suffix(".json.gz")
    with gzip.open(compressed_file, "wt", encoding="utf-8") as f:
        json.dump(data, f)

    capture_file.unlink()  # 删除原文件
    return compressed_file
```

### 5. 隐私和安全

#### 脱敏验证

```python
def verify_redaction(capture_data):
    """验证脱敏是否完整"""
    sensitive_patterns = [
        r"AIza[0-9A-Za-z-_]{20,}",
        r"sk-[0-9A-Za-z-_]{20,}",
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    ]

    import re

    def check_text(text):
        for pattern in sensitive_patterns:
            if re.search(pattern, text):
                return False
        return True

    # 检查所有文本字段
    for request in capture_data.get("requests", []):
        if not check_text(str(request)):
            raise ValueError("Sensitive data detected in requests!")

    for response in capture_data.get("responses", []):
        if not check_text(str(response)):
            raise ValueError("Sensitive data detected in responses!")

    return True
```

#### 加密存储

```python
from cryptography.fernet import Fernet

class EncryptedCapture:
    def __init__(self, capture, key=None):
        self.capture = capture
        self.key = key or Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def save_encrypted(self, capture_data, filepath):
        # 序列化
        json_data = json.dumps(capture_data)

        # 加密
        encrypted = self.cipher.encrypt(json_data.encode())

        # 保存
        with open(filepath, "wb") as f:
            f.write(encrypted)

    def load_encrypted(self, filepath):
        # 读取
        with open(filepath, "rb") as f:
            encrypted = f.read()

        # 解密
        decrypted = self.cipher.decrypt(encrypted)

        # 反序列化
        return json.loads(decrypted.decode())
```

### 6. 监控和告警

#### Prometheus 集成

```python
from prometheus_client import Counter, Histogram, Gauge

# 定义指标
capture_requests_total = Counter("tigerhill_capture_requests_total", "Total capture requests")
capture_tokens_total = Counter("tigerhill_capture_tokens_total", "Total tokens captured")
capture_duration_seconds = Histogram("tigerhill_capture_duration_seconds", "Capture duration")
active_captures = Gauge("tigerhill_active_captures", "Active capture sessions")

class MonitoredCapture:
    def __init__(self, capture):
        self.capture = capture

    def start_capture(self, agent_name):
        capture_id = self.capture.start_capture(agent_name)
        active_captures.inc()
        return capture_id

    def capture_request(self, capture_id, data):
        self.capture.capture_request(capture_id, data)
        capture_requests_total.inc()

    def capture_response(self, capture_id, data):
        self.capture.capture_response(capture_id, data)
        if data.get("usage"):
            tokens = data["usage"].get("total_tokens", 0)
            capture_tokens_total.inc(tokens)

    def end_capture(self, capture_id):
        result = self.capture.end_capture(capture_id)
        active_captures.dec()
        capture_duration_seconds.observe(result["duration"])
        return result
```

#### Slack 告警

```python
import requests

def send_slack_alert(webhook_url, message):
    """发送 Slack 告警"""
    payload = {"text": message}
    requests.post(webhook_url, json=payload)

def check_and_alert(report, webhook_url):
    """检查报告并发送告警"""
    alerts = []

    # Token 使用过高
    avg_tokens = report["token_analysis"]["avg_tokens_per_request"]
    if avg_tokens > 3000:
        alerts.append(f"⚠️ High token usage: {avg_tokens:.0f} tokens/request")

    # 响应时间过长
    avg_duration = report["performance"]["avg_duration"]
    if avg_duration > 10:
        alerts.append(f"⚠️ Slow response: {avg_duration:.2f}s")

    # 质量评分低
    clarity = report["prompt_quality"]["clarity_score"]
    if clarity < 0.5:
        alerts.append(f"⚠️ Low prompt quality: {clarity:.2f}/1.0")

    if alerts:
        message = "TigerHill Observer Alerts:\n" + "\n".join(alerts)
        send_slack_alert(webhook_url, message)
```

---

## 故障排除

### 常见问题

#### 1. 捕获数据为空

**症状**: `end_capture()` 返回空的 requests/responses 列表

**原因**:
- 包装器未正确应用
- 回调函数未正确设置
- Capture ID 不匹配

**解决方案**:
```python
# 检查包装是否成功
print(type(model))  # 应该是 WrappedGenerativeModel

# 检查 callback 是否被调用
def debug_callback(data):
    print(f"Callback called: {data}")
    capture.capture_request(capture_id, data)

# 确保使用正确的 capture_id
print(f"Using capture_id: {capture_id}")
```

#### 2. JSON 序列化错误

**症状**: `TypeError: Object of type X is not JSON serializable`

**原因**:
- 捕获的数据包含不可序列化的对象（如 Mock 对象）

**解决方案**:
```python
# 禁用 auto_save 进行测试
capture = PromptCapture(auto_save=False)

# 或自定义序列化
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return str(obj)

json.dump(data, f, cls=CustomEncoder)
```

#### 3. 脱敏不完整

**症状**: 捕获数据中仍包含敏感信息

**原因**:
- 默认规则未覆盖
- 自定义格式的敏感数据

**解决方案**:
```python
# 添加自定义规则
custom_patterns = [
    {"pattern": r"your-custom-pattern", "replacement": "<REDACTED>"}
]

capture = PromptCapture(redact_patterns=custom_patterns)

# 验证
verify_redaction(capture_data)
```

#### 4. 性能影响

**症状**: 应用变慢

**原因**:
- 同步捕获阻塞主流程
- 频繁的文件 I/O

**解决方案**:
```python
# 使用异步捕获
async_capture = AsyncCapture(capture)

# 禁用 auto_save
capture = PromptCapture(auto_save=False)

# 批量保存
batch_capture = BatchCapture(capture, batch_size=20)
```

#### 5. 内存占用过高

**症状**: 内存持续增长

**原因**:
- 长时间运行未释放捕获数据
- 大量文本数据堆积

**解决方案**:
```python
# 定期结束捕获
if time.time() - start_time > 3600:  # 1 小时
    capture.end_capture(capture_id)
    capture_id = capture.start_capture(agent_name)

# 限制历史数据
max_captures = 100
if len(capture.captures) > max_captures:
    # 移除最旧的
    oldest = min(capture.captures.keys())
    del capture.captures[oldest]
```

### 调试技巧

#### 启用详细日志

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("tigerhill.observer")
logger.setLevel(logging.DEBUG)
```

#### 验证捕获流程

```python
def verify_capture_flow():
    """验证捕获流程是否正常"""
    capture = PromptCapture()

    # 1. 开始捕获
    capture_id = capture.start_capture("test")
    assert capture_id in capture.captures
    print("✅ Start capture OK")

    # 2. 捕获请求
    capture.capture_request(capture_id, {"model": "test", "prompt": "hi"})
    assert len(capture.get_capture(capture_id)["requests"]) == 1
    print("✅ Capture request OK")

    # 3. 捕获响应
    capture.capture_response(capture_id, {"text": "hello"})
    assert len(capture.get_capture(capture_id)["responses"]) == 1
    print("✅ Capture response OK")

    # 4. 结束捕获
    result = capture.end_capture(capture_id)
    assert result["status"] == "completed"
    print("✅ End capture OK")

    print("\n✅ All verification passed!")

verify_capture_flow()
```

#### 检查包装器

```python
def check_wrapper():
    """检查包装器是否正确应用"""
    from tigerhill.observer import wrap_python_model

    # 创建 mock 类
    class MockModel:
        def generate_content(self, prompt):
            return f"Response to: {prompt}"

    # 包装
    captured = []
    WrappedModel = wrap_python_model(
        MockModel,
        capture_callback=lambda data: captured.append(data)
    )

    # 测试
    model = WrappedModel()
    result = model.generate_content("test")

    # 验证
    assert len(captured) > 0, "No data captured!"
    assert captured[0].get("prompt") == "test"
    print("✅ Wrapper working correctly")

check_wrapper()
```

### 获取帮助

如果遇到问题：

1. **查看日志**: 启用 DEBUG 级别日志
2. **运行验证**: 使用上述验证脚本
3. **检查版本**: 确保使用最新版本
4. **查看示例**: 参考 `examples/` 目录
5. **提交 Issue**: GitHub Issues

---

## 总结

TigerHill Observer SDK 提供了：

✅ **无侵入式捕获** - 透明包装，不改代码
✅ **自动分析** - 5 维度深度分析
✅ **隐私保护** - 自动脱敏敏感信息
✅ **无缝集成** - 导出到 TraceStore
✅ **跨语言支持** - Python 和 Node.js

**开始使用**:
```bash
# Python
python examples/observer_python_basic.py

# Node.js
node examples/observer_nodejs_basic.js
```

**下一步**:
- 在开发环境集成 Observer
- 定期运行分析获取优化建议
- 将捕获数据转换为测试用例
- 集成到 CI/CD 流程

---

📚 **相关文档**:
- [快速开始](./QUICK_START.md)
- [API 参考](./API_REFERENCE.md)
- [示例代码](./examples/README.md)
- [最佳实践](./BEST_PRACTICES.md)

🤝 **社区**:
- [GitHub Issues](https://github.com/yourusername/tigerhill/issues)
- [Discussions](https://github.com/yourusername/tigerhill/discussions)

📝 **License**: MIT

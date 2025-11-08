# 🚀 TigerHill 快速开始

5 分钟快速上手 TigerHill Agent 测试平台

---

## 🎯 新功能速览：Observer SDK **[新]**

TigerHill 现在支持 **Debug Mode**，可以无侵入式捕获和分析 LLM 交互！

### 30 秒快速体验

```python
from tigerhill.observer import PromptCapture, wrap_python_model
from tigerhill.observer.python_observer import create_observer_callback
import google.generativeai as genai

# 1. 创建捕获器
capture = PromptCapture()
capture_id = capture.start_capture("my_agent")

# 2. 包装模型
callback = create_observer_callback(capture, capture_id)
WrappedModel = wrap_python_model(genai.GenerativeModel, callback)
model = WrappedModel("gemini-pro")

# 3. 正常使用（完全透明）
response = model.generate_content("Hello!")

# 4. 获取分析
result = capture.end_capture(capture_id)
print(f"📊 Captured {result['statistics']['total_tokens']} tokens")
```

**功能特性**:
- ✅ 无侵入式捕获（不改代码）
- ✅ 自动分析（5 维度、22 指标）
- ✅ 智能建议（Token/质量/性能优化）
- ✅ 隐私保护（自动脱敏）
- ✅ TraceStore 集成（转测试用例）

**详细文档**:
- [OBSERVER_SDK_QUICK_SUMMARY.md](OBSERVER_SDK_QUICK_SUMMARY.md) - 快速参考
- [OBSERVER_SDK_DOCUMENTATION.md](OBSERVER_SDK_DOCUMENTATION.md) - 完整文档
- [examples/README.md](examples/README.md) - 示例指南

**示例代码**:
```bash
python examples/observer_python_basic.py      # Python 基础
python examples/observer_python_analysis.py   # 自动分析
node examples/observer_nodejs_basic.js        # Node.js
```

---

## 🏗️ 使用架构说明

**TigerHill 是一个独立的测试框架**，有两种使用方式：

### 方式 1: 在你的 Agent 项目中安装 TigerHill（推荐）✅

```
你的 Agent 项目/
├── my_agent/
│   ├── __init__.py
│   └── agent.py          # 你的 Agent 代码
├── tests/
│   └── test_agent.py     # 使用 TigerHill 测试
├── requirements.txt
└── pyproject.toml
```

**安装方式**:
```bash
# 在你的 Agent 项目目录
cd /path/to/your_agent_project/

# 方式 A: 从本地安装 TigerHill（开发中）
pip install -e /path/to/TigerHill

# 方式 B: 从 PyPI 安装（将来支持）
# pip install tigerhill

# 可选：安装 AgentBay SDK
pip install wuying-agentbay-sdk
```

### 方式 2: 测试非 Python Agent（HTTP/CLI/等）

如果你的 Agent 是用其他语言编写的（Node.js、Go、Rust 等），你不需要安装到同一个环境：

```
TigerHill/               # TigerHill 测试框架
└── tests/
    └── test_my_agent.py # 测试脚本

你的 Agent/              # 可以在任何地方
├── agent.js            # Node.js Agent
└── package.json
```

**测试方式**: 通过 HTTP API、CLI 命令等方式调用

---

## 📦 安装步骤

### 选项 1: 测试 Python Agent（在你的项目中）

```bash
# 1. 在你的 Agent 项目目录
cd /path/to/your_agent_project/

# 2. 安装 TigerHill
pip install -e /path/to/TigerHill

# 3. 创建测试文件
mkdir -p tests
touch tests/test_my_agent.py
```

### 选项 2: 测试非 Python Agent（使用适配器）

```bash
# 1. 进入 TigerHill 目录或任何测试目录
cd /path/to/TigerHill

# 2. 确保 TigerHill 已安装
pip install -e ".[dev]"

# 3. 启动你的 Agent（如果需要）
# 例如: node your_agent.js
# 或: ./go_agent
```

---

## 🎯 快速上手示例

### 示例 1: 测试 Python Agent

假设你有一个 Python Agent 项目：

```python
# your_agent_project/my_agent/agent.py
class MyAgent:
    def run(self, prompt: str) -> str:
        # 你的 Agent 逻辑
        if "计算" in prompt:
            return "计算结果是 13"
        return f"处理了: {prompt}"
```

**创建测试文件**:

```python
# your_agent_project/tests/test_my_agent.py
from tigerhill.storage.trace_store import TraceStore
from tigerhill.core.models import Task
from tigerhill.eval.assertions import run_assertions

from my_agent.agent import MyAgent  # 导入你的 Agent

def test_my_agent():
    """测试我的 Agent"""

    # 1. 初始化 TigerHill
    store = TraceStore(storage_path="./traces")

    # 2. 定义测试任务
    task = Task(
        prompt="计算 6 + 7",
        assertions=[
            {"type": "contains", "expected": "13"}
        ]
    )

    # 3. 开始追踪
    trace_id = store.start_trace(agent_name="my_agent")

    # 4. 运行你的 Agent
    agent = MyAgent()
    output = agent.run(task.prompt)

    # 5. 记录执行过程
    store.write_event({"type": "prompt", "content": task.prompt})
    store.write_event({"type": "model_response", "text": output})
    store.end_trace(trace_id)

    # 6. 评估结果
    results = run_assertions(output, task.assertions)
    passed = sum(1 for r in results if r["ok"])

    print(f"✅ 通过: {passed}/{len(results)}")
    print(f"📊 追踪 ID: {trace_id}")

    assert passed == len(results), "断言未全部通过"

if __name__ == "__main__":
    test_my_agent()
```

**运行测试**:
```bash
cd /path/to/your_agent_project/
python tests/test_my_agent.py
```

---

### 示例 2: 测试 HTTP Agent (Node.js/Go/等)

假设你有一个 Node.js Agent 提供 HTTP 接口：

```javascript
// your_nodejs_agent/agent.js
const express = require('express');
const app = express();
app.use(express.json());

app.post('/api/agent', (req, res) => {
    const { prompt } = req.body;
    const output = `处理了: ${prompt}`;
    res.json({ output });
});

app.listen(3000, () => console.log('Agent running on port 3000'));
```

**创建测试文件** (可以在任何地方):

```python
# test_nodejs_agent.py
from tigerhill.adapters import HTTPAgentAdapter, UniversalAgentTester
from tigerhill.storage.trace_store import TraceStore

def test_nodejs_agent():
    """测试 Node.js HTTP Agent"""

    # 1. 创建 HTTP 适配器
    adapter = HTTPAgentAdapter(
        base_url="http://localhost:3000",
        endpoint="/api/agent"
    )

    # 2. 创建测试器
    store = TraceStore(storage_path="./traces")
    tester = UniversalAgentTester(adapter, store)

    # 3. 执行测试
    result = tester.test(
        task={
            "prompt": "测试消息",
            "assertions": [
                {"type": "contains", "expected": "处理了"}
            ]
        },
        agent_name="nodejs_agent"
    )

    print(f"✅ 通过: {result['passed']}/{result['total']}")

if __name__ == "__main__":
    # 确保 Node.js Agent 正在运行
    test_nodejs_agent()
```

**运行测试**:
```bash
# 终端 1: 启动 Node.js Agent
cd your_nodejs_agent/
node agent.js

# 终端 2: 运行测试
python test_nodejs_agent.py
```

---

### 示例 3: 测试 CLI Agent (Go/Rust/等)

假设你有一个 Go 编写的命令行 Agent：

```go
// go_agent/agent.go
package main
import "fmt"
import "os"

func main() {
    if len(os.Args) < 2 {
        fmt.Println("用法: agent <prompt>")
        return
    }
    prompt := os.Args[1]
    fmt.Printf("Go Agent 处理: %s\n", prompt)
}
```

**编译并测试**:

```python
# test_go_agent.py
from tigerhill.adapters import CLIAgentAdapter, UniversalAgentTester
from tigerhill.storage.trace_store import TraceStore

def test_go_agent():
    """测试 Go CLI Agent"""

    # 1. 创建 CLI 适配器
    adapter = CLIAgentAdapter(
        command="./go_agent/agent",  # Go 编译后的可执行文件
        args_template=["{prompt}"]
    )

    # 2. 创建测试器
    store = TraceStore(storage_path="./traces")
    tester = UniversalAgentTester(adapter, store)

    # 3. 执行测试
    result = tester.test(
        task={
            "prompt": "测试",
            "assertions": [
                {"type": "contains", "expected": "Go Agent"}
            ]
        },
        agent_name="go_agent"
    )

    print(f"✅ 通过: {result['passed']}/{result['total']}")

if __name__ == "__main__":
    test_go_agent()
```

**运行**:
```bash
# 编译 Go Agent
cd go_agent/
go build -o agent agent.go

# 运行测试
cd ..
python test_go_agent.py
```

---

## 📂 推荐的项目结构

### Python Agent 项目

```
my_agent_project/
├── my_agent/              # 你的 Agent 代码
│   ├── __init__.py
│   ├── agent.py
│   └── utils.py
├── tests/                 # 测试目录
│   ├── __init__.py
│   ├── test_agent.py     # 使用 TigerHill 的测试
│   └── test_utils.py
├── traces/               # TigerHill 生成的追踪数据 (gitignore)
├── requirements.txt
│   # 包含: tigerhill
└── pyproject.toml
```

### 多语言 Agent 项目

```
my_project/
├── agent/                # 你的 Agent (任何语言)
│   ├── agent.js         # Node.js
│   ├── agent.go         # Go
│   └── ...
├── tests/                # Python 测试脚本
│   ├── test_agent.py    # 使用 TigerHill
│   └── ...
└── traces/              # 追踪数据 (gitignore)
```

---

## 🔧 集成到现有项目

### 步骤 1: 安装依赖

在你的项目中添加 TigerHill：

**requirements.txt**:
```txt
# 从本地安装（开发期间）
-e /path/to/TigerHill

# 或将来从 PyPI 安装
# tigerhill

# 可选
wuying-agentbay-sdk
```

或者 **pyproject.toml**:
```toml
[project]
dependencies = [
    "tigerhill",  # 将来支持
    # 或临时用本地路径
]

[project.optional-dependencies]
dev = [
    "pytest",
    "wuying-agentbay-sdk",
]
```

### 步骤 2: 添加 .gitignore

```gitignore
# TigerHill 生成的数据
traces/
*_traces/
*.trace
```

### 步骤 3: 创建测试

参考上面的示例创建 `tests/test_agent.py`

### 步骤 4: 运行测试

```bash
python tests/test_agent.py
# 或使用 pytest
pytest tests/
```

---

## 📊 查看追踪数据

测试运行后，追踪数据保存在 `traces/` 目录：

```python
from tigerhill.storage.trace_store import TraceStore

store = TraceStore(storage_path="./traces")

# 列出所有追踪
traces = store.get_all_traces()
print(f"总追踪数: {len(traces)}")

# 查看特定追踪
trace_id = "your-trace-id"
summary = store.get_summary(trace_id)
print(f"Agent: {summary['agent_name']}")
print(f"事件数: {summary['total_events']}")
print(f"耗时: {summary['duration_seconds']:.2f} 秒")

# 导出追踪
store.export_trace(trace_id, "./report.json")
```

---

## 🌐 使用 AgentBay（可选）

如果需要在云端隔离环境测试：

```python
from tigerhill.agentbay.client import AgentBayClient, EnvironmentType
from tigerhill.storage.trace_store import TraceStore

# 设置 API Key
# export AGENTBAY_API_KEY=your_key_here

store = TraceStore()

# 使用 AgentBay
with AgentBayClient() as client:
    # 创建云端会话
    session = client.create_session(env_type=EnvironmentType.CODESPACE)
    session_id = session["session_id"]

    # 执行命令
    result = client.execute_command(
        session_id,
        "python -c 'print(6 + 7)'"
    )

    print(f"输出: {result['output']}")
    # 自动清理
```

---

## ❓ 常见问题

### Q1: TigerHill 安装在哪里？

**A**: TigerHill 作为 Python 包安装到你的项目虚拟环境中，就像安装 pytest 或 requests 一样。

```bash
# 在你的项目中
pip install -e /path/to/TigerHill

# TigerHill 会被安装到 site-packages/
# 你的 Agent 代码保持在原来的位置
```

### Q2: 我的 Agent 代码放在哪里？

**A**: 你的 Agent 代码保持在自己的项目中，不需要移动。

- **Python Agent**: 通过 import 调用
- **非 Python Agent**: 通过 HTTP/CLI/STDIO 调用

### Q3: 如何测试已经在运行的 Agent？

**A**: 使用相应的适配器：

```python
# HTTP Agent
from tigerhill.adapters import HTTPAgentAdapter
adapter = HTTPAgentAdapter("http://your-agent:8000")

# CLI Agent
from tigerhill.adapters import CLIAgentAdapter
adapter = CLIAgentAdapter("./your_agent")
```

### Q4: 追踪数据保存在哪里？

**A**: 默认保存在当前目录的 `traces/` 文件夹，可以自定义：

```python
store = TraceStore(storage_path="./my_custom_traces")
```

建议在 `.gitignore` 中排除追踪数据。

### Q5: 可以在 CI/CD 中使用吗？

**A**: 可以！TigerHill 可以集成到任何 CI/CD 流程：

```yaml
# .github/workflows/test.yml
- name: Install dependencies
  run: pip install -e /path/to/TigerHill

- name: Run tests
  run: pytest tests/
```

---

## 📚 下一步

- **完整文档**: 查看 [USER_GUIDE.md](USER_GUIDE.md)
- **跨语言测试**: 查看 [CROSS_LANGUAGE_TESTING.md](CROSS_LANGUAGE_TESTING.md)
- **示例代码**: 查看 `examples/` 目录
- **AgentBay 使用**: 查看 [AGENTBAY_TESTING_GUIDE.md](AGENTBAY_TESTING_GUIDE.md)

---

## 🆘 获取帮助

遇到问题？

1. 检查项目结构是否正确
2. 确认 TigerHill 已正确安装: `pip list | grep tigerhill`
3. 查看完整错误信息
4. 参考 `examples/` 目录的示例

---

**🎉 开始测试你的 Agent 吧！**

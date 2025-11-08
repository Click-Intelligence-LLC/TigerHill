# 跨语言 Agent 测试示例 / Cross-Language Agent Testing Examples

本目录包含使用 TigerHill 测试不同编程语言 Agent 的完整示例。

## 📁 文件说明

| 文件 | 说明 |
|------|------|
| `nodejs_agent.js` | Node.js Agent 实现（HTTP API） |
| `test_nodejs_agent.py` | Node.js Agent 测试脚本 |
| `go_agent.go` | Go Agent 实现（CLI） |
| `test_go_agent.py` | Go Agent 测试脚本 |
| `batch_test_multilang.py` | 批量测试多语言 Agent |
| `package.json` | Node.js 依赖配置 |

## 🚀 快速开始

### 1. 测试 Node.js Agent

```bash
# 终端 1: 启动 Node.js Agent
cd examples/cross_language
npm install
node nodejs_agent.js

# 终端 2: 运行测试
python test_nodejs_agent.py
```

### 2. 测试 Go Agent

```bash
# 编译 Go Agent
cd examples/cross_language
go build -o go_agent go_agent.go

# 运行测试
python test_go_agent.py
```

### 3. 批量测试多语言

```bash
# 确保 Node.js Agent 正在运行，Go Agent 已编译
python batch_test_multilang.py
```

## 📊 示例输出

### Node.js Agent 测试

```
==============================================================
测试 Node.js 计算器 Agent
==============================================================
✓ TraceStore 初始化完成
✓ HTTP Agent 适配器创建完成
✓ 通用测试器创建完成

开始批量测试...

测试 1:
  状态: ✅
  提示: 计算 6 + 7
  输出: 计算结果: 6 + 7 = 13
  断言: 1/1 通过
  耗时: 0.05 秒

==============================================================
测试汇总报告
==============================================================
总测试数: 3
成功: 3
成功率: 100.0%
断言通过率: 100.0%
==============================================================
```

### Go Agent 测试

```
==============================================================
测试 Go CLI Agent
==============================================================
✓ TraceStore 初始化完成
✓ CLI Agent 适配器创建完成

测试 1:
  状态: ✅
  提示: 列出文件
  输出: {"output":"Go Agent 文件列表功能：...","status":"success"}
  断言: 2/2 通过
  耗时: 0.012 秒
```

### 批量多语言测试

```
======================================================================
                   TigerHill 跨语言批量测试
======================================================================

检测到 3 个可用 Agent

======================================================================
测试 Node.js Agent: nodejs_http_agent
======================================================================

执行任务 1/2: 计算 10 + 20...
  结果: ✅
  断言: 1/1 通过
  耗时: 0.045 秒

======================================================================
测试 Go Agent: go_cli_agent
======================================================================

执行任务 1/2: 列出文件...
  结果: ✅
  断言: 1/1 通过
  耗时: 0.008 秒

======================================================================
                        总体测试报告
======================================================================

测试的语言数: 3
总测试数: 6
成功测试: 6
总体成功率: 100.0%

总断言数: 6
通过断言: 6
断言通过率: 100.0%

按语言统计:
----------------------------------------------------------------------

Node.js:
  测试数: 2
  成功率: 100.0%
  断言通过率: 100.0%
  平均耗时: 0.047 秒

Go:
  测试数: 2
  成功率: 100.0%
  断言通过率: 100.0%
  平均耗时: 0.009 秒

Python:
  测试数: 2
  成功率: 100.0%
  断言通过率: 100.0%
  平均耗时: 0.001 秒
```

## 🎯 核心概念

### Agent 适配器

TigerHill 使用适配器模式支持不同类型的 Agent：

#### 1. HTTPAgentAdapter - HTTP/REST API Agent

```python
from tigerhill.adapters import HTTPAgentAdapter

adapter = HTTPAgentAdapter(
    base_url="http://localhost:3000",
    endpoint="/api/agent",
    timeout=30
)

response = adapter.invoke("你的提示")
```

适用于：
- Node.js Express/Fastify
- Python Flask/FastAPI
- Go HTTP 服务
- Java Spring Boot
- 任何提供 HTTP 接口的 Agent

#### 2. CLIAgentAdapter - 命令行 Agent

```python
from tigerhill.adapters import CLIAgentAdapter

adapter = CLIAgentAdapter(
    command="./my_agent",
    args_template=["{prompt}"],
    timeout=10
)

response = adapter.invoke("你的提示")
```

适用于：
- Go 可执行文件
- Rust 编译程序
- C/C++ 程序
- Shell 脚本
- 任何命令行工具

#### 3. STDIOAgentAdapter - 标准输入输出

```python
from tigerhill.adapters import STDIOAgentAdapter

adapter = STDIOAgentAdapter(
    command="java -jar agent.jar",
    response_timeout=30
)

response = adapter.invoke("你的提示")
adapter.cleanup()
```

适用于：
- Java 长期运行进程
- 交互式 Agent
- 流式处理程序

#### 4. AgentBayAdapter - 云环境

```python
from tigerhill.adapters import AgentBayAdapter
from tigerhill.agentbay.client import AgentBayClient

client = AgentBayClient()
session = client.create_session()

adapter = AgentBayAdapter(
    client=client,
    session_id=session["session_id"],
    agent_command="./agent '{prompt}'"
)

response = adapter.invoke("你的提示")
```

适用于：
- 需要隔离环境的 Agent
- 多语言混合测试
- 云原生应用

### UniversalAgentTester - 通用测试器

统一的测试接口，支持所有适配器：

```python
from tigerhill.adapters import UniversalAgentTester
from tigerhill.storage.trace_store import TraceStore

store = TraceStore()
tester = UniversalAgentTester(adapter, store)

result = tester.test(
    task={
        "prompt": "测试提示",
        "assertions": [
            {"type": "contains", "expected": "关键词"}
        ]
    },
    agent_name="my_agent"
)

print(f"通过: {result['passed']}/{result['total']}")
```

## 🔧 自定义 Agent 适配器

创建自己的适配器：

```python
from tigerhill.adapters.multi_language import AgentAdapter

class MyCustomAdapter(AgentAdapter):
    def __init__(self, config):
        self.config = config

    def invoke(self, prompt: str, **kwargs) -> str:
        # 实现你的调用逻辑
        response = my_custom_call(prompt)
        return response

    def cleanup(self):
        # 清理资源（可选）
        pass

# 使用
adapter = MyCustomAdapter(config={...})
tester = UniversalAgentTester(adapter, store)
```

## 📝 添加新语言

要添加新语言的 Agent：

### 1. 实现 Agent

创建你的 Agent（任何语言）：

**示例: Rust Agent (agent.rs)**
```rust
use std::env;

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage: {} <prompt>", args[0]);
        return;
    }

    let prompt = &args[1];
    let response = process_prompt(prompt);

    println!("{}", response);
}

fn process_prompt(prompt: &str) -> String {
    format!("Rust Agent 处理: {}", prompt)
}
```

### 2. 选择适配器

根据 Agent 类型选择适配器：

```python
# 如果是命令行工具
adapter = CLIAgentAdapter(command="./rust_agent")

# 如果是 HTTP 服务
adapter = HTTPAgentAdapter(base_url="http://localhost:8080")
```

### 3. 编写测试

```python
from tigerhill.adapters import CLIAgentAdapter, UniversalAgentTester
from tigerhill.storage.trace_store import TraceStore

def test_rust_agent():
    store = TraceStore(storage_path="./traces/rust_agent")
    adapter = CLIAgentAdapter("./rust_agent", ["{prompt}"])
    tester = UniversalAgentTester(adapter, store)

    result = tester.test(
        task={
            "prompt": "测试 Rust Agent",
            "assertions": [
                {"type": "contains", "expected": "Rust Agent"}
            ]
        },
        agent_name="rust_cli_agent"
    )

    print(f"✅ 通过: {result['passed']}/{result['total']}")

if __name__ == "__main__":
    test_rust_agent()
```

## 🌟 最佳实践

### 1. 统一响应格式

建议 Agent 返回 JSON 格式：

```json
{
    "output": "Agent 的响应文本",
    "status": "success",
    "metadata": { }
}
```

### 2. 错误处理

确保 Agent 正确处理错误：

```javascript
// Node.js 示例
app.post('/api/agent', async (req, res) => {
    try {
        const output = await processPrompt(req.body.prompt);
        res.json({ output, status: 'success' });
    } catch (error) {
        res.status(500).json({
            error: error.message,
            status: 'error'
        });
    }
});
```

### 3. 超时控制

设置合理的超时时间：

```python
adapter = HTTPAgentAdapter(
    base_url="http://localhost:3000",
    timeout=30  # 秒
)

adapter = CLIAgentAdapter(
    command="./agent",
    timeout=10
)
```

### 4. 资源清理

使用上下文管理器：

```python
with STDIOAgentAdapter("java -jar agent.jar") as adapter:
    response = adapter.invoke("测试")
    # 自动清理
```

## 🐛 故障排查

### Node.js Agent 无法连接

```bash
# 检查端口占用
lsof -i :3000

# 查看 Agent 日志
node nodejs_agent.js
```

### Go Agent 编译失败

```bash
# 检查 Go 安装
go version

# 清理并重新编译
go clean
go build -o go_agent go_agent.go
```

### 测试超时

增加超时时间：

```python
adapter = HTTPAgentAdapter(
    base_url="http://localhost:3000",
    timeout=60  # 增加到 60 秒
)
```

## 📚 更多资源

- **完整文档**: [CROSS_LANGUAGE_TESTING.md](../../CROSS_LANGUAGE_TESTING.md)
- **用户指南**: [USER_GUIDE.md](../../USER_GUIDE.md)
- **快速开始**: [QUICK_START.md](../../QUICK_START.md)
- **API 文档**: [tigerhill/adapters/](../../tigerhill/adapters/)

## 🤝 贡献

欢迎添加更多语言的示例！

要添加新示例：
1. 创建 Agent 实现文件（如 `rust_agent.rs`）
2. 创建测试文件（如 `test_rust_agent.py`）
3. 更新本 README
4. 提交 Pull Request

## 📄 许可证

MIT License - 详见 [LICENSE](../../LICENSE)

---

**开始测试你的多语言 Agent 吧！** 🚀

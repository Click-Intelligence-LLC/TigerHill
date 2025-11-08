# 跨语言 Agent 测试指南 / Cross-Language Agent Testing Guide

## 概述 / Overview

TigerHill 虽然是用 Python 编写的，但可以测试**任何编程语言**编写的 Agent。本指南展示如何测试非 Python Agent。

While TigerHill is written in Python, it can test agents written in **any programming language**. This guide shows how to test non-Python agents.

---

## 核心原理 / Core Principles

TigerHill 通过以下方式与非 Python Agent 交互：

1. **HTTP/REST API** - Agent 作为 Web 服务
2. **命令行接口 (CLI)** - Agent 作为可执行程序
3. **AgentBay 云环境** - 语言无关的执行环境
4. **进程间通信 (IPC)** - 通过标准输入/输出
5. **消息队列** - 异步通信

---

## 方法 1: HTTP/REST API（推荐）

### 适用场景
- Agent 提供 HTTP 接口
- 微服务架构
- 云部署的 Agent

### 示例：测试 Node.js Agent

#### Node.js Agent (agent.js)

```javascript
// agent.js - 一个简单的 Node.js Agent
const express = require('express');
const app = express();
app.use(express.json());

app.post('/api/agent', async (req, res) => {
    const { prompt } = req.body;

    // Agent 逻辑
    const response = await processPrompt(prompt);

    res.json({
        output: response,
        status: 'success'
    });
});

async function processPrompt(prompt) {
    // 模拟 Agent 处理
    if (prompt.includes('计算')) {
        return '计算结果: 42';
    }
    return `处理了提示: ${prompt}`;
}

app.listen(3000, () => {
    console.log('Agent 运行在 http://localhost:3000');
});
```

#### TigerHill 测试代码 (Python)

```python
import requests
from tigerhill.storage.trace_store import TraceStore
from tigerhill.core.models import Task
from tigerhill.eval.assertions import run_assertions

def test_nodejs_agent():
    """测试 Node.js Agent"""

    # 1. 初始化 TraceStore
    store = TraceStore(storage_path="./traces/nodejs_agent")

    # 2. 定义测试任务
    task = Task(
        prompt="计算 1 + 1 的结果",
        assertions=[
            {"type": "contains", "expected": "42"}
        ]
    )

    # 3. 开始追踪
    trace_id = store.start_trace(
        agent_name="nodejs_calculator",
        task_id="test_001"
    )

    # 4. 调用 Node.js Agent
    store.write_event({
        "type": "prompt",
        "content": task.prompt
    })

    try:
        response = requests.post(
            "http://localhost:3000/api/agent",
            json={"prompt": task.prompt},
            timeout=30
        )
        response.raise_for_status()

        agent_output = response.json()["output"]

        store.write_event({
            "type": "http_request",
            "url": "http://localhost:3000/api/agent",
            "method": "POST",
            "status_code": response.status_code
        })

        store.write_event({
            "type": "model_response",
            "text": agent_output
        })

    except Exception as e:
        store.write_event({
            "type": "error",
            "error": str(e)
        })
        raise
    finally:
        store.end_trace(trace_id)

    # 5. 评估结果
    results = run_assertions(agent_output, task.assertions)
    passed = sum(1 for r in results if r["ok"])

    print(f"✅ 通过: {passed}/{len(results)}")
    print(f"📊 追踪 ID: {trace_id}")

    return results

# 运行测试
if __name__ == "__main__":
    # 确保 Node.js Agent 已启动
    # node agent.js
    test_nodejs_agent()
```

### 启动和测试

```bash
# 终端 1: 启动 Node.js Agent
cd nodejs_agent
npm install express
node agent.js

# 终端 2: 运行 TigerHill 测试
cd TigerHill
python examples/test_nodejs_agent.py
```

---

## 方法 2: 命令行接口 (CLI)

### 适用场景
- Agent 是独立可执行文件
- 命令行工具
- Shell 脚本

### 示例：测试 Go Agent

#### Go Agent (agent.go)

```go
// agent.go - 一个简单的 Go Agent
package main

import (
    "encoding/json"
    "fmt"
    "os"
)

type Request struct {
    Prompt string `json:"prompt"`
}

type Response struct {
    Output string `json:"output"`
    Status string `json:"status"`
}

func main() {
    if len(os.Args) < 2 {
        fmt.Println("用法: agent <prompt>")
        os.Exit(1)
    }

    prompt := os.Args[1]

    // Agent 逻辑
    output := processPrompt(prompt)

    // 输出 JSON 响应
    response := Response{
        Output: output,
        Status: "success",
    }

    jsonOutput, _ := json.Marshal(response)
    fmt.Println(string(jsonOutput))
}

func processPrompt(prompt string) string {
    // 简单的处理逻辑
    return fmt.Sprintf("Go Agent 处理: %s", prompt)
}
```

#### TigerHill 测试代码

```python
import subprocess
import json
from tigerhill.storage.trace_store import TraceStore
from tigerhill.core.models import Task
from tigerhill.eval.assertions import run_assertions

def test_go_agent():
    """测试 Go CLI Agent"""

    store = TraceStore(storage_path="./traces/go_agent")

    task = Task(
        prompt="列出当前目录文件",
        assertions=[
            {"type": "contains", "expected": "Go Agent"},
            {"type": "regex", "pattern": r"处理"}
        ]
    )

    trace_id = store.start_trace(
        agent_name="go_cli_agent",
        task_id="test_cli_001"
    )

    store.write_event({
        "type": "prompt",
        "content": task.prompt
    })

    try:
        # 调用 Go Agent
        result = subprocess.run(
            ["./go_agent/agent", task.prompt],
            capture_output=True,
            text=True,
            timeout=30
        )

        store.write_event({
            "type": "subprocess_call",
            "command": f"./go_agent/agent {task.prompt}",
            "exit_code": result.returncode
        })

        if result.returncode != 0:
            raise RuntimeError(f"Agent 失败: {result.stderr}")

        # 解析 JSON 输出
        response = json.loads(result.stdout)
        agent_output = response["output"]

        store.write_event({
            "type": "model_response",
            "text": agent_output
        })

    except Exception as e:
        store.write_event({
            "type": "error",
            "error": str(e)
        })
        raise
    finally:
        store.end_trace(trace_id)

    # 评估
    results = run_assertions(agent_output, task.assertions)
    passed = sum(1 for r in results if r["ok"])

    print(f"✅ 通过: {passed}/{len(results)}")

    return results

if __name__ == "__main__":
    test_go_agent()
```

### 编译和测试

```bash
# 编译 Go Agent
cd go_agent
go build -o agent agent.go

# 测试
chmod +x agent
./agent "测试提示"

# 运行 TigerHill 测试
cd ..
python examples/test_go_agent.py
```

---

## 方法 3: AgentBay 云环境（最强大）

### 适用场景
- 需要隔离环境
- 多语言 Agent 混合测试
- 需要特定系统依赖
- 云原生 Agent

### 优势
- **语言无关**: 支持任何可以在 Linux 环境运行的语言
- **环境隔离**: 每个测试独立环境
- **云端执行**: 不占用本地资源
- **可重现**: 环境配置标准化

### 示例：在 AgentBay 测试 Python/Node.js/Go Agent

```python
from tigerhill.agentbay.client import AgentBayClient, EnvironmentType
from tigerhill.storage.trace_store import TraceStore
from tigerhill.core.models import Task
from tigerhill.eval.assertions import run_assertions

def test_multi_language_agents():
    """在 AgentBay 测试多语言 Agent"""

    store = TraceStore(storage_path="./traces/agentbay_multilang")

    with AgentBayClient() as client:
        # 测试 1: Python Agent
        print("\n=== 测试 Python Agent ===")
        test_python_in_agentbay(client, store)

        # 测试 2: Node.js Agent
        print("\n=== 测试 Node.js Agent ===")
        test_nodejs_in_agentbay(client, store)

        # 测试 3: Go Agent
        print("\n=== 测试 Go Agent ===")
        test_go_in_agentbay(client, store)

def test_python_in_agentbay(client, store):
    """测试 Python Agent"""
    trace_id = store.start_trace(agent_name="python_agent_cloud")

    session = client.create_session(env_type=EnvironmentType.CODESPACE)
    session_id = session["session_id"]

    try:
        # 创建 Python Agent 代码
        agent_code = """
import sys
prompt = sys.argv[1]
print(f"Python Agent 说: {prompt}")
"""

        # 上传并执行
        result = client.execute_command(
            session_id,
            f"echo '{agent_code}' > agent.py && python agent.py '计算 1+1'"
        )

        store.write_event({
            "type": "agentbay_execution",
            "language": "python",
            "output": result["output"]
        })

        print(f"✅ Python Agent: {result['output']}")

    finally:
        client.delete_session(session_id)
        store.end_trace(trace_id)

def test_nodejs_in_agentbay(client, store):
    """测试 Node.js Agent"""
    trace_id = store.start_trace(agent_name="nodejs_agent_cloud")

    session = client.create_session(env_type=EnvironmentType.CODESPACE)
    session_id = session["session_id"]

    try:
        # Node.js Agent 代码
        agent_code = """
const prompt = process.argv[2];
console.log(`Node.js Agent 说: ${prompt}`);
"""

        # 安装 Node.js 并执行
        commands = [
            "apt-get update && apt-get install -y nodejs",
            f"echo '{agent_code}' > agent.js",
            "node agent.js '你好'"
        ]

        for cmd in commands:
            result = client.execute_command(session_id, cmd)

        store.write_event({
            "type": "agentbay_execution",
            "language": "nodejs",
            "output": result["output"]
        })

        print(f"✅ Node.js Agent: {result['output']}")

    finally:
        client.delete_session(session_id)
        store.end_trace(trace_id)

def test_go_in_agentbay(client, store):
    """测试 Go Agent"""
    trace_id = store.start_trace(agent_name="go_agent_cloud")

    session = client.create_session(env_type=EnvironmentType.CODESPACE)
    session_id = session["session_id"]

    try:
        # Go Agent 代码
        agent_code = """
package main
import (
    "fmt"
    "os"
)
func main() {
    if len(os.Args) > 1 {
        fmt.Printf("Go Agent 说: %s\\n", os.Args[1])
    }
}
"""

        # 安装 Go 并编译执行
        commands = [
            "apt-get update && apt-get install -y golang",
            f"echo '{agent_code}' > agent.go",
            "go run agent.go '世界你好'"
        ]

        for cmd in commands:
            result = client.execute_command(session_id, cmd)

        store.write_event({
            "type": "agentbay_execution",
            "language": "go",
            "output": result["output"]
        })

        print(f"✅ Go Agent: {result['output']}")

    finally:
        client.delete_session(session_id)
        store.end_trace(trace_id)

if __name__ == "__main__":
    # 需要设置环境变量: export AGENTBAY_API_KEY=your_key
    test_multi_language_agents()
```

---

## 方法 4: 标准输入/输出 (STDIN/STDOUT)

### 适用场景
- Agent 通过标准 I/O 通信
- 管道式交互
- 流式处理

### 示例：测试 Java Agent

#### Java Agent (Agent.java)

```java
// Agent.java
import java.util.Scanner;

public class Agent {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);

        while (scanner.hasNextLine()) {
            String prompt = scanner.nextLine();

            if (prompt.equals("EXIT")) {
                break;
            }

            // Agent 逻辑
            String response = processPrompt(prompt);
            System.out.println(response);
            System.out.flush();
        }
    }

    private static String processPrompt(String prompt) {
        return "Java Agent 处理: " + prompt;
    }
}
```

#### TigerHill 测试代码

```python
import subprocess
from tigerhill.storage.trace_store import TraceStore
from tigerhill.core.models import Task
from tigerhill.eval.assertions import run_assertions

def test_java_agent_stdio():
    """通过标准 I/O 测试 Java Agent"""

    store = TraceStore(storage_path="./traces/java_agent")

    task = Task(
        prompt="分析这段代码",
        assertions=[
            {"type": "contains", "expected": "Java Agent"}
        ]
    )

    trace_id = store.start_trace(agent_name="java_agent_stdio")

    try:
        # 启动 Java Agent 进程
        process = subprocess.Popen(
            ["java", "Agent"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # 发送提示
        store.write_event({
            "type": "prompt",
            "content": task.prompt
        })

        process.stdin.write(task.prompt + "\n")
        process.stdin.flush()

        # 读取响应
        agent_output = process.stdout.readline().strip()

        store.write_event({
            "type": "model_response",
            "text": agent_output
        })

        # 关闭进程
        process.stdin.write("EXIT\n")
        process.stdin.flush()
        process.wait(timeout=5)

    except Exception as e:
        store.write_event({
            "type": "error",
            "error": str(e)
        })
        raise
    finally:
        store.end_trace(trace_id)

    # 评估
    results = run_assertions(agent_output, task.assertions)
    passed = sum(1 for r in results if r["ok"])

    print(f"✅ 通过: {passed}/{len(results)}")

    return results

if __name__ == "__main__":
    test_java_agent_stdio()
```

---

## 方法 5: gRPC（高性能）

### 适用场景
- 高性能要求
- 复杂数据类型
- 双向流式通信

### 示例：测试 Rust Agent

#### Rust Agent (agent.proto + agent.rs)

```protobuf
// agent.proto
syntax = "proto3";

service AgentService {
    rpc Process(PromptRequest) returns (PromptResponse);
}

message PromptRequest {
    string prompt = 1;
}

message PromptResponse {
    string output = 1;
    string status = 2;
}
```

#### TigerHill 测试代码

```python
import grpc
from tigerhill.storage.trace_store import TraceStore
from tigerhill.core.models import Task
from tigerhill.eval.assertions import run_assertions

# 假设已生成 agent_pb2 和 agent_pb2_grpc
import agent_pb2
import agent_pb2_grpc

def test_rust_agent_grpc():
    """测试 Rust gRPC Agent"""

    store = TraceStore(storage_path="./traces/rust_agent")

    task = Task(
        prompt="优化这个算法",
        assertions=[
            {"type": "contains", "expected": "优化"}
        ]
    )

    trace_id = store.start_trace(agent_name="rust_grpc_agent")

    try:
        # 连接 gRPC Agent
        channel = grpc.insecure_channel('localhost:50051')
        stub = agent_pb2_grpc.AgentServiceStub(channel)

        store.write_event({
            "type": "prompt",
            "content": task.prompt
        })

        # 调用 Agent
        request = agent_pb2.PromptRequest(prompt=task.prompt)
        response = stub.Process(request)

        agent_output = response.output

        store.write_event({
            "type": "grpc_call",
            "method": "Process",
            "status": response.status
        })

        store.write_event({
            "type": "model_response",
            "text": agent_output
        })

    except Exception as e:
        store.write_event({
            "type": "error",
            "error": str(e)
        })
        raise
    finally:
        store.end_trace(trace_id)

    # 评估
    results = run_assertions(agent_output, task.assertions)
    passed = sum(1 for r in results if r["ok"])

    print(f"✅ 通过: {passed}/{len(results)}")

    return results
```

---

## 通用测试框架封装

创建一个通用的 Agent 测试框架，支持所有语言：

```python
# tigerhill/adapters/multi_language.py

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from tigerhill.storage.trace_store import TraceStore
from tigerhill.eval.assertions import run_assertions

class AgentAdapter(ABC):
    """Agent 适配器基类"""

    @abstractmethod
    def invoke(self, prompt: str) -> str:
        """调用 Agent"""
        pass

    @abstractmethod
    def cleanup(self):
        """清理资源"""
        pass

class HTTPAgentAdapter(AgentAdapter):
    """HTTP Agent 适配器"""

    def __init__(self, base_url: str, endpoint: str = "/api/agent"):
        self.base_url = base_url
        self.endpoint = endpoint

    def invoke(self, prompt: str) -> str:
        import requests
        response = requests.post(
            f"{self.base_url}{self.endpoint}",
            json={"prompt": prompt}
        )
        return response.json()["output"]

    def cleanup(self):
        pass

class CLIAgentAdapter(AgentAdapter):
    """CLI Agent 适配器"""

    def __init__(self, command: str):
        self.command = command

    def invoke(self, prompt: str) -> str:
        import subprocess
        result = subprocess.run(
            [self.command, prompt],
            capture_output=True,
            text=True
        )
        return result.stdout.strip()

    def cleanup(self):
        pass

class AgentBayAdapter(AgentAdapter):
    """AgentBay Agent 适配器"""

    def __init__(self, client, session_id: str):
        self.client = client
        self.session_id = session_id

    def invoke(self, prompt: str) -> str:
        result = self.client.execute_command(
            self.session_id,
            f"./agent '{prompt}'"
        )
        return result["output"]

    def cleanup(self):
        self.client.delete_session(self.session_id)

class UniversalAgentTester:
    """通用 Agent 测试器"""

    def __init__(self, adapter: AgentAdapter, store: TraceStore):
        self.adapter = adapter
        self.store = store

    def test(self, task: Dict[str, Any], agent_name: str) -> Dict[str, Any]:
        """执行测试"""

        prompt = task["prompt"]
        assertions = task.get("assertions", [])

        trace_id = self.store.start_trace(agent_name=agent_name)

        try:
            self.store.write_event({
                "type": "prompt",
                "content": prompt
            })

            # 调用 Agent
            output = self.adapter.invoke(prompt)

            self.store.write_event({
                "type": "model_response",
                "text": output
            })

            # 评估
            results = run_assertions(output, assertions)
            passed = sum(1 for r in results if r["ok"])

            return {
                "trace_id": trace_id,
                "output": output,
                "passed": passed,
                "total": len(results),
                "results": results
            }

        except Exception as e:
            self.store.write_event({
                "type": "error",
                "error": str(e)
            })
            raise
        finally:
            self.store.end_trace(trace_id)
            self.adapter.cleanup()

# 使用示例
def example_usage():
    """使用通用测试框架"""

    store = TraceStore(storage_path="./traces/universal")

    # 测试 HTTP Agent (Node.js)
    http_adapter = HTTPAgentAdapter("http://localhost:3000")
    tester = UniversalAgentTester(http_adapter, store)

    result = tester.test(
        task={
            "prompt": "计算 1+1",
            "assertions": [{"type": "contains", "expected": "2"}]
        },
        agent_name="nodejs_http_agent"
    )

    print(f"HTTP Agent - 通过: {result['passed']}/{result['total']}")

    # 测试 CLI Agent (Go)
    cli_adapter = CLIAgentAdapter("./go_agent/agent")
    tester = UniversalAgentTester(cli_adapter, store)

    result = tester.test(
        task={
            "prompt": "列出文件",
            "assertions": [{"type": "contains", "expected": "Go"}]
        },
        agent_name="go_cli_agent"
    )

    print(f"CLI Agent - 通过: {result['passed']}/{result['total']}")
```

---

## 批量测试多语言 Agent

```python
# examples/batch_test_multilang.py

from tigerhill.adapters.multi_language import (
    UniversalAgentTester,
    HTTPAgentAdapter,
    CLIAgentAdapter
)
from tigerhill.storage.trace_store import TraceStore

def batch_test_agents():
    """批量测试多语言 Agent"""

    store = TraceStore(storage_path="./traces/batch_multilang")

    # 定义测试配置
    test_configs = [
        {
            "name": "nodejs_agent",
            "adapter": HTTPAgentAdapter("http://localhost:3000"),
            "tasks": [
                {
                    "prompt": "计算 6 + 7",
                    "assertions": [{"type": "contains", "expected": "13"}]
                },
                {
                    "prompt": "列出素数",
                    "assertions": [{"type": "regex", "pattern": r"\d+"}]
                }
            ]
        },
        {
            "name": "go_agent",
            "adapter": CLIAgentAdapter("./agents/go_agent"),
            "tasks": [
                {
                    "prompt": "分析代码",
                    "assertions": [{"type": "contains", "expected": "分析"}]
                }
            ]
        },
        {
            "name": "java_agent",
            "adapter": CLIAgentAdapter("java -jar agents/agent.jar"),
            "tasks": [
                {
                    "prompt": "优化算法",
                    "assertions": [{"type": "contains", "expected": "优化"}]
                }
            ]
        }
    ]

    # 执行批量测试
    all_results = []

    for config in test_configs:
        agent_name = config["name"]
        adapter = config["adapter"]
        tasks = config["tasks"]

        print(f"\n{'='*50}")
        print(f"测试 {agent_name}")
        print(f"{'='*50}")

        tester = UniversalAgentTester(adapter, store)

        for i, task in enumerate(tasks, 1):
            try:
                result = tester.test(task, agent_name=f"{agent_name}_task_{i}")
                all_results.append({
                    "agent": agent_name,
                    "task_id": i,
                    "passed": result["passed"],
                    "total": result["total"]
                })

                print(f"  任务 {i}: ✅ {result['passed']}/{result['total']}")

            except Exception as e:
                print(f"  任务 {i}: ❌ 失败 - {e}")
                all_results.append({
                    "agent": agent_name,
                    "task_id": i,
                    "passed": 0,
                    "total": 0,
                    "error": str(e)
                })

    # 生成报告
    print(f"\n{'='*50}")
    print("测试总结")
    print(f"{'='*50}")

    total_passed = sum(r["passed"] for r in all_results)
    total_tests = sum(r["total"] for r in all_results)

    print(f"总计: {total_passed}/{total_tests} 通过")
    print(f"通过率: {total_passed/total_tests*100:.1f}%")

    # 按 Agent 分组统计
    from collections import defaultdict
    by_agent = defaultdict(lambda: {"passed": 0, "total": 0})

    for r in all_results:
        agent = r["agent"]
        by_agent[agent]["passed"] += r["passed"]
        by_agent[agent]["total"] += r["total"]

    print(f"\n按 Agent 统计:")
    for agent, stats in by_agent.items():
        rate = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
        print(f"  {agent}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")

if __name__ == "__main__":
    batch_test_agents()
```

---

## 最佳实践

### 1. 选择合适的集成方式

| 方式 | 优点 | 缺点 | 推荐场景 |
|------|------|------|----------|
| **HTTP/REST** | 标准化、易用 | 需要网络 | 微服务、Web Agent |
| **CLI** | 简单、直接 | 进程开销 | 命令行工具 |
| **AgentBay** | 隔离、强大 | 需要云服务 | 复杂环境、多语言 |
| **STDIN/STDOUT** | 低延迟 | 复杂性 | 流式处理 |
| **gRPC** | 高性能 | 配置复杂 | 性能要求高 |

### 2. 错误处理

```python
def robust_agent_test(adapter, task, max_retries=3):
    """健壮的 Agent 测试"""

    for attempt in range(max_retries):
        try:
            result = adapter.invoke(task["prompt"])
            return result
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            print(f"重试 {attempt + 1}/{max_retries}: {e}")
            time.sleep(2 ** attempt)  # 指数退避
```

### 3. 超时控制

```python
import signal
from contextlib import contextmanager

@contextmanager
def timeout(seconds):
    """超时上下文管理器"""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"操作超时 ({seconds}秒)")

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

# 使用
with timeout(30):
    result = adapter.invoke(prompt)
```

### 4. 日志和追踪

```python
def test_with_detailed_logging(adapter, task):
    """详细日志记录"""

    store = TraceStore()
    trace_id = store.start_trace(agent_name="detailed_test")

    # 记录环境信息
    store.write_event({
        "type": "environment",
        "python_version": sys.version,
        "platform": platform.platform()
    })

    # 记录 Agent 元数据
    store.write_event({
        "type": "agent_info",
        "adapter_type": type(adapter).__name__,
        "task": task
    })

    # 执行并记录
    start_time = time.time()
    result = adapter.invoke(task["prompt"])
    duration = time.time() - start_time

    store.write_event({
        "type": "performance",
        "duration_seconds": duration
    })

    store.end_trace(trace_id)

    return result
```

---

## 常见问题 (FAQ)

### Q1: 如何测试需要认证的 Agent？

```python
class AuthenticatedHTTPAdapter(HTTPAgentAdapter):
    def __init__(self, base_url, api_key):
        super().__init__(base_url)
        self.api_key = api_key

    def invoke(self, prompt):
        import requests
        response = requests.post(
            f"{self.base_url}/api/agent",
            json={"prompt": prompt},
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return response.json()["output"]
```

### Q2: 如何测试有状态的 Agent？

```python
class StatefulCLIAdapter(CLIAgentAdapter):
    def __init__(self, command):
        super().__init__(command)
        self.process = subprocess.Popen(
            [command],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True
        )

    def invoke(self, prompt):
        self.process.stdin.write(prompt + "\n")
        self.process.stdin.flush()
        return self.process.stdout.readline().strip()

    def cleanup(self):
        self.process.terminate()
```

### Q3: 如何测试异步 Agent？

```python
import asyncio

class AsyncHTTPAdapter(AgentAdapter):
    async def invoke_async(self, prompt):
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/agent",
                json={"prompt": prompt}
            ) as response:
                data = await response.json()
                return data["output"]

    def invoke(self, prompt):
        return asyncio.run(self.invoke_async(prompt))
```

---

## 总结

TigerHill 可以测试**任何语言**编写的 Agent，关键是选择合适的集成方式：

1. **HTTP/REST API** - 最通用、最推荐
2. **CLI** - 最简单、适合工具类 Agent
3. **AgentBay** - 最强大、适合复杂场景
4. **STDIN/STDOUT** - 适合流式交互
5. **gRPC** - 适合高性能需求

通过 `UniversalAgentTester` 框架，可以用统一的方式测试所有类型的 Agent。

---

## 下一步

- 查看 `USER_GUIDE.md` 了解完整功能
- 查看 `examples/` 目录获取更多示例
- 查看 `AGENTBAY_TESTING_GUIDE.md` 了解 AgentBay 使用

**开始测试你的多语言 Agent 吧！** 🚀

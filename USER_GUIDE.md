# 🐯 TigerHill（虎丘）使用手册

**AI Agent 测试、评估和调试完全指南**

---

## 📚 目录

1. [快速开始](#快速开始)
2. [核心概念](#核心概念)
3. [基础工作流](#基础工作流)
4. [测试 Agent](#测试-agent)
5. [评估 Agent](#评估-agent)
6. [调试 Agent](#调试-agent)
7. [使用 AgentBay](#使用-agentbay)
8. [高级功能](#高级功能)
9. [最佳实践](#最佳实践)
10. [故障排查](#故障排查)

---

## 快速开始

### 安装

```bash
# 克隆项目
cd /path/to/TigerHill

# 安装依赖
pip install -e ".[dev]"

# 安装 AgentBay SDK（可选）
pip install wuying-agentbay-sdk

# 设置 API Key（如果使用 AgentBay）
export AGENTBAY_API_KEY=your_api_key_here
```

### 5 分钟快速体验

```python
from tigerhill.storage.trace_store import TraceStore
from tigerhill.core.models import Task
from tigerhill.eval.assertions import run_assertions

# 1. 创建追踪存储
store = TraceStore(storage_path="./my_traces")

# 2. 定义测试任务
task = Task(
    prompt="计算 6 + 7 的结果",
    assertions=[
        {"type": "contains", "expected": "13"},
        {"type": "regex", "pattern": r"\d+"}
    ]
)

# 3. 开始追踪
trace_id = store.start_trace(agent_name="calculator_agent", task_id="test_001")

# 4. 运行你的 Agent（这里用模拟输出）
agent_output = "计算结果是 13"

# 5. 记录执行过程
store.write_event({"type": "prompt", "content": task.prompt})
store.write_event({"type": "model_response", "text": agent_output})

# 6. 结束追踪
store.end_trace(trace_id)

# 7. 评估结果
results = run_assertions(agent_output, task.assertions)

# 8. 查看结果
print(f"通过: {sum(1 for r in results if r['ok'])}/{len(results)}")
print(f"追踪已保存到: {store.storage_path}")
```

---

## 核心概念

### 1. Task（任务）

任务定义了要测试的内容和期望的结果。

```python
from tigerhill.core.models import Task

task = Task(
    prompt="用户的输入提示词",
    setup=["setup_step_1", "setup_step_2"],  # 可选的准备步骤
    assertions=[                              # 断言列表
        {"type": "contains", "expected": "期望的内容"}
    ]
)
```

**字段说明**:
- `prompt`: Agent 需要处理的输入
- `setup`: 测试前的准备步骤（可选）
- `assertions`: 用于验证输出的断言列表

---

### 2. Environment（环境）

环境定义了 Agent 运行的上下文。

```python
from tigerhill.core.models import Environment

env = Environment(
    name="测试环境",
    agentbay_env_id="codespace",        # AgentBay 环境类型
    agentbay_tool_set_id="command"      # AgentBay 工具集
)
```

**AgentBay 环境类型**:
- `codespace`: 代码执行环境
- `browser`: 浏览器环境
- `computer`: 桌面环境
- `mobile`: 移动环境

---

### 3. TraceStore（追踪存储）

TraceStore 记录 Agent 执行的所有细节。

```python
from tigerhill.storage.trace_store import TraceStore

store = TraceStore(
    storage_path="./traces",  # 存储路径
    auto_save=True            # 自动保存
)
```

**追踪生命周期**:
```
开始追踪 → 记录事件 → 结束追踪 → 查询分析
```

---

### 4. Assertions（断言）

断言用于验证 Agent 的输出是否符合预期。

**支持的断言类型**:

| 类型 | 说明 | 示例 |
|------|------|------|
| `contains` | 包含检查 | `{"type": "contains", "expected": "13"}` |
| `equals` | 精确匹配 | `{"type": "equals", "expected": "result: 13"}` |
| `regex` | 正则匹配 | `{"type": "regex", "pattern": r"\d+"}` |
| `starts_with` | 前缀匹配 | `{"type": "starts_with", "expected": "结果是"}` |
| `ends_with` | 后缀匹配 | `{"type": "ends_with", "expected": "完成"}` |
| `negate` | 否定断言 | `{"type": "contains", "expected": "错误", "negate": true}` |

---

## 基础工作流

### 完整的测试流程

```python
from tigerhill.storage.trace_store import TraceStore
from tigerhill.core.models import Task, Environment
from tigerhill.eval.assertions import run_assertions

# ============================================
# 第 1 步：准备工作
# ============================================

# 创建追踪存储
store = TraceStore(storage_path="./agent_traces")

# 定义测试任务
task = Task(
    prompt="写一个函数计算两个数的和",
    assertions=[
        {"type": "contains", "expected": "def"},
        {"type": "contains", "expected": "return"},
        {"type": "regex", "pattern": r"def\s+\w+\s*\("}
    ]
)

# ============================================
# 第 2 步：开始追踪
# ============================================

trace_id = store.start_trace(
    agent_name="code_generator",
    task_id="function_test_001",
    metadata={
        "version": "1.0",
        "model": "gpt-4",
        "temperature": 0.7
    }
)

print(f"开始追踪: {trace_id}")

# ============================================
# 第 3 步：执行 Agent
# ============================================

# 记录输入
store.write_event({
    "type": "prompt",
    "messages": [
        {"role": "system", "content": "你是一个编程助手"},
        {"role": "user", "content": task.prompt}
    ]
})

# 这里调用你的 Agent
# agent_output = your_agent.run(task.prompt)
# 示例输出
agent_output = """
def add(a, b):
    return a + b
"""

# 记录输出
store.write_event({
    "type": "model_response",
    "text": agent_output,
    "tool_calls": []
})

# ============================================
# 第 4 步：结束追踪
# ============================================

store.end_trace(trace_id)

# ============================================
# 第 5 步：评估结果
# ============================================

results = run_assertions(agent_output, task.assertions)

# 打印评估结果
print("\n评估结果:")
for i, result in enumerate(results, 1):
    status = "✅ 通过" if result["ok"] else "❌ 失败"
    print(f"{i}. {status} - {result['type']}")
    if not result["ok"]:
        print(f"   原因: {result['message']}")

# ============================================
# 第 6 步：查看追踪摘要
# ============================================

summary = store.get_summary(trace_id)
print(f"\n追踪摘要:")
print(f"- Agent: {summary['agent_name']}")
print(f"- 耗时: {summary['duration_seconds']:.2f} 秒")
print(f"- 事件数: {summary['total_events']}")
print(f"- 事件统计: {summary['event_counts']}")

# ============================================
# 第 7 步：导出追踪（可选）
# ============================================

store.export_trace(trace_id, f"./reports/trace_{trace_id}.json")
print(f"\n追踪已导出")
```

---

## 测试 Agent

### 1. 单次测试

测试 Agent 对单个输入的响应。

```python
from tigerhill.storage.trace_store import TraceStore
from tigerhill.core.models import Task
from tigerhill.eval.assertions import run_assertions

def test_single_input():
    """测试单个输入"""

    # 创建存储
    store = TraceStore()

    # 定义任务
    task = Task(
        prompt="什么是 Python？",
        assertions=[
            {"type": "contains", "expected": "编程语言"},
            {"type": "contains", "expected": "Python"}
        ]
    )

    # 追踪和执行
    trace_id = store.start_trace(agent_name="qa_agent", task_id="single_test")

    # 调用你的 Agent
    output = your_agent.query(task.prompt)

    # 记录
    store.write_event({"type": "prompt", "content": task.prompt})
    store.write_event({"type": "model_response", "text": output})
    store.end_trace(trace_id)

    # 评估
    results = run_assertions(output, task.assertions)

    # 返回结果
    return {
        "trace_id": trace_id,
        "passed": all(r["ok"] for r in results),
        "results": results
    }

# 运行测试
result = test_single_input()
print(f"测试通过: {result['passed']}")
```

---

### 2. 批量测试

测试 Agent 对多个输入的响应。

```python
from tigerhill.storage.trace_store import TraceStore
from tigerhill.core.models import Task
from tigerhill.eval.assertions import run_assertions

def test_batch_inputs():
    """批量测试多个输入"""

    store = TraceStore(storage_path="./batch_tests")

    # 定义测试用例
    test_cases = [
        {
            "prompt": "2 + 2 = ?",
            "assertions": [{"type": "contains", "expected": "4"}]
        },
        {
            "prompt": "10 - 3 = ?",
            "assertions": [{"type": "contains", "expected": "7"}]
        },
        {
            "prompt": "5 × 6 = ?",
            "assertions": [{"type": "contains", "expected": "30"}]
        }
    ]

    results = []

    for i, test_case in enumerate(test_cases):
        print(f"\n测试用例 {i+1}/{len(test_cases)}")

        # 创建任务
        task = Task(
            prompt=test_case["prompt"],
            assertions=test_case["assertions"]
        )

        # 追踪
        trace_id = store.start_trace(
            agent_name="math_agent",
            task_id=f"batch_test_{i+1}"
        )

        # 执行
        output = your_agent.query(task.prompt)

        # 记录
        store.write_event({"type": "prompt", "content": task.prompt})
        store.write_event({"type": "model_response", "text": output})
        store.end_trace(trace_id)

        # 评估
        assertion_results = run_assertions(output, task.assertions)
        passed = all(r["ok"] for r in assertion_results)

        results.append({
            "test_case": i+1,
            "prompt": task.prompt,
            "output": output,
            "passed": passed,
            "trace_id": trace_id
        })

        print(f"  {'✅ 通过' if passed else '❌ 失败'}")

    # 统计
    total = len(results)
    passed = sum(1 for r in results if r["passed"])

    print(f"\n批量测试完成:")
    print(f"  总数: {total}")
    print(f"  通过: {passed}")
    print(f"  失败: {total - passed}")
    print(f"  通过率: {passed/total*100:.1f}%")

    return results

# 运行批量测试
batch_results = test_batch_inputs()
```

---

### 3. 回归测试

确保 Agent 的改进不会破坏已有功能。

```python
import json
from pathlib import Path
from tigerhill.storage.trace_store import TraceStore
from tigerhill.core.models import Task
from tigerhill.eval.assertions import run_assertions

def create_test_suite(name: str, test_cases: list):
    """创建测试套件"""
    suite_path = Path(f"./test_suites/{name}.json")
    suite_path.parent.mkdir(parents=True, exist_ok=True)

    with open(suite_path, 'w', encoding='utf-8') as f:
        json.dump(test_cases, f, indent=2, ensure_ascii=False)

    print(f"测试套件已创建: {suite_path}")

def run_regression_tests(suite_name: str, agent_version: str):
    """运行回归测试"""

    # 加载测试套件
    suite_path = Path(f"./test_suites/{suite_name}.json")
    with open(suite_path, 'r', encoding='utf-8') as f:
        test_cases = json.load(f)

    store = TraceStore(storage_path=f"./regression/{agent_version}")

    print(f"\n开始回归测试: {suite_name}")
    print(f"Agent 版本: {agent_version}")
    print(f"测试用例数: {len(test_cases)}\n")

    results = []

    for i, test_case in enumerate(test_cases):
        task = Task(
            prompt=test_case["prompt"],
            assertions=test_case["assertions"]
        )

        trace_id = store.start_trace(
            agent_name=f"agent_{agent_version}",
            task_id=test_case.get("id", f"test_{i+1}"),
            metadata={"suite": suite_name, "version": agent_version}
        )

        # 执行 Agent
        output = your_agent.query(task.prompt)

        # 记录
        store.write_event({"type": "prompt", "content": task.prompt})
        store.write_event({"type": "model_response", "text": output})
        store.end_trace(trace_id)

        # 评估
        assertion_results = run_assertions(output, task.assertions)
        passed = all(r["ok"] for r in assertion_results)

        results.append({
            "test_id": test_case.get("id"),
            "passed": passed,
            "trace_id": trace_id
        })

        status = "✅" if passed else "❌"
        print(f"{status} 测试 {i+1}: {test_case.get('id', 'unnamed')}")

    # 保存结果
    report_path = Path(f"./regression/{agent_version}/report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            "suite": suite_name,
            "version": agent_version,
            "total": len(results),
            "passed": sum(1 for r in results if r["passed"]),
            "results": results
        }, f, indent=2)

    print(f"\n回归测试报告: {report_path}")

    return results

# 使用示例
# 1. 创建测试套件
test_cases = [
    {
        "id": "math_add",
        "prompt": "计算 5 + 3",
        "assertions": [{"type": "contains", "expected": "8"}]
    },
    {
        "id": "math_multiply",
        "prompt": "计算 4 × 7",
        "assertions": [{"type": "contains", "expected": "28"}]
    }
]

create_test_suite("math_suite", test_cases)

# 2. 运行回归测试
run_regression_tests("math_suite", "v1.0")
run_regression_tests("math_suite", "v1.1")  # 新版本测试
```

### 6. 测试非 Python Agent（跨语言测试）

TigerHill 可以测试**任何编程语言**编写的 Agent。通过适配器模式，支持：
- **HTTP/REST API** Agent（Node.js、Go、Java 等）
- **命令行 CLI** Agent（Go、Rust、C++ 等）
- **标准输入输出** Agent（Java、C# 等）
- **AgentBay 云环境** Agent（任何语言）

#### 测试 HTTP Agent（Node.js 示例）

```python
from tigerhill.adapters import HTTPAgentAdapter, UniversalAgentTester
from tigerhill.storage.trace_store import TraceStore

def test_nodejs_agent():
    """测试 Node.js HTTP Agent"""

    # 1. 创建 HTTP 适配器
    adapter = HTTPAgentAdapter(
        base_url="http://localhost:3000",
        endpoint="/api/agent",
        timeout=30
    )

    # 2. 创建测试器
    store = TraceStore(storage_path="./traces/nodejs_agent")
    tester = UniversalAgentTester(adapter, store)

    # 3. 执行测试
    result = tester.test(
        task={
            "prompt": "计算 6 + 7",
            "assertions": [
                {"type": "contains", "expected": "13"}
            ]
        },
        agent_name="nodejs_calculator"
    )

    # 4. 查看结果
    print(f"✅ 通过: {result['passed']}/{result['total']}")
    print(f"追踪 ID: {result['trace_id']}")

    return result

# 运行测试
test_nodejs_agent()
```

#### 测试 CLI Agent（Go 示例）

```python
from tigerhill.adapters import CLIAgentAdapter, UniversalAgentTester
from tigerhill.storage.trace_store import TraceStore

def test_go_agent():
    """测试 Go 命令行 Agent"""

    # 1. 创建 CLI 适配器
    adapter = CLIAgentAdapter(
        command="./go_agent",       # Go 编译后的可执行文件
        args_template=["{prompt}"], # 参数模板
        timeout=10
    )

    # 2. 创建测试器
    store = TraceStore(storage_path="./traces/go_agent")
    tester = UniversalAgentTester(adapter, store)

    # 3. 执行测试
    result = tester.test(
        task={
            "prompt": "列出文件",
            "assertions": [
                {"type": "contains", "expected": "文件"}
            ]
        },
        agent_name="go_cli_agent"
    )

    print(f"✅ 通过: {result['passed']}/{result['total']}")

    return result

# 运行测试
test_go_agent()
```

#### 批量测试多语言 Agent

```python
from tigerhill.adapters import (
    HTTPAgentAdapter,
    CLIAgentAdapter,
    UniversalAgentTester
)
from tigerhill.storage.trace_store import TraceStore

def batch_test_multilang():
    """批量测试多语言 Agent"""

    store = TraceStore(storage_path="./traces/multilang")

    # 测试配置
    test_configs = [
        {
            "name": "nodejs_agent",
            "adapter": HTTPAgentAdapter("http://localhost:3000"),
            "task": {
                "prompt": "计算 10 + 20",
                "assertions": [{"type": "contains", "expected": "30"}]
            }
        },
        {
            "name": "go_agent",
            "adapter": CLIAgentAdapter("./go_agent", ["{prompt}"]),
            "task": {
                "prompt": "列出文件",
                "assertions": [{"type": "contains", "expected": "文件"}]
            }
        }
    ]

    # 执行所有测试
    all_results = []
    for config in test_configs:
        tester = UniversalAgentTester(config["adapter"], store)
        result = tester.test(
            task=config["task"],
            agent_name=config["name"]
        )
        all_results.append(result)

        print(f"\n{config['name']}: {result['passed']}/{result['total']} 通过")

    # 生成汇总报告
    report = tester.generate_report(all_results)
    print(f"\n总体成功率: {report['success_rate']:.1f}%")

    return all_results

# 运行批量测试
batch_test_multilang()
```

#### 在 AgentBay 测试多语言 Agent

```python
from tigerhill.agentbay.client import AgentBayClient, EnvironmentType
from tigerhill.adapters import AgentBayAdapter, UniversalAgentTester
from tigerhill.storage.trace_store import TraceStore

def test_multilang_in_agentbay():
    """在 AgentBay 云环境测试多语言 Agent"""

    store = TraceStore(storage_path="./traces/agentbay_multilang")

    with AgentBayClient() as client:
        # 创建云环境会话
        session = client.create_session(env_type=EnvironmentType.CODESPACE)
        session_id = session["session_id"]

        # 测试 Node.js Agent
        print("测试 Node.js Agent...")
        node_adapter = AgentBayAdapter(
            client=client,
            session_id=session_id,
            agent_command="node agent.js '{prompt}'",
            setup_commands=[
                "apt-get update && apt-get install -y nodejs npm",
                "echo 'console.log(process.argv[2])' > agent.js"
            ]
        )

        tester = UniversalAgentTester(node_adapter, store)
        result = tester.test(
            task={"prompt": "测试", "assertions": []},
            agent_name="nodejs_cloud_agent"
        )

        print(f"Node.js Agent: {'✅' if result['success'] else '❌'}")

        # 测试 Go Agent
        print("\n测试 Go Agent...")
        go_adapter = AgentBayAdapter(
            client=client,
            session_id=session_id,
            agent_command="./agent '{prompt}'",
            setup_commands=[
                "apt-get update && apt-get install -y golang",
                "echo 'package main\nimport \"fmt\"\nimport \"os\"\nfunc main() { fmt.Println(os.Args[1]) }' > agent.go",
                "go build -o agent agent.go"
            ]
        )

        tester = UniversalAgentTester(go_adapter, store)
        result = tester.test(
            task={"prompt": "测试", "assertions": []},
            agent_name="go_cloud_agent"
        )

        print(f"Go Agent: {'✅' if result['success'] else '❌'}")

        # 会话自动清理

# 运行测试
test_multilang_in_agentbay()
```

**完整文档**: 详见 [CROSS_LANGUAGE_TESTING.md](CROSS_LANGUAGE_TESTING.md)

**示例代码**: 查看 `examples/cross_language/` 目录：
- `test_nodejs_agent.py` - Node.js Agent 测试
- `test_go_agent.py` - Go Agent 测试
- `batch_test_multilang.py` - 批量多语言测试

---

## 评估 Agent

### 1. 基础评估

使用断言评估 Agent 输出的质量。

```python
from tigerhill.eval.assertions import run_assertions

def evaluate_agent_output(output: str, expected_criteria: dict):
    """评估 Agent 输出"""

    # 定义断言
    assertions = []

    # 内容检查
    if "required_keywords" in expected_criteria:
        for keyword in expected_criteria["required_keywords"]:
            assertions.append({
                "type": "contains",
                "expected": keyword
            })

    # 格式检查
    if "format_pattern" in expected_criteria:
        assertions.append({
            "type": "regex",
            "pattern": expected_criteria["format_pattern"]
        })

    # 禁止内容
    if "forbidden_keywords" in expected_criteria:
        for keyword in expected_criteria["forbidden_keywords"]:
            assertions.append({
                "type": "contains",
                "expected": keyword,
                "negate": True  # 否定断言
            })

    # 运行断言
    results = run_assertions(output, assertions)

    # 计算分数
    total = len(results)
    passed = sum(1 for r in results if r["ok"])
    score = (passed / total * 100) if total > 0 else 0

    return {
        "score": score,
        "passed": passed,
        "total": total,
        "details": results
    }

# 使用示例
output = """
def calculate_sum(a, b):
    \"\"\"计算两个数的和\"\"\"
    return a + b
"""

criteria = {
    "required_keywords": ["def", "return"],
    "format_pattern": r"def\s+\w+\s*\(",
    "forbidden_keywords": ["print", "input"]
}

evaluation = evaluate_agent_output(output, criteria)
print(f"评估分数: {evaluation['score']:.1f}%")
```

---

### 2. 对比评估

对比不同版本或不同配置的 Agent。

```python
from tigerhill.storage.trace_store import TraceStore
from tigerhill.eval.assertions import run_assertions

def compare_agents(test_cases: list, agents: dict):
    """对比多个 Agent 的表现"""

    store = TraceStore(storage_path="./comparisons")

    comparison_results = {agent_name: [] for agent_name in agents.keys()}

    for i, test_case in enumerate(test_cases):
        print(f"\n测试用例 {i+1}: {test_case['prompt']}")

        for agent_name, agent_func in agents.items():
            # 追踪
            trace_id = store.start_trace(
                agent_name=agent_name,
                task_id=f"compare_test_{i+1}"
            )

            # 执行
            output = agent_func(test_case['prompt'])

            # 记录
            store.write_event({"type": "prompt", "content": test_case['prompt']})
            store.write_event({"type": "model_response", "text": output})
            store.end_trace(trace_id)

            # 评估
            results = run_assertions(output, test_case['assertions'])
            passed = all(r["ok"] for r in results)

            # 统计
            comparison_results[agent_name].append({
                "test_id": i+1,
                "passed": passed,
                "output_length": len(output),
                "trace_id": trace_id
            })

            print(f"  {agent_name}: {'✅ 通过' if passed else '❌ 失败'}")

    # 生成对比报告
    print("\n" + "="*60)
    print("对比结果:")
    print("="*60)

    for agent_name, results in comparison_results.items():
        total = len(results)
        passed = sum(1 for r in results if r["passed"])
        avg_length = sum(r["output_length"] for r in results) / total

        print(f"\n{agent_name}:")
        print(f"  通过率: {passed}/{total} ({passed/total*100:.1f}%)")
        print(f"  平均输出长度: {avg_length:.0f} 字符")

    return comparison_results

# 使用示例
test_cases = [
    {
        "prompt": "解释什么是递归",
        "assertions": [
            {"type": "contains", "expected": "函数"},
            {"type": "contains", "expected": "自己"}
        ]
    }
]

agents = {
    "agent_v1": lambda prompt: your_agent_v1.query(prompt),
    "agent_v2": lambda prompt: your_agent_v2.query(prompt),
    "agent_gpt4": lambda prompt: gpt4_agent.query(prompt)
}

comparison = compare_agents(test_cases, agents)
```

---

## 调试 Agent

### 1. 详细追踪

记录 Agent 执行的每一步。

```python
from tigerhill.storage.trace_store import TraceStore, EventType

def debug_agent_execution(prompt: str):
    """详细追踪 Agent 执行过程"""

    store = TraceStore(storage_path="./debug_traces")

    # 开始追踪
    trace_id = store.start_trace(
        agent_name="debug_agent",
        task_id="debug_session",
        metadata={"debug_mode": True}
    )

    print(f"开始调试追踪: {trace_id}\n")

    # 1. 记录输入
    print("1️⃣ 用户输入:")
    print(f"   {prompt}")
    store.write_event({
        "type": "prompt",
        "content": prompt
    })

    # 2. 记录系统提示词
    system_prompt = "你是一个有帮助的助手"
    print(f"\n2️⃣ 系统提示词:")
    print(f"   {system_prompt}")
    store.write_event({
        "type": "custom",
        "event": "system_prompt",
        "content": system_prompt
    })

    # 3. 调用 LLM
    print(f"\n3️⃣ 调用 LLM...")
    # llm_response = your_llm.generate(prompt)
    llm_response = "这是 LLM 的响应"

    store.write_event({
        "type": "model_response",
        "text": llm_response,
        "metadata": {
            "model": "gpt-4",
            "temperature": 0.7,
            "tokens": 150
        }
    })
    print(f"   响应: {llm_response}")

    # 4. 工具调用（如果有）
    tool_calls = []  # 假设 LLM 建议使用工具
    if tool_calls:
        print(f"\n4️⃣ 工具调用:")
        for i, tool_call in enumerate(tool_calls):
            print(f"   {i+1}. {tool_call['name']}({tool_call['args']})")

            # 执行工具
            result = execute_tool(tool_call['name'], tool_call['args'])

            store.write_event({
                "type": "tool_call",
                "tool": tool_call['name'],
                "args": tool_call['args']
            })

            store.write_event({
                "type": "tool_result",
                "tool": tool_call['name'],
                "result": result
            })

            print(f"      结果: {result}")

    # 5. 最终输出
    final_output = llm_response  # 或者是工具调用后的结果
    print(f"\n5️⃣ 最终输出:")
    print(f"   {final_output}")

    # 结束追踪
    store.end_trace(trace_id)

    # 6. 分析追踪
    print(f"\n" + "="*60)
    print("追踪分析:")
    print("="*60)

    summary = store.get_summary(trace_id)
    print(f"总事件数: {summary['total_events']}")
    print(f"执行耗时: {summary['duration_seconds']:.2f} 秒")
    print(f"事件分布:")
    for event_type, count in summary['event_counts'].items():
        print(f"  - {event_type}: {count}")

    # 导出详细追踪
    export_path = f"./debug_traces/debug_{trace_id}.json"
    store.export_trace(trace_id, export_path)
    print(f"\n详细追踪已导出: {export_path}")

    return trace_id

# 使用
trace_id = debug_agent_execution("写一个冒泡排序算法")
```

---

### 2. 性能分析

分析 Agent 的性能瓶颈。

```python
import time
from tigerhill.storage.trace_store import TraceStore

def profile_agent_performance(prompt: str, iterations: int = 10):
    """性能分析"""

    store = TraceStore(storage_path="./performance")

    print(f"开始性能分析（{iterations} 次迭代）\n")

    timings = {
        "llm_call": [],
        "tool_execution": [],
        "total": []
    }

    for i in range(iterations):
        print(f"迭代 {i+1}/{iterations}...")

        trace_id = store.start_trace(
            agent_name="perf_agent",
            task_id=f"perf_test_{i+1}"
        )

        start_time = time.time()

        # LLM 调用计时
        llm_start = time.time()
        # llm_response = your_llm.generate(prompt)
        time.sleep(0.5)  # 模拟 LLM 调用
        llm_end = time.time()
        llm_time = llm_end - llm_start
        timings["llm_call"].append(llm_time)

        store.write_event({
            "type": "model_response",
            "text": "response",
            "metadata": {"latency_ms": llm_time * 1000}
        })

        # 工具执行计时
        tool_start = time.time()
        # tool_result = execute_tool(...)
        time.sleep(0.1)  # 模拟工具执行
        tool_end = time.time()
        tool_time = tool_end - tool_start
        timings["tool_execution"].append(tool_time)

        store.write_event({
            "type": "tool_result",
            "tool": "example_tool",
            "result": "result",
            "metadata": {"latency_ms": tool_time * 1000}
        })

        end_time = time.time()
        total_time = end_time - start_time
        timings["total"].append(total_time)

        store.end_trace(trace_id)

    # 分析结果
    print(f"\n" + "="*60)
    print("性能分析结果:")
    print("="*60)

    for component, times in timings.items():
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        print(f"\n{component}:")
        print(f"  平均: {avg_time*1000:.2f} ms")
        print(f"  最小: {min_time*1000:.2f} ms")
        print(f"  最大: {max_time*1000:.2f} ms")

    # 瓶颈识别
    avg_llm = sum(timings["llm_call"]) / len(timings["llm_call"])
    avg_tool = sum(timings["tool_execution"]) / len(timings["tool_execution"])
    avg_total = sum(timings["total"]) / len(timings["total"])

    llm_percent = (avg_llm / avg_total) * 100
    tool_percent = (avg_tool / avg_total) * 100

    print(f"\n时间分布:")
    print(f"  LLM 调用: {llm_percent:.1f}%")
    print(f"  工具执行: {tool_percent:.1f}%")
    print(f"  其他: {100 - llm_percent - tool_percent:.1f}%")

    if llm_percent > 70:
        print(f"\n⚠️ 瓶颈: LLM 调用占用了大部分时间")
        print(f"   建议: 考虑使用更快的模型或缓存策略")
    elif tool_percent > 70:
        print(f"\n⚠️ 瓶颈: 工具执行占用了大部分时间")
        print(f"   建议: 优化工具实现或使用异步执行")

# 使用
profile_agent_performance("测试提示词", iterations=10)
```

---

### 3. 错误追踪

记录和分析 Agent 的错误。

```python
from tigerhill.storage.trace_store import TraceStore
import traceback

def trace_agent_errors(prompt: str):
    """追踪 Agent 错误"""

    store = TraceStore(storage_path="./error_traces")

    trace_id = store.start_trace(
        agent_name="error_agent",
        task_id="error_test",
        metadata={"debug": True}
    )

    try:
        print("执行 Agent...")

        # 记录输入
        store.write_event({
            "type": "prompt",
            "content": prompt
        })

        # 执行 Agent（可能出错）
        # result = your_agent.run(prompt)

        # 模拟错误
        raise ValueError("示例错误：输入格式不正确")

    except Exception as e:
        # 记录错误
        error_info = {
            "type": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc()
        }

        store.write_event(error_info)

        print(f"❌ 错误: {e}")
        print(f"\n详细追踪:")
        print(traceback.format_exc())

        # 保存错误上下文
        store.write_event({
            "type": "custom",
            "event": "error_context",
            "prompt": prompt,
            "metadata": {
                "error_occurred": True
            }
        })

    finally:
        store.end_trace(trace_id)

        # 导出错误追踪
        error_trace_path = f"./error_traces/error_{trace_id}.json"
        store.export_trace(trace_id, error_trace_path)
        print(f"\n错误追踪已保存: {error_trace_path}")

    return trace_id

# 使用
trace_agent_errors("导致错误的输入")
```

---

## 使用 AgentBay

### 1. 基础使用

在 AgentBay 云端环境中测试 Agent。

```python
from tigerhill.agentbay.client import AgentBayClient, EnvironmentType
from tigerhill.storage.trace_store import TraceStore

def test_agent_with_agentbay(prompt: str):
    """使用 AgentBay 测试 Agent"""

    store = TraceStore(storage_path="./agentbay_tests")

    # 创建 AgentBay 客户端
    with AgentBayClient() as client:
        print("✅ AgentBay 客户端已连接")

        # 创建追踪
        trace_id = store.start_trace(
            agent_name="agentbay_agent",
            task_id="agentbay_test",
            metadata={"platform": "agentbay"}
        )

        # 创建云端会话
        print("创建 AgentBay 会话...")
        session = client.create_session(env_type=EnvironmentType.CODESPACE)
        session_id = session["session_id"]
        print(f"✅ 会话已创建: {session_id}")

        # 记录会话创建
        store.write_event({
            "type": "custom",
            "event": "agentbay_session_created",
            "session_id": session_id,
            "env_type": "codespace"
        })

        try:
            # 执行命令
            print(f"\n执行命令...")
            result = client.execute_command(
                session_id,
                "python -c 'print(\"Hello from AgentBay!\")'"
            )

            print(f"✅ 命令输出: {result['output']}")

            # 记录执行
            store.write_event({
                "type": "tool_call",
                "tool": "execute_command",
                "args": {"command": "python -c '...'"}
            })

            store.write_event({
                "type": "tool_result",
                "tool": "execute_command",
                "result": result['output'],
                "exit_code": result['exit_code']
            })

        finally:
            # 清理会话
            client.delete_session(session_id)
            print(f"✅ 会话已清理")

            # 记录清理
            store.write_event({
                "type": "custom",
                "event": "agentbay_session_deleted",
                "session_id": session_id
            })

        # 结束追踪
        store.end_trace(trace_id)

        # 查看摘要
        summary = store.get_summary(trace_id)
        print(f"\n追踪摘要:")
        print(f"  总事件: {summary['total_events']}")
        print(f"  耗时: {summary['duration_seconds']:.2f} 秒")

        return trace_id

# 使用（需要设置 AGENTBAY_API_KEY）
trace_id = test_agent_with_agentbay("测试提示词")
```

---

### 2. 工具调用测试

测试 Agent 使用 AgentBay 工具的能力。

```python
from tigerhill.agentbay.client import AgentBayClient, EnvironmentType
from tigerhill.storage.trace_store import TraceStore

def test_tool_usage():
    """测试工具调用"""

    store = TraceStore()
    client = AgentBayClient()

    # 加载可用工具
    print("加载 AgentBay 工具...")
    tools = client.load_tools("command")
    print(f"✅ 已加载 {len(tools)} 个工具")
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description']}")

    # 创建会话
    session = client.create_session(env_type=EnvironmentType.CODESPACE)
    session_id = session["session_id"]

    # 开始追踪
    trace_id = store.start_trace(agent_name="tool_test_agent")

    try:
        # 测试多个工具调用
        test_commands = [
            "echo 'Test 1'",
            "python -c 'print(2 + 2)'",
            "ls /tmp"
        ]

        for i, cmd in enumerate(test_commands):
            print(f"\n测试 {i+1}: {cmd}")

            # 记录工具调用
            store.write_event({
                "type": "tool_call",
                "tool": "execute_command",
                "args": {"command": cmd},
                "index": i
            })

            # 执行
            result = client.execute_command(session_id, cmd)

            # 记录结果
            store.write_event({
                "type": "tool_result",
                "tool": "execute_command",
                "result": result['output'],
                "exit_code": result['exit_code'],
                "index": i
            })

            print(f"  输出: {result['output']}")
            print(f"  退出码: {result['exit_code']}")

    finally:
        client.delete_session(session_id)
        store.end_trace(trace_id)

    print(f"\n✅ 工具测试完成")
    return trace_id

# 使用
test_tool_usage()
```

---

## 高级功能

### 1. 自定义评估器

创建自己的评估逻辑。

```python
from tigerhill.eval.assertions import AssertionResult
from typing import List, Dict, Any

class CustomEvaluator:
    """自定义评估器"""

    def __init__(self, name: str):
        self.name = name

    def evaluate_length(self, output: str, min_length: int, max_length: int) -> AssertionResult:
        """评估输出长度"""
        length = len(output)
        ok = min_length <= length <= max_length

        return AssertionResult(
            type="length_check",
            ok=ok,
            expected=f"{min_length}-{max_length}",
            actual=length,
            message="" if ok else f"长度 {length} 不在范围内"
        )

    def evaluate_sentiment(self, output: str, expected_sentiment: str) -> AssertionResult:
        """评估情感倾向"""
        # 这里使用简单的关键词匹配，实际应用可以使用 NLP 模型
        positive_keywords = ["好", "棒", "优秀", "完美"]
        negative_keywords = ["差", "糟", "失败", "错误"]

        positive_count = sum(1 for kw in positive_keywords if kw in output)
        negative_count = sum(1 for kw in negative_keywords if kw in output)

        if expected_sentiment == "positive":
            ok = positive_count > negative_count
        elif expected_sentiment == "negative":
            ok = negative_count > positive_count
        else:
            ok = positive_count == negative_count

        return AssertionResult(
            type="sentiment_check",
            ok=ok,
            expected=expected_sentiment,
            actual=f"pos:{positive_count}, neg:{negative_count}",
            message="" if ok else "情感倾向不匹配"
        )

    def evaluate_code_quality(self, code: str) -> AssertionResult:
        """评估代码质量"""
        issues = []

        # 检查文档字符串
        if '"""' not in code and "'''" not in code:
            issues.append("缺少文档字符串")

        # 检查类型注解
        if "->" not in code and ":" not in code:
            issues.append("缺少类型注解")

        # 检查命名规范
        if any(c.isupper() for c in code.split("def ")[1].split("(")[0] if "def " in code):
            issues.append("函数名应使用小写")

        ok = len(issues) == 0

        return AssertionResult(
            type="code_quality",
            ok=ok,
            expected="高质量代码",
            actual=f"{len(issues)} 个问题",
            message="; ".join(issues) if issues else ""
        )

    def run_all_evaluations(self, output: str, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """运行所有评估"""
        results = []

        # 长度检查
        if "length" in criteria:
            result = self.evaluate_length(
                output,
                criteria["length"]["min"],
                criteria["length"]["max"]
            )
            results.append(result.to_dict())

        # 情感检查
        if "sentiment" in criteria:
            result = self.evaluate_sentiment(
                output,
                criteria["sentiment"]
            )
            results.append(result.to_dict())

        # 代码质量检查
        if criteria.get("check_code_quality", False):
            result = self.evaluate_code_quality(output)
            results.append(result.to_dict())

        return results

# 使用示例
evaluator = CustomEvaluator("my_evaluator")

output = """
def calculate_sum(a, b):
    \"\"\"计算两个数的和\"\"\"
    return a + b
"""

criteria = {
    "length": {"min": 50, "max": 200},
    "sentiment": "positive",
    "check_code_quality": True
}

results = evaluator.run_all_evaluations(output, criteria)

for result in results:
    status = "✅" if result["ok"] else "❌"
    print(f"{status} {result['type']}: {result['message'] or 'OK'}")
```

---

### 2. 数据集管理

组织和管理测试数据集。

```python
import json
from pathlib import Path
from typing import List, Dict, Any

class DatasetManager:
    """数据集管理器"""

    def __init__(self, datasets_dir: str = "./datasets"):
        self.datasets_dir = Path(datasets_dir)
        self.datasets_dir.mkdir(parents=True, exist_ok=True)

    def create_dataset(self, name: str, data: List[Dict[str, Any]]):
        """创建数据集"""
        dataset_path = self.datasets_dir / f"{name}.json"

        with open(dataset_path, 'w', encoding='utf-8') as f:
            json.dump({
                "name": name,
                "version": "1.0",
                "count": len(data),
                "data": data
            }, f, indent=2, ensure_ascii=False)

        print(f"✅ 数据集已创建: {dataset_path}")
        print(f"   包含 {len(data)} 条数据")

    def load_dataset(self, name: str) -> Dict[str, Any]:
        """加载数据集"""
        dataset_path = self.datasets_dir / f"{name}.json"

        if not dataset_path.exists():
            raise FileNotFoundError(f"数据集不存在: {name}")

        with open(dataset_path, 'r', encoding='utf-8') as f:
            dataset = json.load(f)

        print(f"✅ 数据集已加载: {name}")
        print(f"   版本: {dataset['version']}")
        print(f"   数据量: {dataset['count']}")

        return dataset

    def list_datasets(self) -> List[str]:
        """列出所有数据集"""
        datasets = [f.stem for f in self.datasets_dir.glob("*.json")]
        return datasets

    def merge_datasets(self, dataset_names: List[str], output_name: str):
        """合并多个数据集"""
        merged_data = []

        for name in dataset_names:
            dataset = self.load_dataset(name)
            merged_data.extend(dataset['data'])

        self.create_dataset(output_name, merged_data)
        print(f"✅ 已合并 {len(dataset_names)} 个数据集")

    def split_dataset(self, name: str, train_ratio: float = 0.8):
        """分割数据集为训练集和测试集"""
        dataset = self.load_dataset(name)
        data = dataset['data']

        # 打乱数据
        import random
        random.shuffle(data)

        # 分割
        split_point = int(len(data) * train_ratio)
        train_data = data[:split_point]
        test_data = data[split_point:]

        # 保存
        self.create_dataset(f"{name}_train", train_data)
        self.create_dataset(f"{name}_test", test_data)

        print(f"✅ 数据集已分割:")
        print(f"   训练集: {len(train_data)} 条")
        print(f"   测试集: {len(test_data)} 条")

# 使用示例
manager = DatasetManager()

# 创建数据集
math_problems = [
    {
        "id": "math_001",
        "prompt": "计算 5 + 3",
        "expected_output": "8",
        "assertions": [{"type": "contains", "expected": "8"}],
        "difficulty": "easy"
    },
    {
        "id": "math_002",
        "prompt": "计算 12 × 7",
        "expected_output": "84",
        "assertions": [{"type": "contains", "expected": "84"}],
        "difficulty": "easy"
    },
    {
        "id": "math_003",
        "prompt": "求解方程 2x + 5 = 13",
        "expected_output": "x = 4",
        "assertions": [
            {"type": "contains", "expected": "4"},
            {"type": "contains", "expected": "x"}
        ],
        "difficulty": "medium"
    }
]

manager.create_dataset("math_problems", math_problems)

# 加载数据集
dataset = manager.load_dataset("math_problems")

# 分割数据集
manager.split_dataset("math_problems", train_ratio=0.7)

# 列出所有数据集
datasets = manager.list_datasets()
print(f"\n所有数据集: {datasets}")
```

---

## 最佳实践

### 1. 测试组织

```python
# tests/test_agent_math.py

from tigerhill.storage.trace_store import TraceStore
from tigerhill.core.models import Task
from tigerhill.eval.assertions import run_assertions

class TestMathAgent:
    """数学 Agent 测试套件"""

    def setup_method(self):
        """每个测试前的设置"""
        self.store = TraceStore(storage_path="./test_traces")
        self.agent = YourMathAgent()  # 你的 Agent 实现

    def teardown_method(self):
        """每个测试后的清理"""
        pass

    def test_addition(self):
        """测试加法"""
        task = Task(
            prompt="计算 5 + 3",
            assertions=[{"type": "contains", "expected": "8"}]
        )

        trace_id = self.store.start_trace(agent_name="math_agent", task_id="test_addition")
        output = self.agent.run(task.prompt)
        self.store.end_trace(trace_id)

        results = run_assertions(output, task.assertions)
        assert all(r["ok"] for r in results), "加法测试失败"

    def test_multiplication(self):
        """测试乘法"""
        task = Task(
            prompt="计算 4 × 7",
            assertions=[{"type": "contains", "expected": "28"}]
        )

        trace_id = self.store.start_trace(agent_name="math_agent", task_id="test_multiplication")
        output = self.agent.run(task.prompt)
        self.store.end_trace(trace_id)

        results = run_assertions(output, task.assertions)
        assert all(r["ok"] for r in results), "乘法测试失败"

    def test_equation_solving(self):
        """测试方程求解"""
        task = Task(
            prompt="求解 2x + 5 = 13",
            assertions=[
                {"type": "contains", "expected": "4"},
                {"type": "regex", "pattern": r"x\s*=\s*4"}
            ]
        )

        trace_id = self.store.start_trace(agent_name="math_agent", task_id="test_equation")
        output = self.agent.run(task.prompt)
        self.store.end_trace(trace_id)

        results = run_assertions(output, task.assertions)
        assert all(r["ok"] for r in results), "方程求解失败"
```

---

### 2. 配置管理

```python
# config.py

from dataclasses import dataclass
from typing import Optional

@dataclass
class TigerHillConfig:
    """TigerHill 配置"""

    # 追踪配置
    trace_storage_path: str = "./traces"
    auto_save_traces: bool = True

    # AgentBay 配置
    agentbay_api_key: Optional[str] = None
    agentbay_default_env: str = "codespace"

    # 评估配置
    enable_llm_judge: bool = False
    llm_judge_model: str = "gpt-4"

    # 调试配置
    debug_mode: bool = False
    verbose_logging: bool = True

    # 性能配置
    max_retries: int = 3
    timeout_seconds: int = 30

# 使用配置
config = TigerHillConfig(
    trace_storage_path="./my_traces",
    debug_mode=True
)
```

---

### 3. 日志记录

```python
import logging
from tigerhill.storage.trace_store import TraceStore

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tigerhill.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('tigerhill')

def test_with_logging():
    """带日志记录的测试"""
    logger.info("开始测试")

    store = TraceStore()
    trace_id = store.start_trace(agent_name="test_agent")

    try:
        logger.info("执行 Agent")
        # ... Agent 执行
        logger.info("Agent 执行成功")
    except Exception as e:
        logger.error(f"Agent 执行失败: {e}", exc_info=True)
        raise
    finally:
        store.end_trace(trace_id)
        logger.info(f"测试完成，追踪 ID: {trace_id}")
```

---

## 故障排查

### 常见问题

#### 1. AgentBay API Key 错误

**问题**: `NOT_LOGIN` 错误

**解决方案**:
```bash
# 1. 检查 API key 是否设置
echo $AGENTBAY_API_KEY

# 2. 确保 key 格式正确（应该以 akm- 开头）
export AGENTBAY_API_KEY=akm-your-key-here

# 3. 验证 key 是否有效
python -c "from tigerhill.agentbay.client import AgentBayClient; AgentBayClient()"
```

#### 2. 追踪文件找不到

**问题**: 无法加载追踪文件

**解决方案**:
```python
from tigerhill.storage.trace_store import TraceStore

# 检查存储路径
store = TraceStore(storage_path="./traces")
print(f"存储路径: {store.storage_path}")
print(f"路径存在: {store.storage_path.exists()}")

# 列出所有追踪
traces = store.get_all_traces()
print(f"追踪数量: {len(traces)}")
```

#### 3. 断言失败

**问题**: 断言总是失败

**解决方案**:
```python
from tigerhill.eval.assertions import run_assertions

output = "实际输出内容"
assertions = [{"type": "contains", "expected": "期望内容"}]

results = run_assertions(output, assertions)

# 详细查看失败原因
for result in results:
    if not result["ok"]:
        print(f"断言类型: {result['type']}")
        print(f"期望值: {result['expected']}")
        print(f"实际值: {result['actual']}")
        print(f"失败原因: {result['message']}")
```

---

## 附录

### A. 完整示例项目

```
my_agent_project/
├── agent/
│   └── my_agent.py          # 你的 Agent 实现
├── tests/
│   ├── test_basic.py        # 基础测试
│   ├── test_advanced.py     # 高级测试
│   └── test_integration.py  # 集成测试
├── datasets/
│   ├── train.json          # 训练数据集
│   └── test.json           # 测试数据集
├── traces/
│   └── (自动生成)          # 追踪文件
├── reports/
│   └── (自动生成)          # 测试报告
├── config.py               # 配置文件
└── run_tests.py            # 测试运行脚本
```

### B. 命令行工具

```bash
# 创建一个命令行脚本 (cli.py)
from tigerhill.storage.trace_store import TraceStore
from tigerhill.eval.assertions import run_assertions
import click

@click.group()
def cli():
    """TigerHill CLI 工具"""
    pass

@cli.command()
@click.argument('trace_id')
def show_trace(trace_id):
    """显示追踪详情"""
    store = TraceStore()
    trace = store.get_trace(trace_id)

    if trace:
        summary = store.get_summary(trace_id)
        click.echo(f"追踪 ID: {trace_id}")
        click.echo(f"Agent: {summary['agent_name']}")
        click.echo(f"耗时: {summary['duration_seconds']:.2f} 秒")
        click.echo(f"事件数: {summary['total_events']}")
    else:
        click.echo(f"追踪不存在: {trace_id}")

@cli.command()
def list_traces():
    """列出所有追踪"""
    store = TraceStore()
    traces = store.get_all_traces()

    click.echo(f"总追踪数: {len(traces)}")
    for trace in traces[:10]:  # 显示最近 10 个
        click.echo(f"- {trace.trace_id}: {trace.agent_name}")

if __name__ == '__main__':
    cli()
```

使用：
```bash
python cli.py list-traces
python cli.py show-trace <trace_id>
```

---

## 总结

TigerHill 提供了完整的 Agent 测试、评估和调试能力：

✅ **测试**: 单次、批量、回归测试
✅ **评估**: 断言、对比、自定义评估器
✅ **调试**: 详细追踪、性能分析、错误追踪
✅ **集成**: AgentBay 云端环境支持
✅ **管理**: 数据集管理、配置管理

**开始使用**:
1. 安装 TigerHill
2. 定义测试任务
3. 运行并追踪 Agent
4. 评估和分析结果
5. 持续优化

**获取帮助**:
- 文档: `REFACTORING_SUMMARY.md`
- 示例: `examples/basic_usage.py`
- 测试: `tests/test_integration.py`

**祝你的 Agent 开发顺利！** 🐯

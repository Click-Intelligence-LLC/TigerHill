# AgentBay 使用指南

## 🎯 什么是 AgentBay？

**AgentBay** 是阿里云提供的**云端Agent执行环境**平台，让你的Agent可以在**真实的浏览器、计算机、手机、代码空间**中执行任务。

### 简单类比

想象AgentBay是一个"云端操作系统租赁服务"：

```
你的Agent说: "帮我在浏览器打开百度并搜索Python"
     ↓
AgentBay提供: 一个真实的Chrome浏览器（在云端）
     ↓
你的Agent执行: 打开、搜索、截图等操作
     ↓
结果返回给你: 搜索结果、截图等
```

---

## 🆚 AgentBay vs 本地执行

### 本地执行的限制

```python
# 你的Agent在本地运行
agent.run("在浏览器中打开网页并截图")

# 问题：
❌ 需要本地安装浏览器
❌ 需要处理不同操作系统兼容性
❌ 资源受限于本地机器
❌ 难以并行测试
❌ 安全风险（Agent可能执行危险操作）
```

### 使用AgentBay的优势

```python
# Agent在云端AgentBay环境中运行
client = AgentBayClient()
session = client.create_session(env_type="browser")
result = client.execute_command(session_id, "打开网页...")

# 优势：
✅ 云端提供完整环境（浏览器、工具等）
✅ 跨平台一致性
✅ 按需扩容
✅ 可并行多个环境
✅ 安全隔离
```

---

## 🎪 核心使用场景

### 场景1: 测试浏览器自动化Agent 🌐

**问题**: 你开发了一个自动化Agent，需要测试它是否能正确操作浏览器

```python
from tigerhill.agentbay import AgentBayClient
from tigerhill.storage.trace_store import TraceStore

# 1. 初始化
client = AgentBayClient(api_key="your_key")
store = TraceStore()

# 2. 创建浏览器环境
session = client.create_session(env_type="browser")
session_id = session["session_id"]

# 3. 开始追踪
trace_id = store.start_trace("web_automation_agent")

# 4. 让Agent执行任务
commands = [
    "open https://www.google.com",
    "search for Python tutorials",
    "screenshot result.png"
]

for cmd in commands:
    result = client.execute_command(session_id, cmd)
    store.write_event({
        "type": "command_execution",
        "command": cmd,
        "output": result["output"]
    })

# 5. 验证结果
store.end_trace(trace_id)
client.delete_session(session_id)
```

**用途**:
- Web scraping Agent测试
- UI自动化测试
- 浏览器插件测试

---

### 场景2: 测试代码生成Agent 💻

**问题**: Agent生成了代码，需要在真实环境中执行验证

```python
client = AgentBayClient()
store = TraceStore()

# 创建代码空间环境
session = client.create_session(env_type="codespace")
session_id = session["session_id"]

trace_id = store.start_trace("code_gen_agent")

# Agent生成的代码
generated_code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

print(fibonacci(10))
"""

# 在云端代码空间执行
result = client.execute_command(
    session_id,
    f"python3 -c '{generated_code}'"
)

# 验证输出
assert "55" in result["output"], "Fibonacci计算错误"

store.write_event({
    "type": "code_execution",
    "code": generated_code,
    "output": result["output"],
    "validation": "passed"
})

store.end_trace(trace_id, status="success")
client.delete_session(session_id)
```

**用途**:
- 代码生成Agent验证
- 算法正确性测试
- 多语言代码执行

---

### 场景3: 移动应用测试Agent 📱

**问题**: 测试Agent是否能正确操作移动应用

```python
client = AgentBayClient()

# 创建移动设备环境
session = client.create_session(
    env_type="mobile",
    config={
        "device": "iPhone 15",
        "os": "iOS 17"
    }
)

session_id = session["session_id"]

# 执行移动应用操作
commands = [
    "launch app com.example.myapp",
    "tap button login",
    "input username test@example.com",
    "tap button submit"
]

for cmd in commands:
    result = client.execute_command(session_id, cmd)
    print(f"执行: {cmd}")
    print(f"结果: {result['output']}")

client.delete_session(session_id)
```

**用途**:
- 移动应用UI测试
- 手机游戏自动化
- App功能验证

---

### 场景4: 跨环境并行测试 🔄

**问题**: 需要同时在多个环境测试Agent的行为

```python
from tigerhill.agentbay import AgentBayClient
import concurrent.futures

client = AgentBayClient()

def test_in_environment(env_type):
    """在指定环境中测试Agent"""
    session = client.create_session(env_type=env_type)
    session_id = session["session_id"]

    # 执行相同的测试任务
    result = client.execute_command(
        session_id,
        "echo 'Hello from ' + env_type"
    )

    client.delete_session(session_id)
    return {
        "env": env_type,
        "result": result["output"]
    }

# 并行测试多个环境
environments = ["browser", "computer", "codespace"]

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(test_in_environment, env)
        for env in environments
    ]

    results = [f.result() for f in futures]

# 对比结果
for result in results:
    print(f"{result['env']}: {result['result']}")
```

**用途**:
- 跨平台兼容性测试
- 性能对比
- 环境差异分析

---

### 场景5: 集成到TigerHill完整测试流程 🧪

**问题**: 将AgentBay集成到完整的Agent评估流程

```python
from tigerhill.storage.trace_store import TraceStore
from tigerhill.agentbay import AgentBayClient
from tigerhill.core.models import Task
from tigerhill.eval.assertions import run_assertions

# 1. 准备
client = AgentBayClient()
store = TraceStore()

# 2. 定义测试任务
task = Task(
    prompt="创建一个文件test.txt并写入'Hello World'",
    assertions=[
        {"type": "contains", "expected": "test.txt"},
        {"type": "contains", "expected": "Hello World"}
    ]
)

# 3. 创建环境
session = client.create_session(env_type="computer")
session_id = session["session_id"]

# 4. 开始追踪
trace_id = store.start_trace("file_agent", task_id="task_001")

# 5. 执行Agent任务
commands = [
    "echo 'Hello World' > test.txt",
    "cat test.txt"
]

agent_output = []
for cmd in commands:
    result = client.execute_command(session_id, cmd)
    agent_output.append(result["output"])

    store.write_event({
        "type": "agentbay_command",
        "command": cmd,
        "result": result
    })

# 6. 评估结果
combined_output = "\n".join(agent_output)
assertion_results = run_assertions(combined_output, task.assertions)

store.write_event({
    "type": "evaluation",
    "results": assertion_results
})

# 7. 清理
all_passed = all(r["ok"] for r in assertion_results)
store.end_trace(trace_id, status="success" if all_passed else "failed")
client.delete_session(session_id)

print(f"测试完成: {'✅ 通过' if all_passed else '❌ 失败'}")
```

**用途**:
- 完整的Agent评估流程
- 自动化测试套件
- CI/CD集成

---

## 🛠️ AgentBay API 参考

### 初始化客户端

```python
from tigerhill.agentbay import AgentBayClient

# 方法1: 直接传入API key
client = AgentBayClient(api_key="your_api_key")

# 方法2: 使用环境变量
# export AGENTBAY_API_KEY=your_api_key
client = AgentBayClient()
```

### 环境类型

```python
from tigerhill.agentbay import EnvironmentType

# 支持的环境
EnvironmentType.BROWSER      # 浏览器环境
EnvironmentType.COMPUTER     # 完整计算机环境
EnvironmentType.MOBILE       # 移动设备环境
EnvironmentType.CODESPACE    # 代码开发环境
```

### 核心方法

#### 1. 创建会话

```python
session = client.create_session(
    env_type=EnvironmentType.BROWSER,  # 可选
    config={                            # 可选配置
        "resolution": "1920x1080",
        "browser": "chrome"
    }
)

# 返回
{
    "session_id": "12345",
    "status": "active",
    "env_type": "browser",
    "created_at": "2025-11-01T12:00:00"
}
```

#### 2. 执行命令

```python
result = client.execute_command(
    session_id="12345",
    command="ls -la",
    timeout=30  # 可选，秒
)

# 返回
{
    "output": "文件列表...",
    "exit_code": 0,
    "error": None
}
```

#### 3. 执行工具

```python
result = client.execute_tool(
    tool_name="bash",
    tool_args={"command": "pwd"},
    session_id="12345"  # 可选，不提供会创建临时会话
)

# 返回
{
    "tool_name": "bash",
    "result": "/home/user"
}
```

#### 4. 查询会话状态

```python
status = client.get_session_status(session_id="12345")

# 返回
{
    "session_id": "12345",
    "status": "active",
    "uptime": 120,  # 秒
    "resources": {
        "cpu": "25%",
        "memory": "512MB"
    }
}
```

#### 5. 加载工具集

```python
tools = client.load_tools(tool_set_id="web_automation")

# 返回可用工具列表
[
    {
        "name": "open_url",
        "description": "打开网页",
        "parameters": {...}
    },
    {
        "name": "click",
        "description": "点击元素",
        "parameters": {...}
    }
]
```

#### 6. 删除会话

```python
success = client.delete_session(session_id="12345")
# 返回: True/False
```

#### 7. 上下文管理器

```python
# 自动清理会话
with client.session(env_type="browser") as session:
    result = client.execute_command(
        session["session_id"],
        "your command"
    )
    # 会话会在with块结束时自动删除
```

---

## 🎓 最佳实践

### 1. 始终清理会话

```python
# ❌ 错误 - 可能导致资源泄漏
session = client.create_session()
# ... 忘记删除

# ✅ 正确 - 使用try/finally
session = client.create_session()
try:
    # 使用session
    pass
finally:
    client.delete_session(session["session_id"])

# ✅ 最佳 - 使用上下文管理器
with client.session() as session:
    # 使用session
    pass
```

### 2. 合理设置超时

```python
# ✅ 对于快速命令
result = client.execute_command(
    session_id,
    "echo hello",
    timeout=5
)

# ✅ 对于耗时操作
result = client.execute_command(
    session_id,
    "npm install",
    timeout=300
)
```

### 3. 错误处理

```python
try:
    session = client.create_session()
    session_id = session["session_id"]

    result = client.execute_command(
        session_id,
        "some command"
    )

    if result["exit_code"] != 0:
        print(f"命令失败: {result['error']}")

except RuntimeError as e:
    print(f"AgentBay错误: {e}")

finally:
    client.delete_session(session_id)
```

### 4. 日志记录

```python
import logging
logging.basicConfig(level=logging.INFO)

# AgentBay会自动输出详细日志
client = AgentBayClient()
```

---

## 💰 成本考虑

### 计费方式

AgentBay通常按以下方式计费：

1. **会话时长** - 按分钟计费
2. **环境类型** - 不同环境价格不同
3. **资源使用** - CPU、内存、带宽

### 优化成本

```python
# 1. 使用临时会话（自动清理）
result = client.execute_tool(
    tool_name="bash",
    tool_args={"command": "pwd"}
    # 不传session_id，自动创建并清理
)

# 2. 复用会话（多个命令）
session = client.create_session()
session_id = session["session_id"]

for cmd in commands:  # 多个命令复用同一会话
    client.execute_command(session_id, cmd)

client.delete_session(session_id)

# 3. 并行执行（减少总时间）
with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = [
        executor.submit(test_function, env)
        for env in environments
    ]
```

---

## 🔐 安全性

### API Key 保护

```python
# ✅ 使用环境变量
export AGENTBAY_API_KEY=your_key
client = AgentBayClient()

# ❌ 不要硬编码
client = AgentBayClient(api_key="hardcoded_key")  # 危险！
```

### 命令安全

```python
# ⚠️ 注意命令注入
user_input = "file.txt; rm -rf /"  # 恶意输入

# ❌ 不安全
client.execute_command(session_id, f"cat {user_input}")

# ✅ 安全 - 验证和转义
import shlex
safe_input = shlex.quote(user_input)
client.execute_command(session_id, f"cat {safe_input}")
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 安装TigerHill（已包含AgentBay客户端）
pip install -e .

# 安装AgentBay SDK
pip install wuying-agentbay-sdk
```

### 2. 获取API Key

1. 访问：https://agentbay.console.aliyun.com/service-management
2. 注册阿里云账号
3. 创建API Key
4. 设置环境变量：`export AGENTBAY_API_KEY=your_key`

### 3. 第一个测试

```python
from tigerhill.agentbay import AgentBayClient

# 初始化
client = AgentBayClient()

# 创建会话
session = client.create_session(env_type="computer")
print(f"✅ 会话创建成功: {session['session_id']}")

# 执行命令
result = client.execute_command(
    session["session_id"],
    "echo 'Hello from AgentBay!'"
)
print(f"📤 命令输出: {result['output']}")

# 清理
client.delete_session(session["session_id"])
print("✅ 会话已清理")
```

### 4. 运行测试

```bash
# 运行AgentBay集成测试
pytest tests/test_agentbay_real.py -v -s
```

---

## 📚 更多资源

### TigerHill文档
- **快速开始**: `QUICK_START.md`
- **完整指南**: `USER_GUIDE.md`
- **测试指南**: `AGENTBAY_TESTING_GUIDE.md`

### AgentBay官方
- **官方文档**: https://www.alibabacloud.com/help/en/agentbay/
- **SDK GitHub**: https://github.com/aliyun/wuying-agentbay-sdk
- **控制台**: https://agentbay.console.aliyun.com

---

## ❓ 常见问题

### Q: 什么时候需要使用AgentBay？

**A**: 当你的Agent需要：
- ✅ 真实浏览器环境（不是模拟）
- ✅ 完整操作系统（不只是Python环境）
- ✅ 移动设备模拟
- ✅ 跨平台一致性
- ✅ 并行测试环境
- ✅ 安全隔离执行

### Q: 不用AgentBay可以测试吗？

**A**: 可以！TigerHill的核心功能不依赖AgentBay：
- ✅ **TraceStore** - 本地追踪
- ✅ **Assertions** - 本地评估
- ✅ **Observer SDK** - 本地调试
- ⚠️ **AgentBay** - 需要云端环境时才用

### Q: AgentBay和Docker的区别？

**A**:
```
Docker:
- 容器化你的应用
- 需要自己管理环境
- 本地或自己的服务器运行

AgentBay:
- 完全托管的云端环境
- 提供现成的浏览器、移动设备等
- 按需使用，无需维护
```

### Q: 免费额度是多少？

**A**: 请查看阿里云AgentBay定价页面，通常有：
- 免费试用额度
- 新用户优惠
- 学生优惠

### Q: 测试失败怎么办？

**A**: 常见问题检查：
1. API Key是否正确
2. 网络能否访问阿里云
3. SDK版本是否最新
4. 查看详细日志：`logging.basicConfig(level=logging.DEBUG)`

---

**文档版本**: 1.0
**更新日期**: 2025-11-01
**适用版本**: TigerHill 0.0.3+

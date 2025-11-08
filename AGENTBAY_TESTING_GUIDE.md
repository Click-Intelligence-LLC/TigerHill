# AgentBay 测试指南

## 当前测试状态 ⚠️

### ❌ AgentBay 真实环境测试：未完成

**原因**：缺少以下前提条件

1. **AGENTBAY_API_KEY** - 未设置 ❌
2. **wuying-agentbay-sdk** - 未安装 ❌

### ✅ 已完成的测试

| 测试类型 | 状态 | 说明 |
|---------|------|------|
| TraceStore 功能 | ✅ 通过 (5/5) | 追踪存储完全测试 |
| 评估框架 | ✅ 通过 (2/2) | 断言系统测试 |
| AgentBay Mock | ⏭ 跳过 (3/3) | 需要真实 SDK |
| AgentBay Real | ⚠️ 未运行 | 需要 API key |

---

## 获取 AgentBay API Key

### 步骤 1: 注册阿里云账号

如果您还没有阿里云账号：
1. 访问：https://www.alibabacloud.com
2. 注册账号并完成认证

### 步骤 2: 访问 AgentBay 控制台

1. 访问：https://agentbay.console.aliyun.com/service-management
2. 登录您的阿里云账号

### 步骤 3: 创建 API Key

1. 在控制台中找到 "API Key" 或 "服务管理" 部分
2. 点击 "创建 API Key" 或 "生成密钥"
3. 复制生成的 API Key

### 步骤 4: 设置环境变量

**Linux / macOS:**
```bash
export AGENTBAY_API_KEY=your_api_key_here
```

**Windows (PowerShell):**
```powershell
$env:AGENTBAY_API_KEY="your_api_key_here"
```

**Windows (CMD):**
```cmd
set AGENTBAY_API_KEY=your_api_key_here
```

**永久设置 (添加到 ~/.bashrc 或 ~/.zshrc):**
```bash
echo 'export AGENTBAY_API_KEY=your_api_key_here' >> ~/.bashrc
source ~/.bashrc
```

---

## 安装 AgentBay SDK

### 使用 pip 安装

```bash
pip install wuying-agentbay-sdk
```

### 验证安装

```python
python -c "import agentbay; print('AgentBay SDK installed successfully!')"
```

---

## 运行 AgentBay 真实测试

### 1. 完整测试套件

```bash
# 运行所有 AgentBay 真实测试
pytest tests/test_agentbay_real.py -v -s
```

### 2. 运行特定测试

```bash
# 测试客户端初始化
pytest tests/test_agentbay_real.py::TestAgentBayReal::test_client_initialization -v -s

# 测试会话管理
pytest tests/test_agentbay_real.py::TestAgentBayReal::test_create_and_delete_session -v -s

# 测试命令执行
pytest tests/test_agentbay_real.py::TestAgentBayReal::test_execute_command -v -s

# 测试追踪集成
pytest tests/test_agentbay_real.py::TestAgentBayWithTraceStore::test_trace_agentbay_execution -v -s
```

### 3. 检查前提条件

```bash
# 快速检查是否满足所有前提条件
python tests/test_agentbay_real.py
```

---

## 测试内容

### TestAgentBayReal 类

| 测试方法 | 功能 | 预期结果 |
|---------|------|---------|
| `test_client_initialization` | 初始化 AgentBay 客户端 | 成功创建客户端实例 |
| `test_create_and_delete_session` | 创建和删除会话 | 会话生命周期管理正常 |
| `test_execute_command` | 在云端执行命令 | 命令执行成功并返回输出 |
| `test_execute_python_code` | 执行 Python 代码 | Python 代码运行正常 |
| `test_context_manager` | 上下文管理器 | 自动清理会话 |
| `test_load_tools` | 加载工具定义 | 返回可用工具列表 |
| `test_get_session_status` | 查询会话状态 | 返回会话信息 |

### TestAgentBayWithTraceStore 类

| 测试方法 | 功能 | 预期结果 |
|---------|------|---------|
| `test_trace_agentbay_execution` | 追踪 AgentBay 执行 | 完整记录执行过程 |

---

## 预期测试输出

```
======================== test session starts ========================

tests/test_agentbay_real.py::TestAgentBayReal::test_client_initialization
[TEST] Initializing AgentBay client...
✓ Client initialized successfully
PASSED

tests/test_agentbay_real.py::TestAgentBayReal::test_create_and_delete_session
[TEST] Creating AgentBay session...
✓ Session created: abc123...
  - Status: active
  - Environment: codespace
[TEST] Deleting session abc123...
✓ Session deleted successfully
PASSED

tests/test_agentbay_real.py::TestAgentBayReal::test_execute_command
[TEST] Executing command in AgentBay...
✓ Session created: def456...
[TEST] Running command: echo 'Hello from TigerHill!'
✓ Command executed
  - Output: Hello from TigerHill!
  - Exit Code: 0
✓ Session cleaned up
PASSED

... (更多测试输出)

=================== 8 passed in 45.3s ===================
```

---

## 常见问题

### Q1: 获取 API key 需要付费吗？

**A**: 请参考阿里云 AgentBay 的定价页面。通常有免费试用额度。

### Q2: 测试会产生费用吗？

**A**: 可能会产生少量费用。我们的测试：
- 创建和删除会话：~10 次
- 执行简单命令：~5 次
- 总时长：< 1 分钟

建议先查看 AgentBay 计费规则。

### Q3: 没有 API key 能用 TigerHill 吗？

**A**: 可以！TigerHill 的核心功能不依赖 AgentBay：
- ✅ TraceStore - 本地追踪存储
- ✅ Assertions - 评估框架
- ✅ Core Models - 数据模型
- ⚠️ AgentBay Client - 需要 API key

### Q4: 测试失败怎么办？

**A**: 常见问题：
1. **网络问题** - 检查能否访问阿里云
2. **API key 无效** - 验证 key 是否正确
3. **配额限制** - 检查是否超出使用限制
4. **SDK 版本** - 尝试更新 SDK：`pip install -U wuying-agentbay-sdk`

### Q5: 如何调试 AgentBay 调用？

**A**: 启用日志：
```python
import logging
logging.basicConfig(level=logging.DEBUG)

from tigerhill.agentbay.client import AgentBayClient
client = AgentBayClient()
```

---

## 完整测试检查清单

使用此清单确保所有测试都已完成：

### 前提条件
- [ ] 阿里云账号已创建
- [ ] AgentBay API key 已获取
- [ ] 环境变量 `AGENTBAY_API_KEY` 已设置
- [ ] wuying-agentbay-sdk 已安装

### 单元测试
- [x] TraceStore 测试 (5/5 通过)
- [x] 评估框架测试 (2/2 通过)
- [x] 数据模型测试 (已通过)

### 集成测试
- [ ] AgentBay 客户端初始化
- [ ] AgentBay 会话管理
- [ ] AgentBay 命令执行
- [ ] AgentBay Python 代码执行
- [ ] AgentBay 上下文管理器
- [ ] AgentBay 工具加载
- [ ] AgentBay 会话状态查询
- [ ] AgentBay + TraceStore 集成

### 端到端测试
- [ ] DynamicAgent + AgentBay 完整流程
- [ ] 评估工作流测试
- [ ] 实验对比测试

---

## 下一步行动

### 立即可做（不需要 API key）
1. ✅ 查看 TraceStore 功能
2. ✅ 尝试评估框架
3. ✅ 运行示例代码：`PYTHONPATH=. python examples/basic_usage.py`

### 获取 API key 后
1. 🔑 运行 AgentBay 真实测试
2. 🔑 测试完整的评估工作流
3. 🔑 进行端到端集成测试

### 后续开发
1. 🔨 修复 DynamicAgent 集成问题
2. 🔨 添加更多 AgentBay 工具支持
3. 🔨 实现 LLM-as-a-Judge 评估器

---

## 联系方式

如果遇到问题：
- AgentBay 官方文档：https://www.alibabacloud.com/help/en/agentbay/
- AgentBay SDK GitHub：https://github.com/aliyun/wuying-agentbay-sdk
- TigerHill Issues：（您的项目 issue tracker）

---

**最后更新**: 2025-10-28
**测试状态**: ⚠️ 需要 API key 才能完成 AgentBay 集成测试

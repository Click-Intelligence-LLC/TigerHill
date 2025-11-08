# 🐯 TigerHill

**AI Agent 测试与评估平台**

开源的 Agent 测试框架，提供类似 LangSmith 的功能

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-124%20core%20passing-brightgreen.svg)](tests/)
[![Version](https://img.shields.io/badge/version-0.0.3-orange.svg)](CHANGELOG.md)

> **最新更新 v0.0.3** (2025-11-07): 完整支持 Gemini CLI 复杂任务捕获，修复数据库和 Dashboard 关键 bug

---

## ✨ 核心特性

### 🎯 Observer SDK (Debug Mode)
- **无侵入式捕获**: 不修改代码，自动记录 LLM 交互
- **多轮对话追踪**: 完整的会话级别数据管理
- **智能分析**: 5 维度 22+ 指标自动分析
- **隐私保护**: 自动脱敏敏感数据（API keys、邮箱等）
- **Gemini CLI 支持**: 完整支持复杂任务和流式响应 **[v0.0.3]**
- **跨语言**: Python + Node.js SDK

### 📊 TraceStore (Test Mode)
- **追踪存储**: 完整记录 Agent 执行过程
- **双后端**: 文件系统 + SQLite，按需选择
- **高级查询**: 按成本、Token、标签等筛选
- **统计分析**: 自动计算成本、耗时、质量评分

### 🔍 评估框架
- **断言评估**: 8 种断言类型验证输出质量
- **代码验证**: 自动提取并验证生成代码（Python/JS/Go/Rust）
- **多语言 Agent**: 通过 HTTP/CLI/STDIO 测试任何语言的 Agent

### 🌐 云集成
- **AgentBay**: 云端隔离环境测试
- **Dashboard**: Streamlit 数据可视化
- **导出导入**: JSON 格式轻松迁移

---

## ✅ 核心测试覆盖

当前 release 已在本地通过以下关键测试套件（Python 3.12.7 / pytest 7.4.4）：

```bash
pytest tests/test_sqlite_trace_store.py \
       tests/test_trace_db_serialization.py \
       tests/test_observer_phase1_enhancements.py \
       tests/test_template_engine
```

- TraceStore / SQLite：23 个测试
- Trace 序列化：12 个测试
- Observer Phase 1：18 个测试
- 模板引擎 CLI & 生成：71 个测试
- ✅ 合计 124 / 124 用例全部通过

## 🚀 快速安装

### 安装

```bash
cd TigerHill
pip install -e ".[dev]"

# 可选：安装 AgentBay SDK
pip install wuying-agentbay-sdk
export AGENTBAY_API_KEY=your_api_key_here
```

### 5 分钟上手

```python
from tigerhill.storage.trace_store import TraceStore
from tigerhill.core.models import Task
from tigerhill.eval.assertions import run_assertions

# 1. 初始化追踪存储
store = TraceStore(storage_path="./my_traces")

# 2. 定义测试任务
task = Task(
    prompt="计算 6 + 7",
    assertions=[
        {"type": "contains", "expected": "13"}
    ]
)

# 3. 开始追踪
trace_id = store.start_trace(agent_name="calculator_agent")

# 运行你的 Agent
agent_output = your_agent.run(task.prompt)  # 替换为你的 Agent 调用

# 记录执行过程
store.write_event({"type": "prompt", "content": task.prompt})
store.write_event({"type": "model_response", "text": agent_output})
store.end_trace(trace_id)

# 4. 评估结果
results = run_assertions(agent_output, task.assertions)
passed = sum(1 for r in results if r["ok"])

print(f"✅ 通过: {passed}/{len(results)}")
print(f"📊 追踪 ID: {trace_id}")
```

---

## 📚 文档索引

### 用户文档
| 文档 | 说明 |
|------|------|
| **[QUICK_START.md](QUICK_START.md)** | 5 分钟快速上手 |
| **[USER_GUIDE.md](USER_GUIDE.md)** | 完整使用手册和最佳实践 |
| **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** | API 快速参考 |
| **[CHANGELOG.md](CHANGELOG.md)** | 版本更新日志 **[新]** |

### Observer SDK (Gemini CLI 支持)
| 文档 | 说明 |
|------|------|
| **[OBSERVER_SDK_DOCUMENTATION.md](OBSERVER_SDK_DOCUMENTATION.md)** | Observer SDK 完整文档 |
| **[OBSERVER_SDK_QUICK_SUMMARY.md](OBSERVER_SDK_QUICK_SUMMARY.md)** | Observer SDK 快速参考 |
| **[GEMINI_CLI_INTERCEPTOR_GUIDE.md](GEMINI_CLI_INTERCEPTOR_GUIDE.md)** | Gemini CLI 拦截器指南 **[v0.0.3]** |
| **[GEMINI_CAPTURE_USAGE.md](GEMINI_CAPTURE_USAGE.md)** | Gemini 捕获使用说明 **[v0.0.3]** |
| **[GEMINI_429_ERROR.md](GEMINI_429_ERROR.md)** | Gemini API 限流说明 **[v0.0.3]** |

### 测试和集成
| 文档 | 说明 |
|------|------|
| **[CODE_VALIDATION_TEST_REPORT.md](CODE_VALIDATION_TEST_REPORT.md)** | 代码验证测试报告（17/17 通过） |
| **[CROSS_LANGUAGE_TESTING.md](CROSS_LANGUAGE_TESTING.md)** | 跨语言 Agent 测试指南 |
| **[CROSS_LANGUAGE_TEST_REPORT.md](CROSS_LANGUAGE_TEST_REPORT.md)** | 跨语言测试报告 |
| **[AGENTBAY_TESTING_GUIDE.md](AGENTBAY_TESTING_GUIDE.md)** | AgentBay 使用指南 |
| **[AGENTBAY_COMPLETE_TEST_REPORT.md](AGENTBAY_COMPLETE_TEST_REPORT.md)** | AgentBay 测试报告（7/8 通过） |
| **[AGENTBAY_USAGE_GUIDE.md](AGENTBAY_USAGE_GUIDE.md)** | AgentBay 详细用法 |
| **[AGENTBAY_TEST_RESULTS.md](AGENTBAY_TEST_RESULTS.md)** | AgentBay 测试结果 |
| **[AGENT_INTERCEPTION_TEST_GUIDE.md](AGENT_INTERCEPTION_TEST_GUIDE.md)** | Agent 拦截测试指南 |

### Phase 1 功能
| 文档 | 说明 |
|------|------|
| **[PHASE1_QUICK_START.md](PHASE1_QUICK_START.md)** | Phase 1 快速开始 |
| **[PHASE1_TEST_REPORT.md](PHASE1_TEST_REPORT.md)** | Phase 1 测试报告 |
| **[PHASE1_COMPLETION_SUMMARY.md](PHASE1_COMPLETION_SUMMARY.md)** | Phase 1 功能总结 |

### 架构和设计
| 文档 | 说明 |
|------|------|
| **[ARCHITECTURE_ANALYSIS_STORAGE.md](ARCHITECTURE_ANALYSIS_STORAGE.md)** | 存储架构分析 |
| **[STORAGE_DIRECTORIES_GUIDE.md](STORAGE_DIRECTORIES_GUIDE.md)** | 存储目录指南 |
| **[OBSERVER_SDK_COMPLETION_REPORT.md](OBSERVER_SDK_COMPLETION_REPORT.md)** | Observer SDK 完成报告（28/28 测试通过） |
| **[COMPREHENSIVE_REVIEW_REPORT.md](COMPREHENSIVE_REVIEW_REPORT.md)** | 项目综合评审（评分 8.7/10） |

---

## 🌟 核心功能

### 1. TraceStore - 追踪存储

完整记录 Agent 执行过程，便于调试和分析。

### 2. 断言评估 - 质量验证

灵活的断言系统评估 Agent 输出质量。

### 3. Observer SDK - Debug Mode **[新功能]**

无侵入式捕获 LLM 交互，自动分析和优化 prompts。

#### 特性

- 🎯 **无侵入捕获**: 包装器模式，不修改原代码
- 📊 **智能分析**: 5 维度、22 指标、7+ 类建议
  - Token 使用分析（成本优化）
  - Prompt 质量评估（效果提升）
  - 性能分析（速度优化）
  - 工具使用分析（功能优化）
  - 自动优化建议
- 🔒 **隐私保护**: 自动脱敏 API keys、邮箱等
- 🔄 **TraceStore 集成**: 自动转换为测试用例
- 🌍 **跨语言**: Python + Node.js

#### 快速开始

```python
from tigerhill.observer import PromptCapture, wrap_python_model
from tigerhill.observer.python_observer import create_observer_callback
import google.generativeai as genai

# 1. 创建捕获器
capture = PromptCapture()
capture_id = capture.start_capture("my_agent")

# 2. 包装模型（唯一需要改的地方）
callback = create_observer_callback(capture, capture_id)
WrappedModel = wrap_python_model(genai.GenerativeModel, callback)
model = WrappedModel("gemini-pro")

# 3. 正常使用（完全透明）
response = model.generate_content("Write a function...")

# 4. 获取分析
result = capture.end_capture(capture_id)
print(f"Tokens: {result['statistics']['total_tokens']}")

# 5. 自动分析
from tigerhill.observer import PromptAnalyzer
analyzer = PromptAnalyzer(result)
analyzer.print_report(analyzer.analyze_all())
```

**详细文档**:
- [OBSERVER_SDK_DOCUMENTATION.md](OBSERVER_SDK_DOCUMENTATION.md) - 完整文档
- [OBSERVER_SDK_QUICK_SUMMARY.md](OBSERVER_SDK_QUICK_SUMMARY.md) - 快速参考
- [examples/README.md](examples/README.md) - 示例指南

**示例代码**:
```bash
# Python 基础示例
python examples/observer_python_basic.py

# 分析示例
python examples/observer_python_analysis.py

# TraceStore 集成
python examples/observer_tracestore_integration.py

# Node.js 示例
node examples/observer_nodejs_basic.js
```

### 4. AgentBay - 云端集成

云端隔离环境测试 Agent。

### 5. 跨语言测试 - 支持任何编程语言

通过适配器模式测试**任何语言**编写的 Agent：
- **HTTP/REST API**: Node.js、Go、Java、Python 等
- **CLI 命令行**: Go、Rust、C++ 等编译型语言
- **STDIN/STDOUT**: Java、C# 等交互式程序
- **AgentBay 云环境**: 任何可在 Linux 运行的语言

#### 快速示例：测试 Node.js Agent

```python
from tigerhill.adapters import HTTPAgentAdapter, UniversalAgentTester
from tigerhill.storage.trace_store import TraceStore

# 创建适配器
adapter = HTTPAgentAdapter(
    base_url="http://localhost:3000",
    endpoint="/api/agent"
)

# 创建测试器
store = TraceStore()
tester = UniversalAgentTester(adapter, store)

# 执行测试
result = tester.test(
    task={
        "prompt": "计算 1+1",
        "assertions": [{"type": "contains", "expected": "2"}]
    },
    agent_name="nodejs_agent"
)

print(f"✅ 通过: {result['passed']}/{result['total']}")
```

**详细文档**: 查看 [CROSS_LANGUAGE_TESTING.md](CROSS_LANGUAGE_TESTING.md)

**示例代码**:
- `examples/cross_language/test_nodejs_agent.py` - Node.js Agent 测试
- `examples/cross_language/test_go_agent.py` - Go Agent 测试
- `examples/cross_language/batch_test_multilang.py` - 批量多语言测试

---

## 📊 测试状态

```
总测试数（核心套件）:   124
✅ 通过:                124 (100%)
❌ 失败:                0
⚠️  跳过:               依赖云 API 的额外场景

TraceStore / SQLite:    23/23 ✅
Trace 序列化:          12/12 ✅
Observer Phase 1:       18/18 ✅
模板引擎 CLI/生成:     71/71 ✅
```

详见:
- [OBSERVER_SDK_COMPLETION_REPORT.md](OBSERVER_SDK_COMPLETION_REPORT.md) - **Observer SDK 完成报告 [新]**
- [CODE_VALIDATION_TEST_REPORT.md](CODE_VALIDATION_TEST_REPORT.md) - 代码验证测试报告
- [AGENTBAY_COMPLETE_TEST_REPORT.md](AGENTBAY_COMPLETE_TEST_REPORT.md) - AgentBay 完整测试报告
- [FINAL_COMPLETE_TEST_REPORT.md](FINAL_COMPLETE_TEST_REPORT.md) - 完整测试报告（历史）

---

## 🛠️ 快速使用

```bash
# 1. 安装
pip install -e ".[dev]"

# 2. 运行示例
python examples/basic_usage.py

# 3. 运行测试
pytest tests/test_integration.py -v

# 4. 查看文档
cat QUICK_START.md
```

**当前版本**: 0.0.3

**开发状态**: ✅ 活跃开发中

---

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

### 添加新语言支持

TigerHill 的跨语言测试功能欢迎社区贡献更多语言示例：

1. 在 `examples/cross_language/` 创建 Agent 实现
2. 编写相应的测试文件
3. 更新文档
4. 提交 Pull Request

当前支持的示例：
- ✅ Python
- ✅ Node.js (HTTP API)
- ✅ Go (CLI)
- 🔜 Rust
- 🔜 Java
- 🔜 C++

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 🌐 相关链接

- **AgentBay 官网**: https://www.alibabacloud.com/help/en/agentbay/
- **AgentBay SDK**: https://github.com/aliyun/wuying-agentbay-sdk

---

**🎉 开始测试你的 Agent 吧！**

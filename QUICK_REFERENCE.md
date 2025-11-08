# TigerHill 快速参考指南

**最新更新**: 2025-10-29 - 新增代码验证功能

---

## 🎯 核心功能速查

### 1. Trace Viewer - 查看追踪记录

```bash
# 列出所有 trace
python -m tigerhill.utils.trace_viewer --storage ./traces --list

# 查看对话格式
python -m tigerhill.utils.trace_viewer \
    --storage ./traces \
    --conversation <trace_id>

# 查看详细信息
python -m tigerhill.utils.trace_viewer \
    --storage ./traces \
    --view <trace_id> \
    --verbose
```

**功能**: 清晰展示 prompt、response 和评估结果

---

### 2. Code Validation - 验证生成的代码

#### 在断言中使用

```python
from tigerhill.eval.assertions import run_assertions

assertions = [
    # 语法检查（推荐始终启用）
    {
        "type": "code_validation",
        "language": "python",
        "validation_type": "syntax"
    },

    # 代码执行（按需启用）
    {
        "type": "code_validation",
        "language": "python",
        "validation_type": "execution",
        "timeout": 30
    },

    # 运行测试（完整验证）
    {
        "type": "code_validation",
        "language": "python",
        "validation_type": "test",
        "test_command": "pytest",
        "timeout": 60
    }
]

results = run_assertions(llm_output, assertions)
```

#### 直接使用验证器

```python
from tigerhill.eval.code_validator import CodeValidator

validator = CodeValidator()

# 验证代码
result = validator.validate(
    text=llm_output,
    language="python",
    validation_type="syntax"
)

print(f"验证结果: {result['ok']}")
print(f"详情: {result['details']}")
```

---

### 3. 完整测试流程

```python
from tigerhill.adapters import CLIAgentAdapter, UniversalAgentTester
from tigerhill.storage.trace_store import TraceStore

# 1. 创建存储和适配器
store = TraceStore(storage_path="./traces")
adapter = CLIAgentAdapter(command="your_agent")

# 2. 创建测试器
tester = UniversalAgentTester(adapter, store)

# 3. 定义任务（包含代码验证）
task = {
    "prompt": "生成一个排序函数",
    "assertions": [
        {"type": "contains", "expected": "def"},
        {
            "type": "code_validation",
            "language": "python",
            "validation_type": "syntax"
        }
    ]
}

# 4. 执行测试
result = tester.test(task, agent_name="my_agent")

# 5. 查看结果
print(f"通过: {result['passed']}/{result['total']}")
print(f"Trace ID: {result['trace_id']}")

# 6. 查看 trace
# python -m tigerhill.utils.trace_viewer \
#     --storage ./traces \
#     --conversation <trace_id>
```

---

## 📋 断言类型速查

| 类型 | 用途 | 示例 |
|------|------|------|
| `contains` | 检查是否包含字符串 | `{"type": "contains", "expected": "hello"}` |
| `equals` | 检查完全相等 | `{"type": "equals", "expected": "42"}` |
| `regex` | 正则表达式匹配 | `{"type": "regex", "pattern": "\\d+"}` |
| `starts_with` | 检查开头 | `{"type": "starts_with", "expected": "Error"}` |
| `ends_with` | 检查结尾 | `{"type": "ends_with", "expected": "."}` |
| **`code_validation`** | **验证代码** [新] | 见下方详细说明 |

### code_validation 参数

```python
{
    "type": "code_validation",
    "language": "python",           # 语言: python, javascript, go, etc.
    "validation_type": "syntax",    # 类型: syntax, execution, test
    "timeout": 30,                  # 超时（秒，可选）
    "test_command": "pytest"        # 测试命令（可选）
}
```

**validation_type 选项**:
- `syntax`: 语法检查（毫秒级，推荐）
- `execution`: 执行代码（秒级）
- `test`: 运行测试（分钟级）

---

## 🔧 常用命令

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/test_code_validation_integration.py -v

# 运行代码验证示例
python examples/code_validation_example.py

# 运行 Gemini 测试（需要 API key）
python examples/cross_language/test_gemini_cli.py
```

### 查看文档

```bash
# 快速上手
cat QUICK_START.md

# 代码验证解决方案
cat SOLUTIONS_FOR_CODE_VALIDATION.md

# 测试报告
cat CODE_VALIDATION_TEST_REPORT.md

# 用户指南
cat USER_GUIDE.md
```

---

## 🎯 使用场景

### 场景 1: 测试代码生成 Agent

```python
task = {
    "prompt": "生成一个质数检测函数",
    "assertions": [
        {"type": "contains", "expected": "def is_prime"},
        {"type": "code_validation", "language": "python", "validation_type": "syntax"},
        {"type": "code_validation", "language": "python", "validation_type": "execution"}
    ]
}
```

**验证**:
- ✅ 是否生成了函数
- ✅ 代码语法正确
- ✅ 代码可以执行

---

### 场景 2: 测试文档生成 Agent

```python
task = {
    "prompt": "生成 API 文档",
    "assertions": [
        {"type": "contains", "expected": "## API"},
        {"type": "regex", "pattern": "```python.*?```"},
        {"type": "code_validation", "language": "python", "validation_type": "syntax"}
    ]
}
```

**验证**:
- ✅ 包含 API 标题
- ✅ 包含代码示例
- ✅ 代码示例语法正确

---

### 场景 3: 查看测试历史

```bash
# 1. 列出最近的测试
python -m tigerhill.utils.trace_viewer --storage ./traces --list

# 2. 选择一个 trace_id，查看详情
python -m tigerhill.utils.trace_viewer \
    --storage ./traces \
    --conversation <trace_id>

# 3. 分析失败原因
# 查看 prompt、response 和评估结果
```

---

## 🚀 最佳实践

### 1. 分层验证策略

```python
assertions = [
    # 第一层：文本内容（快速，必须）
    {"type": "contains", "expected": "def"},

    # 第二层：语法检查（快速，推荐）
    {"type": "code_validation", "validation_type": "syntax"},

    # 第三层：执行验证（较慢，可选）
    # {"type": "code_validation", "validation_type": "execution"}
]
```

### 2. 超时设置

```python
# 简单代码: 10 秒
{"type": "code_validation", "validation_type": "execution", "timeout": 10}

# 测试套件: 60 秒
{"type": "code_validation", "validation_type": "test", "timeout": 60}
```

### 3. 安全执行

```python
# 开发环境: 本地验证
validator = CodeValidator()

# 生产环境: 使用 AgentBay（推荐）
validator = CodeValidator(
    use_agentbay=True,
    agentbay_client=client,
    agentbay_session_id=session_id
)
```

---

## 📊 性能参考

| 操作 | 时间 |
|------|------|
| 代码提取 | < 1ms |
| 语法检查 | < 10ms |
| 代码执行 | 0.1 - 2s |
| 运行测试 | 1 - 30s |
| Trace 查看 | < 100ms |

---

## 🐛 故障排查

### 问题: 找不到代码块

**原因**: 输出没有使用 Markdown 代码块格式

**解决**:
```python
# 确保 LLM 输出使用标准格式
"""
```python
code here
```
"""
```

---

### 问题: 语法检查失败

**原因**: 代码有语法错误

**解决**:
1. 查看错误详情: `result['message']`
2. 检查 LLM 输出
3. 调整 prompt 要求更严格的代码格式

---

### 问题: 执行超时

**原因**: 代码运行时间过长

**解决**:
```python
# 增加超时时间
{
    "type": "code_validation",
    "validation_type": "execution",
    "timeout": 60  # 增加到 60 秒
}
```

---

## 📚 相关文档

- **[QUICK_START.md](QUICK_START.md)** - 5 分钟上手
- **[SOLUTIONS_FOR_CODE_VALIDATION.md](SOLUTIONS_FOR_CODE_VALIDATION.md)** - 代码验证详解
- **[CODE_VALIDATION_TEST_REPORT.md](CODE_VALIDATION_TEST_REPORT.md)** - 测试报告
- **[USER_GUIDE.md](USER_GUIDE.md)** - 完整用户指南

---

## 💡 快速示例

### 最小示例

```python
from tigerhill.eval.assertions import run_assertions

# LLM 输出
output = """
```python
def hello():
    print("Hello!")
```
"""

# 验证
results = run_assertions(output, [
    {"type": "code_validation", "language": "python", "validation_type": "syntax"}
])

print(f"✅ 验证通过" if results[0]["ok"] else "❌ 验证失败")
```

### 完整示例

查看: `examples/code_validation_example.py`

---

**最后更新**: 2025-10-29
**版本**: 0.0.3
**状态**: ✅ 生产就绪

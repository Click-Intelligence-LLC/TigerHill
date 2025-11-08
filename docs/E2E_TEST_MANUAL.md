# TigerHill 端到端测试手册

**版本**: 1.0
**日期**: 2025-01-04
**适用范围**: Phase 1.2 (SQLite数据库) + Phase 1.3 (模板库)
**测试时长**: 约30-45分钟

---

## 测试目标

本测试手册将验证TigerHill的所有核心功能：
1. ✅ **模板库** - 生成测试脚本
2. ✅ **Observer SDK** - 拦截和捕获LLM交互
3. ✅ **Trace存储** - SQLite数据库存储
4. ✅ **Dashboard** - 可视化查看和分析
5. ✅ **端到端流程** - 从Agent执行到Dashboard查看

---

## 测试环境准备

### 前置条件

```bash
# 1. 确认Python版本
python --version  # 需要 Python 3.8+

# 2. 确认在TigerHill项目根目录
pwd  # 应该显示 .../TigerHill

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装额外依赖（如果需要）
pip install streamlit openai anthropic google-generativeai

# 5. 确认测试通过
PYTHONPATH=. pytest tests/ -v --tb=short
```

### 准备API密钥（可选，用于实际LLM测试）

```bash
# 如果要测试真实的LLM交互，设置API密钥
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
export GOOGLE_API_KEY="your-google-key"
```

---

## 测试场景 1: 模板库功能验证

**目标**: 验证模板生成、参数验证、代码生成功能

### 步骤 1.1: 列出所有可用模板

```bash
cd /Users/yinaruto/MyProjects/ChatLLM/TigerHill

python -m tigerhill.template_engine.cli --list
```

**预期输出**:
```
Available Templates:
============================================================

http-api-test
  Name: HTTP API Testing
  Description: Test an HTTP API endpoint with request/response validation
  Category: http
  Tags: http, api, rest, validation

[... 更多模板 ...]

llm-prompt-response
  Name: LLM Prompt-Response Testing
  Description: Test LLM prompt and response with quality validation
  Category: llm
  Tags: llm, prompt, response, quality

[共11个模板]
```

**验证点**:
- ✅ 显示了11个模板
- ✅ 每个模板有Name、Description、Category、Tags
- ✅ 包含5个类别：http, cli, stdio, llm, integration

**状态**: ⬜ 通过 / ⬜ 失败

---

### 步骤 1.2: 生成LLM测试脚本（非交互模式）

创建测试生成脚本：

```bash
cat > /tmp/test_template_generation.py << 'EOF'
#!/usr/bin/env python3
"""测试模板生成功能"""

import sys
from pathlib import Path
import tempfile

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tigerhill.template_engine.loader import TemplateLoader
from tigerhill.template_engine.validator import TemplateValidator
from tigerhill.template_engine.generator import CodeGenerator

def test_generation():
    # 创建临时输出目录
    output_dir = tempfile.mkdtemp(prefix="tigerhill_test_")
    print(f"✅ 输出目录: {output_dir}")

    # 加载模板
    loader = TemplateLoader()
    template = loader.load_template("llm/llm-prompt-response.yaml")
    print(f"✅ 加载模板: {template.name}")

    # 定义参数
    params = {
        "agent_name": "gemini-test",
        "model_name": "gemini-pro",
        "prompt": "What is the capital of France?",
        "max_tokens": 100,
        "temperature": 0.7,
        "validate_quality": True,
        "expected_keywords": "Paris"
    }
    print(f"✅ 配置参数: {len(params)} 个参数")

    # 验证参数
    validator = TemplateValidator(template)
    params = validator.apply_defaults(params)
    is_valid, errors = validator.validate(params)

    if not is_valid:
        print(f"❌ 参数验证失败:")
        for error in errors:
            print(f"   - {error}")
        return False

    print(f"✅ 参数验证通过")

    # 生成代码
    generator = CodeGenerator(template)
    generated_files = generator.generate(
        params=params,
        output_dir=output_dir,
        overwrite=False
    )

    print(f"\n✅ 生成文件成功:")
    for file_path in generated_files:
        file_size = Path(file_path).stat().st_size
        print(f"   📄 {Path(file_path).name} ({file_size} bytes)")

    # 验证文件内容
    test_file = Path(output_dir) / "test_gemini-test.py"
    if test_file.exists():
        with open(test_file, 'r') as f:
            content = f.read()

        # 检查关键内容
        checks = [
            ("import pytest", "导入pytest"),
            ("gemini-pro", "模型名称"),
            ("What is the capital of France?", "提示内容"),
            ("Paris", "预期关键词"),
        ]

        print(f"\n✅ 内容验证:")
        all_passed = True
        for check_str, description in checks:
            if check_str in content:
                print(f"   ✅ {description}: 存在")
            else:
                print(f"   ❌ {description}: 缺失")
                all_passed = False

        if all_passed:
            print(f"\n🎉 所有验证通过!")
            print(f"📁 生成的测试位于: {output_dir}")
            return True
        else:
            print(f"\n❌ 部分验证失败")
            return False
    else:
        print(f"❌ 测试文件未生成: {test_file}")
        return False

if __name__ == "__main__":
    success = test_generation()
    sys.exit(0 if success else 1)
EOF

# 执行测试
PYTHONPATH=. python /tmp/test_template_generation.py
```

**预期输出**:
```
✅ 输出目录: /tmp/tigerhill_test_xxxxx
✅ 加载模板: llm-prompt-response
✅ 配置参数: 7 个参数
✅ 参数验证通过

✅ 生成文件成功:
   📄 test_gemini-test.py (xxxx bytes)
   📄 requirements.txt (xxx bytes)
   📄 README.md (xxxx bytes)

✅ 内容验证:
   ✅ 导入pytest: 存在
   ✅ 模型名称: 存在
   ✅ 提示内容: 存在
   ✅ 预期关键词: 存在

🎉 所有验证通过!
📁 生成的测试位于: /tmp/tigerhill_test_xxxxx
```

**验证点**:
- ✅ 模板加载成功
- ✅ 参数验证通过
- ✅ 生成了3个文件
- ✅ 文件内容包含所有配置的参数
- ✅ 生成的代码语法正确

**状态**: ⬜ 通过 / ⬜ 失败

---

### 步骤 1.3: 交互式生成测试（可选）

如果想体验交互式CLI：

```bash
python -m tigerhill.template_engine.cli
```

按照提示：
1. 选择类别: `1` (HTTP Testing)
2. 选择模板: `1` (HTTP API Testing)
3. 输入参数:
   - Agent Name: `test-api`
   - API URL: `https://api.github.com`
   - HTTP Method: `GET` (直接回车使用默认值)
   - Expected Status: `200` (直接回车)
   - Request Body: (直接回车)
   - Validate Response: `y`
4. 确认生成: `y`

**预期结果**:
- 在 `./tests/` 目录生成3个文件
- 显示生成成功消息和下一步操作

**状态**: ⬜ 通过 / ⬜ 失败 / ⬜ 跳过

---

## 测试场景 2: SQLite数据库功能验证

**目标**: 验证Trace存储到SQLite、查询、统计功能

### 步骤 2.1: 运行演示Agent生成Trace数据

```bash
cd /Users/yinaruto/MyProjects/ChatLLM/TigerHill

# 运行演示Agent，生成Trace数据
PYTHONPATH=. python examples/demo_agent_with_tracing.py
```

**预期输出**:
```
============================================================
TigerHill 端到端验证 - Agent执行演示
============================================================

✅ 初始化TraceStore: ./tigerhill_validation.db

--- 任务 1/3 ---
✅ 开始任务: 分析用户反馈并生成报告
   Trace ID: xxxxxxxx
   📝 LLM调用 #1: xxx tokens
   📝 LLM调用 #2: xxx tokens
   🔧 工具调用: calculator
   🔧 工具调用: search
✅ 任务完成

--- 任务 2/3 ---
[...]

--- 任务 3/3 ---
[...]

============================================================
执行统计
============================================================
总Traces: 3
总Events: xx
LLM调用: xx
总Tokens: xxxx
总成本: $x.xxxx
状态分布: {'completed': 3}

============================================================
Trace摘要
============================================================
1. xxxxxxxx...
   Agent: validation-agent
   状态: completed
   Events: x
   [...]

============================================================
✅ 演示完成！
============================================================

下一步:
1. 数据已保存到: ./tigerhill_validation.db
2. 运行Dashboard查看: PYTHONPATH=. streamlit run tigerhill/web/dashboard/app.py
[...]
```

**验证点**:
- ✅ 成功创建数据库文件
- ✅ 生成了3个Traces
- ✅ 每个Trace包含多个Events
- ✅ 统计信息正确显示
- ✅ Trace摘要显示完整

**状态**: ⬜ 通过 / ⬜ 失败

---

### 步骤 2.2: 验证数据库内容

```bash
# 检查数据库文件是否存在
ls -lh ./tigerhill_validation.db

# 运行数据验证脚本
PYTHONPATH=. python examples/verify_stored_data.py
```

**预期输出**:
```
============================================================
验证存储的数据
============================================================

✅ 找到 3 个traces

1. Trace ID: xxxxxxxx...
   Agent: validation-agent
   状态: completed
   Events: 7
   Tokens: xxx
   成本: $x.xxxx

2. Trace ID: xxxxxxxx...
   [...]

3. Trace ID: xxxxxxxx...
   [...]

============================================================
详细查看第一个Trace
============================================================
Trace ID: xxxxxxxxxxxxxxxx
Agent: validation-agent
开始时间: 1704412800.123456
结束时间: 1704412801.234567
Events数量: 7

Events列表:
  1. prompt @ 2025-01-04 12:00:00.123456
     内容: Prompt 0...
  2. model_response @ 2025-01-04 12:00:00.234567
     内容: Response 0...
  [...]

============================================================
✅ 验证完成
============================================================
```

**验证点**:
- ✅ 数据库文件存在且大小合理
- ✅ 查询到3个Traces
- ✅ 每个Trace的统计信息正确
- ✅ Events详情可以正常获取

**状态**: ⬜ 通过 / ⬜ 失败

---

### 步骤 2.3: 运行自动化端到端测试

```bash
# 运行端到端验证测试
PYTHONPATH=. pytest tests/test_end_to_end_validation.py -v -s
```

**预期输出**:
```
tests/test_end_to_end_validation.py::TestEndToEndValidation::test_complete_workflow
============================================================
✅ 端到端验证测试通过！
============================================================
验证项目:
  ✅ Agent执行和Trace记录
  ✅ 数据存储到SQLite
  ✅ 统计信息计算
  ✅ 查询和筛选功能
  ✅ Dashboard集成
  ✅ Trace摘要生成
============================================================
PASSED
```

**验证点**:
- ✅ 完整工作流测试通过
- ✅ 6个验证项目全部通过

**状态**: ⬜ 通过 / ⬜ 失败

---

## 测试场景 3: Dashboard可视化验证

**目标**: 验证Dashboard能正确加载和显示数据

### 步骤 3.1: 启动Dashboard

```bash
cd /Users/yinaruto/MyProjects/ChatLLM/TigerHill

# 启动Dashboard
PYTHONPATH=. streamlit run tigerhill/web/dashboard/app.py
```

**预期输出**:
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

浏览器会自动打开 `http://localhost:8501`

**状态**: ⬜ 通过 / ⬜ 失败

---

### 步骤 3.2: 配置数据源

在Dashboard侧边栏：

1. **选择数据源类型**:
   - 点击 "SQLite Database"

2. **设置数据库路径**:
   - 输入: `./tigerhill_validation.db`
   - 点击 "Connect"

**预期结果**:
- ✅ 显示 "Connected to SQLite Database"
- ✅ 显示数据库路径

**验证截图位置**: 侧边栏顶部

**状态**: ⬜ 通过 / ⬜ 失败

---

### 步骤 3.3: 查看Traces列表

在主页面：

1. **Traces列表**:
   - 应该显示3个traces
   - 每个trace显示：Agent名称、状态、时长、事件数、成本等

2. **验证字段**:
   - ✅ Trace ID (前8位)
   - ✅ Agent Name: "validation-agent"
   - ✅ Status: "completed" (绿色标记)
   - ✅ Events: 7
   - ✅ LLM Calls: 6
   - ✅ Total Tokens: 900
   - ✅ Cost: ~$0.027

**预期显示**:
```
📊 Traces Overview
Total Traces: 3

[表格显示3个traces，包含所有字段]
```

**状态**: ⬜ 通过 / ⬜ 失败

---

### 步骤 3.4: 查看Trace详情

点击第一个Trace的 "View Details"：

**预期显示**:

1. **Trace信息卡片**:
   - Trace ID
   - Agent Name
   - Status
   - Duration
   - Created At

2. **统计信息**:
   - Total Events: 7
   - LLM Calls: 6
   - Total Tokens: 900
   - Total Cost: $0.027

3. **Events时间线**:
   - 显示7个events
   - 每个event显示类型、时间戳
   - Prompt events显示内容预览
   - Response events显示内容预览

4. **Event详情展开器**:
   - 可以展开查看每个event的完整内容
   - 显示JSON格式的数据

**验证点**:
- ✅ 所有统计数字正确
- ✅ Events按时间顺序排列
- ✅ 可以展开查看详情
- ✅ JSON格式正确

**状态**: ⬜ 通过 / ⬜ 失败

---

### 步骤 3.5: 使用筛选功能

在侧边栏设置筛选条件：

1. **Agent筛选**:
   - 选择 "validation-agent"
   - 验证只显示该Agent的traces

2. **状态筛选**:
   - 选择 "completed"
   - 验证只显示完成的traces

3. **成本范围**:
   - Min Cost: 0.02
   - Max Cost: 0.03
   - 验证只显示符合成本范围的traces

**预期结果**:
- ✅ 筛选后显示3个traces（因为都符合条件）
- ✅ 筛选条件可以组合使用

**状态**: ⬜ 通过 / ⬜ 失败

---

## 测试场景 4: Observer SDK验证（使用Gemini CLI）

**目标**: 验证Observer SDK能拦截和捕获真实的LLM交互

### 前置条件

```bash
# 1. 确认有Gemini API密钥
echo $GOOGLE_API_KEY

# 2. 确认gemini-cli已安装（如果没有，跳过此场景）
which gemini-cli || npm install -g @google/generative-ai

# 3. 创建拦截器测试目录
mkdir -p /Users/yinaruto/MyProjects/ChatLLM/TigerHill/prompt_captures/manual_test
```

### 步骤 4.1: 配置Gemini拦截器

创建测试脚本：

```bash
cat > /tmp/test_gemini_interception.sh << 'EOF'
#!/bin/bash

# 设置环境变量
export TIGERHILL_CAPTURE_PATH="/Users/yinaruto/MyProjects/ChatLLM/TigerHill/prompt_captures/manual_test"
export NODE_OPTIONS="--require /Users/yinaruto/MyProjects/ChatLLM/TigerHill/tigerhill/observer/gemini_http_interceptor.cjs"

echo "🎯 TigerHill Gemini拦截测试"
echo "================================"
echo "捕获路径: $TIGERHILL_CAPTURE_PATH"
echo ""

# 清空之前的捕获
rm -f $TIGERHILL_CAPTURE_PATH/*.jsonl

# 执行gemini-cli命令
echo "执行: gemini-cli 'What is 2+2?'"
echo ""

gemini-cli "What is 2+2?" || echo "如果gemini-cli未安装，请使用: npm install -g @google/generative-ai"

echo ""
echo "================================"
echo "✅ 测试完成"
echo ""
echo "检查捕获文件:"
ls -lh $TIGERHILL_CAPTURE_PATH/*.jsonl 2>/dev/null || echo "❌ 未找到捕获文件"
EOF

chmod +x /tmp/test_gemini_interception.sh
/tmp/test_gemini_interception.sh
```

**预期输出**:
```
🎯 TigerHill Gemini拦截测试
================================
捕获路径: /Users/yinaruto/MyProjects/ChatLLM/TigerHill/prompt_captures/manual_test

执行: gemini-cli 'What is 2+2?'

[Gemini的响应: 2+2等于4的解释]

================================
✅ 测试完成

检查捕获文件:
-rw-r--r--  1 user  staff  xxx bytes  gemini_session_xxxxx.jsonl
```

**验证点**:
- ✅ Gemini命令执行成功
- ✅ 生成了.jsonl捕获文件
- ✅ 文件大小>0

**状态**: ⬜ 通过 / ⬜ 失败 / ⬜ 跳过（无gemini-cli）

---

### 步骤 4.2: 查看捕获的数据

```bash
# 查看捕获文件
cat /Users/yinaruto/MyProjects/ChatLLM/TigerHill/prompt_captures/manual_test/*.jsonl | python -m json.tool
```

**预期输出**:
```json
{
  "timestamp": "2025-01-04T12:00:00.000Z",
  "type": "gemini_request",
  "session_id": "xxxxx",
  "model": "gemini-pro",
  "prompt": "What is 2+2?",
  "request": {
    "contents": [
      {
        "parts": [
          {
            "text": "What is 2+2?"
          }
        ]
      }
    ]
  }
}
{
  "timestamp": "2025-01-04T12:00:01.000Z",
  "type": "gemini_response",
  "session_id": "xxxxx",
  "response": {
    "candidates": [...]
  }
}
```

**验证点**:
- ✅ JSON格式正确
- ✅ 包含请求和响应
- ✅ prompt内容正确
- ✅ session_id一致

**状态**: ⬜ 通过 / ⬜ 失败

---

### 步骤 4.3: 将捕获数据导入数据库

```bash
# 使用capture迁移工具导入（支持capture_*.json格式）
python scripts/migrate_captures_to_db.py \
  -s ./prompt_captures/manual_test \
  -d ./tigerhill_gemini_test.db

# 如果要查看详细进度
python scripts/migrate_captures_to_db.py \
  -s ./prompt_captures/manual_test \
  -d ./tigerhill_gemini_test.db \
  -v
```

**预期输出**:
```
============================================================
TigerHill Capture数据迁移工具
============================================================
源目录: /Users/yinaruto/MyProjects/ChatLLM/TigerHill/prompt_captures/manual_test
目标数据库: ./tigerhill_gemini_test.db
增量迁移: 是
详细日志: 否
============================================================

开始迁移 1 个文件...

进度: 1/1 | 成功: 1 | 跳过: 0 | 失败: 0

============================================================

迁移统计:
  总文件数: 1
  处理成功: 1
  已存在跳过: 0
  处理失败: 0
  插入traces: 1
  插入events: 2

============================================================
```

**验证数据**:
```bash
# 查询导入的数据
sqlite3 ./tigerhill_gemini_test.db \
  "SELECT COUNT(*) as traces FROM traces; \
   SELECT COUNT(*) as events FROM events; \
   SELECT agent_name, status, total_events FROM traces LIMIT 5;"
```

**验证点**:
- ✅ 成功导入数据库
- ✅ Events数量正确
- ✅ Traces状态为completed

**状态**: ⬜ 通过 / ⬜ 失败 / ⬜ 跳过

---

**支持的文件格式**:
- `capture_*.json` - PromptCapture生成的格式
- `trace_*.json` - TraceStore生成的格式
- `gemini_session_*.jsonl` - Gemini session格式

**批量迁移示例**:
```bash
# 迁移整个prompt_captures目录
python scripts/migrate_captures_to_db.py \
  -s ./prompt_captures \
  -d ./all_captures.db

# 迁移swarm_agent目录
python scripts/migrate_captures_to_db.py \
  -s ./prompt_captures/swarm_agent \
  -d ./swarm.db \
  -v
```

---

## 测试场景 5: 完整集成测试

**目标**: 串联所有功能，完成完整的测试流程

### 步骤 5.1: 使用模板生成集成测试

```bash
# 使用集成测试模板
PYTHONPATH=. python -m tigerhill.template_engine.cli --template integration-e2e --output /tmp/integration_test
```

按提示输入：
- Agent Name: `full-integration-test`
- Workflow Name: `Complete TigerHill Validation`
- Number of Steps: `5`
- Use Database: `y`

**预期结果**:
- 生成测试文件到 `/tmp/integration_test/`

**状态**: ⬜ 通过 / ⬜ 失败

---

### 步骤 5.2: 运行生成的集成测试

```bash
cd /tmp/integration_test

# 安装依赖
pip install -r requirements.txt

# 运行测试
pytest test_full-integration-test.py -v -s
```

**预期输出**:
```
test_full_integration_test.py::TestFullIntegrationTest::test_full_integration_test

🚀 Starting workflow: Complete TigerHill Validation
  ✅ Step 1 completed
  ✅ Step 2 completed
  ✅ Step 3 completed
  ✅ Step 4 completed
  ✅ Step 5 completed

✅ Workflow completed: Complete TigerHill Validation

Trace Summary:
  Total Events: 10
  Status: completed

PASSED
```

**验证点**:
- ✅ 测试通过
- ✅ 所有步骤完成
- ✅ Trace正确记录

**状态**: ⬜ 通过 / ⬜ 失败

---

## 测试结果汇总

### 测试场景统计

| 场景 | 测试项 | 通过 | 失败 | 跳过 | 状态 |
|------|--------|------|------|------|------|
| 场景1: 模板库 | 3 | ___ | ___ | ___ | ⬜ |
| 场景2: SQLite数据库 | 3 | ___ | ___ | ___ | ⬜ |
| 场景3: Dashboard | 5 | ___ | ___ | ___ | ⬜ |
| 场景4: Observer SDK | 3 | ___ | ___ | ___ | ⬜ |
| 场景5: 集成测试 | 2 | ___ | ___ | ___ | ⬜ |
| **总计** | **16** | ___ | ___ | ___ | ⬜ |

### 详细测试结果

**场景1: 模板库功能**
- [ ] 1.1 列出模板
- [ ] 1.2 生成LLM测试
- [ ] 1.3 交互式生成（可选）

**场景2: SQLite数据库**
- [ ] 2.1 运行演示Agent
- [ ] 2.2 验证数据库内容
- [ ] 2.3 自动化测试

**场景3: Dashboard可视化**
- [ ] 3.1 启动Dashboard
- [ ] 3.2 配置数据源
- [ ] 3.3 查看Traces列表
- [ ] 3.4 查看Trace详情
- [ ] 3.5 使用筛选功能

**场景4: Observer SDK**
- [ ] 4.1 配置拦截器
- [ ] 4.2 查看捕获数据
- [ ] 4.3 导入数据库（可选）

**场景5: 集成测试**
- [ ] 5.1 生成集成测试
- [ ] 5.2 运行集成测试

---

## 问题记录

如果测试过程中遇到问题，请在此记录：

### 问题1
- **场景**: _______________
- **步骤**: _______________
- **问题描述**: _______________
- **错误信息**: _______________
- **解决方案**: _______________

### 问题2
- **场景**: _______________
- **步骤**: _______________
- **问题描述**: _______________
- **错误信息**: _______________
- **解决方案**: _______________

---

## 测试总结

### 通过标准

- ✅ **完全通过**: 所有场景的所有必选测试项通过
- ⚠️ **基本通过**: 核心功能测试通过，可选功能可跳过
- ❌ **未通过**: 核心功能存在失败项

### 测试人员签名

- **测试人员**: _______________
- **测试日期**: _______________
- **测试环境**: _______________
- **测试结果**: ⬜ 完全通过 / ⬜ 基本通过 / ⬜ 未通过

### 备注

_______________________________________________
_______________________________________________
_______________________________________________

---

## 附录：常见问题解决

### Q1: Dashboard无法启动

```bash
# 检查streamlit是否安装
pip install streamlit

# 检查端口是否被占用
lsof -i :8501

# 使用其他端口
streamlit run tigerhill/web/dashboard/app.py --server.port 8502
```

### Q2: 数据库文件不存在

```bash
# 确认文件路径
ls -l ./tigerhill_validation.db

# 重新运行演示脚本
PYTHONPATH=. python examples/demo_agent_with_tracing.py
```

### Q3: 模板生成失败

```bash
# 检查依赖
pip install jinja2 pyyaml

# 查看详细错误
PYTHONPATH=. python -m tigerhill.template_engine.cli --template http-api-test -v
```

### Q4: Observer拦截器不工作

```bash
# 检查Node.js版本
node --version  # 需要 v14+

# 检查环境变量
echo $NODE_OPTIONS
echo $TIGERHILL_CAPTURE_PATH

# 检查拦截器文件
ls -l tigerhill/observer/gemini_http_interceptor.cjs
```

---

**文档版本**: 1.0
**最后更新**: 2025-01-04
**维护者**: TigerHill Team

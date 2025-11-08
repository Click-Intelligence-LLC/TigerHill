# 🤖 TigerHill与AI Coding工具完整集成指南

本指南介绍如何将TigerHill与各种AI coding工具（Claude Code、Cursor、GitHub Copilot等）深度集成。

## 📋 目录

1. [Claude Code集成](#1-claude-code集成)
2. [Cursor集成](#2-cursor集成)
3. [GitHub Copilot集成](#3-github-copilot集成)
4. [VSCode通用集成](#4-vscode通用集成)
5. [最佳实践](#5-最佳实践)
6. [实战示例](#6-实战示例)

---

## 1. Claude Code集成

### 1.1 自定义Slash Commands ⭐ 推荐

Claude Code项目中已包含以下自定义命令：

#### 可用命令

```bash
/generate-test      # 生成单个测试
/batch-generate     # 批量生成测试
/show-templates     # 查看可用模板
```

#### 使用示例

**场景1：快速生成API测试**
```
You: /generate-test

Claude: 我将帮你生成测试。请选择模板类型：
1. HTTP API Test (单个端点)
2. REST CRUD Test (完整CRUD)
3. LLM Prompt-Response Test
...

You: 1

Claude: 好的，请提供参数：
- Agent名称：
- API URL：
- HTTP方法 (GET/POST/PUT/DELETE)：
- 期望状态码：

You: user-api, http://localhost:3000/users, GET, 200

Claude: 正在生成测试...
[执行命令]
python -m tigerhill.template_engine.cli \
  -t http/http-api-test \
  -p agent_name=user-api \
  -p api_url=http://localhost:3000/users \
  -p http_method=GET \
  -p expected_status=200 \
  -o ./tests/api

✅ 已生成以下文件：
- tests/api/test_user-api.py
- tests/api/requirements.txt
- tests/api/README.md

下一步：
1. cd tests/api
2. pip install -r requirements.txt
3. pytest -v
```

**场景2：批量生成**
```
You: /batch-generate

Claude: 你想生成哪种类型的测试套件？
1. API测试套件 (多个端点)
2. LLM Agent测试
3. 混合测试套件

You: 1 - 为用户管理API生成完整测试

Claude: 我将创建配置文件...
[创建 tests/config/user_api_tests.yaml]
[显示配置内容]

是否执行生成？(Y/n)

You: Y

Claude: [执行批量生成]
✅ 成功生成4个测试模块
```

### 1.2 项目规则文件

项目已包含 `docs/AI_CODING_INTEGRATION.md`，Claude Code会自动读取这些规则：

**关键规则**：
- ✅ 优先使用TigerHill模板，不要手写测试代码
- ✅ 批量测试使用YAML配置
- ✅ 使用shared_params减少重复
- ✅ 遵循命名规范

### 1.3 快速提示词

直接对Claude说：

```
"使用TigerHill为我的REST API生成测试"
"创建一个批量测试配置，包含users和posts的CRUD测试"
"生成LLM对话Agent的测试，需要3轮对话"
"帮我创建一个配置文件来测试所有API端点"
```

---

## 2. Cursor集成

### 2.1 .cursorrules文件

项目根目录已包含 `.cursorrules` 文件，Cursor会自动加载。

**包含内容**：
- 项目概览
- 可用模板列表
- 生成方法优先级
- 代码风格指南
- 测试命令
- 最佳实践

### 2.2 使用方式

在Cursor中，直接使用自然语言：

```
"为 /api/users 端点创建GET测试"
"生成完整的用户CRUD测试"
"创建一个配置文件，包含所有API测试"
```

Cursor会根据.cursorrules自动：
1. 识别需要使用TigerHill模板
2. 选择正确的模板
3. 生成命令或YAML配置
4. 执行生成

### 2.3 Cursor Composer集成

在Composer中描述需求：

```
@workspace 为项目生成API测试套件

要求：
- 测试所有user和post端点
- 使用批量配置
- 组织在tests/api目录下
```

Cursor会：
1. 扫描.cursorrules
2. 创建YAML配置
3. 执行TigerHill命令
4. 显示生成结果

---

## 3. GitHub Copilot集成

### 3.1 代码注释触发

在YAML文件中使用注释触发Copilot：

```yaml
# TigerHill batch config for user API tests
output_base: ./tests/api
shared_params:
  base_url: http://localhost:3000

templates:
  # TODO: Copilot, add GET /api/users test
```

Copilot会自动建议：
```yaml
  - template: http/http-api-test
    output: users
    params:
      agent_name: user-list
      api_url: ${base_url}/api/users
      http_method: GET
      expected_status: 200
```

### 3.2 GitHub Copilot Chat

在Chat中询问：

```
@workspace How do I generate tests for my API using TigerHill?

Copilot: Based on your project, you can use TigerHill templates...
[提供详细步骤和示例]
```

### 3.3 GitHub Actions集成

项目包含 `.github/workflows/generate-and-test.yml.example`

**功能**：
- 配置文件变更自动触发
- 自动生成测试
- 运行测试
- 上传覆盖率报告

**使用**：
```bash
# 重命名示例文件
mv .github/workflows/generate-and-test.yml.example \
   .github/workflows/generate-and-test.yml

# 提交配置文件
git add tests/config/api_tests.yaml
git commit -m "Add API test config"
git push

# GitHub Actions自动触发
```

---

## 4. VSCode通用集成

### 4.1 Code Snippets

项目包含 `.vscode/tigerhill.code-snippets`

**可用Snippets**：

| 前缀 | 描述 | 输出 |
|------|------|------|
| `th-config-single` | 单模板配置 | YAML配置骨架 |
| `th-config-batch` | 批量配置 | 批量YAML配置 |
| `th-http-api` | HTTP API测试 | HTTP测试配置 |
| `th-rest-crud` | REST CRUD | CRUD测试配置 |
| `th-llm-prompt` | LLM单轮 | LLM测试配置 |
| `th-llm-multiturn` | LLM多轮 | 对话测试配置 |
| `th-cli-basic` | CLI测试 | CLI测试配置 |
| `th-generate` | 生成命令 | CLI生成命令 |
| `th-generate-config` | 配置生成 | 配置文件生成命令 |

**使用方法**：

1. 创建新的YAML文件
2. 输入snippet前缀（如 `th-config-batch`）
3. 按Tab键展开
4. 填写参数（Tab键跳转）

**示例**：
```yaml
# 输入: th-http-api [Tab]
# 自动生成：
- template: http/http-api-test
  output: api
  params:
    agent_name: [cursor here]
    api_url: http://localhost:3000/api/endpoint
    http_method: GET
    expected_status: 200
    validate_response: true
```

### 4.2 VSCode Tasks

项目包含 `.vscode/tasks.json`

**可用任务**：

按 `Cmd/Ctrl + Shift + P`，输入 "Tasks: Run Task"：

| 任务名 | 功能 | 快捷键提示 |
|--------|------|-----------|
| TigerHill: List Templates | 列出所有模板 | - |
| TigerHill: Generate from Config | 从配置生成 | - |
| TigerHill: Generate Single Test | 生成单个测试 | - |
| TigerHill: Run Generated Tests | 运行生成的测试 | Cmd/Ctrl+Shift+B |
| TigerHill: Run All Template Tests | 运行所有模板测试 | - |

**使用示例**：
1. `Cmd/Ctrl + Shift + P`
2. 输入 "Run Task"
3. 选择 "TigerHill: Generate from Config"
4. 输入配置文件路径
5. 自动执行生成

### 4.3 Launch Configuration

添加到 `.vscode/launch.json`：

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "TigerHill: Generate Tests (Debug)",
      "type": "python",
      "request": "launch",
      "module": "tigerhill.template_engine.cli",
      "args": [
        "--config",
        "${input:configFile}"
      ],
      "console": "integratedTerminal"
    },
    {
      "name": "TigerHill: Run Generated Tests",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": [
        "tests/",
        "-v",
        "-s"
      ],
      "console": "integratedTerminal"
    }
  ],
  "inputs": [
    {
      "id": "configFile",
      "type": "promptString",
      "description": "Config file path",
      "default": "tests/config/test_suite.yaml"
    }
  ]
}
```

---

## 5. 最佳实践

### 5.1 项目结构

推荐的目录结构：

```
project/
├── .claude/
│   └── commands/           # Claude slash commands
├── .vscode/
│   ├── tigerhill.code-snippets
│   ├── tasks.json
│   └── launch.json
├── .cursorrules            # Cursor规则
├── tests/
│   ├── config/
│   │   ├── api_tests.yaml      # API测试配置
│   │   ├── llm_tests.yaml      # LLM测试配置
│   │   └── integration_tests.yaml
│   ├── api/                    # 生成的API测试
│   ├── llm/                    # 生成的LLM测试
│   └── integration/            # 生成的集成测试
├── docs/
│   ├── AI_CODING_INTEGRATION.md
│   └── TEMPLATE_AUTO_GENERATION_GUIDE.md
└── .github/
    └── workflows/
        └── generate-and-test.yml
```

### 5.2 配置文件管理

**版本控制**：
```bash
# 纳入版本控制
git add tests/config/*.yaml
git add .claude/commands/
git add .cursorrules
git add .vscode/tigerhill.code-snippets

# 不纳入版本控制（个人配置）
echo ".vscode/settings.json" >> .gitignore
```

**命名规范**：
- `<feature>_tests.yaml` - 功能测试配置
- `<environment>_config.yaml` - 环境配置
- `ci_tests.yaml` - CI专用配置

### 5.3 AI工具使用优先级

| 场景 | 推荐工具 | 理由 |
|------|---------|------|
| 探索项目 | Cursor/Claude Code | 理解项目结构 |
| 创建配置 | Claude Code | 交互式指导 |
| 编写配置 | VSCode Snippets | 快速输入 |
| 批量生成 | CLI/YAML | 自动化 |
| CI/CD | GitHub Actions | 持续集成 |
| Debug | Claude Code | 错误分析 |

### 5.4 团队协作

**分享配置**：
```bash
# 团队成员克隆后立即可用
git clone <repo>
cd <repo>

# 配置文件已就绪
ls tests/config/

# AI工具规则已就绪
ls .claude/commands/
ls .cursorrules
```

**文档更新**：
```bash
# 添加新模板时
1. 更新 .cursorrules
2. 更新 .claude/commands/
3. 添加example config
4. 提交并通知团队
```

---

## 6. 实战示例

### 示例1：快速原型

**场景**：新项目，需要快速搭建测试框架

**使用Claude Code**：

```
You: 我有一个新的REST API项目，需要快速搭建测试框架

Claude: 我会帮你：
1. 分析你的API endpoints
2. 创建批量测试配置
3. 生成测试代码
4. 设置GitHub Actions

你的API有哪些endpoints？

You:
- GET /api/users
- POST /api/users
- GET /api/users/:id
- PUT /api/users/:id
- DELETE /api/users/:id
- GET /api/posts
- POST /api/posts

Claude: [创建配置文件并生成测试]
```

### 示例2：CI/CD集成

**场景**：将测试生成集成到CI流程

**步骤**：

1. 使用Cursor创建配置文件：
```
You: @workspace 创建CI测试配置，包含所有API端点

Cursor: [生成 tests/config/ci_tests.yaml]
```

2. 复制GitHub Actions模板：
```bash
cp .github/workflows/generate-and-test.yml.example \
   .github/workflows/generate-and-test.yml
```

3. 提交并触发：
```bash
git add tests/config/ci_tests.yaml
git add .github/workflows/generate-and-test.yml
git commit -m "Add CI test generation"
git push
```

### 示例3：重构现有测试

**场景**：将手写测试迁移到TigerHill模板

**使用Claude Code**：

```
You: 我有一些手写的API测试，想迁移到TigerHill模板

Claude: 请分享你的测试代码，我会：
1. 分析测试覆盖的endpoint
2. 创建对应的配置文件
3. 用TigerHill重新生成
4. 对比差异

You: [粘贴测试代码]

Claude:
我识别到以下测试：
- User GET endpoint
- User POST endpoint
- User CRUD operations

我将创建配置文件...
[创建并生成]

对比：
✅ 所有测试用例都已覆盖
✅ 新增了trace tracking
✅ 新增了成本追踪（LLM测试）
```

### 示例4：Debug测试失败

**场景**：生成的测试失败，需要调试

**使用Claude Code**：

```
You: 生成的测试失败了，错误信息：[粘贴错误]

Claude: 让我分析错误...

问题：API URL不正确
解决方案：
1. 更新配置文件中的base_url
2. 重新生成测试

是否自动修复？

You: 是

Claude: [更新配置并重新生成]
✅ 已更新并重新生成
✅ 测试现在应该通过
```

---

## 📚 参考资料

### 文档
- [模板自动生成指南](./TEMPLATE_AUTO_GENERATION_GUIDE.md)
- [模板参考](../templates/)
- [示例配置](../examples/template_configs/)

### 配置文件
- `.claude/commands/` - Claude Code命令
- `.cursorrules` - Cursor规则
- `.vscode/tigerhill.code-snippets` - VSCode snippets
- `.vscode/tasks.json` - VSCode任务
- `.github/workflows/` - GitHub Actions

### 命令速查
```bash
# 列出模板
python -m tigerhill.template_engine.cli --list

# 单个测试
python -m tigerhill.template_engine.cli -t <template> -p key=value

# 批量测试
python -m tigerhill.template_engine.cli --config <config.yaml>

# 运行测试
pytest tests/ -v
```

---

## 🎯 下一步

1. **尝试slash commands**：
   - 在Claude Code中运行 `/generate-test`
   - 体验交互式生成流程

2. **创建配置文件**：
   - 使用VSCode snippets快速创建
   - 尝试变量替换功能

3. **设置CI/CD**：
   - 启用GitHub Actions
   - 自动化测试生成

4. **团队分享**：
   - 提交配置文件到Git
   - 分享最佳实践

---

**有问题？**

- 查看 [完整文档](./TEMPLATE_AUTO_GENERATION_GUIDE.md)
- 运行 `/show-templates` 查看可用模板
- 提交 [Issue](https://github.com/yourusername/tigerhill/issues)

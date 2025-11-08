# TigerHill模板自动生成指南

本指南介绍如何使用TigerHill的模板引擎自动生成测试脚本，无需手动编写代码。

## 📖 目录

- [快速开始](#快速开始)
- [使用方式](#使用方式)
  - [方式1：命令行参数](#方式1命令行参数)
  - [方式2：环境变量](#方式2环境变量)
  - [方式3：配置文件（推荐）](#方式3配置文件推荐)
- [配置文件详解](#配置文件详解)
- [实际场景示例](#实际场景示例)
- [最佳实践](#最佳实践)

---

## 快速开始

### 1. 查看可用模板

```bash
python -m tigerhill.template_engine.cli --list
```

### 2. 生成第一个测试

```bash
python -m tigerhill.template_engine.cli \
  --template http/http-api-test \
  --param agent_name=my-api \
  --param api_url=http://localhost:3000 \
  --param http_method=GET \
  --param expected_status=200 \
  --param validate_response=true \
  --output ./tests
```

### 3. 查看生成的文件

```bash
cd tests
ls -la
# test_my-api.py
# requirements.txt
# README.md
```

---

## 使用方式

TigerHill支持三种使用方式，适应不同场景。

### 方式1：命令行参数

**适用场景**：快速生成单个测试

```bash
python -m tigerhill.template_engine.cli \
  -t http/http-api-test \
  -p agent_name=user-api \
  -p api_url=http://localhost:3000/users \
  -p http_method=GET \
  -o ./tests/api
```

**优点**：
- ✅ 快速，一行命令
- ✅ 适合临时生成
- ✅ 易于脚本化

**缺点**：
- ❌ 参数多时命令很长
- ❌ 难以重复使用
- ❌ 不能版本控制

---

### 方式2：环境变量

**适用场景**：CI/CD环境，参数来自环境

```bash
# 设置环境变量
export TIGERHILL_AGENT_NAME=user-api
export TIGERHILL_API_URL=http://localhost:3000/users
export TIGERHILL_HTTP_METHOD=GET
export TIGERHILL_EXPECTED_STATUS=200
export TIGERHILL_VALIDATE_RESPONSE=true

# 生成测试
python -m tigerhill.template_engine.cli \
  --template http/http-api-test \
  --output ./tests/api
```

**环境变量命名规则**：`TIGERHILL_<参数名大写>`

**优点**：
- ✅ 适合CI/CD
- ✅ 参数可以来自环境
- ✅ 命令行更简洁

**缺点**：
- ❌ 需要设置多个环境变量
- ❌ 不直观

**参数优先级**：命令行 > 环境变量 > 默认值

```bash
# 环境变量设置为8080
export TIGERHILL_API_URL=http://localhost:8080

# 命令行覆盖为9000（最终使用9000）
python -m tigerhill.template_engine.cli \
  -t http/http-api-test \
  -p api_url=http://localhost:9000
```

---

### 方式3：配置文件（推荐）

**适用场景**：批量生成、可重复使用、团队协作

#### 单模板配置

`config/api_test.yaml`:
```yaml
template: http/http-api-test
output: ./tests/api

params:
  agent_name: user-api
  api_url: http://localhost:3000/users
  http_method: GET
  expected_status: 200
  validate_response: true
```

使用：
```bash
python -m tigerhill.template_engine.cli --config config/api_test.yaml
```

#### 批量模板配置

`config/test_suite.yaml`:
```yaml
output_base: ./tests

# 共享参数（用于变量替换）
shared_params:
  base_url: http://localhost:3000
  timeout: 30

# 多个模板
templates:
  # User API GET
  - template: http/http-api-test
    output: api/users
    params:
      agent_name: user-get
      api_url: ${base_url}/users  # 使用共享参数
      http_method: GET
      expected_status: 200
      validate_response: true

  # User API POST
  - template: http/http-api-test
    output: api/users
    params:
      agent_name: user-post
      api_url: ${base_url}/users
      http_method: POST
      expected_status: 201
      request_body: '{"name": "test"}'

  # Posts CRUD
  - template: http/http-rest-crud
    output: api/posts
    params:
      agent_name: post-crud
      base_url: ${base_url}
      resource_path: /posts
      resource_name: post
```

使用：
```bash
# 生成所有测试
python -m tigerhill.template_engine.cli --config config/test_suite.yaml

# 强制覆盖已存在文件
python -m tigerhill.template_engine.cli --config config/test_suite.yaml --force
```

**优点**：
- ✅ 可重复使用
- ✅ 可版本控制（Git）
- ✅ 团队共享
- ✅ 支持批量生成
- ✅ 支持变量替换
- ✅ 配置清晰易读

---

## 配置文件详解

### 单模板配置结构

```yaml
# 模板名称或路径
template: <template-name>

# 输出目录
output: <output-directory>

# 参数
params:
  <param-name>: <param-value>
  ...
```

### 批量配置结构

```yaml
# 基础输出目录
output_base: <base-directory>

# 共享参数（用于变量替换）
shared_params:
  <var-name>: <var-value>
  ...

# 模板列表
templates:
  - template: <template-name>
    output: <relative-path>  # 相对于output_base
    params:
      <param-name>: <param-value>
      # 可使用 ${var-name} 引用shared_params

  - template: ...
    ...
```

### 变量替换

在params中可以使用 `${变量名}` 引用 shared_params：

```yaml
shared_params:
  base_url: http://localhost:3000
  api_version: v1

templates:
  - template: http/http-api-test
    params:
      api_url: ${base_url}/api/${api_version}/users
      # 结果: http://localhost:3000/api/v1/users
```

---

## 实际场景示例

### 场景1：测试REST API的所有端点

**需求**：为一个REST API的多个端点生成测试

**解决方案**：使用批量配置

`config/rest_api_tests.yaml`:
```yaml
output_base: ./tests/api

shared_params:
  base_url: http://localhost:3000
  expected_success: 200

templates:
  # Users endpoints
  - template: http/http-api-test
    output: users
    params:
      agent_name: users-list
      api_url: ${base_url}/api/users
      http_method: GET
      expected_status: ${expected_success}

  - template: http/http-api-test
    output: users
    params:
      agent_name: users-get-by-id
      api_url: ${base_url}/api/users/1
      http_method: GET
      expected_status: ${expected_success}

  # Posts endpoints
  - template: http/http-rest-crud
    output: posts
    params:
      agent_name: posts-crud
      base_url: ${base_url}
      resource_path: /api/posts
      resource_name: post
```

### 场景2：CI/CD集成

**需求**：在CI/CD pipeline中自动生成和运行测试

**解决方案**：

`.github/workflows/test.yml`:
```yaml
name: API Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.8'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Generate tests from config
        run: |
          python -m tigerhill.template_engine.cli \
            --config tests/config/ci_tests.yaml \
            --force

      - name: Run generated tests
        run: pytest tests/ -v
```

### 场景3：LLM Agent测试

**需求**：测试多个LLM Agent的不同能力

`config/llm_tests.yaml`:
```yaml
output_base: ./tests/llm

shared_params:
  model: gpt-4
  max_tokens: 1000

templates:
  # Code review
  - template: llm/llm-prompt-response
    output: code_review
    params:
      agent_name: code-reviewer
      model_name: ${model}
      prompt: "Review this code for bugs"
      max_tokens: ${max_tokens}
      validate_quality: true

  # Multi-turn conversation
  - template: llm/llm-multi-turn
    output: conversation
    params:
      agent_name: chatbot
      model_name: ${model}
      num_turns: 5
      validate_context: true

  # Cost tracking
  - template: llm/llm-cost-validation
    output: cost
    params:
      agent_name: content-gen
      model_name: gpt-3.5-turbo
      max_budget_usd: 0.50
      max_tokens_per_call: 500
```

---

## 最佳实践

### 1. 组织配置文件

推荐的目录结构：

```
project/
├── tests/
│   ├── config/
│   │   ├── api_tests.yaml        # API测试配置
│   │   ├── llm_tests.yaml        # LLM测试配置
│   │   └── integration_tests.yaml # 集成测试配置
│   ├── api/                       # 生成的API测试
│   ├── llm/                       # 生成的LLM测试
│   └── integration/               # 生成的集成测试
├── README.md
└── requirements.txt
```

### 2. 使用shared_params减少重复

❌ **不好**：
```yaml
templates:
  - template: http/http-api-test
    params:
      api_url: http://localhost:3000/users
  - template: http/http-api-test
    params:
      api_url: http://localhost:3000/posts  # 重复base_url
```

✅ **好**：
```yaml
shared_params:
  base_url: http://localhost:3000

templates:
  - template: http/http-api-test
    params:
      api_url: ${base_url}/users
  - template: http/http-api-test
    params:
      api_url: ${base_url}/posts
```

### 3. 版本控制配置文件

```bash
# 将配置文件纳入Git
git add tests/config/*.yaml
git commit -m "Add test generation configs"
```

**优势**：
- 团队共享配置
- 追踪配置变更
- 回滚到历史版本

### 4. 命名规范

- **配置文件**：`<功能>_tests.yaml`
- **Agent名称**：`<资源>-<操作>`，如 `user-get`, `post-create`
- **输出目录**：按功能分组，如 `api/users`, `llm/chatbot`

### 5. 使用--force谨慎

```bash
# 开发时：不使用--force，避免覆盖手动修改
python -m tigerhill.template_engine.cli --config config.yaml

# CI/CD：使用--force，确保是最新生成
python -m tigerhill.template_engine.cli --config config.yaml --force
```

### 6. 组合使用

可以结合命令行、环境变量和配置文件：

```bash
# 配置文件 + 环境变量覆盖
export TIGERHILL_BASE_URL=http://staging.example.com

python -m tigerhill.template_engine.cli --config config.yaml
```

---

## 常用命令速查

```bash
# 查看帮助
python -m tigerhill.template_engine.cli --help

# 列出所有模板
python -m tigerhill.template_engine.cli --list

# 单个测试（命令行）
python -m tigerhill.template_engine.cli -t <template> -p key=value -o <dir>

# 单个测试（环境变量）
export TIGERHILL_AGENT_NAME=test
python -m tigerhill.template_engine.cli -t <template> -o <dir>

# 批量测试（配置文件）
python -m tigerhill.template_engine.cli --config <config.yaml>

# 强制覆盖
python -m tigerhill.template_engine.cli --config <config.yaml> --force

# 指定模板目录
python -m tigerhill.template_engine.cli --templates-dir custom/templates -t <template>
```

---

## 故障排除

### 问题1：参数验证失败

**错误**：
```
❌ Validation errors:
  - expected_status: expected integer, got str
```

**原因**：参数类型不匹配

**解决**：
- 命令行：直接传数字 `-p expected_status=200`
- 配置文件：使用正确类型
  ```yaml
  params:
    expected_status: 200  # YAML会自动识别为整数
  ```

### 问题2：模板未找到

**错误**：
```
❌ Template not found: my-template
```

**解决**：
- 使用 `--list` 查看可用模板
- 使用完整路径：`http/http-api-test`（不需要.yaml后缀）

### 问题3：变量替换不起作用

**配置**：
```yaml
shared_params:
  url: http://localhost:3000

templates:
  - params:
      api_url: $url/users  # 错误：应该是 ${url}
```

**解决**：使用 `${var_name}` 语法

---

## 下一步

- 查看[模板参考文档](./TEMPLATE_REFERENCE.md)了解每个模板的详细参数
- 查看[示例配置](../examples/template_configs/)获取更多灵感
- 学习如何[自定义模板](./CUSTOM_TEMPLATES.md)

---

**需要帮助？**

- 查看 [FAQ](./FAQ.md)
- 提交 [Issue](https://github.com/yourusername/tigerhill/issues)
- 阅读 [完整文档](./README.md)

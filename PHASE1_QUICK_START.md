# Phase 1 快速开始指南

## 🎯 Phase 1 解决的问题

**之前的问题**:
- ❌ 无法捕获系统prompt（Python wrapper缺失该功能）
- ❌ 对话历史结构不清晰（只有原始数组）
- ❌ 多轮对话请求无法关联
- ❌ gemini-cli会话追踪不完整

**Phase 1 的解决方案**:
- ✅ 支持从Gemini、OpenAI、Anthropic等格式提取系统prompt
- ✅ 结构化对话历史（角色、轮次、token统计）
- ✅ conversation_id和turn_number关联多轮请求
- ✅ 完整的会话追踪和导出功能

---

## 📦 核心功能

### 1. 系统Prompt提取（跨agent支持）

```python
from tigerhill.observer.conversation_models import SystemPromptExtractor

# Gemini格式
gemini_kwargs = {
    'system_instruction': "You are a helpful assistant."
}
system_prompt = SystemPromptExtractor.extract_from_kwargs(gemini_kwargs)

# OpenAI格式
openai_kwargs = {
    'messages': [
        {'role': 'system', 'content': 'You are an expert.'},
        {'role': 'user', 'content': 'Hello'}
    ]
}
system_prompt = SystemPromptExtractor.extract_from_kwargs(openai_kwargs)

# Anthropic格式
anthropic_kwargs = {
    'system': 'You are Claude, an AI assistant.'
}
system_prompt = SystemPromptExtractor.extract_from_kwargs(anthropic_kwargs)
```

### 2. 多轮对话追踪

```python
from tigerhill.observer import PromptCapture

capture = PromptCapture(storage_path="./prompt_captures")
capture_id = capture.start_capture("my_agent")

conversation_id = "conv_001"

# Turn 1
request_id_1 = capture.capture_request(
    capture_id,
    {
        "model": "gemini-2.0-flash-exp",
        "prompt": "What is Python?",
        "system_prompt": "You are a programming tutor."
    },
    conversation_id=conversation_id,
    turn_number=1
)

capture.capture_response(
    capture_id,
    {
        "text": "Python is a high-level programming language.",
        "usage": {"prompt_tokens": 20, "completion_tokens": 15, "total_tokens": 35}
    },
    request_id=request_id_1
)

# Turn 2
request_id_2 = capture.capture_request(
    capture_id,
    {
        "model": "gemini-2.0-flash-exp",
        "prompt": "Tell me more"
    },
    conversation_id=conversation_id,
    turn_number=2
)

capture.capture_response(
    capture_id,
    {"text": "Python was created by Guido van Rossum."},
    request_id=request_id_2
)

# 获取完整对话历史
conv = capture.get_conversation_history(conversation_id)
print(f"Total turns: {conv.total_turns}")
print(f"Total messages: {len(conv.messages)}")
print(f"System prompt: {conv.system_prompt}")
print(f"Total tokens: {conv.total_tokens}")
```

### 3. 对话结构查询

```python
# 列出所有对话
conversations = capture.list_conversations()
for conv in conversations:
    print(f"对话ID: {conv['conversation_id']}")
    print(f"轮次数: {conv['total_turns']}")
    print(f"消息数: {conv['message_count']}")

# 获取对话摘要
summary = capture.get_conversation_summary(conversation_id)
print(summary)

# 导出对话历史为JSON
capture.export_conversation(conversation_id, "./conversation.json")
```

### 4. 对话历史数据模型

```python
from tigerhill.observer.conversation_models import ConversationHistory

conv = ConversationHistory(
    conversation_id="test_conv",
    agent_name="my_agent"
)

# 添加系统消息
conv.add_system_message("You are helpful.")

# 添加用户消息（自动创建新turn）
conv.add_user_message("Hello", turn_number=1)

# 添加助手回复
conv.add_assistant_message(
    "Hi there!",
    turn_number=1,
    tokens_used={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
)

# 查询消息
turn1_messages = conv.get_messages_by_turn(1)
user_messages = conv.get_messages_by_role("user")

# 导出为字典
data = conv.to_dict()
```

---

## 🚀 使用场景

### 场景1: gemini-cli多轮对话捕获

使用增强的session interceptor自动捕获gemini-cli的对话：

```bash
# 设置环境变量
export TIGERHILL_CAPTURE_PATH="/path/to/captures"

# 运行gemini-cli时使用interceptor
NODE_OPTIONS="--require /path/to/tigerhill/observer/gemini_session_interceptor.cjs" \
gemini-cli chat
```

Interceptor会自动：
- ✅ 提取并存储系统prompt
- ✅ 追踪每一轮的user和assistant消息
- ✅ 记录消息角色和turn_number
- ✅ 统计token使用
- ✅ 生成结构化的conversation_history

### 场景2: Python SDK直接使用

```python
from tigerhill.observer import wrap_gemini_model
import google.generativeai as genai

# 配置Gemini
genai.configure(api_key="your-api-key")

# 包装模型
model = genai.GenerativeModel('gemini-2.0-flash-exp')
wrapped_model = wrap_gemini_model(
    model,
    capture_path="./prompt_captures",
    agent_name="my_gemini_app"
)

# 使用时会自动捕获system prompt和对话历史
response = wrapped_model.generate_content(
    "What is Python?",
    system_instruction="You are a programming tutor."
)
```

### 场景3: 跨agent对话分析

```python
# 支持分析多个agent的对话
agents = ["gemini-cli", "openai-assistant", "claude-api"]

for agent in agents:
    conversations = capture.list_conversations()
    for conv in conversations:
        if conv['agent_name'] == agent:
            # 分析该agent的对话质量
            history = capture.get_conversation_history(conv['conversation_id'])
            print(f"{agent} - 平均每轮token: {history.total_tokens['total_tokens'] / history.total_turns}")
```

---

## 📊 导出的JSON格式

导出的对话历史包含完整信息：

```json
{
  "conversation_id": "conv_001",
  "agent_name": "gemini-cli",
  "system_prompt": "You are a programming tutor.",
  "total_turns": 3,
  "message_count": 7,
  "started_at": 1762419130.351877,
  "total_tokens": {
    "prompt_tokens": 75,
    "completion_tokens": 110,
    "total_tokens": 185
  },
  "messages": [
    {
      "role": "system",
      "content": "You are a programming tutor.",
      "turn": 0,
      "index": 0,
      "timestamp": 1762419130.351904
    },
    {
      "role": "user",
      "content": "What is Python?",
      "turn": 1,
      "index": 1,
      "timestamp": 1762419130.351909,
      "metadata": {
        "model": "gemini-2.0-flash-exp",
        "request_id": "uuid-here"
      }
    },
    {
      "role": "assistant",
      "content": "Python is a programming language.",
      "turn": 1,
      "index": 2,
      "timestamp": 1762419130.351936
    }
  ],
  "turns": [
    {
      "turn_number": 1,
      "user_content": "What is Python?",
      "assistant_content": "Python is a programming language.",
      "duration": 0.000028,
      "tokens_used": {
        "prompt_tokens": 20,
        "completion_tokens": 15,
        "total_tokens": 35
      }
    }
  ]
}
```

---

## ✅ 兼容性矩阵

| Agent类型 | 系统Prompt提取 | 对话历史 | Token统计 | 状态 |
|----------|--------------|---------|---------|------|
| **Gemini (Python SDK)** | ✅ system_instruction | ✅ | ✅ | 完全支持 |
| **Gemini CLI** | ✅ 自动捕获 | ✅ | ✅ | 完全支持 |
| **OpenAI** | ✅ messages[role=system] | ✅ | ✅ | 完全支持 |
| **Anthropic** | ✅ system参数 | ✅ | ✅ | 完全支持 |
| **其他HTTP Agent** | ✅ 通用格式 | ✅ | ✅ | 兼容支持 |

---

## 🧪 运行测试

```bash
# 单元测试（18个测试）
PYTHONPATH=. pytest tests/test_observer_phase1_enhancements.py -v

# 集成测试（3个测试）
PYTHONPATH=. pytest tests/test_phase1_integration.py -v

# 运行演示示例
PYTHONPATH=. python examples/phase1_multiturn_example.py
```

---

## 📈 下一步

Phase 1 已完成并可投入使用。如果需要更多功能：

**Phase 2 计划** (可选):
- 工具调用追踪（tool_use和tool_result）
- 结果与请求的关联
- 工具调用统计和分析

**Phase 3 计划** (可选):
- 动态上下文注入追踪
- RAG上下文监控
- 代码执行结果捕获

---

## 🔗 相关文档

- **测试报告**: `PHASE1_TEST_REPORT.md`
- **完成总结**: `PHASE1_COMPLETION_SUMMARY.md`
- **单元测试**: `tests/test_observer_phase1_enhancements.py`
- **集成测试**: `tests/test_phase1_integration.py`
- **演示示例**: `examples/phase1_multiturn_example.py`

---

## 💬 常见问题

### Q: 如何处理没有系统prompt的对话？
A: Phase 1完全兼容无系统prompt的场景。system_prompt字段会是None，其他功能正常工作。

### Q: 可以在同一个session中追踪多个对话吗？
A: 可以！使用不同的conversation_id即可完全隔离不同对话。

### Q: Token统计不准确怎么办？
A: Token统计基于API返回的usage信息。如果API没有返回，该字段会是默认值。

### Q: 如何自定义conversation_id？
A: 在capture_request时直接传入conversation_id参数即可。建议使用有意义的ID如"user_123_session_456"。

---

**🎉 Phase 1 已就绪，可以开始使用！**

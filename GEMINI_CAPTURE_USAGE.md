# Gemini CLI Capture 使用指南

## 问题说明

如果你遇到 `zsh: command not found: -p` 错误，这是**命令格式问题**，不是 TigerHill interceptor 的问题。

### ❌ 错误用法（有换行）

```bash
TIGERHILL_CAPTURE_PATH="./prompt_captures/gemini_cli" TIGERHILL_DEBUG="true" TIGERHILL_SAVE_RAW="true"
NODE_OPTIONS="--require ./tigerhill/observer/gemini_session_interceptor.cjs" node ../gemini-cli/bundle/gemini.js
-p "用一句话介绍你自己" --output-format text
```

**问题**: Shell 会将第二行和第三行当作独立命令执行，导致 `-p` 被当作命令。

---

## ✅ 正确用法

### 方式 1: 单行命令（推荐）

```bash
TIGERHILL_CAPTURE_PATH="./prompt_captures/gemini_cli" TIGERHILL_DEBUG="true" TIGERHILL_SAVE_RAW="true" NODE_OPTIONS="--require ./tigerhill/observer/gemini_session_interceptor.cjs" node ../gemini-cli/bundle/gemini.js
```

### 方式 2: 使用反斜杠换行

```bash
TIGERHILL_CAPTURE_PATH="./prompt_captures/gemini_cli" \
TIGERHILL_DEBUG="true" \
TIGERHILL_SAVE_RAW="true" \
NODE_OPTIONS="--require ./tigerhill/observer/gemini_session_interceptor.cjs" \
node ../gemini-cli/bundle/gemini.js
```

**注意**: 每行末尾必须有 `\`，且 `\` 后面不能有空格。

### 方式 3: 使用 export（最清晰）

```bash
# 设置环境变量
export TIGERHILL_CAPTURE_PATH="./prompt_captures/gemini_cli"
export TIGERHILL_DEBUG="true"
export TIGERHILL_SAVE_RAW="true"
export NODE_OPTIONS="--require ./tigerhill/observer/gemini_session_interceptor.cjs"

# 运行 Gemini CLI
node ../gemini-cli/bundle/gemini.js
```

### 方式 4: 使用脚本（最方便）

```bash
# 运行测试脚本
./scripts/test_gemini_capture.sh
```

---

## 环境变量说明

| 变量 | 作用 | 默认值 | 必需 |
|------|------|--------|------|
| `TIGERHILL_CAPTURE_PATH` | 捕获文件保存路径 | `./prompt_captures` | ❌ |
| `TIGERHILL_DEBUG` | 启用调试输出 | `false` | ❌ |
| `TIGERHILL_SAVE_RAW` | 保存完整原始请求/响应 | `false` | ❌ |
| `NODE_OPTIONS` | Node.js 启动参数（加载 interceptor） | - | ✅ |

---

## 使用示例

### 1. 交互模式（推荐）

```bash
export TIGERHILL_CAPTURE_PATH="./prompt_captures/gemini_cli"
export TIGERHILL_DEBUG="true"
export TIGERHILL_SAVE_RAW="true"
export NODE_OPTIONS="--require ./tigerhill/observer/gemini_session_interceptor.cjs"

node ../gemini-cli/bundle/gemini.js
```

然后在 Gemini CLI 中正常对话：

```
> 请帮我写一个 Python 函数计算斐波那契数列
> 能优化一下性能吗？
> 添加单元测试
> /quit
```

### 2. 单次命令模式（已弃用）

**注意**: Gemini CLI 可能不支持通过 `-p` 参数直接传递 prompt，建议使用交互模式。

如果你想传递初始 prompt，可以这样：

```bash
export TIGERHILL_CAPTURE_PATH="./prompt_captures/gemini_cli"
export NODE_OPTIONS="--require ./tigerhill/observer/gemini_session_interceptor.cjs"

# 注意：这可能不工作，取决于 Gemini CLI 版本
echo "写一个 Python 函数计算斐波那契数列" | node ../gemini-cli/bundle/gemini.js
```

---

## 验证捕获是否成功

### 1. 检查捕获文件

```bash
ls -lh ./prompt_captures/gemini_cli/
```

应该看到：
- `session_*.json` - 会话数据文件
- `.session_store.json` - 会话存储索引

### 2. 查看捕获内容

```bash
# 美化输出最新的捕获文件
cat ./prompt_captures/gemini_cli/session_*.json | python -m json.tool | head -100
```

### 3. 分析捕获数据

```python
import json
from pathlib import Path

# 读取最新的捕获文件
capture_dir = Path("./prompt_captures/gemini_cli")
capture_files = list(capture_dir.glob("session_*.json"))

if capture_files:
    latest_file = max(capture_files, key=lambda p: p.stat().st_mtime)

    with open(latest_file) as f:
        data = json.load(f)

    print(f"Session ID: {data['session_id']}")
    print(f"Total turns: {data['statistics']['total_turns']}")
    print(f"Total tokens: {data['statistics']['total_tokens']}")
    print(f"\nConversation history:")

    for msg in data['conversation_history']['messages']:
        print(f"  [{msg['role']}] Turn {msg['turn_number']}: {msg['content'][:100]}...")
```

---

## 调试问题

### 1. Interceptor 未激活

**症状**: 没有看到 `[TigerHill Session Interceptor] Active` 输出

**解决**:
```bash
# 检查 NODE_OPTIONS 是否正确设置
echo $NODE_OPTIONS

# 检查 interceptor 文件是否存在
ls -l ./tigerhill/observer/gemini_session_interceptor.cjs
```

### 2. 没有捕获文件生成

**症状**: 运行后 `./prompt_captures/gemini_cli/` 目录为空

**可能原因**:
1. Gemini CLI 没有发送任何 API 请求
2. Interceptor 未正确拦截请求
3. 路径权限问题

**解决**:
```bash
# 启用调试模式
export TIGERHILL_DEBUG="true"

# 检查目录权限
ls -ld ./prompt_captures/gemini_cli/

# 手动创建目录
mkdir -p ./prompt_captures/gemini_cli
```

### 3. Gemini CLI 运行异常

**症状**: Gemini CLI 启动失败或行为异常

**解决**:
```bash
# 先不加 interceptor 测试 Gemini CLI 是否正常
node ../gemini-cli/bundle/gemini.js

# 如果正常，再加上 interceptor
export NODE_OPTIONS="--require ./tigerhill/observer/gemini_session_interceptor.cjs"
node ../gemini-cli/bundle/gemini.js
```

---

## 从你的错误输出分析

### 你的输出显示

```
[TigerHill] Process pid_3830_1762513901058 exiting
[TigerHill] Process pid_3820_1762513900760 exiting
zsh: command not found: -p
```

### 分析

1. ✅ **Interceptor 正常工作**: 看到了 `[TigerHill] Process ... exiting`
2. ✅ **Gemini CLI 正常运行**: 你成功进行了多轮对话
3. ✅ **正常退出**: 看到了完整的统计信息
4. ❌ **命令格式错误**: `zsh: command not found: -p` 是因为命令有换行

### 结论

**TigerHill interceptor 工作正常！** 问题只是命令格式导致的 shell 错误。

---

## 推荐工作流

### 开发阶段

```bash
# 1. 设置环境变量（在 ~/.zshrc 或 ~/.bashrc 中）
export TIGERHILL_CAPTURE_PATH="$HOME/tigerhill_captures"
export TIGERHILL_DEBUG="true"

# 2. 使用时临时加载 interceptor
NODE_OPTIONS="--require /path/to/tigerhill/observer/gemini_session_interceptor.cjs" \
node ../gemini-cli/bundle/gemini.js
```

### 生产环境

```bash
# 关闭调试，不保存原始数据
export TIGERHILL_CAPTURE_PATH="./captures"
export TIGERHILL_DEBUG="false"
export TIGERHILL_SAVE_RAW="false"
export NODE_OPTIONS="--require ./tigerhill/observer/gemini_session_interceptor.cjs"

node ../gemini-cli/bundle/gemini.js
```

---

## 与 TraceStore 集成

捕获的数据可以导入到 TraceStore 进行分析：

```python
from tigerhill.observer import PromptCapture
from tigerhill.storage.trace_store import TraceStore
import json
from pathlib import Path

# 读取捕获文件
capture_file = Path("./prompt_captures/gemini_cli/session_conv_xxx.json")
with open(capture_file) as f:
    session_data = json.load(f)

# 导入到 TraceStore
store = TraceStore()
trace_id = store.start_trace(
    agent_name="gemini-cli",
    metadata={
        "session_id": session_data["session_id"],
        "total_turns": session_data["statistics"]["total_turns"]
    }
)

# 添加每一轮对话
for turn in session_data["turns"]:
    for request in turn["requests"]:
        store.write_event(
            trace_id=trace_id,
            event_type="PROMPT",
            event_data=request
        )

    for response in turn["responses"]:
        store.write_event(
            trace_id=trace_id,
            event_type="MODEL_RESPONSE",
            event_data=response
        )

store.end_trace(trace_id)
print(f"Imported to TraceStore: {trace_id}")
```

---

## 总结

- ✅ 使用单行命令或 `\` 续行
- ✅ 或使用 `export` 设置环境变量
- ✅ 或使用提供的测试脚本
- ❌ 不要直接换行（会导致命令分割）

**你的 interceptor 是正常工作的！** 只需要修复命令格式即可。

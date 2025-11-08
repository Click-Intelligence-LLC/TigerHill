# TigerHill 端到端验证流程

**完整测试验证：LLM交互抓取 → 存储 → Dashboard查看**

本文档提供完整的端到端验证流程，验证TigerHill系统的所有核心功能。

---

## 📋 验证流程概览

```
┌─────────────────┐
│  1. 创建Agent   │
│  执行LLM任务    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. 抓取交互    │
│  TraceStore记录 │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  3. 存储数据    │
│  SQLite数据库   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  4. Dashboard   │
│  可视化查看     │
└─────────────────┘
```

---

## 🚀 完整验证步骤

### 步骤1: 创建测试Agent并记录Trace

我们将创建一个模拟的LLM Agent来演示完整流程。

**文件**: `examples/demo_agent_with_tracing.py`

```python
#!/usr/bin/env python3
"""
演示Agent - 完整的Trace记录示例
展示如何在实际Agent中集成TigerHill Trace记录
"""

import time
import random
from tigerhill.storage.sqlite_trace_store import SQLiteTraceStore
from tigerhill.storage.trace_store import EventType


class DemoLLMAgent:
    """模拟的LLM Agent - 展示Trace集成"""

    def __init__(self, name: str, trace_store: SQLiteTraceStore):
        self.name = name
        self.store = trace_store

    def run_task(self, task: str, simulate_llm_calls: int = 3):
        """执行任务并记录trace

        Args:
            task: 任务描述
            simulate_llm_calls: 模拟的LLM调用次数
        """
        # 1. 开始trace
        trace_id = self.store.start_trace(
            agent_name=self.name,
            task_id=f"task-{int(time.time())}",
            metadata={
                "task_description": task,
                "tags": ["demo", "validation"],
                "priority": "high"
            }
        )

        print(f"✅ 开始任务: {task}")
        print(f"   Trace ID: {trace_id}")

        try:
            # 2. 模拟多次LLM调用
            for i in range(simulate_llm_calls):
                self._simulate_llm_call(trace_id, i)

            # 3. 模拟工具调用
            self._simulate_tool_calls(trace_id)

            print(f"✅ 任务完成")

        except Exception as e:
            # 记录错误
            self.store.write_event(
                {
                    "type": "error",
                    "error_message": str(e),
                    "error_type": type(e).__name__
                },
                trace_id=trace_id,
                event_type=EventType.ERROR
            )
            print(f"❌ 任务失败: {e}")

        finally:
            # 4. 结束trace
            self.store.end_trace(trace_id)

        return trace_id

    def _simulate_llm_call(self, trace_id: str, call_index: int):
        """模拟LLM调用"""
        # 模拟Prompt
        prompt_tokens = random.randint(50, 200)
        prompt = f"This is prompt #{call_index + 1} for the task"

        self.store.write_event(
            {
                "type": "prompt",
                "content": prompt,
                "model": "gpt-4",
                "temperature": 0.7,
                "total_tokens": prompt_tokens,
                "cost_usd": prompt_tokens * 0.00003  # $0.03 per 1K tokens
            },
            trace_id=trace_id,
            event_type=EventType.PROMPT
        )

        # 模拟处理时间
        time.sleep(0.1)

        # 模拟Response
        completion_tokens = random.randint(100, 300)
        response = f"This is response #{call_index + 1} from the model"

        self.store.write_event(
            {
                "type": "model_response",
                "content": response,
                "model": "gpt-4",
                "finish_reason": "stop",
                "total_tokens": completion_tokens,
                "cost_usd": completion_tokens * 0.00006  # $0.06 per 1K tokens
            },
            trace_id=trace_id,
            event_type=EventType.MODEL_RESPONSE
        )

        print(f"   📝 LLM调用 #{call_index + 1}: {prompt_tokens + completion_tokens} tokens")

    def _simulate_tool_calls(self, trace_id: str):
        """模拟工具调用"""
        tools = ["calculator", "search", "database_query"]

        for tool in random.sample(tools, k=2):
            # 工具调用
            self.store.write_event(
                {
                    "type": "tool_call",
                    "tool_name": tool,
                    "arguments": {"query": f"test {tool}"}
                },
                trace_id=trace_id,
                event_type=EventType.TOOL_CALL
            )

            time.sleep(0.05)

            # 工具结果
            self.store.write_event(
                {
                    "type": "tool_result",
                    "tool_name": tool,
                    "result": f"Result from {tool}",
                    "success": True
                },
                trace_id=trace_id,
                event_type=EventType.TOOL_RESULT
            )

            print(f"   🔧 工具调用: {tool}")


def main():
    """主函数 - 运行演示"""
    print("=" * 60)
    print("TigerHill 端到端验证 - Agent执行演示")
    print("=" * 60)
    print()

    # 1. 初始化TraceStore（使用SQLite）
    db_path = "./tigerhill_validation.db"
    store = SQLiteTraceStore(db_path=db_path, auto_init=True)
    print(f"✅ 初始化TraceStore: {db_path}")
    print()

    # 2. 创建Agent
    agent = DemoLLMAgent(name="validation-agent", trace_store=store)

    # 3. 运行多个任务
    tasks = [
        "分析用户反馈并生成报告",
        "总结技术文档的关键点",
        "生成测试用例"
    ]

    trace_ids = []
    for i, task in enumerate(tasks, 1):
        print(f"--- 任务 {i}/{len(tasks)} ---")
        trace_id = agent.run_task(task, simulate_llm_calls=random.randint(2, 4))
        trace_ids.append(trace_id)
        print()
        time.sleep(0.2)

    # 4. 显示统计信息
    print("=" * 60)
    print("执行统计")
    print("=" * 60)
    stats = store.get_statistics()
    print(f"总Traces: {stats['total_traces']}")
    print(f"总Events: {stats['total_events']}")
    print(f"LLM调用: {stats['total_llm_calls']}")
    print(f"总Tokens: {stats['total_tokens']}")
    print(f"总成本: ${stats['total_cost_usd']:.4f}")
    print(f"状态分布: {stats['status_counts']}")
    print()

    # 5. 显示每个trace的摘要
    print("=" * 60)
    print("Trace摘要")
    print("=" * 60)
    for i, trace_id in enumerate(trace_ids, 1):
        summary = store.get_summary(trace_id)
        print(f"{i}. {summary['trace_id'][:8]}...")
        print(f"   Agent: {summary['agent_name']}")
        print(f"   状态: {summary['status']}")
        print(f"   Events: {summary['total_events']}")
        print(f"   LLM调用: {summary['llm_calls_count']}")
        print(f"   Tokens: {summary['total_tokens']}")
        print(f"   成本: ${summary['total_cost_usd']:.4f}")
        print(f"   事件类型: {summary['event_counts']}")
        print()

    print("=" * 60)
    print("✅ 演示完成！")
    print("=" * 60)
    print()
    print("下一步:")
    print("1. 数据已保存到: ./tigerhill_validation.db")
    print("2. 运行Dashboard查看: PYTHONPATH=. streamlit run tigerhill/web/dashboard/app.py")
    print("3. 在Dashboard侧边栏选择数据源: SQLite Database")
    print()


if __name__ == "__main__":
    main()
```

---

### 步骤2: 运行Agent并记录Trace

```bash
# 创建演示脚本
mkdir -p examples
cat > examples/demo_agent_with_tracing.py << 'EOF'
# (上面的代码)
EOF

# 赋予执行权限
chmod +x examples/demo_agent_with_tracing.py

# 运行演示
PYTHONPATH=. python3 examples/demo_agent_with_tracing.py
```

**预期输出**:
```
============================================================
TigerHill 端到端验证 - Agent执行演示
============================================================

✅ 初始化TraceStore: ./tigerhill_validation.db

--- 任务 1/3 ---
✅ 开始任务: 分析用户反馈并生成报告
   Trace ID: a1b2c3d4-...
   📝 LLM调用 #1: 250 tokens
   📝 LLM调用 #2: 320 tokens
   📝 LLM调用 #3: 180 tokens
   🔧 工具调用: calculator
   🔧 工具调用: search
✅ 任务完成

--- 任务 2/3 ---
...

============================================================
执行统计
============================================================
总Traces: 3
总Events: 21
LLM调用: 9
总Tokens: 2250
总成本: $0.1125
状态分布: {'completed': 3}

============================================================
✅ 演示完成！
============================================================
```

---

### 步骤3: 验证数据存储

```bash
# 使用SQLite命令行查看数据
sqlite3 tigerhill_validation.db

# 查看traces
SELECT trace_id, agent_name, status, total_events, total_tokens, total_cost_usd
FROM traces;

# 查看events
SELECT trace_id, event_type, timestamp
FROM events
LIMIT 5;

# 退出
.exit
```

或使用Python验证：

```python
# 文件: examples/verify_stored_data.py
from tigerhill.storage.sqlite_trace_store import SQLiteTraceStore

store = SQLiteTraceStore(db_path="./tigerhill_validation.db", auto_init=False)

# 查询所有traces
traces = store.query_traces()
print(f"找到 {len(traces)} 个traces")

for trace in traces:
    print(f"- {trace.trace_id[:8]}... | {trace.agent_name} | {trace.metadata['_db_status']}")

# 查看第一个trace的详情
if traces:
    trace_id = traces[0].trace_id
    trace = store.get_trace(trace_id, include_events=True)
    print(f"\nTrace详情: {trace_id[:8]}...")
    print(f"Events: {len(trace.events)}")
    for i, event in enumerate(trace.events[:3], 1):
        print(f"  {i}. {event.event_type.value} @ {event.timestamp}")
```

---

### 步骤4: 启动Dashboard查看

#### 方式1: 使用SQLite数据源（推荐）

创建Dashboard配置脚本：

```python
# 文件: examples/start_dashboard_sqlite.py
import os
import sys
import subprocess

# 设置环境变量
os.environ['PYTHONPATH'] = '.'
os.environ['TIGERHILL_DB_PATH'] = './tigerhill_validation.db'
os.environ['TIGERHILL_USE_DATABASE'] = 'true'

# 启动Dashboard
subprocess.run([
    'streamlit', 'run',
    'tigerhill/web/dashboard/app.py',
    '--server.port', '8501',
    '--server.headless', 'true'
])
```

运行：

```bash
PYTHONPATH=. python3 examples/start_dashboard_sqlite.py
```

#### 方式2: 直接运行Dashboard

更新Dashboard入口以支持数据库配置：

```python
# 文件: tigerhill/web/dashboard/app.py
# 在文件开头添加数据源选择

import streamlit as st
import os

# 侧边栏配置
st.sidebar.title("🐯 TigerHill")

# 数据源选择
data_source = st.sidebar.radio(
    "📁 数据源",
    ["JSONL Files", "SQLite Database"],
    key="data_source"
)

# 根据数据源配置DataLoader
if data_source == "SQLite Database":
    db_path = st.sidebar.text_input(
        "数据库路径",
        value="./tigerhill_validation.db"
    )
    use_database = True
    storage_path = None
else:
    storage_path = st.sidebar.text_input(
        "存储路径",
        value="./test_traces"
    )
    use_database = False
    db_path = None

# 创建DataLoader
from tigerhill.web.dashboard.data.loader import DataLoader
loader = DataLoader(
    storage_path=storage_path or "./test_traces",
    use_database=use_database,
    db_path=db_path
)

st.sidebar.info(f"当前数据源: {loader.data_source_type}")
```

启动Dashboard：

```bash
PYTHONPATH=. streamlit run tigerhill/web/dashboard/app.py
```

访问：http://localhost:8501

---

### 步骤5: Dashboard验证检查清单

在Dashboard中验证以下内容：

#### ✅ 检查1: 数据源配置
- [ ] 侧边栏显示"SQLite Database"
- [ ] 数据库路径正确: `./tigerhill_validation.db`

#### ✅ 检查2: 指标卡片
- [ ] 总测试数 = 3
- [ ] 总Tokens = ~2250
- [ ] 总成本 = ~$0.11
- [ ] 平均质量分 = N/A（或有值）

#### ✅ 检查3: Trace列表
- [ ] 显示3个traces
- [ ] Agent名称 = "validation-agent"
- [ ] 状态 = "completed"
- [ ] 每个trace的events数 > 0

#### ✅ 检查4: 筛选功能
- [ ] 按Agent筛选: 选择"validation-agent"，显示3个
- [ ] 按状态筛选: 选择"completed"，显示3个
- [ ] 按时间筛选: 选择今天，显示3个

#### ✅ 检查5: 排序功能
- [ ] 按时间排序（降序）
- [ ] 按成本排序（降序）
- [ ] 按Tokens排序（降序）

#### ✅ 检查6: Trace详情
- [ ] 选择一个trace
- [ ] 查看基本信息（Trace ID, Agent, 状态等）
- [ ] 查看事件列表
- [ ] 展开事件查看JSON数据

#### ✅ 检查7: 趋势分析
- [ ] 切换到"趋势分析"标签页
- [ ] 查看Token分布柱状图
- [ ] 查看成本趋势折线图
- [ ] 查看Token vs 成本散点图

---

## 🧪 自动化验证脚本

创建完整的自动化验证脚本：

```python
# 文件: tests/test_end_to_end_validation.py
"""
端到端自动化验证测试
验证完整流程：Agent执行 → 存储 → 查询
"""

import pytest
import tempfile
import time
from pathlib import Path

from tigerhill.storage.sqlite_trace_store import SQLiteTraceStore
from tigerhill.storage.trace_store import EventType
from tigerhill.web.dashboard.data.loader import DataLoader


class TestEndToEndValidation:
    """端到端验证测试套件"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        yield db_path

        Path(db_path).unlink(missing_ok=True)

    def test_complete_workflow(self, temp_db):
        """测试完整工作流：Agent执行 → 存储 → 查询 → Dashboard"""

        # === 步骤1: 初始化TraceStore ===
        store = SQLiteTraceStore(db_path=temp_db, auto_init=True)

        # === 步骤2: 模拟Agent执行 ===
        trace_ids = []

        for task_num in range(3):
            # 开始trace
            trace_id = store.start_trace(
                agent_name="e2e-validation-agent",
                task_id=f"task-{task_num}",
                metadata={"task_number": task_num, "tags": ["validation", "e2e"]}
            )
            trace_ids.append(trace_id)

            # 模拟LLM调用
            for call_num in range(3):
                # Prompt
                store.write_event(
                    {
                        "type": "prompt",
                        "content": f"Prompt {call_num}",
                        "total_tokens": 100,
                        "cost_usd": 0.003
                    },
                    trace_id=trace_id,
                    event_type=EventType.PROMPT
                )

                # Response
                store.write_event(
                    {
                        "type": "model_response",
                        "content": f"Response {call_num}",
                        "total_tokens": 200,
                        "cost_usd": 0.006
                    },
                    trace_id=trace_id,
                    event_type=EventType.MODEL_RESPONSE
                )

            # 模拟工具调用
            store.write_event(
                {"type": "tool_call", "tool": "calculator"},
                trace_id=trace_id,
                event_type=EventType.TOOL_CALL
            )

            # 结束trace
            time.sleep(0.01)
            store.end_trace(trace_id)

        # === 步骤3: 验证存储 ===

        # 3.1 验证traces数量
        all_traces = store.query_traces()
        assert len(all_traces) == 3, f"Expected 3 traces, got {len(all_traces)}"

        # 3.2 验证统计信息
        stats = store.get_statistics()
        assert stats['total_traces'] == 3
        assert stats['total_events'] == 21  # (3 prompts + 3 responses + 1 tool) * 3 tasks
        assert stats['total_llm_calls'] == 18  # (3 prompts + 3 responses) * 3 tasks
        assert stats['total_tokens'] == 2700  # (100 + 200) * 3 * 3
        assert abs(stats['total_cost_usd'] - 0.081) < 0.001  # (0.003 + 0.006) * 3 * 3
        assert stats['status_counts']['completed'] == 3

        # 3.3 验证每个trace
        for trace_id in trace_ids:
            trace = store.get_trace(trace_id, include_events=True)
            assert trace is not None
            assert trace.agent_name == "e2e-validation-agent"
            assert len(trace.events) == 7  # 3 prompts + 3 responses + 1 tool
            assert trace.metadata['_db_status'] == 'completed'
            assert trace.metadata['_db_total_events'] == 7
            assert trace.metadata['_db_llm_calls_count'] == 6
            assert trace.metadata['_db_total_tokens'] == 900
            assert abs(trace.metadata['_db_total_cost_usd'] - 0.027) < 0.001

        # === 步骤4: 验证查询功能 ===

        # 4.1 按agent_name查询
        agent_traces = store.query_traces(agent_name="e2e-validation-agent")
        assert len(agent_traces) == 3

        # 4.2 按状态查询
        completed_traces = store.query_traces(status="completed")
        assert len(completed_traces) == 3

        # 4.3 按成本范围查询
        expensive_traces = store.query_traces(min_cost=0.025)
        assert len(expensive_traces) == 3

        # 4.4 排序查询
        by_cost = store.query_traces(order_by="total_cost_usd", order_desc=True)
        assert len(by_cost) == 3
        assert by_cost[0].metadata['_db_total_cost_usd'] >= by_cost[-1].metadata['_db_total_cost_usd']

        # 4.5 分页查询
        page1 = store.query_traces(limit=2, offset=0)
        page2 = store.query_traces(limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 1

        # === 步骤5: 验证Dashboard集成 ===

        # 5.1 创建DataLoader
        loader = DataLoader(use_database=True, db_path=temp_db)
        assert loader.data_source_type == "SQLite Database"

        # 5.2 加载traces
        dashboard_traces = loader.load_traces()
        assert len(dashboard_traces) == 3

        # 5.3 验证TraceMetadata
        for trace_meta in dashboard_traces:
            assert trace_meta.agent_name == "e2e-validation-agent"
            assert trace_meta.status == "completed"
            assert trace_meta.total_events == 7
            assert trace_meta.llm_calls_count == 6
            assert trace_meta.total_tokens == 900
            assert abs(trace_meta.total_cost_usd - 0.027) < 0.001

        # 5.4 获取unique agent names
        agent_names = loader.get_unique_agent_names(dashboard_traces)
        assert len(agent_names) == 1
        assert agent_names[0] == "e2e-validation-agent"

        # 5.5 加载trace详情
        trace_detail = loader.load_trace_detail(trace_ids[0])
        assert trace_detail is not None

        # === 步骤6: 验证摘要功能 ===
        for trace_id in trace_ids:
            summary = store.get_summary(trace_id)
            assert summary is not None
            assert summary['trace_id'] == trace_id
            assert summary['agent_name'] == "e2e-validation-agent"
            assert summary['status'] == 'completed'
            assert summary['total_events'] == 7
            assert summary['llm_calls_count'] == 6
            assert summary['event_counts']['prompt'] == 3
            assert summary['event_counts']['model_response'] == 3
            assert summary['event_counts']['tool_call'] == 1

        print("\n" + "=" * 60)
        print("✅ 端到端验证测试通过！")
        print("=" * 60)
        print(f"验证项目:")
        print(f"  ✅ Agent执行和Trace记录")
        print(f"  ✅ 数据存储到SQLite")
        print(f"  ✅ 统计信息计算")
        print(f"  ✅ 查询和筛选功能")
        print(f"  ✅ Dashboard集成")
        print(f"  ✅ Trace摘要生成")
        print("=" * 60)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
```

---

## 📊 验证结果示例

### 终端输出示例

```
============================================================
执行统计
============================================================
总Traces: 3
总Events: 21
LLM调用: 18
总Tokens: 2700
总成本: $0.0810
状态分布: {'completed': 3}

============================================================
Trace摘要
============================================================
1. a1b2c3d4...
   Agent: e2e-validation-agent
   状态: completed
   Events: 7
   LLM调用: 6
   Tokens: 900
   成本: $0.0270
   事件类型: {'prompt': 3, 'model_response': 3, 'tool_call': 1}
```

### Dashboard截图检查点

1. **指标卡片** ✅
   - 总测试数: 3
   - 总Tokens: 2,700
   - 总成本: $0.08

2. **Trace列表** ✅
   - 3行数据
   - Agent: e2e-validation-agent
   - 状态: completed

3. **详情视图** ✅
   - 基本信息完整
   - 7个events显示
   - JSON数据可展开

4. **趋势图表** ✅
   - Token分布图显示3个柱
   - 成本趋势图显示3个点
   - 散点图显示3个点

---

## ✅ 验证清单

### 核心功能验证

- [ ] **Agent执行**
  - [ ] 创建trace
  - [ ] 写入events
  - [ ] 结束trace

- [ ] **数据存储**
  - [ ] traces表有数据
  - [ ] events表有数据
  - [ ] 统计字段正确计算

- [ ] **查询功能**
  - [ ] 查询所有traces
  - [ ] 按条件筛选
  - [ ] 排序
  - [ ] 分页

- [ ] **Dashboard显示**
  - [ ] 加载数据成功
  - [ ] 指标显示正确
  - [ ] 列表显示正确
  - [ ] 详情显示正确
  - [ ] 图表显示正确

### 性能验证

- [ ] **响应时间**
  - [ ] Agent执行 <1秒/trace
  - [ ] 数据存储 <10ms/trace
  - [ ] Dashboard加载 <100ms

- [ ] **数据完整性**
  - [ ] 所有events都被记录
  - [ ] 统计信息准确
  - [ ] 时间戳正确

---

## 🎯 快速验证命令

### 一键运行完整验证

```bash
# 1. 运行Agent并记录trace
PYTHONPATH=. python3 examples/demo_agent_with_tracing.py

# 2. 验证数据存储
PYTHONPATH=. python3 examples/verify_stored_data.py

# 3. 运行自动化测试
PYTHONPATH=. python3 -m pytest tests/test_end_to_end_validation.py -v -s

# 4. 启动Dashboard
PYTHONPATH=. streamlit run tigerhill/web/dashboard/app.py
```

### 验证脚本（一键运行所有）

```bash
#!/bin/bash
# 文件: scripts/run_end_to_end_validation.sh

echo "=========================================="
echo "TigerHill 端到端验证"
echo "=========================================="
echo

# 步骤1: 运行Agent
echo "步骤1: 运行Agent并记录Trace..."
PYTHONPATH=. python3 examples/demo_agent_with_tracing.py
if [ $? -eq 0 ]; then
    echo "✅ Agent执行成功"
else
    echo "❌ Agent执行失败"
    exit 1
fi
echo

# 步骤2: 验证存储
echo "步骤2: 验证数据存储..."
PYTHONPATH=. python3 examples/verify_stored_data.py
if [ $? -eq 0 ]; then
    echo "✅ 数据存储验证成功"
else
    echo "❌ 数据存储验证失败"
    exit 1
fi
echo

# 步骤3: 自动化测试
echo "步骤3: 运行自动化测试..."
PYTHONPATH=. python3 -m pytest tests/test_end_to_end_validation.py -v
if [ $? -eq 0 ]; then
    echo "✅ 自动化测试通过"
else
    echo "❌ 自动化测试失败"
    exit 1
fi
echo

# 步骤4: 提示启动Dashboard
echo "步骤4: 启动Dashboard验证..."
echo "请运行以下命令启动Dashboard:"
echo "  PYTHONPATH=. streamlit run tigerhill/web/dashboard/app.py"
echo
echo "然后在浏览器中验证:"
echo "  1. 访问 http://localhost:8501"
echo "  2. 选择数据源: SQLite Database"
echo "  3. 数据库路径: ./tigerhill_validation.db"
echo "  4. 检查数据显示是否正确"
echo

echo "=========================================="
echo "✅ 端到端验证完成！"
echo "=========================================="
```

---

## 📚 相关文档

- [Phase 1.2 完整交付报告](PHASE1_2_DELIVERY_FINAL.md)
- [数据库Schema设计](design/database_schema.md)
- [数据迁移指南](MIGRATION_GUIDE.md)
- [Dashboard使用文档](../tigerhill/web/dashboard/README.md)

---

**🎉 恭喜！完成TigerHill端到端验证流程！**

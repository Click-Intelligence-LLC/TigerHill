# TigerHill 存储架构分析：分开 vs 合并

## 🎯 问题

当前TigerHill有两个独立的存储系统：
1. **TraceStore** (`test_traces/`) - 测试执行追踪
2. **Observer SDK** (`prompt_captures/`) - LLM交互捕获

**核心问题**: 这两个功能应该分开还是合并在一起？

---

## 📊 当前架构分析

### 当前设计（分开）

```
TigerHill/
├── TraceStore (测试追踪)
│   ├── 目录: test_traces/
│   ├── 用途: 测试执行流程
│   ├── 粒度: 完整测试周期
│   └── 数据: 事件+断言+结果
│
└── Observer SDK (LLM捕获)
    ├── 目录: prompt_captures/
    ├── 用途: LLM交互调试
    ├── 粒度: 单次LLM调用
    └── 数据: 请求+响应+tokens
```

### 关注点分离（Separation of Concerns）

| 维度 | TraceStore | Observer SDK |
|------|-----------|-------------|
| **主要用户** | 测试工程师 | 提示工程师 |
| **使用时机** | 测试阶段 | 开发+调试阶段 |
| **核心价值** | 验证功能正确性 | 优化Prompt和成本 |
| **数据特点** | 结构化、事件流 | 原始、详细 |
| **生命周期** | 长期保存 | 可清理优化 |

---

## 💡 方案对比

### 方案A: 保持分开（当前）✅ 推荐

#### 优势

1. **关注点清晰** ⭐⭐⭐⭐⭐
   ```python
   # 测试场景 - 只关心功能是否正确
   store = TraceStore()
   trace_id = store.start_trace("agent")
   # 简洁的API，无需关心LLM细节

   # 调试场景 - 只关心LLM交互细节
   capture = PromptCapture()
   capture_id = capture.start_capture("agent")
   # 详细的token、成本分析
   ```

2. **API简洁性** ⭐⭐⭐⭐⭐
   - TraceStore API保持简单（测试导向）
   - Observer API保持专注（调试导向）
   - 用户按需选择，不会被不需要的功能困扰

3. **性能和存储优化** ⭐⭐⭐⭐
   - TraceStore可以只存储必要信息（轻量）
   - Observer可以存储完整LLM数据（详细）
   - 用户可以选择性地清理不同类型的数据

4. **独立演进** ⭐⭐⭐⭐⭐
   - 两个系统可以独立升级
   - Observer可以支持更多LLM（OpenAI, Anthropic...）
   - TraceStore可以添加更多测试特性
   - 不会相互影响

5. **灵活组合** ⭐⭐⭐⭐
   ```python
   # 可以单独使用
   store = TraceStore()  # 只做测试

   # 或单独使用
   capture = PromptCapture()  # 只做调试

   # 或组合使用
   capture.export_to_trace_store(capture_id, store)
   ```

6. **符合UNIX哲学** ⭐⭐⭐⭐⭐
   - "Do one thing and do it well"
   - 每个工具专注于自己的职责
   - 可以通过管道/集成组合

#### 劣势

1. **学习曲线** ⭐⭐
   - 新用户需要理解两个概念
   - 需要文档说明区别（已创建STORAGE_DIRECTORIES_GUIDE.md）

2. **可能的重复** ⭐⭐
   - 某些场景下可能同时使用两个系统
   - 存储了部分相同的数据

---

### 方案B: 合并为统一存储系统

#### 假设设计

```python
class UnifiedTraceStore:
    """统一的追踪和捕获系统"""

    def start_trace(self, agent_name, capture_llm=False):
        """
        开始追踪
        capture_llm: 是否同时捕获LLM详细信息
        """
        pass

    def log_llm_call(self, trace_id, request, response):
        """记录LLM调用（如果enabled）"""
        pass

    def end_trace(self, trace_id, analyze_prompts=False):
        """结束追踪，可选进行prompt分析"""
        pass
```

#### 优势

1. **单一入口** ⭐⭐⭐⭐
   - 只需要学习一个API
   - 所有数据在一个地方

2. **数据关联** ⭐⭐⭐⭐
   - Trace和Capture天然关联
   - 便于分析完整的执行流程

3. **减少重复** ⭐⭐⭐
   - 避免存储重复数据

#### 劣势

1. **API复杂度** ⭐⭐⭐⭐⭐（严重）
   ```python
   # API会变得复杂
   store = UnifiedStore(
       capture_llm=True,           # 要不要捕获LLM？
       capture_tokens=True,         # 要不要统计tokens？
       analyze_prompts=False,       # 要不要分析prompt？
       save_raw_response=True,      # 要不要保存原始响应？
       redact_sensitive=True,       # 要不要脱敏？
       ...                          # 更多配置...
   )

   # 简单的测试场景被迫处理很多不需要的配置
   ```

2. **性能开销** ⭐⭐⭐⭐
   - 即使不需要LLM详细信息，也要处理相关逻辑
   - 存储会变大（包含更多可选字段）

3. **违反单一职责** ⭐⭐⭐⭐⭐
   - 一个类承担太多责任
   - 测试和调试是两个不同的关注点

4. **难以独立演进** ⭐⭐⭐⭐⭐
   - Observer的变化会影响TraceStore
   - 添加新LLM支持会影响测试代码

5. **强耦合** ⭐⭐⭐⭐⭐
   - Observer和TraceStore紧密耦合
   - 难以替换或扩展

---

### 方案C: 松耦合集成（混合方案）✅ 可行

#### 设计

保持两个独立系统，但提供更好的集成：

```python
# 1. 保持独立
store = TraceStore()
capture = PromptCapture()

# 2. 提供便捷的集成API
class IntegratedTester:
    """集成测试器 - 同时使用TraceStore和Observer"""

    def __init__(self):
        self.store = TraceStore()
        self.capture = PromptCapture()

    def start_test(self, agent_name, capture_llm=True):
        """开始测试，可选捕获LLM"""
        trace_id = self.store.start_trace(agent_name)
        capture_id = None
        if capture_llm:
            capture_id = self.capture.start_capture(agent_name)
        return trace_id, capture_id

    def end_test(self, trace_id, capture_id=None, analyze=True):
        """结束测试，自动关联数据"""
        self.store.end_trace(trace_id)

        if capture_id:
            # 关联capture到trace
            self.capture.end_capture(capture_id)
            if analyze:
                # 进行分析
                analysis = self.capture.analyze(capture_id)
                # 添加分析结果到trace
                self.store.add_metadata(trace_id, {
                    'llm_analysis': analysis
                })

# 使用方式1: 只测试（简单）
store = TraceStore()
trace_id = store.start_trace("agent")
# ... 测试 ...

# 使用方式2: 测试+调试（完整）
tester = IntegratedTester()
trace_id, capture_id = tester.start_test("agent", capture_llm=True)
# ... 测试 ...
tester.end_test(trace_id, capture_id, analyze=True)
```

#### 优势

- ✅ 保持了分离的优势
- ✅ 提供了便捷的集成方式
- ✅ 用户可以选择使用级别

---

## 🎯 推荐方案

### ✅ **推荐：方案A（保持分开）+ 方案C（添加集成工具）**

### 理由

#### 1. 符合软件设计原则

**单一职责原则（SRP）**:
- TraceStore负责测试追踪
- Observer负责LLM调试
- 各司其职，职责清晰

**开放封闭原则（OCP）**:
- 可以添加新功能而不修改现有代码
- Observer可以支持新LLM而不影响TraceStore

**依赖倒置原则（DIP）**:
- 高层模块不依赖低层模块
- 可以独立替换实现

#### 2. 实际使用场景分析

**场景1: 快速功能测试（80%的情况）**
```python
# 简单、快速、无干扰
store = TraceStore()
trace_id = store.start_trace("agent")
output = agent.run("test")
store.write_event({"type": "response", "text": output})
results = run_assertions(output, assertions)
store.end_trace(trace_id)
```
✅ 如果合并：被迫处理LLM配置，降低效率

**场景2: 深度调试（15%的情况）**
```python
# 专注于LLM细节
capture = PromptCapture()
capture_id = capture.start_capture("agent")
# ... LLM调用 ...
result = capture.end_capture(capture_id)
analyzer = PromptAnalyzer(result)
report = analyzer.analyze_all()  # 详细分析
```
✅ 如果合并：测试相关的字段会干扰

**场景3: 完整分析（5%的情况）**
```python
# 使用集成工具
tester = IntegratedTester()
trace_id, capture_id = tester.start_test("agent", capture_llm=True)
# ... 测试 ...
tester.end_test(trace_id, capture_id, analyze=True)
```
✅ 保持分开允许这种灵活性

#### 3. 参考业界实践

**类比1: 日志系统**
- Application Logs（应用日志）- 类似TraceStore
- Debug Logs（调试日志）- 类似Observer
- 分开存储，按需启用

**类比2: Git**
- `git log`（提交历史）- 类似TraceStore
- `git diff`（详细变更）- 类似Observer
- 分开的命令，可以组合使用

**类比3: 数据库**
- Transaction Log（事务日志）- 类似TraceStore
- Query Profiler（查询分析）- 类似Observer
- 独立的系统，可集成使用

#### 4. LangSmith的设计

查看LangSmith（竞品）的设计：

```python
# LangSmith也是分离的
from langsmith import Client

# Tracing（类似TraceStore）
client.trace_run(...)

# Evaluation（类似测试）
client.evaluate(...)

# Debugging/Monitoring（类似Observer）
client.get_run_details(...)
```

LangSmith也采用了分离设计！

---

## 🔨 具体实施建议

### 1. 保持现有分离架构 ✅

不做大的改动，继续维护两个独立系统。

### 2. 添加便捷的集成层 🆕

创建 `tigerhill/integration/unified_tester.py`:

```python
"""
统一测试器 - 同时使用TraceStore和Observer的便捷封装
"""

from tigerhill.storage.trace_store import TraceStore
from tigerhill.observer import PromptCapture, PromptAnalyzer
from typing import Optional, Dict, Any, Tuple

class UnifiedTester:
    """
    统一测试器

    提供同时使用TraceStore和Observer的便捷方式。
    但底层仍然是两个独立的系统。

    使用场景：
    1. 快速测试 - 只用TraceStore
    2. 详细调试 - 同时用TraceStore和Observer
    3. 性能分析 - 获取完整的LLM统计

    示例：
        # 简单模式
        tester = UnifiedTester()
        test_id = tester.start("my_agent")
        # ... run test ...
        tester.end(test_id)

        # 详细模式（捕获LLM）
        test_id = tester.start("my_agent", capture_llm=True)
        # ... run test ...
        result = tester.end(test_id, analyze=True)
        print(result['llm_analysis'])
    """

    def __init__(
        self,
        trace_path: str = "./test_traces",
        capture_path: str = "./prompt_captures"
    ):
        self.store = TraceStore(storage_path=trace_path)
        self.capture = PromptCapture(storage_path=capture_path)
        self._active_tests: Dict[str, Dict[str, Any]] = {}

    def start(
        self,
        agent_name: str,
        task_id: Optional[str] = None,
        capture_llm: bool = False,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        开始一个测试

        Args:
            agent_name: Agent名称
            task_id: 任务ID（可选）
            capture_llm: 是否捕获LLM详细信息
            metadata: 额外元数据

        Returns:
            test_id: 测试ID（与trace_id相同）
        """
        # 总是创建trace
        trace_id = self.store.start_trace(
            agent_name=agent_name,
            task_id=task_id,
            metadata=metadata
        )

        # 可选地创建capture
        capture_id = None
        if capture_llm:
            capture_id = self.capture.start_capture(
                agent_name=agent_name,
                task=task_id,
                metadata=metadata
            )

        # 记录关联
        self._active_tests[trace_id] = {
            'trace_id': trace_id,
            'capture_id': capture_id,
            'agent_name': agent_name
        }

        return trace_id

    def end(
        self,
        test_id: str,
        status: str = "success",
        analyze: bool = False
    ) -> Dict[str, Any]:
        """
        结束一个测试

        Args:
            test_id: 测试ID
            status: 测试状态
            analyze: 是否进行LLM分析

        Returns:
            包含trace和可选的分析结果
        """
        if test_id not in self._active_tests:
            raise ValueError(f"Test {test_id} not found")

        test_info = self._active_tests[test_id]
        trace_id = test_info['trace_id']
        capture_id = test_info['capture_id']

        # 结束trace
        self.store.end_trace(trace_id, status=status)

        result = {
            'test_id': test_id,
            'trace_id': trace_id,
            'status': status
        }

        # 如果有capture，处理它
        if capture_id:
            capture_result = self.capture.end_capture(capture_id)
            result['capture_id'] = capture_id
            result['statistics'] = capture_result.get('statistics', {})

            # 可选的分析
            if analyze:
                analyzer = PromptAnalyzer(capture_result)
                analysis = analyzer.analyze_all()
                result['llm_analysis'] = analysis

                # 将关键指标添加到trace metadata
                self.store.update_trace(trace_id, metadata={
                    'total_tokens': capture_result['statistics'].get('total_tokens', 0),
                    'total_cost': capture_result['statistics'].get('total_cost', 0),
                    'avg_response_time': capture_result['statistics'].get('avg_response_time', 0)
                })

        # 清理
        del self._active_tests[test_id]

        return result

    def get_trace(self, test_id: str):
        """获取trace对象"""
        return self.store.get_trace(test_id)

    def get_capture(self, capture_id: str):
        """获取capture数据"""
        return self.capture.get_capture(capture_id)
```

### 3. 改进文档 📚

在 `USER_GUIDE.md` 添加新章节：

```markdown
## 何时使用什么工具？

### 快速决策树

1. 我只需要验证Agent功能是否正确
   → 使用 TraceStore

2. 我需要优化Prompt或降低成本
   → 使用 Observer SDK

3. 我需要完整的测试+调试信息
   → 使用 UnifiedTester（集成工具）

4. 我在测试中发现问题，需要深入调试
   → 先用TraceStore测试，再用Observer SDK调试
```

### 4. 添加迁移便捷工具 🔄

```python
# tigerhill/utils/migration.py

def link_capture_to_trace(capture_id: str, trace_id: str):
    """
    将capture数据关联到trace
    用于事后关联分析
    """
    pass

def export_all_captures_to_traces():
    """
    批量导出所有captures到traces
    用于迁移或分析
    """
    pass
```

---

## 📈 长期路线图

### 短期（已完成）✅
- ✅ TraceStore完整实现
- ✅ Observer SDK完整实现
- ✅ 两者分离设计
- ✅ 文档说明区别

### 中期（建议实施）🔨
- 🔨 实现UnifiedTester集成层
- 🔨 添加便捷的关联工具
- 🔨 改进文档和示例

### 长期（可选）💡
- 💡 Web UI中同时展示trace和capture
- 💡 自动化的最佳实践推荐
- 💡 更智能的数据关联

---

## 🎓 给其他开发者的建议

如果你在设计类似系统，考虑：

### ✅ 应该分开的情况

1. **关注点明显不同**
   - 测试 vs 调试
   - 功能验证 vs 性能优化
   - 结果 vs 过程

2. **用户群体不同**
   - QA工程师 vs 提示工程师
   - 系统管理员 vs 开发者

3. **生命周期不同**
   - 长期保存 vs 临时分析
   - 结构化存储 vs 原始数据

4. **性能要求不同**
   - 轻量级 vs 详细完整
   - 高频调用 vs 按需启用

### ❌ 应该合并的情况

1. **数据高度重叠**
   - 90%以上的字段相同
   - 总是一起使用

2. **用户总是同时需要**
   - 无法独立使用
   - 强依赖关系

3. **维护成本高**
   - 经常需要同步更新
   - 接口高度耦合

---

## 🏁 最终结论

### ✅ **强烈推荐：保持分开 + 添加集成层**

**理由总结**:

1. ⭐⭐⭐⭐⭐ **符合软件工程原则**
   - 单一职责、开放封闭、依赖倒置

2. ⭐⭐⭐⭐⭐ **更好的用户体验**
   - 简单场景保持简单
   - 复杂场景提供工具

3. ⭐⭐⭐⭐⭐ **更好的可维护性**
   - 独立演进
   - 松耦合

4. ⭐⭐⭐⭐⭐ **更好的性能**
   - 按需启用
   - 存储优化

5. ⭐⭐⭐⭐⭐ **业界实践验证**
   - LangSmith采用类似设计
   - 符合UNIX哲学

### 下一步行动

1. ✅ 保持现有架构不变
2. 🔨 实现`UnifiedTester`集成工具（可选）
3. 📚 完善文档说明使用场景
4. 💡 收集用户反馈，持续优化

---

**报告版本**: 1.0
**创建日期**: 2025-11-01
**作者**: TigerHill架构团队

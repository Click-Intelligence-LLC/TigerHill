# TigerHill 数据库Schema设计

**设计日期**: 2025-11-03
**版本**: v1.0
**数据库**: SQLite 3.x
**状态**: 待审核

---

## 1. 设计目标

### 1.1 核心目标
- ✅ 支持高效的Trace数据存储和查询
- ✅ 保持与现有JSONL格式的兼容性
- ✅ 支持复杂的筛选和排序查询
- ✅ 为未来的PromptCapture功能预留空间
- ✅ 保证数据完整性和一致性

### 1.2 性能目标
- 支持10,000+ traces的快速查询（<100ms）
- 支持并发读取
- 优化常见查询场景（按时间、agent、状态筛选）

### 1.3 扩展性目标
- 预留字段支持未来功能
- 支持数据迁移和版本升级
- 支持多种查询模式

---

## 2. 表结构设计

### 2.1 traces 表

**用途**: 存储Trace的基本信息

```sql
CREATE TABLE traces (
    -- 主键
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 业务主键
    trace_id TEXT NOT NULL UNIQUE,

    -- 基本信息
    agent_name TEXT NOT NULL,
    task_id TEXT,

    -- 时间信息
    start_time REAL NOT NULL,  -- Unix timestamp
    end_time REAL,              -- Unix timestamp
    duration_seconds REAL,      -- 持续时间（秒）

    -- 状态
    status TEXT NOT NULL DEFAULT 'running',  -- running, completed, failed

    -- 统计信息（冗余字段，用于快速查询）
    total_events INTEGER DEFAULT 0,
    llm_calls_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost_usd REAL DEFAULT 0.0,

    -- 质量指标（预留）
    quality_score REAL,         -- 0-100
    cost_efficiency REAL,       -- 0-100

    -- 元数据
    tags TEXT,                  -- JSON array: ["tag1", "tag2"]
    metadata TEXT,              -- JSON object: {"key": "value"}

    -- 审计字段
    created_at REAL NOT NULL DEFAULT (julianday('now')),
    updated_at REAL NOT NULL DEFAULT (julianday('now'))
);
```

**字段说明**:

| 字段 | 类型 | 说明 | 索引 |
|------|------|------|------|
| id | INTEGER | 自增主键 | PK |
| trace_id | TEXT | 业务主键（UUID） | UNIQUE |
| agent_name | TEXT | Agent名称 | INDEX |
| task_id | TEXT | 任务ID（可选） | INDEX |
| start_time | REAL | 开始时间（Unix时间戳） | INDEX |
| end_time | REAL | 结束时间 | - |
| duration_seconds | REAL | 持续时间 | - |
| status | TEXT | 状态 | INDEX |
| total_events | INTEGER | 事件总数 | - |
| llm_calls_count | INTEGER | LLM调用次数 | - |
| total_tokens | INTEGER | Token总数 | INDEX |
| total_cost_usd | REAL | 总成本 | INDEX |
| quality_score | REAL | 质量分数 | INDEX |
| cost_efficiency | REAL | 成本效率 | - |
| tags | TEXT | 标签（JSON） | - |
| metadata | TEXT | 元数据（JSON） | - |
| created_at | REAL | 创建时间 | - |
| updated_at | REAL | 更新时间 | - |

---

### 2.2 events 表

**用途**: 存储Trace中的事件数据

```sql
CREATE TABLE events (
    -- 主键
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 关联
    trace_id TEXT NOT NULL,

    -- 事件信息
    event_type TEXT NOT NULL,
    timestamp REAL NOT NULL,    -- Unix timestamp
    sequence_number INTEGER NOT NULL,  -- 事件序号（用于排序）

    -- 事件数据
    data TEXT NOT NULL,         -- JSON object

    -- 审计
    created_at REAL NOT NULL DEFAULT (julianday('now')),

    -- 外键约束
    FOREIGN KEY (trace_id) REFERENCES traces(trace_id) ON DELETE CASCADE
);
```

**字段说明**:

| 字段 | 类型 | 说明 | 索引 |
|------|------|------|------|
| id | INTEGER | 自增主键 | PK |
| trace_id | TEXT | 关联的trace_id | FK, INDEX |
| event_type | TEXT | 事件类型 | INDEX |
| timestamp | REAL | 事件时间戳 | INDEX |
| sequence_number | INTEGER | 序号（保证顺序） | - |
| data | TEXT | 事件数据（JSON） | - |
| created_at | REAL | 创建时间 | - |

---

### 2.3 captures 表（预留）

**用途**: 存储PromptCapture数据（LLM请求/响应）

```sql
CREATE TABLE captures (
    -- 主键
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 业务主键
    capture_id TEXT NOT NULL UNIQUE,

    -- 关联（可选）
    trace_id TEXT,
    event_id INTEGER,

    -- LLM信息
    provider TEXT NOT NULL,     -- openai, anthropic, google
    model TEXT NOT NULL,        -- gpt-4, claude-3-opus

    -- 请求信息
    request TEXT NOT NULL,      -- JSON: {prompt, system_prompt, temperature, ...}

    -- 响应信息
    response TEXT NOT NULL,     -- JSON: {content, finish_reason, ...}

    -- Token统计
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,

    -- 成本和性能
    cost_usd REAL DEFAULT 0.0,
    latency_seconds REAL DEFAULT 0.0,

    -- 工具调用（可选）
    tool_calls TEXT,            -- JSON array

    -- 时间信息
    timestamp REAL NOT NULL,

    -- 审计
    created_at REAL NOT NULL DEFAULT (julianday('now')),

    -- 外键约束
    FOREIGN KEY (trace_id) REFERENCES traces(trace_id) ON DELETE SET NULL,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE SET NULL
);
```

**字段说明**:

| 字段 | 类型 | 说明 | 索引 |
|------|------|------|------|
| id | INTEGER | 自增主键 | PK |
| capture_id | TEXT | 业务主键（UUID） | UNIQUE |
| trace_id | TEXT | 关联的trace（可选） | FK, INDEX |
| event_id | INTEGER | 关联的event（可选） | FK, INDEX |
| provider | TEXT | LLM提供商 | INDEX |
| model | TEXT | 模型名称 | INDEX |
| request | TEXT | 请求数据（JSON） | - |
| response | TEXT | 响应数据（JSON） | - |
| prompt_tokens | INTEGER | Prompt tokens | - |
| completion_tokens | INTEGER | Completion tokens | - |
| total_tokens | INTEGER | 总tokens | INDEX |
| cost_usd | REAL | 成本 | INDEX |
| latency_seconds | REAL | 延迟 | - |
| tool_calls | TEXT | 工具调用（JSON） | - |
| timestamp | REAL | 时间戳 | INDEX |
| created_at | REAL | 创建时间 | - |

---

## 3. 索引策略

### 3.1 traces表索引

```sql
-- 唯一索引
CREATE UNIQUE INDEX idx_traces_trace_id ON traces(trace_id);

-- 单列索引（常用查询字段）
CREATE INDEX idx_traces_agent_name ON traces(agent_name);
CREATE INDEX idx_traces_start_time ON traces(start_time);
CREATE INDEX idx_traces_status ON traces(status);
CREATE INDEX idx_traces_total_tokens ON traces(total_tokens);
CREATE INDEX idx_traces_total_cost ON traces(total_cost_usd);
CREATE INDEX idx_traces_quality_score ON traces(quality_score);

-- 组合索引（常见查询场景）
CREATE INDEX idx_traces_agent_status ON traces(agent_name, status);
CREATE INDEX idx_traces_status_time ON traces(status, start_time DESC);
CREATE INDEX idx_traces_agent_time ON traces(agent_name, start_time DESC);
```

**设计理由**:
- `trace_id`: 业务主键，必须唯一
- `agent_name`: 最常用的筛选条件
- `start_time`: 时间范围查询、排序
- `status`: 状态筛选
- `total_tokens`, `total_cost_usd`: 排序字段
- `quality_score`: 质量分析查询
- 组合索引：优化多条件查询（agent+status, status+time等）

### 3.2 events表索引

```sql
-- 外键索引
CREATE INDEX idx_events_trace_id ON events(trace_id);

-- 查询索引
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_timestamp ON events(timestamp);

-- 组合索引
CREATE INDEX idx_events_trace_seq ON events(trace_id, sequence_number);
```

**设计理由**:
- `trace_id`: 外键，查询某个trace的所有events
- `event_type`: 按类型筛选events
- `timestamp`: 时间范围查询
- `trace_id + sequence_number`: 查询并排序某个trace的events

### 3.3 captures表索引

```sql
-- 唯一索引
CREATE UNIQUE INDEX idx_captures_capture_id ON captures(capture_id);

-- 外键索引
CREATE INDEX idx_captures_trace_id ON captures(trace_id);
CREATE INDEX idx_captures_event_id ON captures(event_id);

-- 查询索引
CREATE INDEX idx_captures_provider ON captures(provider);
CREATE INDEX idx_captures_model ON captures(model);
CREATE INDEX idx_captures_timestamp ON captures(timestamp);
CREATE INDEX idx_captures_total_tokens ON captures(total_tokens);
CREATE INDEX idx_captures_cost ON captures(cost_usd);

-- 组合索引
CREATE INDEX idx_captures_provider_model ON captures(provider, model);
```

**设计理由**:
- `capture_id`: 业务主键
- `trace_id`, `event_id`: 关联查询
- `provider`, `model`: 按LLM提供商/模型筛选
- `timestamp`: 时间范围查询
- `total_tokens`, `cost_usd`: 统计分析

---

## 4. 查询优化

### 4.1 常见查询场景

#### 场景1: Dashboard列表查询
```sql
-- 查询最近的traces，按时间降序，支持分页
SELECT
    trace_id, agent_name, start_time, end_time,
    status, total_events, llm_calls_count,
    total_tokens, total_cost_usd, quality_score
FROM traces
WHERE status IN ('completed', 'failed')
  AND start_time >= ?  -- 日期范围
  AND start_time <= ?
ORDER BY start_time DESC
LIMIT ? OFFSET ?;

-- 使用索引: idx_traces_status_time
```

#### 场景2: 按Agent筛选
```sql
SELECT *
FROM traces
WHERE agent_name = ?
  AND status = 'completed'
ORDER BY start_time DESC
LIMIT 20;

-- 使用索引: idx_traces_agent_status
```

#### 场景3: 按成本排序
```sql
SELECT *
FROM traces
WHERE status = 'completed'
ORDER BY total_cost_usd DESC
LIMIT 20;

-- 使用索引: idx_traces_status, idx_traces_total_cost
```

#### 场景4: 查询Trace的所有Events
```sql
SELECT *
FROM events
WHERE trace_id = ?
ORDER BY sequence_number ASC;

-- 使用索引: idx_events_trace_seq
```

#### 场景5: 统计查询
```sql
-- 统计总数、总成本、总tokens
SELECT
    COUNT(*) as total_traces,
    SUM(total_tokens) as total_tokens,
    SUM(total_cost_usd) as total_cost,
    AVG(quality_score) as avg_quality
FROM traces
WHERE status = 'completed'
  AND start_time >= ?;

-- 使用索引: idx_traces_status_time
```

### 4.2 性能优化建议

1. **使用EXPLAIN QUERY PLAN分析**
```sql
EXPLAIN QUERY PLAN
SELECT * FROM traces WHERE agent_name = 'test-agent' ORDER BY start_time DESC;
```

2. **定期VACUUM**
```sql
VACUUM;  -- 重新组织数据库文件，优化空间
```

3. **定期ANALYZE**
```sql
ANALYZE;  -- 更新查询优化器的统计信息
```

4. **使用事务批量插入**
```sql
BEGIN TRANSACTION;
INSERT INTO traces (...) VALUES (...);
INSERT INTO events (...) VALUES (...);
COMMIT;
```

---

## 5. 数据完整性

### 5.1 外键约束

- `events.trace_id` → `traces.trace_id` (ON DELETE CASCADE)
  - 删除trace时自动删除关联的events

- `captures.trace_id` → `traces.trace_id` (ON DELETE SET NULL)
  - 删除trace时capture的trace_id设为NULL（capture可以独立存在）

- `captures.event_id` → `events.id` (ON DELETE SET NULL)
  - 删除event时capture的event_id设为NULL

### 5.2 触发器

#### 自动更新updated_at
```sql
CREATE TRIGGER update_traces_timestamp
AFTER UPDATE ON traces
FOR EACH ROW
BEGIN
    UPDATE traces SET updated_at = julianday('now') WHERE id = NEW.id;
END;
```

#### 自动更新统计信息
```sql
-- 插入event时更新traces.total_events
CREATE TRIGGER increment_event_count
AFTER INSERT ON events
FOR EACH ROW
BEGIN
    UPDATE traces
    SET total_events = total_events + 1
    WHERE trace_id = NEW.trace_id;
END;

-- 删除event时更新traces.total_events
CREATE TRIGGER decrement_event_count
AFTER DELETE ON events
FOR EACH ROW
BEGIN
    UPDATE traces
    SET total_events = total_events - 1
    WHERE trace_id = OLD.trace_id;
END;
```

### 5.3 CHECK约束

```sql
-- 在表定义中添加CHECK约束
CREATE TABLE traces (
    ...
    status TEXT NOT NULL DEFAULT 'running'
        CHECK(status IN ('running', 'completed', 'failed')),

    quality_score REAL CHECK(quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 100)),

    total_events INTEGER DEFAULT 0 CHECK(total_events >= 0),
    total_tokens INTEGER DEFAULT 0 CHECK(total_tokens >= 0),
    total_cost_usd REAL DEFAULT 0.0 CHECK(total_cost_usd >= 0),
    ...
);
```

---

## 6. 数据迁移

### 6.1 JSONL → SQLite

**迁移策略**:
1. 读取JSONL文件
2. 解析每条trace
3. 插入traces表
4. 插入events表
5. 提交事务

**伪代码**:
```python
with db.transaction():
    for trace_data in read_jsonl(file):
        # 插入trace
        trace_id = insert_trace(trace_data)

        # 插入events
        for event in trace_data['events']:
            insert_event(trace_id, event)
```

### 6.2 增量迁移

**策略**: 只迁移新增的traces
- 记录最后迁移的trace_id或时间戳
- 下次迁移时只处理新数据

---

## 7. 版本管理

### 7.1 Schema版本表

```sql
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at REAL NOT NULL DEFAULT (julianday('now')),
    description TEXT
);

-- 插入初始版本
INSERT INTO schema_version (version, description)
VALUES (1, 'Initial schema with traces, events, and captures tables');
```

### 7.2 升级脚本

**目录结构**:
```
scripts/migrations/
├── v1_initial_schema.sql
├── v2_add_quality_metrics.sql
└── v3_add_captures_table.sql
```

---

## 8. 与现有代码的兼容性

### 8.1 Trace类映射

| Trace类字段 | 数据库字段 | 转换 |
|------------|-----------|------|
| trace_id | trace_id | 直接映射 |
| agent_name | agent_name | 直接映射 |
| task_id | task_id | 直接映射 |
| start_time | start_time | float → REAL |
| end_time | end_time | float → REAL |
| events | events表 | List → 多行 |
| metadata | metadata | dict → JSON TEXT |

### 8.2 查询接口兼容

保持现有的`TraceStore.query_traces()`接口不变：
```python
def query_traces(
    agent_name: Optional[str] = None,
    task_id: Optional[str] = None,
    start_after: Optional[float] = None,
    end_before: Optional[float] = None
) -> List[Trace]:
    # 内部使用SQL查询
    # 返回Trace对象列表
```

---

## 9. 安全考虑

### 9.1 SQL注入防护
- ✅ 使用参数化查询
- ✅ 不直接拼接SQL字符串
- ✅ 验证输入参数

### 9.2 数据备份
- 定期备份SQLite文件
- 支持导出为JSONL格式（向后兼容）

### 9.3 并发控制
- SQLite默认支持多读单写
- 使用WAL模式提升并发性能
```python
conn.execute("PRAGMA journal_mode=WAL")
```

---

## 10. 总结

### 10.1 优势
✅ **性能**: 索引优化，快速查询
✅ **扩展性**: 预留字段，支持未来功能
✅ **完整性**: 外键约束，触发器自动维护
✅ **兼容性**: 保持现有接口不变
✅ **维护性**: 版本管理，支持平滑升级

### 10.2 待审核项
- [ ] 表结构是否合理？
- [ ] 索引策略是否满足查询需求？
- [ ] 是否需要调整字段类型或添加新字段？
- [ ] 外键约束是否合理？
- [ ] 触发器逻辑是否正确？

---

**下一步**: 编写SQL DDL脚本

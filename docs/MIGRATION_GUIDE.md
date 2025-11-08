# TigerHill 数据迁移指南

**版本**: v0.0.3
**日期**: 2025-11-04

---

## 📋 概述

本指南介绍如何将TigerHill的trace数据从JSONL文件格式迁移到SQLite数据库。

### 为什么需要迁移？

- **性能提升**: 数据库查询比文件系统扫描快得多
- **高级查询**: 支持复杂的筛选、排序、聚合操作
- **数据完整性**: 外键约束和触发器确保数据一致性
- **可扩展性**: 支持10,000+条trace记录

---

## 🚀 快速开始

### 基本用法

```bash
# 从默认目录迁移到默认数据库
PYTHONPATH=. python scripts/migrate_to_db.py
```

### 指定源目录和目标数据库

```bash
PYTHONPATH=. python scripts/migrate_to_db.py \
  -s ./test_traces \
  -d ./tigerhill.db
```

### 显示详细日志

```bash
PYTHONPATH=. python scripts/migrate_to_db.py -v
```

---

## 📖 命令行参数

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--source` | `-s` | `./test_traces` | 包含trace JSON文件的源目录 |
| `--database` | `-d` | `./tigerhill.db` | 目标SQLite数据库路径 |
| `--no-incremental` | - | - | 禁用增量迁移（重新插入已存在的traces） |
| `--verbose` | `-v` | - | 启用详细日志输出 |
| `--help` | `-h` | - | 显示帮助信息 |

---

## 🔄 增量迁移

默认情况下，迁移工具支持增量迁移：

- 检查每个trace是否已存在于数据库
- 跳过已存在的traces
- 只插入新的traces

### 示例：初次迁移

```bash
$ PYTHONPATH=. python scripts/migrate_to_db.py

============================================================
TigerHill 数据迁移工具
============================================================
源目录: /path/to/test_traces
目标数据库: /path/to/tigerhill.db
增量迁移: 是
详细日志: 否
============================================================

开始迁移 49 个trace文件...

进度: 49/49 | 成功: 49 | 跳过: 0 | 失败: 0

============================================================

迁移统计:
  总文件数: 49
  处理成功: 49
  已存在跳过: 0
  处理失败: 0
  插入traces: 49
  插入events: 140

============================================================
```

### 示例：增量迁移

再次运行相同命令：

```bash
$ PYTHONPATH=. python scripts/migrate_to_db.py

进度: 49/49 | 成功: 0 | 跳过: 49 | 失败: 0

迁移统计:
  总文件数: 49
  处理成功: 0
  已存在跳过: 49
  处理失败: 0
  插入traces: 0
  插入events: 0
```

所有traces都被跳过！

---

## 🛠️ 高级用法

### 完全重新迁移

如果需要重新迁移所有数据（覆盖已存在的），使用 `--no-incremental` 选项：

```bash
# 警告：这会删除并重新创建数据库
rm tigerhill.db*  # 删除现有数据库

PYTHONPATH=. python scripts/migrate_to_db.py --no-incremental
```

### 详细日志模式

使用 `-v` 查看每个trace的详细处理信息：

```bash
PYTHONPATH=. python scripts/migrate_to_db.py -v
```

输出示例：

```
2025-11-04 00:57:54,645 - INFO - [1/49] Success: 9a343be0-5e63-43cf-a11c-db6497d59623 (3 events)
2025-11-04 00:57:54,645 - INFO - [2/49] Success: 38a2d939-fa7b-47a2-89e9-a377416f6dc7 (2 events)
...
```

### 迁移多个目录

可以多次运行迁移工具，从不同目录导入：

```bash
# 迁移生产traces
PYTHONPATH=. python scripts/migrate_to_db.py -s ./prod_traces

# 迁移测试traces
PYTHONPATH=. python scripts/migrate_to_db.py -s ./test_traces

# 迁移历史traces
PYTHONPATH=. python scripts/migrate_to_db.py -s ./archive_traces
```

增量迁移会自动跳过重复的traces。

---

## 🔍 验证迁移结果

### 使用SQLite命令行工具

```bash
sqlite3 tigerhill.db

sqlite> SELECT COUNT(*) FROM traces;
49

sqlite> SELECT COUNT(*) FROM events;
140

sqlite> SELECT trace_id, agent_name, status, total_events
        FROM traces
        LIMIT 5;
```

### 使用Python验证

```python
from tigerhill.storage.database import DatabaseManager

db = DatabaseManager('./tigerhill.db')

# 查询traces数量
traces_count = db.fetch_one('SELECT COUNT(*) as count FROM traces')
print(f'总traces数: {traces_count["count"]}')

# 查询events数量
events_count = db.fetch_one('SELECT COUNT(*) as count FROM events')
print(f'总events数: {events_count["count"]}')

# 查询前5个traces
traces = db.fetch_all('''
    SELECT trace_id, agent_name, status, total_events
    FROM traces
    ORDER BY start_time DESC
    LIMIT 5
''')
for t in traces:
    print(f'  {t["trace_id"][:8]}... | {t["agent_name"]} | {t["status"]} | {t["total_events"]} events')
```

---

## ⚠️ 常见问题

### 问题1: "Source directory does not exist"

**错误信息**:
```
ERROR - Source directory does not exist: ./test_traces
```

**解决方案**:
- 检查源目录路径是否正确
- 使用绝对路径或相对于当前工作目录的路径

### 问题2: 迁移失败

**错误信息**:
```
ERROR - [5/49] Failed: trace_abc123.json - UNIQUE constraint failed: traces.trace_id
```

**解决方案**:
- 这通常是因为trace_id重复
- 检查源文件是否有重复的trace_id
- 如果需要覆盖，先删除数据库文件

### 问题3: 数据库锁定

**错误信息**:
```
ERROR - database is locked
```

**解决方案**:
- 关闭所有正在访问数据库的程序（Dashboard、其他脚本）
- 等待当前操作完成后再运行迁移

---

## 🗃️ 数据格式

### 源格式 (JSONL)

每个trace存储在单独的JSON文件中：

```json
{
  "trace_id": "9a343be0-5e63-43cf-a11c-db6497d59623",
  "agent_name": "python_agent",
  "task_id": null,
  "start_time": 1730617874.537941,
  "end_time": 1730617874.5438201,
  "events": [
    {
      "event_id": "e1",
      "trace_id": "9a343be0-...",
      "event_type": "prompt",
      "timestamp": 1730617874.537941,
      "data": {...},
      "metadata": {...}
    }
  ],
  "metadata": {...}
}
```

### 目标格式 (SQLite)

数据被拆分到两个表：

**traces表**:
```sql
trace_id, agent_name, task_id, start_time, end_time,
duration_seconds, status, total_events, llm_calls_count,
total_tokens, total_cost_usd, quality_score, ...
```

**events表**:
```sql
trace_id, event_type, timestamp, sequence_number, data
```

---

## 📊 性能数据

基于实际测试数据：

| 指标 | 值 |
|------|-----|
| 测试文件数 | 49个traces |
| 总events数 | 140个events |
| 迁移时间 | ~0.15秒 |
| 处理速度 | ~326 traces/秒 |
| 数据库大小 | ~150KB |

---

## 🔐 数据安全

### 迁移前备份

建议在迁移前备份原始数据：

```bash
# 备份JSONL文件
tar -czf traces_backup_$(date +%Y%m%d).tar.gz ./test_traces

# 如果数据库已存在，也备份
cp tigerhill.db tigerhill.db.backup
```

### 事务保证

迁移工具使用数据库事务：

- 每个trace的插入是原子操作
- 如果插入失败，自动回滚
- 不会留下不完整的数据

---

## 🚦 最佳实践

1. **首次迁移前测试**
   ```bash
   # 使用测试数据库
   PYTHONPATH=. python scripts/migrate_to_db.py -d test.db -v
   ```

2. **使用增量迁移**
   - 保持默认的增量模式
   - 定期运行以导入新traces

3. **监控迁移进度**
   - 对于大量数据，使用 `-v` 查看详细进度
   - 检查统计信息中的失败数

4. **验证数据完整性**
   - 迁移后使用SQL查询验证
   - 对比源文件数量和数据库记录数

---

## 📚 相关文档

- [数据库Schema设计](design/database_schema.md)
- [SQLite TraceStore API](../tigerhill/storage/README.md)
- [Dashboard使用指南](../tigerhill/web/dashboard/README.md)

---

## 🆘 获取帮助

```bash
# 查看完整帮助信息
PYTHONPATH=. python scripts/migrate_to_db.py --help

# 查看版本信息
PYTHONPATH=. python scripts/migrate_to_db.py --version
```

如遇到问题，请查阅 [故障排查指南](TROUBLESHOOTING.md) 或提交Issue。

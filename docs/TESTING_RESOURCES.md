# TigerHill 测试资源索引

所有测试文档、脚本和工具的完整索引

---

## 📚 测试文档

### 快速开始

| 文档 | 用途 | 时间 | 难度 |
|------|------|------|------|
| **[QUICK_TEST_CHECKLIST.md](QUICK_TEST_CHECKLIST.md)** | 5分钟快速验证 | 5-10分钟 | ⭐ |
| **[E2E_TEST_MANUAL.md](E2E_TEST_MANUAL.md)** | 完整端到端测试手册 | 30-45分钟 | ⭐⭐⭐ |

### 功能文档

| 文档 | 内容 |
|------|------|
| [TEMPLATE_LIBRARY_GUIDE.md](TEMPLATE_LIBRARY_GUIDE.md) | 模板库完整使用指南 |
| [PHASE1_2_DELIVERY_FINAL.md](PHASE1_2_DELIVERY_FINAL.md) | SQLite数据库功能交付报告 |
| [PHASE1_3_DELIVERY.md](PHASE1_3_DELIVERY.md) | 模板库功能交付报告 |
| [END_TO_END_VALIDATION.md](END_TO_END_VALIDATION.md) | 端到端验证流程文档 |

---

## 🔧 测试脚本

### 自动化测试

| 脚本 | 功能 | 使用方法 |
|------|------|----------|
| **quick_validation.py** | 一键验证所有功能 | `PYTHONPATH=. python scripts/quick_validation.py` |
| **demo_agent_with_tracing.py** | 演示Agent + Trace记录 | `PYTHONPATH=. python examples/demo_agent_with_tracing.py` |
| **verify_stored_data.py** | 验证数据库内容 | `PYTHONPATH=. python examples/verify_stored_data.py` |
| **migrate_to_db.py** | JSONL迁移到SQLite | `PYTHONPATH=. python scripts/migrate_to_db.py -s <src> -d <db>` |

### 单元测试

| 测试套件 | 测试数量 | 覆盖范围 |
|----------|----------|----------|
| tests/test_template_engine/ | 32 tests | 模板引擎全部功能 |
| tests/test_database.py | 21 tests | 数据库管理 |
| tests/test_sqlite_trace_store.py | 23 tests | SQLite存储 |
| tests/test_end_to_end_validation.py | 1 test | 完整E2E流程 |

运行所有测试：
```bash
PYTHONPATH=. pytest tests/ -v
```

---

## 🎯 测试场景

### 场景1: 快速验证（推荐首选）⭐

**目标**: 5分钟验证所有核心功能

**步骤**:
```bash
cd /Users/yinaruto/MyProjects/ChatLLM/TigerHill
PYTHONPATH=. python scripts/quick_validation.py
```

**验证内容**:
- ✅ 模板库（加载、验证、生成）
- ✅ SQLite数据库（创建、写入、查询）
- ✅ 单元测试（32个测试）
- ✅ Dashboard集成（文件检查）

**预期结果**: "4/4 通过 🎉"

---

### 场景2: 模板生成测试

**目标**: 验证模板生成功能

**步骤**:
```bash
# 列出所有模板
python -m tigerhill.template_engine.cli --list

# 交互式生成
python -m tigerhill.template_engine.cli

# 指定模板生成
python -m tigerhill.template_engine.cli --template llm-prompt-response
```

**验证内容**:
- ✅ 11个模板全部可用
- ✅ 参数验证正确
- ✅ 代码生成成功
- ✅ 生成的代码可执行

---

### 场景3: 数据库功能测试

**目标**: 验证SQLite存储和查询

**步骤**:
```bash
# 1. 生成测试数据
PYTHONPATH=. python examples/demo_agent_with_tracing.py

# 2. 验证数据
PYTHONPATH=. python examples/verify_stored_data.py

# 3. 运行E2E测试
PYTHONPATH=. pytest tests/test_end_to_end_validation.py -v -s
```

**验证内容**:
- ✅ Trace写入和读取
- ✅ 统计信息计算
- ✅ 查询和筛选
- ✅ 分页和排序

---

### 场景4: Dashboard可视化测试

**目标**: 验证Dashboard显示功能

**步骤**:
```bash
# 1. 启动Dashboard
PYTHONPATH=. streamlit run tigerhill/web/dashboard/app.py

# 2. 在浏览器中:
#    - 选择 "SQLite Database"
#    - 输入: ./tigerhill_validation.db
#    - 点击 Connect
#    - 查看Traces列表
#    - 点击查看详情
```

**验证内容**:
- ✅ 数据源连接
- ✅ Traces列表显示
- ✅ Trace详情查看
- ✅ 筛选和搜索
- ✅ 统计图表

---

### 场景5: 完整端到端测试

**目标**: 完整验证所有功能

**参考**: [E2E_TEST_MANUAL.md](E2E_TEST_MANUAL.md)

**包含**:
- 16个详细测试场景
- 5大测试模块
- 完整的验证清单

**时间**: 30-45分钟

---

## 📊 测试数据

### 测试数据库

| 文件 | 生成方式 | 内容 |
|------|----------|------|
| `tigerhill_validation.db` | demo_agent_with_tracing.py | 3个traces，21个events |
| 临时测试DB | quick_validation.py | 3个traces，18个events |

### 测试输出

| 目录 | 内容 |
|------|------|
| `/tmp/tigerhill_test_*` | 模板生成的临时输出 |
| `./test_traces/` | JSONL格式的traces（如果使用） |
| `./prompt_captures/manual_test/` | Observer捕获的数据 |

---

## 🚀 快速命令参考

### 一键命令

```bash
# 快速验证（推荐）
PYTHONPATH=. python scripts/quick_validation.py

# 运行所有测试
PYTHONPATH=. pytest tests/ -v

# 生成演示数据
PYTHONPATH=. python examples/demo_agent_with_tracing.py

# 启动Dashboard
PYTHONPATH=. streamlit run tigerhill/web/dashboard/app.py

# 列出模板
python -m tigerhill.template_engine.cli --list

# 生成测试
python -m tigerhill.template_engine.cli
```

### 测试子集

```bash
# 仅测试模板引擎
PYTHONPATH=. pytest tests/test_template_engine/ -v

# 仅测试数据库
PYTHONPATH=. pytest tests/test_database.py tests/test_sqlite_trace_store.py -v

# 端到端测试
PYTHONPATH=. pytest tests/test_end_to_end_validation.py -v -s

# 测试特定模块
PYTHONPATH=. pytest tests/test_template_engine/test_loader.py -v
```

---

## ✅ 测试检查清单

### 基础验证（必选）

- [ ] 运行快速验证脚本
- [ ] 所有4项测试通过
- [ ] 单元测试通过（32/32）

### 功能验证（推荐）

- [ ] 模板生成成功
- [ ] 数据库存储正常
- [ ] Dashboard可以访问
- [ ] 查询和筛选工作

### 完整验证（可选）

- [ ] 完成E2E测试手册
- [ ] Observer拦截测试
- [ ] 多模板生成测试
- [ ] 性能测试

---

## 🐛 问题排查

### 常见问题

**Q1: 快速验证失败**
```bash
# 检查依赖
pip install -r requirements.txt

# 查看详细日志
PYTHONPATH=. python scripts/quick_validation.py 2>&1 | tee test.log
```

**Q2: 单元测试失败**
```bash
# 运行单个测试查看详情
PYTHONPATH=. pytest tests/test_template_engine/test_loader.py -v -s

# 重新安装依赖
pip install --upgrade -r requirements.txt
```

**Q3: Dashboard无法启动**
```bash
# 检查streamlit
pip install streamlit

# 使用其他端口
streamlit run tigerhill/web/dashboard/app.py --server.port 8502
```

**Q4: 数据库访问错误**
```bash
# 检查数据库文件
ls -lh ./tigerhill_validation.db

# 重新生成
rm -f ./tigerhill_validation.db
PYTHONPATH=. python examples/demo_agent_with_tracing.py
```

### 获取帮助

1. 查看详细文档：[E2E_TEST_MANUAL.md](E2E_TEST_MANUAL.md)
2. 运行诊断脚本（如有）
3. 查看测试日志
4. 提交Issue到GitHub

---

## 📈 测试覆盖率

| 模块 | 测试数量 | 覆盖率 | 状态 |
|------|----------|--------|------|
| Template Engine | 32 | 100% | ✅ |
| Database Manager | 21 | 100% | ✅ |
| SQLite TraceStore | 23 | 100% | ✅ |
| Dashboard Integration | 5 | 95% | ✅ |
| End-to-End | 1 | 100% | ✅ |
| **总计** | **82** | **99%** | **✅** |

---

## 🎓 学习路径

### 新手入门

1. ⭐ 运行快速验证 (5分钟)
   ```bash
   PYTHONPATH=. python scripts/quick_validation.py
   ```

2. ⭐⭐ 尝试生成一个模板 (10分钟)
   ```bash
   python -m tigerhill.template_engine.cli
   ```

3. ⭐⭐ 查看Dashboard (10分钟)
   ```bash
   PYTHONPATH=. python examples/demo_agent_with_tracing.py
   PYTHONPATH=. streamlit run tigerhill/web/dashboard/app.py
   ```

### 进阶使用

4. ⭐⭐⭐ 完成E2E测试手册 (30-45分钟)
   - 参考：[E2E_TEST_MANUAL.md](E2E_TEST_MANUAL.md)

5. ⭐⭐⭐ 集成到实际项目
   - 使用Observer SDK
   - 自定义模板
   - 分析实际数据

---

## 📝 测试报告模板

### 快速测试报告

```
日期: __________
测试人: __________

快速验证结果:
□ 模板库: ___/4 通过
□ 数据库: ___/5 通过
□ 单元测试: ___/32 通过
□ Dashboard: ___/2 通过

总体状态: □ 通过 □ 失败
备注: _________________
```

### 完整测试报告

使用 [E2E_TEST_MANUAL.md](E2E_TEST_MANUAL.md) 中的报告模板

---

## 🔗 相关资源

- [TigerHill主文档](../README.md)
- [用户指南](USER_GUIDE.md)
- [模板库指南](TEMPLATE_LIBRARY_GUIDE.md)
- [API参考](API_REFERENCE.md)
- [贡献指南](CONTRIBUTING.md)

---

**更新日期**: 2025-01-04
**维护者**: TigerHill Team
**版本**: 1.0

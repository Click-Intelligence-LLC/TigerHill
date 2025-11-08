# TigerHill 快速测试清单

**预计时间**: 5-10分钟
**适用人员**: 开发者、测试人员
**前置条件**: Python 3.8+，已安装依赖

---

## 一键快速验证 ⚡

```bash
cd /Users/yinaruto/MyProjects/ChatLLM/TigerHill

# 运行快速验证脚本
PYTHONPATH=. python scripts/quick_validation.py
```

**预期输出**:
```
🎯 TigerHill 快速验证
============================================================

测试1: 模板库功能
✅ 找到 11 个模板 (预期: 11+)
✅ 模板加载成功: HTTP API Testing
✅ 参数验证通过
✅ 生成 3 个文件
✅ 模板库功能测试通过!

测试2: SQLite数据库功能
✅ 数据库创建成功
✅ 写入 3 个Traces
✅ 查询到 3 个Traces
✅ 验证统计信息 (4项全部正确)
✅ 筛选查询正确
✅ SQLite数据库功能测试通过!

测试3: 单元测试套件
✅ 单元测试通过: 32 个测试

测试4: Dashboard集成
✅ Dashboard应用存在
✅ DataLoader存在
✅ Dashboard集成检查通过!

📊 验证结果汇总
✅ 模板库: 通过
✅ SQLite数据库: 通过
✅ 单元测试: 通过
✅ Dashboard集成: 通过

总计: 4/4 通过

🎉 所有测试通过！TigerHill已准备就绪！
```

**验证点**: ✅ 显示 "4/4 通过"

---

## 手动测试步骤（可选）

如果想手动验证每个功能，按照以下步骤：

### ✅ 步骤 1: 测试模板生成（2分钟）

```bash
# 列出所有模板
python -m tigerhill.template_engine.cli --list

# 应该显示11个模板
```

**验证**: 看到11个模板列表

---

### ✅ 步骤 2: 测试数据库存储（3分钟）

```bash
# 运行演示Agent
PYTHONPATH=. python examples/demo_agent_with_tracing.py

# 查看生成的数据库
ls -lh ./tigerhill_validation.db

# 验证数据
PYTHONPATH=. python examples/verify_stored_data.py
```

**验证**:
- 数据库文件存在
- 显示3个traces
- 每个trace有7个events

---

### ✅ 步骤 3: 测试Dashboard（3分钟）

```bash
# 启动Dashboard
PYTHONPATH=. streamlit run tigerhill/web/dashboard/app.py
```

在浏览器中（http://localhost:8501）：
1. 侧边栏选择 "SQLite Database"
2. 输入路径: `./tigerhill_validation.db`
3. 点击 Connect

**验证**:
- 显示3个traces
- 可以点击查看详情
- 统计信息正确

按 `Ctrl+C` 停止Dashboard

---

### ✅ 步骤 4: 运行完整测试（2分钟）

```bash
# 运行所有测试
PYTHONPATH=. pytest tests/test_template_engine/ -v

# 运行端到端测试
PYTHONPATH=. pytest tests/test_end_to_end_validation.py -v -s
```

**验证**: 所有测试通过

---

## 完整端到端测试（10-15分钟）

参考详细文档：[E2E_TEST_MANUAL.md](E2E_TEST_MANUAL.md)

包含16个详细测试场景，涵盖：
- 模板库（3项）
- SQLite数据库（3项）
- Dashboard可视化（5项）
- Observer SDK（3项）
- 集成测试（2项）

---

## 测试结果记录

**日期**: _______________

| 测试项 | 状态 | 备注 |
|--------|------|------|
| 一键快速验证 | ⬜ 通过 / ⬜ 失败 | |
| 模板生成 | ⬜ 通过 / ⬜ 失败 | |
| 数据库存储 | ⬜ 通过 / ⬜ 失败 | |
| Dashboard | ⬜ 通过 / ⬜ 失败 | |
| 完整测试 | ⬜ 通过 / ⬜ 失败 | |

**测试人员**: _______________

**总体评价**: ⬜ 全部通过 / ⬜ 基本通过 / ⬜ 有问题

---

## 常见问题

### Q1: 快速验证失败怎么办？

```bash
# 查看详细错误
PYTHONPATH=. python scripts/quick_validation.py 2>&1 | tee validation.log

# 检查依赖
pip install -r requirements.txt

# 重新运行测试
PYTHONPATH=. pytest tests/ -v
```

### Q2: Dashboard无法启动？

```bash
# 安装streamlit
pip install streamlit

# 检查端口
lsof -i :8501

# 使用其他端口
streamlit run tigerhill/web/dashboard/app.py --server.port 8502
```

### Q3: 模板生成失败？

```bash
# 检查依赖
pip install jinja2 pyyaml

# 测试单个模板
python -m tigerhill.template_engine.cli --template http-api-test
```

### Q4: 如何导入capture_*.json文件到数据库？

```bash
# 使用新的迁移工具
python scripts/migrate_captures_to_db.py \
  -s ./prompt_captures \
  -d ./my_captures.db

# 查看导入的数据
sqlite3 ./my_captures.db "SELECT COUNT(*) FROM traces; SELECT COUNT(*) FROM events;"
```

支持的格式：
- `capture_*.json` - PromptCapture生成
- `trace_*.json` - TraceStore生成
- `gemini_session_*.jsonl` - Gemini session

---

## 下一步

测试通过后，您可以：

1. **使用模板生成测试**
   ```bash
   python -m tigerhill.template_engine.cli
   ```

2. **查看文档**
   - [模板库指南](TEMPLATE_LIBRARY_GUIDE.md)
   - [用户指南](USER_GUIDE.md)
   - [完整测试手册](E2E_TEST_MANUAL.md)

3. **集成到项目**
   - 使用Observer SDK拦截LLM
   - 将Traces存储到数据库
   - 使用Dashboard分析

---

**快速验证通过？** 🎉 恭喜！TigerHill已准备就绪！

**遇到问题？** 📖 查看 [E2E_TEST_MANUAL.md](E2E_TEST_MANUAL.md) 获取详细指导

# Changelog

All notable changes to TigerHill will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.3] - 2025-11-07

### Added

#### Gemini CLI 支持
- ✨ 完整的 Gemini CLI 复杂任务捕获支持
- ✨ 修复版 Gemini Session Interceptor (`gemini_session_interceptor.cjs`)
- ✨ 支持多轮对话的完整追踪
- ✨ 自动捕获系统 Prompt、用户输入和 AI 回复
- ✨ Token 使用统计和成本计算
- ✨ 会话级别的数据管理

#### Observer SDK 增强
- ✨ 修复 HTTP 响应流消费 bug（透明代理模式）
- ✨ 支持 SSE (Server-Sent Events) 流式响应
- ✨ 支持 gzip/deflate 压缩响应
- ✨ 结构化对话历史模型
- ✨ 自动数据脱敏（API keys、邮箱、信用卡等）
- ✨ 异步响应处理，不阻塞原始流程

#### 存储改进
- ✨ 修复数据库序列化问题
- ✨ 完善 SQLite TraceStore 实现
- ✨ 支持按成本、Token、标签等高级查询
- ✨ 自动统计计算（总轮次、总 Tokens、总成本等）

#### Dashboard 修复
- ✨ 修复 Dashboard 数据模型错误
- ✨ 修复 SQLite 集成问题
- ✨ 改进数据展示和可视化

#### 工具和脚本
- ✨ `view_latest_capture.py` - 查看最新捕获文件
- ✨ `migrate_to_db.py` - 捕获文件迁移到数据库
- ✨ `migrate_captures_to_db.py` - 批量迁移工具

#### 文档
- 📝 `GEMINI_CLI_INTERCEPTOR_GUIDE.md` - Gemini CLI 拦截器使用指南
- 📝 `GEMINI_CAPTURE_USAGE.md` - Gemini 捕获详细说明
- 📝 `GEMINI_429_ERROR.md` - API 限流问题说明
- 📝 `OBSERVER_SDK_DOCUMENTATION.md` - Observer SDK 完整文档
- 📝 `PHASE1_COMPLETION_SUMMARY.md` - Phase 1 功能总结

### Fixed

#### Critical Bugs
- 🐛 **修复 Gemini CLI Interceptor 流消费 bug**
  - 问题：旧版本直接监听 `res.on('data')`，消费了响应流
  - 影响：Gemini CLI 无法读取响应数据，报错 "Requested entity was not found"
  - 解决：使用透明代理模式，包装 `res.emit` 方法，复制数据副本
  - 结果：Gemini CLI 正常工作，TigerHill 成功捕获数据

- 🐛 **修复数据库存储序列化错误**
  - 问题：TraceEvent 对象无法正确序列化到 SQLite
  - 解决：实现 `to_db_dict()` 方法，正确处理嵌套对象和枚举类型

- 🐛 **修复 Dashboard 数据加载错误**
  - 问题：Dashboard 无法从 SQLite 加载数据
  - 解决：修复 data processor 的数据模型映射

#### Minor Bugs
- 🐛 修复 gzip 响应解压缩问题
- 🐛 修复 SSE 格式解析错误
- 🐛 修复会话存储跨进程同步问题
- 🐛 修复 conversation_history 统计计算

### Changed

- ♻️  重构 `gemini_session_interceptor.cjs`，集成透明代理修复并移除单独的 `_fixed` 版本
- ♻️  改进捕获文件命名：`session_conv_<uuid>_<timestamp>.json`
- ♻️  优化数据结构：添加 `conversation_history` 字段
- ♻️  改进错误处理：异步处理不阻塞原始流程

### Removed

- ❌ 移除 Codex/OpenAI 相关代码和文档（不在本次发布范围）
- ❌ 移除中间过程的调试和分析文档
- ❌ 移除临时测试脚本和数据文件

### Performance

- ⚡ 使用 `setImmediate()` 异步处理捕获数据，不影响 Gemini CLI 性能
- ⚡ 使用 `Buffer.from()` 复制数据，避免 buffer pool 重用问题
- ⚡ 额外内存开销：~10KB per response（可接受）
- ⚡ 额外时间开销：<10ms per request（可忽略）

### Testing

- ✅ TraceStore / SQLite 回归套件：23/23 通过
- ✅ Trace 序列化套件：12/12 通过
- ✅ Observer Phase 1 增强套件：18/18 通过
- ✅ 模板引擎 CLI & 生成套件：71/71 通过
- ⚠️ 依赖 AgentBay / 外部 API 的测试需在具备凭据的环境另行执行

### Documentation

完整的用户文档和 API 文档，包括：
- 快速开始指南
- 完整用户手册
- Observer SDK 文档
- 跨语言测试指南
- AgentBay 集成指南
- 架构分析文档

### Known Issues

- ⚠️  部分测试需要 Google API key（11 个测试跳过）
- ⚠️  Gemini API 可能遇到 429 限流（非 TigerHill 问题）
- ⚠️  Dashboard 可视化功能还需要更多图表类型

---

## [Unreleased]

### Planned Features

- 🔮 OpenAI/Anthropic Claude 支持
- 🔮 实时流式捕获 UI
- 🔮 Prompt 自动优化建议
- 🔮 成本预测和预警
- 🔮 团队协作功能
- 🔮 更多可视化图表
- 🔮 导出到常见格式（CSV、Excel 等）

---

## Version History

- **v0.0.3** (2025-11-07) - 初始发布：Gemini CLI 支持和 Bug 修复
- **v0.0.1** (2025-10-28) - 内部测试版本

---

## Migration Guide

### 从 v0.0.1 升级到 v0.0.3

#### Gemini CLI Interceptor

**旧版本（有 bug）**:
```bash
NODE_OPTIONS="--require ./tigerhill/observer/gemini_session_interceptor.cjs" \
node path/to/gemini-cli
```

**新版本（修复，默认内置）**:
```bash
NODE_OPTIONS="--require ./tigerhill/observer/gemini_session_interceptor.cjs" \
node path/to/gemini-cli
```

> 当前仓库中的 `gemini_session_interceptor.cjs` 已包含透明代理修复，
> 不再需要单独的 `_fixed` 文件或手动拷贝步骤。

#### 数据库迁移

如果你有旧的捕获数据：

```bash
# 迁移单个文件
python scripts/migrate_to_db.py capture_file.json

# 批量迁移
python scripts/migrate_captures_to_db.py ./prompt_captures/
```

---

## Credits

TigerHill is developed and maintained by the TigerHill team.

Special thanks to:
- Google Gemini team for the excellent AI models
- All contributors and testers

---

## License

Apache-2.0 License - see LICENSE file for details

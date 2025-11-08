# TigerHill Streamlit Dashboard

AI Agent 测试和分析的可视化仪表板。

## 功能特性

### ✅ 已实现 (Phase 1 Week 1-2)

- **📊 数据可视化**
  - 指标卡片：总测试数、Token数、成本、平均质量分
  - Trace列表：分页显示、筛选、排序
  - 趋势图表：Token分布、成本趋势、质量热力图

- **🔍 筛选和搜索**
  - 按Agent名称筛选
  - 按状态筛选（completed, running, failed）
  - 日期范围筛选
  - 成本范围筛选
  - 标签筛选

- **📈 多标签页**
  - 概览：Trace列表
  - 详情：单个Trace的详细信息
  - 分析：Prompt分析（占位符，待实现）
  - 趋势：多种图表展示

- **💾 数据持久化**
  - 基于TraceStore的数据加载
  - 支持本地文件存储

## 安装依赖

```bash
# 安装dashboard依赖
pip install streamlit>=1.28.0 plotly>=5.17.0 pandas>=2.0.0

# 或者使用项目配置
pip install -e ".[dashboard]"
```

## 使用方法

### 方法1: 使用启动脚本

```bash
cd tigerhill/web/dashboard
chmod +x run.sh
./run.sh
```

### 方法2: 直接运行

```bash
# 从项目根目录运行
PYTHONPATH=. streamlit run tigerhill/web/dashboard/app.py
```

### 方法3: 自定义配置

```bash
streamlit run tigerhill/web/dashboard/app.py \
    --server.port 8502 \
    --server.address 0.0.0.0 \
    --browser.gatherUsageStats false
```

## 配置

Dashboard默认从 `./test_traces` 目录加载数据。你可以在侧边栏修改数据源路径。

## 架构

```
dashboard/
├── app.py              # 主应用入口
├── components/         # UI组件
│   ├── sidebar.py     # 侧边栏（筛选器）
│   ├── metrics_cards.py  # 指标卡片
│   ├── trace_list.py  # Trace列表
│   ├── analysis_panel.py  # 分析面板
│   └── charts.py      # 图表组件
├── data/              # 数据层
│   ├── loader.py      # 数据加载器
│   └── processor.py   # 数据处理
├── models/            # 数据模型
│   ├── trace_metadata.py
│   ├── llm_call_record.py
│   ├── analysis_result.py
│   └── dashboard_state.py
└── utils/             # 工具函数
    └── formatters.py
```

## 数据模型

### TraceMetadata
- trace_id: 追踪ID
- agent_name: Agent名称
- start_time/end_time: 时间戳
- status: 状态（completed, running, failed）
- total_events: 事件总数
- llm_calls_count: LLM调用次数
- total_tokens: Token总数
- total_cost_usd: 成本（美元）
- quality_score: 质量分数（0-100）

## 测试

```bash
# 运行单元测试
PYTHONPATH=. pytest tests/test_dashboard_models.py tests/test_dashboard_processor.py -v

# 测试数据加载
PYTHONPATH=. python -c "
from tigerhill.web.dashboard.data.loader import DataLoader
loader = DataLoader(storage_path='./test_traces')
traces = loader.load_traces(limit=10)
print(f'Loaded {len(traces)} traces')
"
```

## 待开发功能

### Phase 1.2 (Week 3-4): 数据库存储
- SQLite集成
- 持久化筛选条件
- 历史数据对比

### Phase 1.3 (Week 5-6): 模板库和CLI向导
- 测试脚本模板库
- 交互式脚本生成
- 命令行工具

### Phase 2: Web平台
- FastAPI后端
- React前端
- 用户认证
- 在线调试

### Phase 3: 高级分析
- PromptAnalyzer集成
- 5维度质量分析
- 优化建议
- 成本预测

## 故障排除

### 问题：No module named 'streamlit'
```bash
pip install streamlit plotly pandas
```

### 问题：没有找到测试数据
确保 `test_traces` 目录存在且包含trace数据。运行测试生成数据：
```bash
PYTHONPATH=. pytest tests/test_adapters.py -v
```

### 问题：Port 8501 already in use
```bash
streamlit run tigerhill/web/dashboard/app.py --server.port 8502
```

## 贡献

欢迎提交Issue和Pull Request！

## License

Apache-2.0

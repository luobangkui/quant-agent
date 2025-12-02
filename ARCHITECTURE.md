# AI Agent + MCP 驱动的量化系统设计稿

本文档给出“Quant Core + Agent 外挂大脑”体系的代码结构设计、接口约定和渐进式落地路线，默认只提供信号、解释和通知，不直接下单。

## 目标原则
- **量化核心 = 纯后端服务**：数据、因子、回测、信号生成全部在后端完成。
- **Agent = 自然语言接口 + 编排器**：只调用工具、组合结果、生成解释、触发通知。
- **可组合、可扩展**：策略和工具均为插件化，方便新增和降权。

## 目录结构（建议）
```
.
├── core/                  # 量化核心逻辑（不依赖 LLM）
│   ├── data/              # 数据访问与适配器（DB/CSV/Parquet）
│   │   ├── loaders.py
│   │   └── registry.py
│   ├── strategies/        # 策略实现与注册
│   │   ├── base.py
│   │   ├── momentum.py
│   │   └── mean_reversion.py
│   ├── backtest/          # 回测引擎与绩效指标
│   │   ├── engine.py
│   │   └── metrics.py
│   ├── signals/           # 多策略综合信号生成
│   │   ├── generator.py
│   │   └── schema.py
│   ├── risk/              # 组合风险与策略健康检查
│   │   ├── exposure.py
│   │   └── health.py
│   └── portfolio/         # 组合/权重建议、持仓接口
│       └── allocator.py
├── api/                   # FastAPI/Flask HTTP 服务，暴露 JSON 接口
│   ├── main.py
│   ├── routers/
│   │   ├── signals.py
│   │   ├── backtest.py
│   │   ├── health.py
│   │   └── portfolio.py
│   └── schemas.py         # Pydantic 请求/响应模型
├── mcp_servers/           # MCP 服务器，转发到 api 服务或第三方
│   ├── quant_core_server.py
│   └── notifier_server.py
├── notifier/              # 通知服务（HTTP API），封装邮件/IM Webhook
│   ├── main.py
│   └── channels/
│       ├── email.py
│       ├── feishu.py
│       └── wecom.py
├── scripts/               # 本地脚本与调度入口（cron/手动）
│   ├── generate_signals.py
│   └── daily_report.py
├── tests/                 # 单元/集成测试
└── ARCHITECTURE.md        # 设计文档（当前文件）
```

## 核心模块与类设计

### 1. 数据层（core/data）
- `DataLoader` 接口：`load_price(symbols, start, end) -> pd.DataFrame`，`load_fundamental(symbols, fields, date)`。
- `Registry`：维护不同数据源适配器（本地文件、数据库、第三方 API）。

### 2. 策略层（core/strategies）
- `BaseStrategy`：定义 `generate_signals(data: pd.DataFrame, params: dict) -> pd.DataFrame`。
- 具体策略（如 `MomentumStrategy`, `MeanReversionStrategy`）继承基类；通过 `StrategyRegistry` 进行发现与参数管理。

### 3. 回测与绩效（core/backtest）
- `BacktestEngine`：输入策略、参数、历史数据，输出交易记录与净值曲线。
- `metrics.py`：实现 `cagr`, `max_drawdown`, `sharpe`, `win_rate` 等指标计算。

### 4. 信号生成（core/signals）
- `SignalGenerator`：聚合多策略信号，进行打分、冲突消解、目标权重计算。
- `SignalSchema`：标准化信号结构 `{symbol, name, side, target_weight, strategies, risk_tags}`。

### 5. 风险与健康检查（core/risk）
- `ExposureAnalyzer`：按行业/风格/波动率评估组合暴露。
- `StrategyHealthChecker`：窗口期内计算最近 Sharpe、回撤、换手率，给出 `status_suggestion`（如降权/停用）。

### 6. 组合管理（core/portfolio）
- `PortfolioAllocator`：根据信号、风险约束和资金规模生成建议持仓与权重。

## HTTP API 设计（api/）
基于 FastAPI：
- `POST /api/signals`：参数 `trade_date`, `universe`，返回综合信号列表。
- `POST /api/backtest`：参数 `strategy_id`, `params`, `start_date`, `end_date`，返回绩效指标与曲线地址。
- `GET  /api/strategy_health`：参数 `strategy_id`, `window_days`，返回健康度与建议。
- `GET  /api/portfolio`：可选 `trade_date/universe`，返回当前建议持仓或组合。

## MCP 工具设计（mcp_servers/）
通过 MCP 将 Agent 的 JSON-RPC 调用转发到 HTTP API 或通知服务。

### quant-core 工具集
- `get_signals(trade_date, universe)` → `/api/signals`
- `backtest_strategy(strategy_id, params, start_date, end_date)` → `/api/backtest`
- `get_strategy_health(strategy_id, window_days)` → `/api/strategy_health`

### notifier 工具集
- `send_message(channel, target, subject?, content)` → `notifier` 服务

工具 schema 与用户示例保持一致，Agent 只做编排与解释。

## 渐进式落地路线
1. **阶段 0：核心脚本** — 完成本地数据加载、策略、回测、信号生成脚本，可独立运行。
2. **阶段 1：HTTP 化** — 用 FastAPI 将信号、回测、健康度封装为 JSON API。
3. **阶段 2：MCP 化** — 编写 MCP 服务器转发到 HTTP API；在 Agent/Copilot 中配置 `quant-core`。
4. **阶段 3：通知渠道** — 实现 `notifier` HTTP API 与 MCP 工具，支持邮箱/企业微信/飞书机器人。
5. **阶段 4：订阅与调度** — 用 cron 或任务服务定时调用 Agent 提示词，自动生成日报/风险提醒（不触碰交易接口）。

## 约束与扩展点
- 默认不触发交易接口，所有输出仅为信号、建议与解释。
- 策略/数据/风险模块均插件化，`registry` 支持动态加载与权重调整。
- 方便后续增加：如 `risk_analyzer` 工具、更多因子/策略、日志与审计链路。

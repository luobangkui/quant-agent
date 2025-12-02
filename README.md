# Quant Agent

AI Agent + MCP 驱动的量化系统的轻量项目说明，默认只提供策略信号、解释与通知，不直接下单。详细设计见 [ARCHITECTURE.md](ARCHITECTURE.md)。

## 项目目标
- 量化核心保持纯后端：数据、因子、回测、信号生成均在 Python 服务中完成。
- Agent 仅做工具编排与文本解释：通过 MCP 调用量化核心与通知服务。
- 提供渐进式落地路径：从本地脚本到 HTTP API，再到 MCP 工具与订阅通知。

## 推荐目录结构
```
.
├── core/            # 量化核心（数据、策略、回测、信号、风险、组合）
├── api/             # FastAPI/Flask HTTP 服务，封装核心能力
├── mcp_servers/     # MCP Server，暴露 quant-core 与 notifier 工具
├── notifier/        # 通知服务（邮件/IM Webhook），仅推送不下单
├── scripts/         # 本地脚本与调度入口（信号生成、日报）
├── tests/           # 单元/集成测试
└── ARCHITECTURE.md  # 详细设计文档
```

## 核心能力（高层 API）
- `POST /api/signals`：综合多策略信号，返回标的、方向、目标权重与风险标签。
- `POST /api/backtest`：对指定策略与参数进行历史回测，输出收益、回撤、Sharpe 等指标。
- `GET  /api/strategy_health`：策略健康检查，提供近期 Sharpe、回撤与权重调整建议。
- `GET  /api/portfolio`：基于信号与风险约束生成建议持仓/组合。

## MCP 工具映射
- `quant-core/get_signals` → `/api/signals`
- `quant-core/backtest_strategy` → `/api/backtest`
- `quant-core/get_strategy_health` → `/api/strategy_health`
- `notifier/send_message` → 通知服务（邮件/飞书/企业微信等）

## 落地路线（示意）
1. **核心脚本阶段**：在 `core/` 与 `scripts/` 完成数据加载、策略、回测与信号生成。
2. **HTTP 化**：用 FastAPI/Flask 暴露 `/api/signals`、`/api/backtest`、`/api/strategy_health` 等接口。
3. **MCP 化**：实现 `mcp_servers/`，将 HTTP API 暴露为 MCP 工具，供 Agent 编排调用。
4. **通知/订阅**：接入 `notifier/` 服务与 MCP 工具，定时或条件触发生成日报/风险提醒（仅通知）。

## 安全边界
- 不连接交易接口；只提供信号、解释、风险提示与通知。
- 策略、数据源、风险模块均可插件化扩展，便于新增/降权与审计。

## 推送到 GitHub 的参考步骤
1. 关联远端仓库（本例使用你提供的 SSH 地址）：
   - `git remote add origin git@github.com:luobangkui/quant-agent.git`
   - 如需改为 HTTPS，可用 `https://github.com/luobangkui/quant-agent.git`
2. 确认当前分支（本地默认 `work`）：`git branch`
3. 首次推送到远端（本地 `work` → 远端 `main`，并建立跟踪关系）：`git push -u origin work:main`
4. 后续常规推送：`git push`

> 需要确保本地已配置可访问 GitHub 的 SSH key；如需保持同名分支，可直接 `git push -u origin work`，再在 GitHub 上设置默认分支。

## 本机会话可用的 SSH 公钥
- 将下列公钥添加到 GitHub（Settings → SSH and GPG keys → New SSH key），即可使用当前会话生成的私钥推送到 `git@github.com:luobangkui/quant-agent.git`：

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOdlkEK3uaOZs7KMVf9u6uEdyhPrMOrNhsq7XcSZ9kUw quant-agent-dev
```

- 私钥位于容器内 `/root/.ssh/quant-agent_ed25519`（仅当前会话可用，不会被提交到仓库）。如果容器重建，请重新生成并更新公钥。

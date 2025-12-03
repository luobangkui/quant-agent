# MCP 服务总览

- 端口规划（建议）：`50001~50006` 预留给 MCP 服务，按域分开，便于最小权限和独立部署。
  - `50001`：数据域（data-server，行情拉取/缓存检查）
  - 其他端口可留给策略/回测/通知等服务
- 启动方式：各子目录下的 `server.py` 直接运行，支持 `--port/--host` 参数或 `PORT/HOST` 环境变量。
- 依赖：统一使用 `requirements.txt`；如各域有额外依赖，可在子目录文档注明。

## 服务列表
- `mcp_servers/data/`：数据域 MCP，提供行情拉取、缓存检查、标的列表工具（默认端口 50001）。

后续新增服务（如策略/回测/通知）请在此处登记端口与简介，并在对应子目录编写 `TOOLS.md`。

## 启动脚本
- 数据域：`scripts/mcp/start_data_server.sh`（可用 HOST/PORT 环境变量覆盖，默认 127.0.0.1:50001）
  - 等价命令：`python mcp_servers/data/server.py --host 127.0.0.1 --port 50001`
  - 在 MCP 客户端配置时，将 host/port 指向运行中的进程。

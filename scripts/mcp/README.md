# MCP 启动脚本

## 数据域（data-service）
- 启动：`scripts/mcp/start_data_server.sh`
- 环境变量：
  - `HOST`（默认 127.0.0.1）
  - `PORT`（默认 50001，对应数据域 MCP）
  - `LOG_DIR`（默认仓库根目录下的 `logs/`）
  - `TRANSPORT`（默认 `sse`，可选 `stdio`/`sse`/`streamable-http`）
- 脚本会切换到仓库根目录，然后执行 `python mcp_servers/data/server.py`。
  - 日志自动写入 `LOG_DIR` 下的 `data_server_<port>.log`，同时输出到控制台。

> 其他域的 MCP 服务可按此模式添加新的启动脚本（如 `start_strategy_server.sh`）并在此文件补充说明。

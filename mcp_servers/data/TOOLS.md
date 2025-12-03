# 数据域 MCP 工具（data-service，默认端口 50001）

## 启动
- 命令：`python mcp_servers/data/server.py --port 50001 --host 127.0.0.1`
- 环境变量：可用 `PORT`/`HOST` 覆盖。
- 依赖：`requirements.txt`（含 jqdatasdk/pyarrow/pyyaml/mcp），`config/data.yaml` 配好聚宽账号与存储路径。

## 工具列表

### `fetch_prices`
- 功能：从聚宽拉取行情并落盘 Parquet，默认按缺口补齐。
- 参数：
  - `symbols: string[]`（必填）如 `["000001.XSHE","600000.XSHG"]`
  - `start: string`（必填）如 `2015-01-01`
  - `end: string`（必填）如 `2024-12-31`
  - `freq: string` 默认为 `1d`，可 `1m`
  - `full_refresh: bool` 默认 `false`，为 `true` 时全量重拉
  - `config_path: string` 默认 `config/data.yaml`
  - `log_level: string` 默认 `INFO`
- 返回：文本汇总，包含每标的的行数/缺口段数/状态。

### `check_cache`
- 功能：检查本地缓存（行数、时间范围、NaN 计数，日线缺口）。
- 参数：
  - `symbol: string`（必填）
  - `freq: string` 默认 `1d`
  - `start/end: string` 可选，限制检查区间
  - `config_path: string` 默认 `config/data.yaml`
- 返回：文本摘要，包含行数、范围、NaN，日线附缺口列表。

### `list_cached_symbols`
- 功能：扫描本地目录列出已缓存标的（限量）。
- 参数：
  - `freq: string` 默认 `1d`
  - `limit: int` 默认 50
  - `config_path: string` 默认 `config/data.yaml`
- 返回：文本列出标的（受 limit 限制）。

### `fetch_universe_prices`
- 功能：自动获取指定类型的标的列表（默认 stock，前 50 个），再批量拉取行情，支持本地缓存。
- 参数：
  - `start/end: string`（必填）
  - `types: string[]` 默认 `["stock"]`
  - `limit: int` 默认 50
  - `use_cache: bool` 默认 `true`，先用本地标的缓存
  - `refresh: bool` 默认 `false`，强制刷新标的列表
  - 其余同 `fetch_prices`（`freq/full_refresh/config_path/log_level`）
- 返回：同 `fetch_prices` 的汇总。

### `list_securities`
- 功能：获取标的列表（默认 stock，前 50），优先本地缓存，可强制刷新。
- 参数：`types: string[]`，`limit: int`，`config_path: string`，`refresh: bool`（是否强制远端刷新）
- 返回：标的代码列表（文本）。

## 示例调用
- 拉取：`fetch_prices` `{ symbols:["000001.XSHE","600000.XSHG"], start:"2015-01-01", end:"2024-12-31", freq:"1d" }`
- 检查：`check_cache` `{ symbol:"000001.XSHE", freq:"1d" }`
- 列表：`list_cached_symbols` `{ freq:"1d", limit:20 }`
- 自动获取前 N 个标的并拉取：`fetch_universe_prices` `{ start:"2025-01-01", end:"2025-12-31", types:["stock"], limit:50, freq:"1d" }`
- 仅获取标的列表：`list_securities` `{ types:["stock"], limit:50 }`

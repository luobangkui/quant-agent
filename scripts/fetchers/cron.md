# 日常拉取（cron 示例）

目标：每日 00:00 运行，拉取上一交易日全市场（大 A 股票）日线行情，按缺口补齐，落盘 Parquet。

## 脚本
- 路径：`scripts/fetchers/daily_job.py`
- 行为：读取 `config/data.yaml`，获取股票列表（带缓存），调用 `MarketFetcher` 拉取目标日（默认昨日）日线。

手动运行示例：
```
python scripts/fetchers/daily_job.py
```
环境要求：已在 `config/data.yaml` 配置好聚宽账号；安装依赖。

## cron 配置示例（Linux）
编辑 crontab（使用你的项目路径和 Python 环境）：
```
0 0 * * * cd /personal/my-proj/quant-agent && /usr/bin/env HOST=0.0.0.0 PORT=50001 TRANSPORT=sse /path/to/python scripts/fetchers/daily_job.py >> logs/daily_job.log 2>&1
```
说明：
- 定时：每日 00:00
- 日志：追加到 `logs/daily_job.log`（需确保 `logs/` 目录存在）
- 如果在虚拟环境，替换 `/path/to/python` 为对应解释器。

## 注意
- 账号/密码敏感信息不要写入 cron；可在环境变量或 `config/data.yaml` 提前配置好。
- 如需交易日历刷新或标的列表刷新，可定期手动运行一次带 `refresh` 的工具（或扩展脚本参数）。
- 运行失败请检查 `logs/daily_job.log` 与数据服务日志；限流/配额不足时可增加重试逻辑。

## 沪深300 专用每日任务
- 脚本：`scripts/fetchers/daily_hs300.py`（默认取昨日，指数 `000300.XSHG`，limit=300）
- 手动：
  ```
  python scripts/fetchers/daily_hs300.py  # 默认昨日
  # 指定日期
  python scripts/fetchers/daily_hs300.py --date 2025-01-10
  ```
- cron 示例：
  ```
  5 0 * * * cd /personal/my-proj/quant-agent && /path/to/python scripts/fetchers/daily_hs300.py >> logs/daily_hs300.log 2>&1
  ```
  可与全市场任务错开几分钟，减少并发压力。

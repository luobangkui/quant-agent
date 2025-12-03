# 日志规范（数据拉取链路）

- 日志库：使用 Python 标准库 `logging`。
- 默认格式：`%(asctime)s %(levelname)s [%(name)s] %(message)s`，默认级别 INFO，可通过脚本参数 `--log-level` 调整（如 DEBUG/INFO/WARN）。
- 输出目标：当前以控制台输出为主；如需文件，可在脚本外部设置 `LOGGING_CONFIG` 或修改脚本。

## 关键日志点
- Provider 认证：JoinQuant 认证成功会记录 INFO。
- 交易日历：首次或区间超出缓存时，记录刷新交易日历的 INFO（缓存目录 `_calendar/<provider>.parquet`）。
- 拉取流程：
  - 无交易日或无缺口时的跳过信息（INFO）。
  - 每个分片的开始（INFO：symbol、freq、日期范围）。
  - 分片返回空结果的提示（INFO）。
  - 异常自动记录堆栈（ERROR）。

## 示例
```
2024-12-03 12:00:00 INFO [core.data.providers.joinquant] Authenticated JoinQuant user=your_user
2024-12-03 12:00:01 INFO [core.data.calendar] Refreshing trading calendar cache for 2015-01-01 -> 2024-12-31 (provider cache=/share/quant/data/jukuan/_calendar/joinquant.parquet)
2024-12-03 12:00:02 INFO [core.data.fetcher] Fetching 000001.XSHE 1d range 2015-01-05 -> 2015-12-31
2024-12-03 12:00:03 INFO [core.data.fetcher] Empty result for 000001.XSHE 1d range 2016-01-01 -> 2016-01-02
2024-12-03 12:00:04 ERROR [core.data.fetcher] Fetch failed for 600000.XSHG 1d
```

## 如何调整
- 调整日志级别：`--log-level DEBUG`。
- 如需写文件，可在运行脚本前设置 `PYTHONWARNINGS`/`LOGGING_CONFIG`，或按需修改脚本添加 `FileHandler`。当前默认仅输出到 stdout，便于在任务调度/容器日志中查看。

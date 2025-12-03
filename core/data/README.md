# 数据层说明（JoinQuant 起步，Parquet 本地落盘）

目标：可替换的数据提供方、统一的数据格式、本地 Parquet 缓存到 `/share/quant/data/jukuan`（可在 `config/data.yaml` 调整）。

## 目录与文件
- `core/data/provider.py`：数据源抽象与配置模型。
- `core/data/providers/joinquant.py`：聚宽适配器，封装认证、频率映射、节流。
- `core/data/storage.py`：本地 Parquet 存取，按 `symbol/freq/year` 分区。
- `core/data/config.py`：YAML 配置加载，生成 ProviderConfig。
- `core/data/fetcher.py`：MarketFetcher，负责缺口扫描、分片拉取、落盘。
- `config/data.yaml`：默认配置示例，默认 provider=joinquant，base_dir=/share/quant/data/jukuan。
- `scripts/fetch_joinquant_prices.py`：单标的缺口补齐脚本。
- `scripts/fetchers/fetch_market.py`：全市场/指定列表批量拉取脚本。

## 使用步骤
1) 安装依赖：`pip install -r requirements.txt`（需含 `jqdatasdk`, `pyarrow`, `pyyaml`）。
2) 配置 `config/data.yaml`：填写聚宽账号密码，如需调整存储目录/节流参数可修改 `base_dir`/`throttle`。
3) 拉取数据（示例）：
   ```
   python scripts/fetch_joinquant_prices.py \
     --symbols HK.09988,000001.XSHE \
     --start 2020-01-01 --end 2024-12-31 \
     --freq 1d \
     --config config/data.yaml
   ```
   脚本会读取已有 Parquet（若存在）并只补缺口，然后按年分区写入 `/share/quant/data/jukuan/symbol=.../freq=.../year=.../data.parquet`。

## 验证与健康检查示例
- 快速查看一只标的的基础信息：
  ```
  python - <<'PY'
  import pandas as pd, pathlib
  path = pathlib.Path("/share/quant/data/jukuan/symbol=HK.09988/freq=1d")
  df = pd.concat(pd.read_parquet(p) for p in path.rglob("data.parquet"))
  print(df["timestamp"].min(), "->", df["timestamp"].max(), "rows:", len(df))
  print(df[["open","high","low","close","volume"]].describe())
  print("NaN counts:\n", df.isna().sum())
  PY
  ```
- 检测时间缺口（按存储频率）：
  ```
  python - <<'PY'
  import pandas as pd, pathlib
  from core.data.storage import LocalParquetStore
  store = LocalParquetStore(pathlib.Path("/share/quant/data/jukuan"))
  df = store.load("HK.09988", "1d")
  missing = list(LocalParquetStore.missing_ranges(df, pd.Timestamp("2020-01-01", tz="UTC"), pd.Timestamp("2024-12-31", tz="UTC"), freq="1d"))
  print("missing ranges:", missing)
  PY
  ```
- 检查去重与排序：`df["timestamp"].is_monotonic_increasing` 应为 True，`df["timestamp"].duplicated().any()` 应为 False。
- 粗检异常值：可对涨跌幅做截面统计，过滤极端值；或检查成交量/金额是否为零的比例。

## 非交易日处理
- 拉取前会通过 provider 的交易日历接口获取交易日，并使用本地缓存（`_calendar/<provider>.parquet`），避免对周末/节假日发送无效请求。
- 日线缺口基于交易日历计算（不会把周末当作缺口）；分钟线按交易日分片拉取，默认每 3 个交易日一片，可用 `--chunk-minutes` 调整。

## 全市场/批量拉取示例
- 全市场日线（A股 stock，限量取前 100 个用于测试）：
  ```
  python scripts/fetchers/fetch_market.py \
    --all --types stock \
    --start 2020-01-01 --end 2024-12-31 \
    --freq 1d --limit 100 \
    --config config/data.yaml
  ```
- 指定列表（覆盖缺口，不重复拉已缓存的日线）：
  ```
  python scripts/fetchers/fetch_market.py \
    --symbols 000001.XSHE,600000.XSHG \
    --start 2015-01-01 --end 2024-12-31 \
    --freq 1d \
    --config config/data.yaml
  ```
- 全量重拉（忽略缺口直接按区间全量拉取）：加 `--full-refresh`。
- 分片参数：`--chunk-days` 控制日线单次请求跨度（默认 366 天）；`--chunk-minutes` 控制分钟线分片跨度（默认 3 天）。

## 规范约定
- 时区：入库前统一转为 UTC（聚宽原始为沪深时区）。
- 列：`symbol, timestamp, open, high, low, close, volume, turnover`，数值列转为 float。
- 频率：目前支持 `1d` 和 `1m`；如需更多频率，在 provider 里补充映射。
- 缓存策略：`LocalParquetStore` 简单去重+排序，无额外压缩/统计，可按需扩展（如添加元数据、校验）。

## 后续扩展
- 新数据源：实现 `DataProvider` 子类并在 YAML `providers` 中增加配置即可复用落盘逻辑。
- 并发/限流：可在 provider 层引入令牌桶或异步队列；当前为简单最小间隔节流。
- 质量校验：可增加文件校验脚本，输出已缓存日期范围、行数、缺口检测报告。

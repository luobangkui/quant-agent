from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from core.data.config import build_provider_config, load_raw_config
from core.data.fetcher import MarketFetcher
from core.data.providers.joinquant import JoinQuantProvider
from core.data.storage import LocalParquetStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="从聚宽拉取行情并落盘 Parquet")
    parser.add_argument("--symbols", required=True, help="标的列表，逗号分隔，如 HK.09988,000001.XSHE")
    parser.add_argument("--start", required=True, help="开始日期，形如 2020-01-01")
    parser.add_argument("--end", required=True, help="结束日期，形如 2024-12-31")
    parser.add_argument("--freq", default="1d", help="频率：1d 或 1m")
    parser.add_argument("--config", type=Path, default=Path("config/data.yaml"), help="配置文件路径")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_cfg = load_raw_config(args.config)
    provider_name = raw_cfg.get("default_provider", "joinquant")
    provider_cfg = build_provider_config(raw_cfg, provider_name)

    provider = JoinQuantProvider(provider_cfg)
    store = LocalParquetStore(provider_cfg.base_dir)
    fetcher = MarketFetcher(provider, store)

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    start_ts = pd.Timestamp(args.start)
    end_ts = pd.Timestamp(args.end)

    for sym in symbols:
        result = fetcher.fetch_symbol(sym, start_ts, end_ts, freq=args.freq, use_missing_ranges=True)
        status = "skipped" if result.skipped else "ok"
        if result.error:
            status = f"error: {result.error}"
        print(
            f"{sym}: rows fetched={result.fetched_rows}, missing_ranges={result.missing_ranges}, status={status}"
        )


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

import logging
import pandas as pd

# Ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.data.config import build_provider_config, load_raw_config
from core.data.fetcher import MarketFetcher
from core.data.providers.joinquant import JoinQuantProvider
from core.data.storage import LocalParquetStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="全市场/单标的行情拉取（聚宽），落盘 Parquet。")
    parser.add_argument("--start", required=True, help="开始日期，例如 2020-01-01")
    parser.add_argument("--end", required=True, help="结束日期，例如 2024-12-31")
    parser.add_argument("--freq", default="1d", help="频率：1d 或 1m")
    parser.add_argument("--symbols", help="指定标的列表，逗号分隔；若与 --all 同时指定，则以 --symbols 为准")
    parser.add_argument("--all", action="store_true", help="是否拉取全市场（通过 provider.list_securities）")
    parser.add_argument("--types", default="stock", help="全市场类型列表，逗号分隔，例如 stock,etf")
    parser.add_argument("--limit", type=int, help="限制标的数量（调试用）")
    parser.add_argument("--config", type=Path, default=Path("config/data.yaml"), help="配置文件路径")
    parser.add_argument("--chunk-days", type=int, default=366, help="日线分片天数")
    parser.add_argument("--chunk-minutes", type=int, default=3 * 24 * 60, help="分钟线分片分钟数")
    parser.add_argument("--full-refresh", action="store_true", help="忽略缺口，直接按区间全量拉取")
    parser.add_argument("--log-level", default="INFO", help="日志级别，默认 INFO")
    return parser.parse_args()


def build_fetcher(args: argparse.Namespace) -> MarketFetcher:
    raw_cfg = load_raw_config(args.config)
    provider_name = raw_cfg.get("default_provider", "joinquant")
    provider_cfg = build_provider_config(raw_cfg, provider_name)
    provider = JoinQuantProvider(provider_cfg)
    store = LocalParquetStore(provider_cfg.base_dir)
    return MarketFetcher(
        provider=provider,
        store=store,
        chunk_days=args.chunk_days,
        chunk_minutes=args.chunk_minutes,
    )


def resolve_symbols(fetcher: MarketFetcher, args: argparse.Namespace) -> List[str]:
    if args.symbols:
        return [s.strip() for s in args.symbols.split(",") if s.strip()]
    if args.all:
        types = [t.strip() for t in args.types.split(",") if t.strip()]
        df = fetcher.list_securities(types=types)
        symbols = df["symbol"].tolist()
        if args.limit:
            symbols = symbols[: args.limit]
        return symbols
    raise ValueError("请指定 --symbols 或 --all")


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    fetcher = build_fetcher(args)
    symbols = resolve_symbols(fetcher, args)
    start_ts = pd.Timestamp(args.start)
    end_ts = pd.Timestamp(args.end)
    use_missing = not args.full_refresh

    print(f"Total symbols: {len(symbols)}; freq={args.freq}; start={start_ts.date()} end={end_ts.date()}")
    for idx, sym in enumerate(symbols, 1):
        result = fetcher.fetch_symbol(sym, start_ts, end_ts, freq=args.freq, use_missing_ranges=use_missing)
        status = "ok"
        if result.skipped:
            status = "skipped"
        if result.error:
            status = f"error: {result.error}"
        print(
            f"[{idx}/{len(symbols)}] {sym} -> rows={result.fetched_rows} "
            f"missing_ranges={result.missing_ranges} status={status}"
        )


if __name__ == "__main__":
    main()

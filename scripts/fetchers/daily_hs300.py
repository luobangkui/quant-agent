from __future__ import annotations

import argparse
import datetime as dt
import logging
import sys
from pathlib import Path
from typing import List

import pandas as pd

# Ensure project root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.data.config import build_provider_config, load_raw_config
from core.data.fetcher import MarketFetcher
from core.data.providers.joinquant import JoinQuantProvider
from core.data.storage import LocalParquetStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="拉取沪深300成份上一交易日（日线）行情")
    parser.add_argument("--date", help="目标日期（默认昨日，UTC），格式 YYYY-MM-DD")
    parser.add_argument("--index", default="000300.XSHG", help="指数代码，默认沪深300")
    parser.add_argument("--config", type=Path, default=Path("config/data.yaml"), help="配置文件路径")
    parser.add_argument("--log-level", default="INFO", help="日志级别")
    parser.add_argument("--limit", type=int, default=300, help="截取前 N 个成份，默认 300")
    return parser.parse_args()


def get_target_date(value: str | None) -> pd.Timestamp:
    if value:
        ts = pd.Timestamp(value)
    else:
        ts = pd.Timestamp(dt.date.today())
        ts = ts - pd.Timedelta(days=1)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts.normalize()


def get_index_constituents(provider: JoinQuantProvider, index_symbol: str, target_date: pd.Timestamp, limit: int) -> List[str]:
    sh_date = target_date.tz_convert(provider.config.timezone).date()
    symbols = provider._client.get_index_stocks(index_symbol, date=sh_date)  # type: ignore[attr-defined]
    if not symbols:
        raise RuntimeError(f"未获取到指数成份: {index_symbol} at {sh_date}")
    return symbols[:limit] if limit else symbols


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=args.log_level.upper(), format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

    raw_cfg = load_raw_config(args.config)
    provider_name = raw_cfg.get("default_provider", "joinquant")
    provider_cfg = build_provider_config(raw_cfg, provider_name)
    provider = JoinQuantProvider(provider_cfg)
    store = LocalParquetStore(provider_cfg.base_dir)
    fetcher = MarketFetcher(provider=provider, store=store)

    target_date = get_target_date(args.date)
    symbols = get_index_constituents(provider, args.index, target_date, args.limit)
    logging.info("HS300 daily fetch date=%s symbols=%s", target_date.date(), len(symbols))

    results = fetcher.fetch_symbols(
        symbols,
        start=target_date,
        end=target_date,
        freq="1d",
        use_missing_ranges=True,
    )
    for r in results:
        status = "skipped" if r.skipped else "ok"
        logging.info(
            "symbol=%s rows=%s missing=%s status=%s error=%s",
            r.symbol,
            r.fetched_rows,
            r.missing_ranges,
            status,
            r.error or "",
        )


if __name__ == "__main__":
    main()

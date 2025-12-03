from __future__ import annotations

import datetime as dt
import logging
import sys
from pathlib import Path

import pandas as pd

# Ensure project root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.data.config import build_provider_config, load_raw_config
from core.data.fetcher import MarketFetcher
from core.data.providers.joinquant import JoinQuantProvider
from core.data.securities import SecuritiesCache
from core.data.storage import LocalParquetStore


def get_all_stock_symbols(cfg_path: Path, use_cache: bool = True, refresh: bool = False) -> list[str]:
    raw_cfg = load_raw_config(cfg_path)
    provider_name = raw_cfg.get("default_provider", "joinquant")
    provider_cfg = build_provider_config(raw_cfg, provider_name)
    provider = JoinQuantProvider(provider_cfg)
    cache = SecuritiesCache(provider_cfg.base_dir, provider.name)

    if use_cache and not refresh:
        df = cache.load()
        if not df.empty:
            return df["symbol"].tolist()

    df = provider.list_securities(types=["stock"])
    if df is None or df.empty:
        raise RuntimeError("无法获取股票列表")
    cache.save(df)
    return df["symbol"].tolist()


def run_daily(cfg_path: Path, target_date: pd.Timestamp, log_level: str = "INFO") -> None:
    logging.basicConfig(level=log_level.upper(), format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
    symbols = get_all_stock_symbols(cfg_path, use_cache=True, refresh=False)

    provider_name = load_raw_config(cfg_path).get("default_provider", "joinquant")
    provider_cfg = build_provider_config(load_raw_config(cfg_path), provider_name)
    provider = JoinQuantProvider(provider_cfg)
    store = LocalParquetStore(provider_cfg.base_dir)
    fetcher = MarketFetcher(provider=provider, store=store)

    start = target_date.normalize()
    end = target_date.normalize()
    logging.info("Daily fetch for %s symbols=%s", target_date.date(), len(symbols))
    results = fetcher.fetch_symbols(symbols, start, end, freq="1d", use_missing_ranges=True)
    for r in results:
        logging.info(
            "symbol=%s rows=%s missing=%s status=%s error=%s",
            r.symbol,
            r.fetched_rows,
            r.missing_ranges,
            "skipped" if r.skipped else "ok",
            r.error or "",
        )


def main() -> None:
    cfg_path = Path("config/data.yaml")
    today = pd.Timestamp(dt.date.today(), tz="UTC")
    target_date = today - pd.Timedelta(days=1)
    run_daily(cfg_path, target_date)


if __name__ == "__main__":
    main()

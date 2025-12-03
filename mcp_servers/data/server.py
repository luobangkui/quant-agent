from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

# Ensure project root on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.data.config import build_provider_config, load_raw_config
from core.data.fetcher import FetchResult, MarketFetcher
from core.data.providers.joinquant import JoinQuantProvider
from core.data.securities import SecuritiesCache
from core.data.storage import LocalParquetStore

logger = logging.getLogger(__name__)

# Default host/port can be overridden via args or ENV
DEFAULT_HOST = os.getenv("HOST", "0.0.0.0")
DEFAULT_PORT = int(os.getenv("PORT", "50001"))

# Instantiate MCP server (host/port may be overwritten in main before run)
mcp = FastMCP("data-service", host=DEFAULT_HOST, port=DEFAULT_PORT)


def get_fetcher(config_path: Path) -> MarketFetcher:
    raw_cfg = load_raw_config(config_path)
    provider_name = raw_cfg.get("default_provider", "joinquant")
    provider_cfg = build_provider_config(raw_cfg, provider_name)
    provider = JoinQuantProvider(provider_cfg)
    store = LocalParquetStore(provider_cfg.base_dir)
    return MarketFetcher(provider=provider, store=store)


def _parse_ts(value: str) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts


def _result_log(results: Iterable[FetchResult]) -> str:
    lines = ["Fetch summary:"]
    for r in results:
        status = "ok"
        if r.skipped:
            status = "skipped"
        if r.error:
            status = f"error: {r.error}"
        lines.append(
            f"- {r.symbol}: rows={r.fetched_rows} missing_ranges={r.missing_ranges} status={status}"
    )
    return "\n".join(lines)


def _list_securities(provider, types: Optional[List[str]] = None) -> pd.DataFrame:
    try:
        return provider.list_securities(types=types)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to list securities")
        raise exc


def _get_index_constituents(provider, index_symbol: str) -> List[str]:
    try:
        # 聚宽指数成份
        if hasattr(provider._client, "get_index_stocks"):
            return provider._client.get_index_stocks(index_symbol)
        # 兜底
        raise ValueError("Provider does not support get_index_stocks")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to get index constituents for %s", index_symbol)
        raise exc


@mcp.tool()
def fetch_prices(
    symbols: List[str],
    start: str,
    end: str,
    freq: str = "1d",
    full_refresh: bool = False,
    config_path: str = "config/data.yaml",
    log_level: str = "INFO",
) -> List[TextContent]:
    """拉取远端行情并落盘本地 Parquet（默认按缺口补齐）。"""
    logging.basicConfig(level=log_level.upper(), format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
    fetcher = get_fetcher(Path(config_path))
    start_ts = _parse_ts(start)
    end_ts = _parse_ts(end)

    symbols = [s.strip() for s in symbols if s.strip()]
    if not symbols:
        raise ValueError("symbols 不能为空")

    logger.info(
        "Fetching symbols=%s start=%s end=%s freq=%s full_refresh=%s",
        symbols,
        start_ts.date(),
        end_ts.date(),
        freq,
        full_refresh,
    )
    results = fetcher.fetch_symbols(
        symbols,
        start_ts,
        end_ts,
        freq=freq,
        use_missing_ranges=not full_refresh,
    )
    return [TextContent(type="text", text=_result_log(results))]


@mcp.tool()
def fetch_universe_prices(
    start: str,
    end: str,
    types: Optional[List[str]] = None,
    limit: int = 50,
    freq: str = "1d",
    full_refresh: bool = False,
    config_path: str = "config/data.yaml",
    log_level: str = "INFO",
    use_cache: bool = True,
    refresh: bool = False,
    index_symbol: Optional[str] = None,
) -> List[TextContent]:
    """拉取指定类型标的（自动获取列表，默认前 50 个）行情并落盘。"""
    logging.basicConfig(level=log_level.upper(), format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
    fetcher = get_fetcher(Path(config_path))
    provider = fetcher.provider
    if index_symbol:
        symbols = _get_index_constituents(provider, index_symbol)
        if not symbols:
            raise ValueError(f"未获取到指数成份: {index_symbol}")
        symbols = symbols[:limit] if limit else symbols
    else:
        cache = SecuritiesCache(provider.config.base_dir, provider.name)
        df_sec = cache.load() if use_cache and not refresh else pd.DataFrame()
        if df_sec.empty:
            df_sec = _list_securities(provider, types=types)
            if not df_sec.empty and use_cache:
                cache.save(df_sec)
        if df_sec.empty:
            raise ValueError("未获取到标的列表")
        symbols = df_sec["symbol"].tolist()[:limit]
    logger.info(
        "Fetching universe symbols (types=%s, index=%s, limit=%s): %s...",
        types or "stock",
        index_symbol or "",
        limit,
        symbols[:5],
    )
    start_ts = _parse_ts(start)
    end_ts = _parse_ts(end)
    results = fetcher.fetch_symbols(
        symbols,
        start_ts,
        end_ts,
        freq=freq,
        use_missing_ranges=not full_refresh,
    )
    return [TextContent(type="text", text=_result_log(results))]


@mcp.tool()
def list_securities(
    types: Optional[List[str]] = None,
    limit: int = 50,
    config_path: str = "config/data.yaml",
    refresh: bool = False,
) -> List[TextContent]:
    """列出标的列表（默认前 50 个），优先本地缓存，可强制刷新远端。"""
    fetcher = get_fetcher(Path(config_path))
    provider = fetcher.provider
    cache = SecuritiesCache(provider.config.base_dir, provider.name)
    df_sec = cache.load()
    if df_sec.empty or refresh:
        logger.info("Refreshing securities cache (types=%s)", types or ["stock"])
        df_sec = _list_securities(provider, types=types)
        if not df_sec.empty:
            cache.save(df_sec)
    if df_sec.empty:
        return [TextContent(type="text", text="No securities returned")]
    symbols = df_sec["symbol"].tolist()[:limit]
    return [
        TextContent(
            type="text",
            text=f"Securities (types={types or 'stock'}, limit={limit}):\n" + "\n".join(f"- {s}" for s in symbols),
        )
    ]


@mcp.tool()
def check_cache(
    symbol: str,
    freq: str = "1d",
    start: Optional[str] = None,
    end: Optional[str] = None,
    config_path: str = "config/data.yaml",
) -> List[TextContent]:
    """检查本地缓存（行数/时间范围/缺口）。"""
    fetcher = get_fetcher(Path(config_path))
    store = fetcher.store
    df = store.load(symbol, freq)
    if df.empty:
        return [TextContent(type="text", text=f"No cached data for {symbol} freq={freq}")]

    if start:
        start_ts = _parse_ts(start)
        df = df[df["timestamp"] >= start_ts]
    if end:
        end_ts = _parse_ts(end)
        df = df[df["timestamp"] <= end_ts]

    if df.empty:
        return [TextContent(type="text", text=f"No data in range for {symbol} freq={freq}")]

    min_ts = df["timestamp"].min()
    max_ts = df["timestamp"].max()
    rows = len(df)
    nan_counts = df.isna().sum().to_dict()

    missing_lines: List[str] = []
    if freq in ("1d", "d", "day", "daily"):
        missing = list(LocalParquetStore.missing_ranges(df, min_ts, max_ts, freq="1d"))
        if missing:
            missing_lines.append("Missing ranges:")
            for s, e in missing:
                missing_lines.append(f"- {s.date()} -> {e.date()}")

    summary_lines = [
        f"Cache stats for {symbol} freq={freq}",
        f"Rows: {rows}",
        f"Range: {min_ts} -> {max_ts}",
        f"NaN counts: {nan_counts}",
    ]
    summary_lines.extend(missing_lines)
    return [TextContent(type="text", text="\n".join(summary_lines))]


@mcp.tool()
def list_cached_symbols(
    freq: str = "1d",
    limit: int = 50,
    config_path: str = "config/data.yaml",
) -> List[TextContent]:
    """列出本地缓存中包含的标的（按目录扫描）。"""
    fetcher = get_fetcher(Path(config_path))
    base = fetcher.store.base_dir
    pattern = f"symbol=*/freq={freq}"
    symbols: List[str] = []
    for path in sorted(base.glob(pattern)):
        symbol_dir = path.parent.name  # symbol=XXX
        symbol = symbol_dir.replace("symbol=", "")
        symbols.append(symbol)
        if len(symbols) >= limit:
            break
    if not symbols:
        return [TextContent(type="text", text=f"No cached symbols for freq={freq}")]
    return [
        TextContent(
            type="text",
            text="Cached symbols (limited):\n" + "\n".join(f"- {s}" for s in symbols),
        )
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MCP data service")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="MCP server port")
    parser.add_argument("--host", default=DEFAULT_HOST, help="MCP server host")
    parser.add_argument(
        "--transport",
        default="sse",
        choices=["stdio", "sse", "streamable-http"],
        help="Transport for MCP server",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
    # Override host/port before starting server (used by SSE/HTTP transports)
    mcp.settings.host = args.host
    mcp.settings.port = args.port
    logger.info("Starting MCP data-service on %s:%s via %s", args.host, args.port, args.transport)
    mcp.run(transport=args.transport)

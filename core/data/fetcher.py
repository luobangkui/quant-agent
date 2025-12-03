from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

import pandas as pd

from core.data.calendar import TradingCalendarCache
from core.data.provider import DataProvider
from core.data.storage import LocalParquetStore

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    symbol: str
    fetched_rows: int
    missing_ranges: int
    skipped: bool = False
    error: Optional[str] = None


class MarketFetcher:
    """Orchestrates remote fetch + local Parquet persistence."""

    def __init__(
        self,
        provider: DataProvider,
        store: LocalParquetStore,
        chunk_days: int = 366,
        chunk_minutes: int = 3 * 24 * 60,
    ) -> None:
        self.provider = provider
        self.store = store
        self.chunk_days = chunk_days
        self.minute_chunk_days = max(1, int(chunk_minutes // (24 * 60))) if chunk_minutes else 1
        self.calendar_cache = TradingCalendarCache(store.base_dir, provider.name)

    def fetch_symbol(
        self,
        symbol: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
        freq: str = "1d",
        use_missing_ranges: bool = True,
    ) -> FetchResult:
        start_utc = self._to_utc(start)
        end_utc = self._to_utc(end)

        freq_norm = freq.lower()
        trade_days = self._get_trade_days(start_utc, end_utc)
        if trade_days.empty:
            logger.info("No trading days for %s in range %s -> %s, skipping", symbol, start_utc.date(), end_utc.date())
            return FetchResult(symbol=symbol, fetched_rows=0, missing_ranges=0, skipped=True)

        if freq_norm in ("1d", "d", "day", "daily"):
            missing_dates = (
                self._missing_trade_dates(symbol, trade_days) if use_missing_ranges else list(trade_days)
            )
            if not missing_dates:
                logger.info("No missing dates for %s (freq=%s), skipping", symbol, freq_norm)
                return FetchResult(symbol=symbol, fetched_rows=0, missing_ranges=0, skipped=True)
            ranges = self._chunk_dates(missing_dates, self.chunk_days)
        else:
            # 分钟线按交易日分片，避免跨周末/节假日
            ranges = self._chunk_dates(list(trade_days), self.minute_chunk_days)

        missing_count = len(ranges)

        fetched_rows = 0
        try:
            for r_start, r_end in ranges:
                logger.info(
                    "Fetching %s %s range %s -> %s",
                    symbol,
                    freq_norm,
                    r_start.date(),
                    r_end.date(),
                )
                df = self.provider.get_price(
                    symbol,
                    start=r_start.to_pydatetime(),
                    end=r_end.to_pydatetime(),
                    freq=freq,
                )
                if df.empty:
                    logger.info("Empty result for %s %s range %s -> %s", symbol, freq_norm, r_start.date(), r_end.date())
                    continue
                self.store.upsert(symbol, freq_norm, df)
                fetched_rows += len(df)
            return FetchResult(symbol=symbol, fetched_rows=fetched_rows, missing_ranges=missing_count)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Fetch failed for %s %s", symbol, freq_norm)
            return FetchResult(symbol=symbol, fetched_rows=fetched_rows, missing_ranges=missing_count, error=str(exc))

    def fetch_symbols(
        self,
        symbols: Iterable[str],
        start: pd.Timestamp,
        end: pd.Timestamp,
        freq: str = "1d",
        use_missing_ranges: bool = True,
    ) -> List[FetchResult]:
        results: List[FetchResult] = []
        for sym in symbols:
            results.append(self.fetch_symbol(sym, start, end, freq=freq, use_missing_ranges=use_missing_ranges))
        return results

    def list_securities(self, types: Optional[Sequence[str]] = None) -> pd.DataFrame:
        return self.provider.list_securities(types=types)

    def _get_trade_days(self, start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
        return self.calendar_cache.get(
            loader=lambda s, e: self.provider.get_trade_days(s.to_pydatetime(), e.to_pydatetime()),
            start=start,
            end=end,
        )

    def _missing_trade_dates(self, symbol: str, trade_days: pd.DatetimeIndex) -> List[pd.Timestamp]:
        existing = self.store.load(symbol, "1d")
        existing_dates = pd.Index([])
        if not existing.empty and "timestamp" in existing:
            ts = pd.to_datetime(existing["timestamp"])
            tz = getattr(ts.dt, "tz", None)
            if tz is None:
                ts = ts.dt.tz_localize("UTC")
            else:
                ts = ts.dt.tz_convert("UTC")
            existing_dates = ts.dt.normalize()
        expected_dates = trade_days.normalize()
        missing = sorted(set(expected_dates) - set(existing_dates))
        return list(missing)

    def _chunk_dates(self, dates: Iterable[pd.Timestamp], max_days: int) -> List[tuple[pd.Timestamp, pd.Timestamp]]:
        dates_sorted = sorted(pd.to_datetime(list(dates)))
        if not dates_sorted:
            return []
        dates_sorted = [self._to_utc(d).normalize() for d in dates_sorted]
        ranges: List[tuple[pd.Timestamp, pd.Timestamp]] = []
        start = dates_sorted[0]
        prev = start
        count = 1
        for current in dates_sorted[1:]:
            contiguous = (current - prev) <= pd.Timedelta(days=1)
            if contiguous and count < max_days:
                count += 1
                prev = current
                continue
            ranges.append((start, prev))
            start = current
            prev = current
            count = 1
        ranges.append((start, prev))
        return ranges

    @staticmethod
    def _to_utc(value: pd.Timestamp) -> pd.Timestamp:
        ts = pd.Timestamp(value)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        else:
            ts = ts.tz_convert("UTC")
        return ts

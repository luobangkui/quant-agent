from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class TradingCalendarCache:
    """Cache trading days to reduce重复查询。"""

    def __init__(self, base_dir: Path, provider_name: str) -> None:
        self.path = Path(base_dir) / "_calendar" / f"{provider_name}.parquet"
        self._calendar: pd.DatetimeIndex | None = None

    def get(self, loader, start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
        """Ensure trading days covering [start, end] exist in cache; loader returns iterable of datetimes."""
        start = self._to_utc_midnight(start)
        end = self._to_utc_midnight(end)
        cal = self._load()

        if cal is None or cal.empty or start < cal.min() or end > cal.max():
            logger.info(
                "Refreshing trading calendar cache for %s -> %s (provider cache=%s)",
                start.date(),
                end.date(),
                self.path,
            )
            fetched = loader(start, end)
            fetched_idx = self._to_index(fetched)
            if cal is None or cal.empty:
                cal = fetched_idx
            else:
                cal = cal.union(fetched_idx)
            self._save(cal)

        if cal is None:
            return pd.DatetimeIndex([], tz="UTC")
        cal = cal[(cal >= start) & (cal <= end)]
        return cal

    def _load(self) -> pd.DatetimeIndex | None:
        if self._calendar is not None:
            return self._calendar
        if self.path.exists():
            df = pd.read_parquet(self.path)
            if "date" in df:
                self._calendar = self._to_index(df["date"])
                return self._calendar
        return pd.DatetimeIndex([], tz="UTC")

    def _save(self, calendar: pd.DatetimeIndex) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame({"date": calendar})
        df.to_parquet(self.path, index=False)
        self._calendar = calendar

    @staticmethod
    def _to_index(values) -> pd.DatetimeIndex:
        idx = pd.to_datetime(values)
        if idx.tz is None:
            idx = idx.tz_localize("UTC")
        else:
            idx = idx.tz_convert("UTC")
        idx = idx.normalize()
        return pd.DatetimeIndex(sorted(idx))

    @staticmethod
    def _to_utc_midnight(value: pd.Timestamp) -> pd.Timestamp:
        ts = pd.Timestamp(value)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        else:
            ts = ts.tz_convert("UTC")
        return ts.normalize()

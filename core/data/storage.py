from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


class LocalParquetStore:
    """Simple Parquet store with year partitions: symbol/freq/year/data.parquet."""

    def __init__(self, base_dir: Path, engine: str = "pyarrow") -> None:
        self.base_dir = base_dir
        self.engine = engine

    def _partition_path(self, symbol: str, freq: str, year: int) -> Path:
        return self.base_dir / f"symbol={symbol}" / f"freq={freq}" / f"year={year}" / "data.parquet"

    def load(self, symbol: str, freq: str) -> pd.DataFrame:
        root = self.base_dir / f"symbol={symbol}" / f"freq={freq}"
        if not root.exists():
            return pd.DataFrame()
        frames = []
        for path in sorted(root.rglob("data.parquet")):
            frames.append(pd.read_parquet(path))
        if not frames:
            return pd.DataFrame()
        df = pd.concat(frames, ignore_index=True)
        return self._normalize(df)

    def upsert(self, symbol: str, freq: str, df: pd.DataFrame) -> None:
        if df.empty:
            return
        df = self._normalize(df)
        df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
        df["year"] = df["timestamp"].dt.year
        for year, chunk in df.groupby("year"):
            chunk = chunk.drop(columns=["year"])
            path = self._partition_path(symbol, freq, int(year))
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                existing = pd.read_parquet(path)
                merged = pd.concat([existing, chunk], ignore_index=True)
                merged = merged.drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
            else:
                merged = chunk
            merged.to_parquet(path, index=False, engine=self.engine)

    @staticmethod
    def missing_ranges(
        existing: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, freq: str = "1d"
    ) -> Iterable[tuple[pd.Timestamp, pd.Timestamp]]:
        """Return missing ranges [start, end] inclusive for timestamp-ordered data."""
        if existing.empty:
            yield (start, end)
            return
        freq_delta = pd.tseries.frequencies.to_offset(freq)
        existing_ts = existing["timestamp"]
        existing_ts = existing_ts[(existing_ts >= start) & (existing_ts <= end)].sort_values()
        if existing_ts.empty:
            yield (start, end)
            return

        first_ts = existing_ts.iloc[0]
        if start < first_ts:
            yield (start, first_ts - freq_delta)

        current = first_ts
        for ts in existing_ts.iloc[1:]:
            expected = current + freq_delta
            if ts > expected:
                yield (expected, ts - freq_delta)
            current = ts

        tail_start = current + freq_delta
        if end >= tail_start:
            yield (tail_start, end)

    @staticmethod
    def _normalize(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if "timestamp" in df:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        return df

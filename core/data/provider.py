from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional, Sequence

import pandas as pd


@dataclass
class ThrottleConfig:
    max_per_minute: int = 60
    burst: int = 5


@dataclass
class RetryConfig:
    max_attempts: int = 3
    backoff_seconds: float = 1.0


@dataclass
class ProviderConfig:
    username: Optional[str] = None
    password: Optional[str] = None
    base_dir: Path = field(default_factory=lambda: Path("/share/quant/data"))
    timezone: str = "Asia/Shanghai"
    throttle: ThrottleConfig = field(default_factory=ThrottleConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)


class DataProvider(ABC):
    name: str

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    @abstractmethod
    def get_price(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        freq: str = "1d",
        fields: Optional[Sequence[str]] = None,
    ) -> pd.DataFrame:
        """Fetch price data from the remote provider."""
        raise NotImplementedError

    def get_price_batch(
        self,
        symbols: Iterable[str],
        start: datetime,
        end: datetime,
        freq: str = "1d",
        fields: Optional[Sequence[str]] = None,
    ) -> pd.DataFrame:
        """Simple batch helper built on top of single-symbol fetch."""
        frames = []
        for sym in symbols:
            df = self.get_price(sym, start, end, freq=freq, fields=fields)
            if not df.empty:
                df["symbol"] = sym
                frames.append(df)
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)

    def list_securities(self, types: Optional[Sequence[str]] = None) -> pd.DataFrame:
        """List securities metadata. Should return at least a `symbol` column."""
        raise NotImplementedError("当前 provider 未实现 list_securities")

    def get_trade_days(self, start: datetime, end: datetime) -> pd.DatetimeIndex:
        """Return trading days between start/end (inclusive)."""
        raise NotImplementedError("当前 provider 未实现 get_trade_days")

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Optional, Sequence

import pandas as pd

from core.data.provider import DataProvider, ProviderConfig

logger = logging.getLogger(__name__)

class JoinQuantProvider(DataProvider):
    """JoinQuant (JQData) provider adapter."""

    name = "joinquant"

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        self._client = self._import_sdk()
        self._min_interval = 0.0
        if config.throttle.max_per_minute > 0:
            self._min_interval = 60.0 / float(config.throttle.max_per_minute)
        self._next_available = 0.0
        self._auth()

    def _import_sdk(self):
        try:
            import jqdatasdk as jq
        except ImportError as exc:
            raise ImportError("请先安装 jqdatasdk：pip install jqdatasdk") from exc
        return jq

    def _auth(self) -> None:
        if not self.config.username or not self.config.password:
            raise ValueError("JoinQuant 配置缺少用户名/密码")
        self._client.auth(self.config.username, self.config.password)
        logger.info("Authenticated JoinQuant user=%s", self.config.username)

    def _throttle(self) -> None:
        if self._min_interval <= 0:
            return
        now = time.monotonic()
        wait = self._next_available - now
        if wait > 0:
            time.sleep(wait)
        self._next_available = time.monotonic() + self._min_interval

    @staticmethod
    def _map_freq(freq: str) -> str:
        freq = freq.lower()
        if freq in ("1d", "d", "day", "daily"):
            return "daily"
        if freq in ("1m", "minute", "min"):
            return "1m"
        raise ValueError(f"不支持的频率: {freq}")

    def list_securities(self, types: Optional[Sequence[str]] = None) -> pd.DataFrame:
        jq_types = list(types) if types else None
        df = self._client.get_all_securities(types=jq_types)
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.reset_index().rename(columns={"index": "symbol"})
        return df

    def get_trade_days(self, start: datetime, end: datetime) -> pd.DatetimeIndex:
        start_dt = self._normalize_dt(start)
        end_dt = self._normalize_dt(end)
        days = self._client.get_trade_days(start_dt, end_dt)
        idx = pd.to_datetime(days)
        if idx.tz is None:
            idx = idx.tz_localize(self.config.timezone)
        else:
            idx = idx.tz_convert(self.config.timezone)
        return idx.tz_convert("UTC").normalize()

    def get_price(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        freq: str = "1d",
        fields: Optional[Sequence[str]] = None,
    ) -> pd.DataFrame:
        fields = fields or ["open", "high", "low", "close", "volume", "money"]
        jq_freq = self._map_freq(freq)

        start_dt = self._normalize_dt(start)
        end_dt = self._normalize_dt(end)

        self._throttle()
        df = self._client.get_price(
            security=symbol,
            start_date=start_dt,
            end_date=end_dt,
            frequency=jq_freq,
            fields=list(fields),
            skip_paused=True,
            fq="post",
        )
        if df is None or df.empty:
            return pd.DataFrame()

        df = df.reset_index()
        timestamp_col = "index"
        if "time" in df:
            timestamp_col = "time"
        df = df.rename(columns={timestamp_col: "timestamp", "money": "turnover"})

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        if df["timestamp"].dt.tz is None:
            df["timestamp"] = df["timestamp"].dt.tz_localize(self.config.timezone)
        df["timestamp"] = df["timestamp"].dt.tz_convert("UTC")

        df["symbol"] = symbol
        numeric_cols = ["open", "high", "low", "close", "volume", "turnover"]
        for col in numeric_cols:
            if col in df:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            else:
                df[col] = pd.NA

        df = df[["symbol", "timestamp", "open", "high", "low", "close", "volume", "turnover"]]
        df = df.dropna(subset=["timestamp"])
        return df.sort_values("timestamp").reset_index(drop=True)

    def _normalize_dt(self, dt: datetime) -> datetime:
        ts = pd.Timestamp(dt)
        if ts.tzinfo is None:
            ts = ts.tz_localize(self.config.timezone)
        else:
            ts = ts.tz_convert(self.config.timezone)
        return ts.tz_localize(None)

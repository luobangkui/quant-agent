from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class MomentumConfig:
    short_window: int = 5
    long_window: int = 20
    annual_trading_days: int = 252


class SimpleMomentumBacktester:
    """A minimal moving-average momentum backtester for POC validation."""

    def __init__(self, data: pd.DataFrame, config: Optional[MomentumConfig] = None) -> None:
        if config is None:
            config = MomentumConfig()
        if config.short_window >= config.long_window:
            raise ValueError("short_window must be smaller than long_window")
        self.data = data.copy()
        self.config = config

    def prepare_features(self) -> pd.DataFrame:
        df = self.data.copy()
        df["short_ma"] = df["close"].rolling(self.config.short_window).mean()
        df["long_ma"] = df["close"].rolling(self.config.long_window).mean()
        df["returns"] = df["close"].pct_change()
        df["signal"] = np.where(df["short_ma"] > df["long_ma"], 1, -1)
        df["strategy_returns"] = df["signal"].shift(1) * df["returns"]
        return df.dropna(subset=["strategy_returns"])

    def performance(self) -> dict:
        df = self.prepare_features()
        total_return = (1 + df["strategy_returns"]).prod() - 1
        days = (df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]).days or 1
        annual_factor = self.config.annual_trading_days / days * len(df)
        cagr = (1 + total_return) ** (annual_factor) - 1
        volatility = df["strategy_returns"].std() * (self.config.annual_trading_days ** 0.5)
        sharpe = (df["strategy_returns"].mean() * self.config.annual_trading_days) / (volatility + 1e-8)
        max_drawdown = self._max_drawdown(df["strategy_returns"])
        return {
            "total_return": total_return,
            "cagr": cagr,
            "sharpe": sharpe,
            "max_drawdown": max_drawdown,
            "signal_count": int(df.shape[0]),
        }

    @staticmethod
    def _max_drawdown(returns: pd.Series) -> float:
        cumulative = (1 + returns).cumprod()
        rolling_max = cumulative.cummax()
        drawdowns = (cumulative - rolling_max) / rolling_max
        return drawdowns.min()

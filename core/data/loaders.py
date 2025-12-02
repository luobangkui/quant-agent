from __future__ import annotations

import pandas as pd


class CSVPriceLoader:
    """Load OHLCV-like data from a CSV file for a single symbol.

    The loader expects a header row with at least the following columns:
    ``code``, ``name``, ``time_key``, ``open``, ``close``, ``high``, ``low``,
    ``volume`` and ``turnover``. Extra columns (e.g. change_rate/pe_ratio) are
    preserved for downstream inspection.
    """

    def __init__(self, csv_path: str) -> None:
        self.csv_path = csv_path

    def load(self) -> pd.DataFrame:
        df = pd.read_csv(self.csv_path)
        df = df.rename(columns={"time_key": "timestamp"})
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

        numeric_cols = [
            "open",
            "close",
            "high",
            "low",
            "volume",
            "turnover",
            "change_rate",
            "pe_ratio",
            "turnover_rate",
        ]
        for col in numeric_cols:
            if col in df:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.sort_values("timestamp").reset_index(drop=True)
        return df

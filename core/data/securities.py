from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd


class SecuritiesCache:
    """Simple local cache for securities list."""

    def __init__(self, base_dir: Path, provider_name: str) -> None:
        self.path = Path(base_dir) / "_securities" / f"{provider_name}.parquet"

    def load(self) -> pd.DataFrame:
        if self.path.exists():
            try:
                df = pd.read_parquet(self.path)
                return df
            except Exception:
                # Corrupted cache; ignore and refresh
                return pd.DataFrame()
        return pd.DataFrame()

    def save(self, df: pd.DataFrame) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(self.path, index=False)

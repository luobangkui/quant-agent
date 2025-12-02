from __future__ import annotations

import sys
from pathlib import Path
from typing import List

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

# Allow imports from project root when running as a script
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.data.loaders import CSVPriceLoader
from core.strategies.momentum import MomentumConfig, SimpleMomentumBacktester

mcp = FastMCP("ali-momentum")


def _format_pct(value: float) -> str:
    return f"{value:.2%}"


@mcp.tool()
def ali_momentum(short_window: int = 5, long_window: int = 20, csv_path: str = "data/ali.csv") -> List[TextContent]:
    """Run simple moving-average momentum backtest on Ali CSV."""
    csv_file = Path(csv_path)
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV not found: {csv_file}")

    loader = CSVPriceLoader(str(csv_file))
    df = loader.load()

    config = MomentumConfig(short_window=short_window, long_window=long_window)
    backtester = SimpleMomentumBacktester(df, config)
    perf = backtester.performance()

    summary_lines = [
        "Ali Momentum Backtest",
        f"CSV: {csv_file}",
        f"Date range: {df['timestamp'].min().date()} -> {df['timestamp'].max().date()}",
        f"Rows loaded: {len(df)}",
        f"Short/Long windows: {config.short_window}/{config.long_window}",
        "-- Metrics --",
        f"Total return: {_format_pct(perf['total_return'])}",
        f"CAGR (approx): {_format_pct(perf['cagr'])}",
        f"Sharpe (naive): {perf['sharpe']:.2f}",
        f"Max drawdown: {_format_pct(perf['max_drawdown'])}",
        f"Signal count: {perf['signal_count']}",
    ]
    return [TextContent(type="text", text="\n".join(summary_lines))]


if __name__ == "__main__":
    mcp.run()

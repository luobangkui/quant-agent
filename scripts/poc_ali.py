from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Ensure project root is on sys.path when running as a script
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.data.loaders import CSVPriceLoader
from core.strategies.momentum import MomentumConfig, SimpleMomentumBacktester


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="POC: run simple momentum on ali.csv")
    parser.add_argument("--csv", type=Path, default=Path("data/ali.csv"), help="Path to price CSV")
    parser.add_argument("--short", type=int, default=5, help="Short moving average window")
    parser.add_argument("--long", type=int, default=20, help="Long moving average window")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.csv.exists():
        raise FileNotFoundError(f"CSV not found: {args.csv}")

    loader = CSVPriceLoader(str(args.csv))
    df = loader.load()

    config = MomentumConfig(short_window=args.short, long_window=args.long)
    backtester = SimpleMomentumBacktester(df, config)
    perf = backtester.performance()

    print("Momentum POC Results (Ali)")
    print(f"Data range: {df['timestamp'].min().date()} -> {df['timestamp'].max().date()}")
    print(f"Rows loaded: {len(df)}")
    print(f"Short/Long windows: {config.short_window}/{config.long_window}")
    print("-- Metrics --")
    print(f"Total return: {perf['total_return']:.2%}")
    print(f"CAGR (approx): {perf['cagr']:.2%}")
    print(f"Sharpe (naive): {perf['sharpe']:.2f}")
    print(f"Max drawdown: {perf['max_drawdown']:.2%}")
    print(f"Signal count: {perf['signal_count']}")


if __name__ == "__main__":
    pd.options.display.float_format = "{:.4f}".format
    main()

#!/usr/bin/env python3
"""
Run the combined backtest over the full ticker list using VectorBT by default.
"""

import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from combined_backtesting import run_combined_backtest, print_backtest_results
from tickers_full import TICKERS


def main() -> None:
    start_date = os.getenv("BT_START", "2024-01-01")
    end_date = os.getenv("BT_END", datetime.today().strftime("%Y-%m-%d"))
    initial_capital = float(os.getenv("BT_INIT", "100000"))
    use_vectorbt = os.getenv("BT_USE_VBT", "1") not in {"0", "false", "False"}
    rebalance = os.getenv("BT_FREQ", "ME")

    result = run_combined_backtest(
        tickers=TICKERS,
        start_date=start_date,
        end_date=end_date,
        rebalance_freq=rebalance,
        initial_capital=initial_capital,
        use_vectorbt=use_vectorbt,
    )

    print_backtest_results(result)


if __name__ == "__main__":
    main()



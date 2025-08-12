#!/usr/bin/env python3
"""
Run the combined backtest over the full ticker list using VectorBT by default.
"""

import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from vectorbt_backtesting import run_combined_backtest, print_backtest_results
import logging
from tickers_full import TICKERS


def main() -> None:
    start_date = os.getenv("BT_START", "2024-01-01")
    end_date = os.getenv("BT_END", datetime.today().strftime("%Y-%m-%d"))
    initial_capital = float(os.getenv("BT_INIT", "100000"))
    use_vectorbt = os.getenv("BT_USE_VBT", "1") not in {"0", "false", "False"}
    rebalance = os.getenv("BT_FREQ", "ME")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(os.path.join(os.path.dirname(__file__), "full_backtest.log"), mode="w")
        ]
    )

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



#!/usr/bin/env python3
import pandas as pd
import numpy as np
import vectorbt as vbt
from datetime import datetime
from services.historical_data_service import HistoricalDataService
from services.fundamentals_service    import FundamentalService

# 1) Fetch price data once
def download_price_matrix(tickers, start, end):
    svc = HistoricalDataService()
    price_data = {}
    for t in tickers:
        df = svc.fetch_historical_data(t, period="5y")
        if df is None or df.empty: continue
        s = df.set_index("Date")["Adj Close"].groupby(level=0).last()
        price_data[t] = s
    P = pd.DataFrame(price_data).ffill().bfill()
    return P.loc[start:end]

# 2) Build your factor screen
def compute_factors(prices, as_of_dates, tickers):
    fund = FundamentalService("data/fundamentals")
    pe  = pd.DataFrame(index=as_of_dates, columns=tickers)
    roe = pd.DataFrame(index=as_of_dates, columns=tickers)
    mom = prices.pct_change(252).loc[as_of_dates]
    for date in as_of_dates:
        f = fund.fundamentals_asof(tickers, pd.to_datetime(date))
        tmp = pd.DataFrame.from_dict(f, orient="index")
        pe.loc[date, tmp.index]  = tmp["priceToEarnings"]
        roe.loc[date, tmp.index] = tmp["returnOnEquity"]
    # rank factors
    pe_r  = pe.rank(axis=1, pct=True, ascending=True)
    roe_r = roe.rank(axis=1, pct=True, ascending=False)
    mom_r = mom.rank(axis=1, pct=True, ascending=True)
    return (pe_r + roe_r + mom_r) / 3

# 3) Setup vectorbt entries/exits
def run_vbt_backtest(tickers, start, end):
    P = download_price_matrix(tickers, start, end)
    # rebalance monthly on last trading day
    rebalance_dates = P.vbt.run_monthly().index

    # multi-factor score on each rebalance date
    score = compute_factors(P, rebalance_dates, tickers)

    # at each rebalance, go long top-20 stocks
    entries = pd.DataFrame(False, index=P.index, columns=P.columns)
    for date in rebalance_dates:
        top20 = score.loc[date].nlargest(20).index
        entries.loc[date, top20] = True

    # exit signals: 
    #   profit target: +25% | stop loss: -10% | trailing stop: 8%
    # vbt has built-in functions for that
    pf = vbt.Portfolio.from_signals(
        close=P,
        entries=entries,
        exits=None,  # we'll handle stops separately
        freq='1D',
        init_cash=100_000,
        fees=0.001,
        slippage=0.0005,
        use_risk_free=True
    )

    # attach a 25% profit‐target stop
    pf = pf.run_with_stop_loss_and_profit_taking(
        fixed_sl_stop=-0.10,    # 10% SL
        fixed_tp_stop= 0.25,    # 25% TP
        trail_sl_stop=0.08      # 8% trailing
    )

    return pf

if __name__ == "__main__":
    TICKERS = [...]  # your 250+ tickers
    pf = run_vbt_backtest(TICKERS, "2024-01-01", "2025-06-30")

    # summary
    print(pf.stats())
    # equity curve
    pf.total_profit().plot().show()
    # individual trades
    print(pf.trades.records_readable)

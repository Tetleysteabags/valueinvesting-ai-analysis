#!/usr/bin/env python3
"""
Multi-Factor Value Investing Backtest

Features:
- Monthly / custom-frequency rebalancing
- Multi-factor screen: low P/E, high ROE, 12m momentum
- Trailing stops, profit targets, stop losses, R-multiple exits
- Transaction costs & slippage
- SPY benchmark & alpha
"""

import pandas as pd
import numpy as np
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# your existing services:
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from services.historical_data_service import HistoricalDataService
from services.stock_service_v2         import fetch_stock_data_batch
from services.fundamentals_service     import FundamentalService
from services.trading_days_align       import trading_days_aligner


@dataclass
class Position:
    ticker: str
    shares: float
    entry_price: float
    entry_date: datetime
    high_price: float
    current_price: float = 0.0
    current_value: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_return: float = 0.0


@dataclass
class BacktestResult:
    strategy_name: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    volatility: float
    num_trades: int
    win_rate: float
    avg_holding_period: float
    transaction_costs: float
    portfolio_values: pd.Series
    cash_history: pd.Series
    position_values_sum: pd.Series
    trades_df: Optional[pd.DataFrame]


class ValueInvestingBacktester:
    def __init__(
        self,
        initial_capital: float = 100_000.0,
        max_positions: int = 20,
        transaction_cost: float = 0.001,
        slippage: float = 0.0005,
        profit_target: float = 0.25,
        stop_loss: float = -0.10,
        trailing_stop: float = 0.08
    ):
        self.initial_capital      = initial_capital
        self.cash                 = initial_capital
        self.max_positions        = max_positions
        self.transaction_cost     = transaction_cost
        self.slippage             = slippage
        self.profit_target        = profit_target
        self.stop_loss            = stop_loss
        self.trailing_stop        = trailing_stop

        self.historical_service   = HistoricalDataService()
        self.fund_service         = FundamentalService(Path("data/fundamentals"))

        self.positions: Dict[str,Position] = {}
        self.trades: List[Dict] = []
        self.portfolio_values: List[float] = []
        self.cash_history: List[float] = []
        self.position_values: List[float] = []
        self.dates: List[datetime] = []

        self.total_trades   = 0
        self.winning_trades = 0
        self.transaction_costs = 0.0

    def _download_price_matrix(
        self, tickers: List[str], start: str, end: str
    ) -> pd.DataFrame:
        price_data = {}
        for t in tickers:
            df = self.historical_service.fetch_historical_data(t, period="5y")
            if df is None or df.empty: continue
            df = df.set_index("Date").sort_index()
            if "Adj Close" in df.columns:
                series = df["Adj Close"].groupby(level=0).last()
            else:
                series = df["Close"].groupby(level=0).last()
            price_data[t] = series
        if not price_data:
            raise RuntimeError("No price data")
        P = pd.DataFrame(price_data).ffill().bfill()
        P = P.loc[start:end]
        return P

    def _apply_costs(self, value: float) -> float:
        fee = value * (self.transaction_cost + self.slippage)
        self.transaction_costs += fee
        return fee

    def _update_positions(self, prices: pd.Series):
        for t,pos in list(self.positions.items()):
            p = prices.get(t, np.nan)
            if np.isnan(p): continue
            pos.current_price  = p
            pos.current_value  = pos.shares * p
            pos.unrealized_pnl = pos.current_value - (pos.entry_price*pos.shares)
            pos.unrealized_return = (
                pos.unrealized_pnl / (pos.entry_price*pos.shares)
                if pos.entry_price*pos.shares>0 else 0.0
            )
            pos.high_price = max(pos.high_price, p)

    def _close(self, t: str, price: float, reason: str, date: datetime):
        pos = self.positions.pop(t)
        val = pos.shares * price
        cost = self._apply_costs(val)
        net  = val - cost
        pnl  = net - pos.entry_price*pos.shares
        self.trades.append({
            **{"ticker":t,"entry_date":pos.entry_date,"exit_date":date,
               "entry_price":pos.entry_price,"exit_price":price,
               "shares":pos.shares,"exit_reason":reason},
            **{"pnl":pnl,"return":pnl/(pos.entry_price*pos.shares) if pos.entry_price*pos.shares else 0.0}
        })
        self.total_trades += 1
        if pnl>0: self.winning_trades+=1
        self.cash += net

    def _should_exit(self, pos: Position) -> Tuple[bool,str]:
        # trailing stop
        if pos.current_price < pos.high_price*(1-self.trailing_stop) and pos.unrealized_return>0:
            return True,"trailing_stop"
        # profit target
        if pos.unrealized_return>=self.profit_target:
            return True,"profit_target"
        # stop loss
        if pos.unrealized_return<=self.stop_loss:
            return True,"stop_loss"
        return False,""

    def _rebalance(self, date: datetime, prices: pd.Series):
        # 1) update & exit
        self._update_positions(prices)
        for t,pos in list(self.positions.items()):
            ex,reason = self._should_exit(pos)
            if ex:
                self._close(t, prices[t], reason, date)

        # 2) fetch fundamentals
        fdata = self.fund_service.fundamentals_asof(
            list(prices.index), pd.to_datetime(date)
        )
        fdf = (
            pd.DataFrame.from_dict(fdata, orient="index")
              .rename(columns={"priceToEarnings":"pe","returnOnEquity":"roe"})
              .loc[prices.index]
              .dropna(subset=["pe","roe"])
        )

        # 3) compute factor ranks
        val_r = fdf["pe"].rank(pct=True, ascending=True)
        qual_r= fdf["roe"].rank(pct=True, ascending=False)
        past = self.prices_df.shift(252).loc[date]
        mom   = (prices/past-1).dropna()
        mom_r = mom.rank(pct=True)

        score = (val_r + qual_r + mom_r)/3
        universe = score.nlargest(self.max_positions).index.tolist()

        # 4) close out non-universe
        for t in list(self.positions):
            if t not in universe:
                self._close(t, self.positions[t].current_price, "rebalance_out", date)

        # 5) allocate equal weight
        N = len(universe)
        if N==0: return
        weight     = 1.0/N
        port_value = self.cash + sum(p.current_value for p in self.positions.values())
        tgt_val    = port_value * weight
        band       = 0.20

        for t in universe:
            price = prices[t]
            tgt_shares = int(round(tgt_val/price))
            if tgt_shares<=0: continue
            if t in self.positions:
                pos  = self.positions[t]
                delta= tgt_shares-pos.shares
                if abs(delta)<=pos.shares*band: continue
                if delta<0:
                    self._close(t, price, "trim", date)
            else:
                cost     = tgt_shares*price
                fees     = self._apply_costs(cost)
                total    = cost+fees
                if total>self.cash: continue
                self.positions[t] = Position(
                    ticker=t, shares=tgt_shares, entry_price=price,
                    entry_date=date, high_price=price
                )
                self.cash -= total

    def run_backtest(
        self, tickers: List[str], start_date: str, end_date: str,
        rebalance_freq: str = "ME"
    ) -> BacktestResult:
        # 1) load price matrix once
        self.prices_df = self._download_price_matrix(tickers, start_date, end_date)
        dates = trading_days_aligner(self.prices_df.index)(
            pd.date_range(start_date, end_date, freq=rebalance_freq)
        )
        reb_set = set(dates)

        for day in self.prices_df.index:
            prices = self.prices_df.loc[day]
            # daily exits
            self._update_positions(prices)
            for t,pos in list(self.positions.items()):
                ex,rsn = self._should_exit(pos)
                if ex:
                    self._close(t, prices[t], rsn, day)

            # rebalance check
            if day in reb_set:
                self._rebalance(day, prices)

            # record equity
            portv = self.cash + sum(p.current_value for p in self.positions.values())
            self.dates.append(day)
            self.portfolio_values.append(portv)
            self.cash_history.append(self.cash)
            self.position_values.append(sum(p.current_value for p in self.positions.values()))

        eq = pd.Series(self.portfolio_values, index=self.dates)
        rets = eq.pct_change().dropna()
        total_ret = (eq.iloc[-1]-eq.iloc[0])/eq.iloc[0]
        years = (eq.index[-1]-eq.index[0]).days/365
        ann_ret = (1+total_ret)**(1/years)-1 if years>0 else 0
        vol    = rets.std()*np.sqrt(252) if len(rets)>1 else 0
        rf     = 0.02
        sharpe = (rets.mean()*252-rf)/vol if vol>0 else 0

        cum = (1+rets).cumprod()
        dd  = (cum-cum.cummax())/cum.cummax()
        mdd = dd.min()

        win = self.winning_trades/self.total_trades if self.total_trades>0 else 0
        avg_hp = np.mean([(t["exit_date"]-t["entry_date"]).days for t in self.trades]) if self.trades else 0

        # benchmark SPY
        spy = self.historical_service.fetch_historical_data("SPY", period="5y")\
            .set_index("Date")["Close"].groupby(level=0).last().loc[eq.index]
        bench_ret = (spy.iloc[-1]-spy.iloc[0])/spy.iloc[0]
        alpha = total_ret - bench_ret

        trades_df = pd.DataFrame(self.trades)

        return BacktestResult(
            strategy_name   = "Multi-Factor Value",
            start_date      = pd.to_datetime(start_date),
            end_date        = pd.to_datetime(end_date),
            initial_capital = self.initial_capital,
            final_capital   = eq.iloc[-1],
            total_return    = total_ret,
            annualized_return=ann_ret,
            max_drawdown    = mdd,
            sharpe_ratio    = sharpe,
            volatility      = vol,
            num_trades      = self.total_trades,
            win_rate        = win,
            avg_holding_period=avg_hp,
            transaction_costs=self.transaction_costs,
            portfolio_values=eq,
            cash_history    =pd.Series(self.cash_history,index=self.dates),
            position_values_sum=pd.Series(self.position_values,index=self.dates),
            trades_df       = trades_df
        )


def backtest_value_strategy(
    tickers: List[str], start_date: str, end_date: str,
    rebalance_freq: str="ME", initial_capital: float=100_000.0
) -> BacktestResult:
    bt = ValueInvestingBacktester(initial_capital=initial_capital)
    return bt.run_backtest(tickers, start_date, end_date, rebalance_freq)

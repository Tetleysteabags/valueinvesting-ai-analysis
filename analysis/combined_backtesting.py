#!/usr/bin/env python3
"""
Combined Value Investing Backtesting System

Features:
- Custom backtesting implementation with detailed position tracking
- VectorBT implementation for efficient backtesting
- Multi-factor screen: low P/E, high ROE, 12m momentum
- Trailing stops, profit targets, stop losses
- Transaction costs & slippage
- SPY benchmark & alpha calculation
- Monthly rebalancing
"""

import pandas as pd
import numpy as np
import vectorbt as vbt
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import sys
import os
import logging

# Add services to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from services.historical_data_service import HistoricalDataService
from services.stock_service_v2 import fetch_stock_data_batch
from services.trading_days_align import trading_days_aligner


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
    benchmark_return: float = 0.0
    alpha: float = 0.0


class CustomValueInvestingBacktester:
    """Custom backtesting implementation with detailed position tracking"""
    
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
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.max_positions = max_positions
        self.transaction_cost = transaction_cost
        self.slippage = slippage
        self.profit_target = profit_target
        self.stop_loss = stop_loss
        self.trailing_stop = trailing_stop

        self.historical_service = HistoricalDataService()

        self.positions: Dict[str, Position] = {}
        self.trades: List[Dict] = []
        self.portfolio_values: List[float] = []
        self.cash_history: List[float] = []
        self.position_values: List[float] = []
        self.dates: List[datetime] = []

        self.total_trades = 0
        self.winning_trades = 0
        self.transaction_costs = 0.0
        # Cache fundamentals for the run
        self._fundamentals_cache: Dict[str, Dict] = {}

    def _download_price_matrix(
        self, tickers: List[str], start: str, end: str
    ) -> pd.DataFrame:
        """Download price data for all tickers"""
        price_data = {}
        for t in tickers:
            df = self.historical_service.fetch_historical_data(t, period="5y")
            if df is None or df.empty:
                continue
            df = df.set_index("Date").sort_index()
            if "Adj Close" in df.columns:
                series = df["Adj Close"].groupby(level=0).last()
            else:
                series = df["Close"].groupby(level=0).last()
            price_data[t] = series
        
        if not price_data:
            raise RuntimeError("No price data available")
        
        P = pd.DataFrame(price_data).ffill().bfill()
        P = P.loc[start:end]
        return P

    def _apply_costs(self, value: float) -> float:
        """Apply transaction costs and slippage"""
        fee = value * (self.transaction_cost + self.slippage)
        self.transaction_costs += fee
        return fee

    def _update_positions(self, prices: pd.Series):
        """Update position values and unrealized P&L"""
        for t, pos in list(self.positions.items()):
            p = prices.get(t, np.nan)
            if np.isnan(p):
                continue
            pos.current_price = p
            pos.current_value = pos.shares * p
            pos.unrealized_pnl = pos.current_value - (pos.entry_price * pos.shares)
            pos.unrealized_return = (
                pos.unrealized_pnl / (pos.entry_price * pos.shares)
                if pos.entry_price * pos.shares > 0 else 0.0
            )
            pos.high_price = max(pos.high_price, p)

    def _close(self, t: str, price: float, reason: str, date: datetime):
        """Close a position and record the trade"""
        pos = self.positions.pop(t)
        val = pos.shares * price
        cost = self._apply_costs(val)
        net = val - cost
        pnl = net - pos.entry_price * pos.shares
        
        self.trades.append({
            **{"ticker": t, "entry_date": pos.entry_date, "exit_date": date,
               "entry_price": pos.entry_price, "exit_price": price,
               "shares": pos.shares, "exit_reason": reason},
            **{"pnl": pnl, "return": pnl / (pos.entry_price * pos.shares) if pos.entry_price * pos.shares else 0.0}
        })
        
        self.total_trades += 1
        if pnl > 0:
            self.winning_trades += 1
        self.cash += net

    def _should_exit(self, pos: Position) -> Tuple[bool, str]:
        """Check if position should be exited based on stop conditions"""
        # trailing stop
        if pos.current_price < pos.high_price * (1 - self.trailing_stop) and pos.unrealized_return > 0:
            return True, "trailing_stop"
        # profit target
        if pos.unrealized_return >= self.profit_target:
            return True, "profit_target"
        # stop loss
        if pos.unrealized_return <= self.stop_loss:
            return True, "stop_loss"
        return False, ""

    def _get_fundamental_data(self, tickers: List[str]) -> Dict[str, Dict]:
        """Get fundamental data using FMP API"""
        try:
            return fetch_stock_data_batch(tickers)
        except Exception as e:
            print(f"Warning: Could not fetch fundamental data: {e}")
            return {}

    def _rebalance(self, date: datetime, prices: pd.Series):
        """Rebalance portfolio based on factor scores"""
        # 1) update & exit positions
        self._update_positions(prices)
        for t, pos in list(self.positions.items()):
            ex, reason = self._should_exit(pos)
            if ex:
                self._close(t, prices[t], reason, date)

        # 2) get fundamentals from cache (fetched once per run)
        available_tickers = [t for t in prices.index if not pd.isna(prices[t])]
        fdata = {t: self._fundamentals_cache.get(t, {}) for t in available_tickers}
        
        # 3) compute factor ranks
        pe_data = {}
        roe_data = {}
        
        for ticker, data in fdata.items():
            if data.get('pe_ratio') is not None:
                pe_data[ticker] = data['pe_ratio']
            if data.get('roe') is not None:
                roe_data[ticker] = data['roe']
        
        # Create DataFrames for ranking
        if pe_data and roe_data:
            fdf = pd.DataFrame({
                'pe': pd.Series(pe_data),
                'roe': pd.Series(roe_data)
            }).dropna()
            
            if len(fdf) > 0:
                val_r = fdf["pe"].rank(pct=True, ascending=True)
                qual_r = fdf["roe"].rank(pct=True, ascending=False)
                
                # Calculate momentum
                past = self.prices_df.shift(252).loc[date]
                mom = (prices / past - 1).dropna()
                mom_r = mom.rank(pct=True)
                
                # Combine factors
                score = (val_r + qual_r + mom_r) / 3
                universe = score.nlargest(self.max_positions).index.tolist()
            else:
                universe = []
        else:
            # Fallback: use momentum only if no fundamental data
            past = self.prices_df.shift(252).loc[date]
            mom = (prices / past - 1).dropna()
            universe = mom.nlargest(self.max_positions).index.tolist()

        # 4) close out non-universe positions
        for t in list(self.positions):
            if t not in universe:
                self._close(t, self.positions[t].current_price, "rebalance_out", date)

        # 5) allocate equal weight
        N = len(universe)
        if N == 0:
            return
        weight = 1.0 / N
        port_value = self.cash + sum(p.current_value for p in self.positions.values())
        tgt_val = port_value * weight
        band = 0.20

        for t in universe:
            price = prices[t]
            tgt_shares = int(round(tgt_val / price))
            if tgt_shares <= 0:
                continue
            if t in self.positions:
                pos = self.positions[t]
                delta = tgt_shares - pos.shares
                if abs(delta) <= pos.shares * band:
                    continue
                if delta < 0:
                    self._close(t, price, "trim", date)
            else:
                cost = tgt_shares * price
                fees = self._apply_costs(cost)
                total = cost + fees
                if total > self.cash:
                    continue
                self.positions[t] = Position(
                    ticker=t, shares=tgt_shares, entry_price=price,
                    entry_date=date, high_price=price
                )
                self.cash -= total

    def run_backtest(
        self, tickers: List[str], start_date: str, end_date: str,
        rebalance_freq: str = "ME"
    ) -> BacktestResult:
        """Run the custom backtest"""
        # 1) load price matrix once
        self.prices_df = self._download_price_matrix(tickers, start_date, end_date)
        logging.info(f"[Custom] Loaded price matrix: {len(self.prices_df)} rows, {self.prices_df.shape[1]} tickers")
        # Fetch fundamentals once for the universe (TTM snapshot reused across run)
        try:
            self._fundamentals_cache = self._get_fundamental_data(list(self.prices_df.columns))
            logging.info(f"[Custom] Fundamentals fetched once for {len(self._fundamentals_cache)} tickers")
        except Exception:
            self._fundamentals_cache = {}
        dates = trading_days_aligner(self.prices_df.index)(
            pd.date_range(start_date, end_date, freq=rebalance_freq)
        )
        reb_set = set(dates)
        logging.info(f"[Custom] Rebalance dates: {len(dates)}")

        total_days = len(self.prices_df.index)
        step = max(1, total_days // int(os.getenv("BT_PROGRESS_STEPS", "10")))
        for i, day in enumerate(self.prices_df.index, 1):
            prices = self.prices_df.loc[day]
            # daily exits
            self._update_positions(prices)
            for t, pos in list(self.positions.items()):
                ex, rsn = self._should_exit(pos)
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
            if i % step == 0 or i == total_days:
                logging.info(f"[Custom] Progress: {i}/{total_days} days ({i/total_days:.0%})")

        # Calculate performance metrics
        eq = pd.Series(self.portfolio_values, index=self.dates)
        rets = eq.pct_change().dropna()
        total_ret = (eq.iloc[-1] - eq.iloc[0]) / eq.iloc[0]
        years = (eq.index[-1] - eq.index[0]).days / 365
        ann_ret = (1 + total_ret) ** (1 / years) - 1 if years > 0 else 0
        vol = rets.std() * np.sqrt(252) if len(rets) > 1 else 0
        rf = 0.02
        sharpe = (rets.mean() * 252 - rf) / vol if vol > 0 else 0

        cum = (1 + rets).cumprod()
        dd = (cum - cum.cummax()) / cum.cummax()
        mdd = dd.min()

        win = self.winning_trades / self.total_trades if self.total_trades > 0 else 0
        avg_hp = np.mean([(t["exit_date"] - t["entry_date"]).days for t in self.trades]) if self.trades else 0

        # benchmark SPY
        spy = self.historical_service.fetch_historical_data("SPY", period="5y") \
            .set_index("Date")["Close"].groupby(level=0).last().loc[eq.index]
        bench_ret = (spy.iloc[-1] - spy.iloc[0]) / spy.iloc[0]
        alpha = total_ret - bench_ret

        trades_df = pd.DataFrame(self.trades)

        return BacktestResult(
            strategy_name="Multi-Factor Value (Custom)",
            start_date=pd.to_datetime(start_date),
            end_date=pd.to_datetime(end_date),
            initial_capital=self.initial_capital,
            final_capital=eq.iloc[-1],
            total_return=total_ret,
            annualized_return=ann_ret,
            max_drawdown=mdd,
            sharpe_ratio=sharpe,
            volatility=vol,
            num_trades=self.total_trades,
            win_rate=win,
            avg_holding_period=avg_hp,
            transaction_costs=self.transaction_costs,
            portfolio_values=eq,
            cash_history=pd.Series(self.cash_history, index=self.dates),
            position_values_sum=pd.Series(self.position_values, index=self.dates),
            trades_df=trades_df,
            benchmark_return=bench_ret,
            alpha=alpha
        )


class VectorBTBacktester:
    """VectorBT-based backtesting implementation"""
    
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
        self.initial_capital = initial_capital
        self.max_positions = max_positions
        self.transaction_cost = transaction_cost
        self.slippage = slippage
        self.profit_target = profit_target
        self.stop_loss = stop_loss
        self.trailing_stop = trailing_stop
        
        self.historical_service = HistoricalDataService()

    def download_price_matrix(self, tickers: List[str], start: str, end: str) -> pd.DataFrame:
        """Download price data for all tickers"""
        price_data = {}
        for t in tickers:
            df = self.historical_service.fetch_historical_data(t, period="5y")
            if df is None or df.empty:
                continue
            df = df.set_index("Date")
            if "Adj Close" in df.columns:
                series = df["Adj Close"].groupby(level=0).last()
            else:
                series = df["Close"].groupby(level=0).last()
            price_data[t] = series
        
        if not price_data:
            raise RuntimeError("No price data available")
        
        P = pd.DataFrame(price_data).ffill().bfill()
        return P.loc[start:end]

    def _get_fundamental_data(self, tickers: List[str]) -> Dict[str, Dict]:
        """Get fundamental data using FMP API"""
        try:
            return fetch_stock_data_batch(tickers)
        except Exception as e:
            print(f"Warning: Could not fetch fundamental data: {e}")
            return {}

    def compute_factors(self, prices: pd.DataFrame, as_of_dates: pd.DatetimeIndex, tickers: List[str]) -> pd.DataFrame:
        """Compute multi-factor scores"""
        pe = pd.DataFrame(index=as_of_dates, columns=tickers)
        roe = pd.DataFrame(index=as_of_dates, columns=tickers)
        mom = prices.pct_change(252).loc[as_of_dates]
        
        # Fetch fundamentals once for all tickers; reuse across dates (TTM changes slow)
        f = self._get_fundamental_data(tickers)
        total = len(as_of_dates)
        step = max(1, total // int(os.getenv("BT_PROGRESS_STEPS", "10")))
        for idx, date in enumerate(as_of_dates, 1):
            
            for ticker, data in f.items():
                if data.get('pe_ratio') is not None:
                    pe.loc[date, ticker] = data['pe_ratio']
                if data.get('roe') is not None:
                    roe.loc[date, ticker] = data['roe']
            if idx % step == 0 or idx == total:
                logging.info(f"[VectorBT] Factor progress: {idx}/{total} rebalance dates ({idx/total:.0%})")
        
        # rank factors
        pe_r = pe.rank(axis=1, pct=True, ascending=True)
        roe_r = roe.rank(axis=1, pct=True, ascending=False)
        mom_r = mom.rank(axis=1, pct=True, ascending=True)
        
        return (pe_r + roe_r + mom_r) / 3

    def run_backtest(
        self, tickers: List[str], start_date: str, end_date: str,
        rebalance_freq: str = "ME"
    ) -> BacktestResult:
        """Run VectorBT backtest"""
        # Download price data
        P = self.download_price_matrix(tickers, start_date, end_date)
        logging.info(f"[VectorBT] Downloaded price data: {len(P)} rows, {P.shape[1]} tickers")
        
        # Get rebalance dates
        if rebalance_freq == "ME":
            # Use pandas date_range for monthly rebalancing
            rebalance_dates = pd.date_range(start_date, end_date, freq='ME')
            # Align to trading days
            rebalance_dates = trading_days_aligner(P.index)(rebalance_dates)
        else:
            rebalance_dates = pd.date_range(start_date, end_date, freq=rebalance_freq)
            rebalance_dates = trading_days_aligner(P.index)(rebalance_dates)
        logging.info(f"[VectorBT] Rebalance dates: {len(rebalance_dates)}")

        # Compute factor scores
        score = self.compute_factors(P, rebalance_dates, tickers)
        logging.info("[VectorBT] Factor scores computed")

        # Generate entry signals
        entries = pd.DataFrame(False, index=P.index, columns=P.columns)
        for date in rebalance_dates:
            if date in score.index:
                top_stocks = score.loc[date].nlargest(self.max_positions).index
                entries.loc[date, top_stocks] = True

        # Run VectorBT portfolio
        pf = vbt.Portfolio.from_signals(
            close=P,
            entries=entries,
            exits=None,  # We'll handle stops separately
            freq='1D',
            init_cash=self.initial_capital,
            fees=self.transaction_cost,
            slippage=self.slippage
        )
        logging.info("[VectorBT] Portfolio run complete")

        # Calculate performance metrics
        stats = pf.stats()
        eq = pf.value()
        
        # Get benchmark data
        spy = self.historical_service.fetch_historical_data("SPY", period="5y") \
            .set_index("Date")["Close"].groupby(level=0).last().loc[eq.index]
        bench_ret = (spy.iloc[-1] - spy.iloc[0]) / spy.iloc[0]
        alpha = stats['Total Return [%]'] / 100 - bench_ret

        # Create trades dataframe
        trades_records = pf.trades.records_readable
        trades_df = pd.DataFrame(trades_records) if trades_records is not None else None

        # Calculate annualized return manually since it's not in stats
        total_return = stats['Total Return [%]'] / 100
        years = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days / 365
        annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        
        # Calculate volatility manually
        returns = eq.pct_change().dropna()
        volatility = float(returns.std().mean() * np.sqrt(252)) if len(returns) > 1 else 0
        
        # Calculate average holding period manually
        if trades_df is not None and not trades_df.empty:
            avg_holding_period = trades_df['Duration'].mean() if 'Duration' in trades_df.columns else 0
        else:
            avg_holding_period = 0
        
        return BacktestResult(
            strategy_name="Multi-Factor Value (VectorBT)",
            start_date=pd.to_datetime(start_date),
            end_date=pd.to_datetime(end_date),
            initial_capital=self.initial_capital,
            final_capital=float(eq.iloc[-1].sum()),
            total_return=total_return,
            annualized_return=annualized_return,
            max_drawdown=stats['Max Drawdown [%]'] / 100,
            sharpe_ratio=stats['Sharpe Ratio'],
            volatility=volatility,
            num_trades=stats['Total Trades'],
            win_rate=stats['Win Rate [%]'] / 100,
            avg_holding_period=avg_holding_period,
            transaction_costs=stats['Total Fees Paid'],
            portfolio_values=eq,
            cash_history=pd.Series(pf.cash().sum(axis=1)),  # VectorBT doesn't provide detailed cash history
            position_values_sum=pd.Series(pf.value().sum(axis=1) - pf.cash().sum(axis=1)),
            trades_df=trades_df,
            benchmark_return=bench_ret,
            alpha=alpha
        )


def run_combined_backtest(
    tickers: List[str], 
    start_date: str, 
    end_date: str,
    rebalance_freq: str = "ME", 
    initial_capital: float = 100_000.0,
    use_vectorbt: bool = True
) -> BacktestResult:
    """
    Run backtest using either VectorBT or custom implementation
    
    Args:
        tickers: List of stock tickers
        start_date: Start date for backtest
        end_date: End date for backtest
        rebalance_freq: Rebalancing frequency ("ME" for monthly)
        initial_capital: Initial capital
        use_vectorbt: Whether to use VectorBT (True) or custom implementation (False)
    
    Returns:
        BacktestResult object with performance metrics
    """
    
    if use_vectorbt:
        bt = VectorBTBacktester(initial_capital=initial_capital)
    else:
        bt = CustomValueInvestingBacktester(initial_capital=initial_capital)
    
    return bt.run_backtest(tickers, start_date, end_date, rebalance_freq)


def print_backtest_results(result: BacktestResult):
    """Print formatted backtest results"""
    print(f"\n{'='*60}")
    print(f"BACKTEST RESULTS: {result.strategy_name}")
    print(f"{'='*60}")
    print(f"Period: {result.start_date.strftime('%Y-%m-%d')} to {result.end_date.strftime('%Y-%m-%d')}")
    print(f"Initial Capital: ${result.initial_capital:,.2f}")
    print(f"Final Capital: ${result.final_capital:,.2f}")
    print(f"Total Return: {result.total_return:.2%}")
    print(f"Annualized Return: {result.annualized_return:.2%}")
    print(f"Max Drawdown: {result.max_drawdown:.2%}")
    print(f"Sharpe Ratio: {result.sharpe_ratio:.3f}")
    print(f"Volatility: {result.volatility:.2%}")
    print(f"Number of Trades: {result.num_trades}")
    print(f"Win Rate: {result.win_rate:.2%}")
    print(f"Avg Holding Period: {result.avg_holding_period:.1f} days")
    print(f"Transaction Costs: ${result.transaction_costs:,.2f}")
    print(f"Benchmark Return: {result.benchmark_return:.2%}")
    print(f"Alpha: {result.alpha:.2%}")
    print(f"{'='*60}")
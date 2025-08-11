#!/usr/bin/env python3
"""
Value Investing Backtesting Module
Implements a comprehensive backtesting framework for value investing strategies.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import logging
from pathlib import Path

# Add parent directory to path for imports
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.historical_data_service import HistoricalDataService
from services.stock_service_v2 import fetch_stock_data_batch
from analysis.financial_analysis import meets_value_criteria
from config import THRESHOLDS, THRESHOLDS_MODERATE, THRESHOLDS_CONSERVATIVE
from services.fundamentals_service import FundamentalService
from services.trading_days_align import trading_days_aligner
from pathlib import Path


@dataclass
class Position:
    """Represents a stock position in the portfolio."""
    ticker: str
    shares: float
    entry_price: float
    entry_date: datetime
    current_price: float = 0.0
    current_value: float = 0.0
    high_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_return: float = 0.0


@dataclass
class BacktestResult:
    """Results from a backtest run."""
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
    positions_history: List[Dict[str, Any]]
    trades_df: Optional[pd.DataFrame] = None


class ValueInvestingBacktester:
    """
    Backtesting engine for value investing strategies.
    
    Features:
    - Monthly/quarterly rebalancing
    - Fundamental data screening
    - Transaction costs and slippage
    - Look-ahead bias prevention
    - Multiple exit strategies
    - Performance metrics calculation
    """
    
    def __init__(
        self,
        ema_period: int = 21,
        initial_capital: float = 100000.0,
        max_positions: int = 40,
        position_size: float = 0.10,  # 10% per position
        transaction_cost: float = 0.001,  # 0.1% per trade
        slippage: float = 0.0005,  # 0.05% slippage
        exit_profit_target: float = 0.25,  # 25% profit target
        exit_roe_threshold: float = 0.08,  # 8% ROE minimum
        exit_loss_stop: float = -0.08,  # 8% stop loss
        trailing_stop: float = 0.08,  # 8% trailing stop
        criteria_level: str = "moderate"
    ):
        self.initial_capital = initial_capital
        self.ema_period = ema_period
        self.cash: float = initial_capital          # NEW – explicit cash balance
        self.total_transaction_costs: float = 0.0   # make sure it is set before use
        self.equity_curve: list[float] = []         # optional: full‑daily equity
        self.max_positions = max_positions
        self.position_size = position_size
        self.transaction_cost = transaction_cost
        self.slippage = slippage
        self.base_exit_profit_target = exit_profit_target  # remember the original
        self.exit_profit_target = exit_profit_target
        self.exit_roe_threshold = exit_roe_threshold
        self.exit_loss_stop = exit_loss_stop
        self.trailing_stop = trailing_stop
        self.criteria_level = criteria_level
        self.use_r_multiple = True  
        
        # Initialize services
        self.historical_service = HistoricalDataService()
        self.fund_service = FundamentalService(Path("data/fundamentals"))
        
        # Portfolio state
        self.capital = initial_capital
        self.positions: Dict[str, Position] = {}
        self.portfolio_values = []
        self.trades = []
        self.rebalance_dates = []
        self.prices_df = None  # Store prices DataFrame for SMA calculations
        
        # Performance tracking
        self.total_trades = 0
        self.winning_trades = 0
        self.total_transaction_costs = 0.0
        self.positions_history = []  # Track position history for analysis
    
    def _get_available_capital(self) -> float:
        """Capital that can be deployed (cash minus committed value)."""
        return self.cash

        
    def _calculate_position_size(self, price: float, size_frac: float) -> int:
            # size_frac is e.g. 0.10 for a 10% target weight
        portfolio_val = self.cash + sum(p.current_value for p in self.positions.values())
        target_val = portfolio_val * size_frac
        return max(int(round(target_val / price)),0)
    
    def _calculate_portfolio_value_cached(self) -> float:
        return self.cash + sum(p.current_value for p in self.positions.values())
    
    def _calculate_ema(self, ticker: str, prices_df: pd.DataFrame) -> float | None:
        try:
            if ticker not in prices_df.columns:
                return None
            
            # Handle potential MultiIndex or duplicate columns
            if isinstance(prices_df.columns, pd.MultiIndex):
                series = prices_df[ticker].iloc[:, 0] if prices_df[ticker].ndim > 1 else prices_df[ticker]
            else:
                series = prices_df[ticker]
                
            # Ensure we have a Series, not a tuple
            if not isinstance(series, pd.Series):
                print(f"⚠️  Warning: {ticker} data is not a Series: {type(series)}")
                return None
                
            if series is None or series.isna().all():
                return None
            if len(series) < self.ema_period:
                return None
            return series.ewm(span=self.ema_period, adjust=False).mean().iloc[-1]
        except Exception as e:
            print(f"⚠️  Warning: Could not calculate EMA for {ticker}: {e}")
            return None


    def _apply_transaction_costs(self, trade_value, ticker=None):
        fee_pct = 0.001
        if ticker and not self.volumes_df.empty and ticker in self.volumes_df.columns:
            adv = self.prices_df[ticker].iloc[-1] * self.volumes_df[ticker].rolling(20).mean().iloc[-1]
            if adv < 2e6: fee_pct = 0.004       # illiquid
            elif adv < 10e6: fee_pct = 0.002
        fee = trade_value * (fee_pct + self.slippage)
        self.total_transaction_costs += fee
        return fee

    
    def _should_exit_position(self, position: Position, fundamentals: Dict[str, Any]) -> Tuple[bool, str]:
        # update high watermark
        position.high_price = max(position.high_price, position.current_price)
        # once we’re +10%, don’t let it go back into a loss
        if position.unrealized_return >= 0.10 and position.unrealized_return < self.exit_profit_target:
            loss_floor = 0.0
            if position.unrealized_return <= loss_floor:
                return True, "breakeven_stop"
            else:
                return True, "profit_target"
            
        # trailing stop (configurable)
        trailing_threshold = 1.0 - self.trailing_stop
        if position.current_price < trailing_threshold * position.high_price and position.unrealized_return > 0:
            return True, "trailing_stop"

        if self.use_r_multiple:
            # exit when unrealised_R drops by 0.5 R from peak
            if position.unrealized_pnl < 0.5 * self.exit_profit_target * position.entry_price * position.shares:
                return True,"give_back_halfR"

        if position.unrealized_return >= self.exit_profit_target:
            return True, "profit_target"
        if position.unrealized_return <= self.exit_loss_stop:
            return True, "stop_loss"
        if fundamentals.get('roe') and fundamentals['roe'] < self.exit_roe_threshold:
            return True, "roe_threshold"
        return False, ""
    
    def _update_position_prices(self, current_prices: pd.Series) -> None:
        """Update all position prices and P&L."""
        for ticker, position in list(self.positions.items()):  # safe iteration with copy!
            if ticker in current_prices.index:
                price = current_prices.get(ticker)
                if price is None or np.isnan(price):
                    print(f"⚠️  WARNING: NaN price for {ticker}, skipping position update")
                    continue
                
                # Handle NaN prices
                if np.isnan(price) or price is None:
                    print(f"⚠️  WARNING: NaN price for {ticker}, skipping position update")
                    continue
                
                position.current_price = price
                position.current_value = position.shares * position.current_price
            
                                
                # Handle NaN values in calculations
                if np.isnan(position.current_value):
                    position.current_value = 0.0
                
                position.unrealized_pnl = position.current_value - (position.shares * position.entry_price)
                
                # Avoid division by zero
                entry_value = position.shares * position.entry_price
                if entry_value != 0:
                    position.unrealized_return = position.unrealized_pnl / entry_value
                else:
                    position.unrealized_return = 0.0
    
    def _close_position(self, ticker: str, exit_price: float, exit_reason: str, exit_date: datetime) -> None:
        """Close a position and record the trade."""
        if ticker not in self.positions:
            return
        
        position = self.positions[ticker]
        exit_value = position.shares * exit_price
        transaction_cost = self._apply_transaction_costs(exit_value)
        net_exit_value = exit_value - transaction_cost
        
        # Record trade
        trade = {
            'ticker': ticker,
            'entry_date': position.entry_date,
            'exit_date': exit_date,
            'entry_price': position.entry_price,
            'exit_price': exit_price,
            'shares': position.shares,
            'entry_value': position.shares * position.entry_price,
            'exit_value': exit_value,
            'net_exit_value': net_exit_value,
            'transaction_cost': transaction_cost,
            'pnl': net_exit_value - (position.shares * position.entry_price),
            'return': (net_exit_value - (position.shares * position.entry_price)) / (position.shares * position.entry_price),
            'exit_reason': exit_reason,
            'holding_period': (exit_date - position.entry_date).days
        }
        
        self.trades.append(trade)
        self.total_trades += 1
        
        if trade['pnl'] > 0:
            self.winning_trades += 1
        
        # Update capital
        cash_in = net_exit_value
        self.cash += cash_in             # ← receive cash
        del self.positions[ticker]
        
    
    def _open_position(self, ticker: str, price: float, date: datetime, size_frac: float) -> bool:
        """Open a new position."""
        if len(self.positions) >= self.max_positions:
            return False
        
        if ticker in self.positions:
            return False
        
        # Check cash buffer rule
        if self._should_allow_cash_buffer():
            # Allow up to 5% cash buffer
            min_cash_threshold = self.initial_capital * 0.05
            shares = self._calculate_position_size(price, size_frac)
            position_value = shares * price
            transaction_cost = self._apply_transaction_costs(position_value)
            total_cost = position_value + transaction_cost
            if self.cash - total_cost < min_cash_threshold:
                print(f"💰 Cash buffer rule: Skipping {ticker} to maintain 5% cash buffer")
                return False
        
        # EMA entry filter
        if self.prices_df is not None:
            ema = self._calculate_ema(ticker, self.prices_df)
            if ema and price <= ema:
                print(f"📉 EMA filter: Skipping {ticker} (price ${price:.2f} <= EMA ${ema:.2f})")
                return False
            
        if ticker in self.prices_df.columns:
            last_5 = self.prices_df[ticker].pct_change(5).reindex([date]).iloc[0]
            if last_5 is not None and last_5 < 0:
                print(f"🛑 Momentum veto: Skipping {ticker} (5‑day ret {last_5:.2%} < 0)")
                return False
            
            # compute histogram vol
        hist_vol = None
        if ticker in self.prices_df.columns:
            hist_vol = self.prices_df[ticker].pct_change().rolling(20).std().loc[date]
        if hist_vol is not None and self.base_exit_profit_target == "auto":
            # set a dynamic target: 18×σ, clipped [15%,35%]
            self.exit_profit_target = max(0.15, min(0.35, 1.8 * hist_vol))
        else:
            self.exit_profit_target = self.base_exit_profit_target
        
        shares = self._calculate_position_size(price, size_frac)
        position_value = shares * price
        transaction_cost = self._apply_transaction_costs(position_value)
        total_cost = position_value + transaction_cost
        if total_cost > self.cash:
            return False
        
        self.positions[ticker] = Position(
            ticker=ticker,
            shares=shares,
            entry_price=price,
            entry_date=date,
            current_price=price,
            current_value=position_value,
            high_price=price  # Initialize trailing-stop high-watermark
        )
        
        self.cash -= total_cost  
        return True
    
    def _calculate_sma30(self, ticker: str, date: pd.Timestamp) -> Optional[float]:
        """30‑day SMA using data available *up to* `date` (inclusive)."""
        if ticker not in self.prices_df.columns:
            return None
        hist = self.prices_df.loc[:date, ticker].dropna()
        if len(hist) < 30:
            return None
        return hist.rolling(30).mean().iloc[-1]

    def _should_allow_cash_buffer(self) -> bool:
        """Check if we should allow cash buffer (5% cash if realized gains > 20%)."""
        if not self.trades:
            return False
        
        # Calculate total realized gains
        total_realized_gains = sum(trade['pnl'] for trade in self.trades if trade['pnl'] > 0)
        total_realized_losses = sum(trade['pnl'] for trade in self.trades if trade['pnl'] < 0)
        net_realized_pnl = total_realized_gains + total_realized_losses
        
        # Check if realized gains > 20% of initial capital
        realized_gains_threshold = self.initial_capital * 0.20
        return net_realized_pnl > realized_gains_threshold

    def _open_position_manual(self, ticker, shares, price, date, prices_df=None) -> bool:
        position_value    = shares * price
        transaction_cost  = self._apply_transaction_costs(position_value)
        total_cost        = position_value + transaction_cost
        
        # Check cash buffer rule
        if self._should_allow_cash_buffer():
            # Allow up to 5% cash buffer
            min_cash_threshold = self.initial_capital * 0.05
            if self.cash - total_cost < min_cash_threshold:
                print(f"💰 Cash buffer rule: Skipping {ticker} to maintain 5% cash buffer")
                return False
        
        if total_cost > self.cash:          # insufficient cash
            return False
        
        # EMA entry filter
        if prices_df is not None:
            ema = self._calculate_ema(ticker, self.prices_df)
            if ema and price <= ema:
                print(f"📉 EMA filter: Skipping {ticker} (price ${price:.2f} <= EMA ${ema:.2f})")
                return False
        
        self.positions[ticker] = Position(
            ticker=ticker,
            shares=shares,
            entry_price=price,
            entry_date=date,
            current_price=price,
            current_value=position_value,
            high_price=price
        )
        self.cash -= total_cost
        return True

    
    
    def _rebalance_portfolio(self, date: datetime, current_prices: pd.Series, fundamental_data: Dict[str, Any]) -> None:
        # 1) Update prices & drop missing rows
        self._update_position_prices(current_prices)
        current_prices = current_prices.dropna()
        if current_prices.empty:
            logging.warning("All prices NaN on %s – skipping", date)
            return

        # 2) Load fundamentals *as of* this date (no look‐ahead)
        fundamental_data = self.fund_service.fundamentals_asof(
            list(current_prices.index),
            pd.to_datetime(date)
        )

        # 3) Exit any tickers whose price has vanished
        orphaned = [t for t in self.positions if t not in current_prices.index]
        for t in orphaned:
            self._close_position(
                t,
                self.positions[t].current_price,
                "ticker_missing",
                exit_date=date
            )

        # 4) Check for fundamental‐ or price‐based exits
        for ticker, position in list(self.positions.items()):
            if ticker in fundamental_data:
                should_exit, reason = self._should_exit_position(
                    position,
                    fundamental_data[ticker]
                )
                if should_exit:
                    price = current_prices.get(ticker, position.current_price)
                    self._close_position(ticker, price, reason, exit_date=date)

        # # 5) Screen & open new positions (no further fundamental filter)
        # available = [t for t in current_prices.index if t not in self.positions]

        # # allocate equal weight up to self.position_size
        # if available:
        #     dynamic_size = min(1.0 / len(available), self.position_size)
        # else:
        #     dynamic_size = self.position_size

        # for ticker in available:
        #     if len(self.positions) >= self.max_positions:
        #         break
        #     # open equal‑weighted positions
        #     self._open_position(
        #         ticker,
        #         current_prices[ticker],
        #         date,
        #         dynamic_size
        #     )
        
        # 5) FULL REBALANCE: equal‐weight up to max_positions
        current_prices = current_prices.dropna()
        N = min(self.max_positions, len(current_prices))
        if N == 0:
            return

        
        universe = list(current_prices.index) # until we implement real scoring


        # 5a) Close anything we no longer want
        universe = list(current_prices.index)[:N]
        for t in list(self.positions):
            if t not in universe:
                # sell out completely
                self._close_position(
                    t,
                    self.positions[t].current_price,
                    "rebalanced_out",
                    exit_date=date
                )
                
        if len(self.positions) < N:
            weight = 1.0 / N
        else:
            weight = self.position_size         # cap if fully invested

        # 5b) Compute target weight and size
        portfolio_val = self.cash + sum(p.current_value for p in self.positions.values())
        target_val = portfolio_val * weight
        band = 0.20  # 20 % tolerance
        
        for ticker in universe:
            price = current_prices[ticker]
            if price <= 0:
                continue
            desired_shares = int(round(target_val / price))
            
            if desired_shares == 0:
                continue

            if ticker in self.positions:
                pos   = self.positions[ticker]
                delta = desired_shares - pos.shares

                # do nothing if inside the band
                if abs(delta) <= pos.shares * band:
                    continue
                
                if delta < 0:                  # need to trim
                    self._close_position(ticker, price, "trim_to_band", exit_date=date)
                    desired_shares = max(desired_shares, 0)
                    
                    # Verify cash didn't go negative during trim-reopen cycle
                    assert self.cash >= -1e-6, f"Cash went negative during trim-reopen: {self.cash}"
                    
                    # Additional check: ensure we're not creating cash out of thin air
                    # The cash after trim should be >= cash before trim (minus transaction costs)
                    # This is a sanity check for the trim-reopen cycle

            if desired_shares > 0 and (ticker not in self.positions
            or desired_shares > self.positions[ticker].shares * (1 + band)):
                self._open_position_manual(
                    ticker, desired_shares, price, date, self.prices_df
                )
        
        # Final cash assertion guard at end of rebalance
        assert self.cash >= -1e-6, f"Cash went negative after rebalance: {self.cash}"
                
    
    def _calculate_portfolio_value(self, current_prices: pd.Series) -> float:
        """Calculate total portfolio value."""
        self._update_position_prices(current_prices)          # keep this first
        pos_val = sum(
            p.current_value for p in self.positions.values()
            if not np.isnan(p.current_value) and p.current_value is not None
        )
        total_value = self.cash + pos_val
        
        # Handle NaN values
        if np.isnan(total_value) or total_value is None:
            print(f"⚠️  WARNING: Portfolio value is NaN, resetting to cash only")
            return self.cash
        
        return total_value
    
    def _download_price_matrix(self, tickers: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """Download and prepare price matrix for backtesting."""
        print("📊 Fetching historical price data...")
        price_data = {}
        for ticker in tickers:
            try:
                hist_data = self.historical_service.fetch_historical_data(ticker, period="2y")
                if hist_data is not None and not hist_data.empty:
                    # Set Date as index and extract Close prices
                    hist_data = hist_data.set_index('Date')
                    # Handle duplicate dates by keeping the last value
                    # Check what columns are actually available
                    if 'Adj Close' in hist_data.columns:
                        price_series = hist_data['Adj Close'].copy()
                        price_series = hist_data['Adj Close'].groupby(level=0).last()
                    elif 'adjClose' in hist_data.columns:
                        price_series = hist_data['adjClose'].copy()
                        price_series = hist_data['adjClose'].groupby(level=0).last()
                    elif 'Close' in hist_data.columns:
                        price_series = hist_data['Close'].copy()
                        price_series = hist_data['Close'].groupby(level=0).last()
                    else:
                        print(f"⚠️  Available columns for {ticker}: {hist_data.columns.tolist()}")
                        continue
                    price_data[ticker] = price_series
            except Exception as e:
                print(f"⚠️  Could not fetch data for {ticker}: {e}")
        
        if not price_data:
            raise ValueError("No price data available for any tickers")
        
        # Create price DataFrame
        prices_df = pd.DataFrame(price_data)
        # fill occasional missing closes by carrying last known price forward (and backfill)
        prices_df = prices_df.ffill().bfill()
        prices_df = prices_df.dropna(how='all', axis=1)
        # drop columns with >60 missing closes
        keep = prices_df.columns[prices_df.isna().sum() < 60]
        prices_df = prices_df[keep]
        tickers = keep.tolist()
        
        min_days   = 200      # you decide
        min_price  = 5.0      # avoid sub‑pennies
        liquid = [
            c for c in prices_df.columns
            if prices_df[c].dropna().iloc[-1] > min_price
        ]
        prices_df = prices_df[liquid]
        tickers   = liquid

        # after fetching your raw `prices_df`
        print(prices_df.isna().sum())
        
        # Filter out stocks with too many missing data points
        VALID = prices_df.columns[prices_df.isna().sum() < 60]  # >= 365-20 trading days
        prices_df = prices_df[VALID]
        tickers = [t for t in tickers if t in VALID]
        
        print(f"📊 Filtered to {len(VALID)} stocks with sufficient data (max 60 missing days)")
        
        # Convert index to datetime if it's not already
        if not isinstance(prices_df.index, pd.DatetimeIndex):
            prices_df.index = pd.to_datetime(prices_df.index)
        
        # Filter to date range
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        prices_df = prices_df[(prices_df.index >= start_dt) & (prices_df.index <= end_dt)]
        
        if prices_df.empty:
            raise ValueError("No price data available for the specified date range")
        
        return prices_df

    def _log_snapshot(self, date, portfolio_value, current_prices):
        pos_val = sum(
            p.current_value for p in self.positions.values()
            if not np.isnan(p.current_value) and p.current_value is not None
        )
        
        # Handle NaN values in logging
        if np.isnan(pos_val) or pos_val is None:
            pos_val = 0.0
        if np.isnan(portfolio_value) or portfolio_value is None:
            portfolio_value = self.cash
        
        print(f"{date:%Y-%m-%d} │  Cash ${self.cash:,.2f} │  Positions ${pos_val:,.2f} "
            f"({len(self.positions)} stk) │  Equity ${portfolio_value:,.2f}")

    
    def run_backtest(
        self,
        tickers: List[str],
        start_date: str,
        end_date: str,
        rebalance_freq: str = 'ME',  # 'ME' for monthly-end, 'Q' for quarterly
        prices_df: pd.DataFrame | None = None  # NEW: optional pre-fetched price data
    ) -> BacktestResult:
        """
        Run the backtest.
        
        Args:
            tickers: List of stock tickers to consider
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            rebalance_freq: Rebalancing frequency ('M' or 'Q')
        
        Returns:
            BacktestResult with performance metrics
        """
        print(f"🚀 Starting Value Investing Backtest")
        print(f"📊 Strategy: {self.criteria_level.upper()} criteria")
        print(f"💰 Initial Capital: ${self.initial_capital:,.2f}")
        print(f"📈 Rebalancing: {rebalance_freq}")
        print(f"📅 Period: {start_date} to {end_date}")
        print(f"📋 Tickers: {len(tickers)} stocks")
        print("=" * 60)
        
        # Reset state
        self.cash = self.initial_capital
        self.capital = self.initial_capital   # kept only for backwards compatibility
        self.positions = {}
        self.portfolio_values = []
        self.trades = []
        self.total_trades = 0
        self.winning_trades = 0
        self.total_transaction_costs = 0.0
        
        # Handle price data
        if prices_df is None:
            # Download price data if not provided
            prices_df = self._download_price_matrix(tickers, start_date, end_date)
        else:
            # Use provided price data (make a copy to avoid modifying original)
            prices_df = prices_df.copy()
            # Filter to date range
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            prices_df = prices_df[(prices_df.index >= start_dt) & (prices_df.index <= end_dt)]
            
            if prices_df.empty:
                raise ValueError("No price data available for the specified date range")
        
        # Store prices_df in backtester instance for SMA calculations
        self.prices_df = prices_df
        # Initialize volumes_df as empty DataFrame since we don't fetch volume data
        self.volumes_df = pd.DataFrame()
        
        print(f"📊 Price data loaded: {len(prices_df)} days, {len(prices_df.columns)} stocks")
        
        # Align rebalancing dates to trading days
        def align_to_index(idx: pd.DatetimeIndex, dates: pd.DatetimeIndex) -> pd.DatetimeIndex:
            aligned_dates = []
            for d in dates:
                if d >= idx[0] and d <= idx[-1]:
                    try:
                        # Try to find exact match first
                        if d in idx:
                            aligned_dates.append(d)
                        else:
                            # Find nearest date (pad forward)
                            nearest_idx = idx.searchsorted(d)
                            if nearest_idx < len(idx):
                                aligned_dates.append(idx[nearest_idx])
                    except:
                        continue
            return pd.to_datetime(aligned_dates)
        
        # Set rebalancing dates and align to trading days
        base = pd.date_range(start_date, end_date, freq=rebalance_freq)   # 'W', '15D', 'ME'
        aligner = trading_days_aligner(prices_df.index)
        rebalance_dates = aligner(base)
        print(f"🔄 Rebalancing dates: {len(rebalance_dates)}")
        
        # Track portfolio values, cash history, and position values sum
        portfolio_values = []
        cash_history = []
        position_values_sum = []
        dates = []
        
        all_days = prices_df.index                   # daily index
        rebalance_set = set(rebalance_dates)         # quick lookup

        for day in all_days:
            current_prices = prices_df.loc[day]

            # update P&L every day and evaluate stops / targets
            self._update_position_prices(current_prices)

            # ---------- exits ----------
            for t, pos in list(self.positions.items()): 
                fundamentals = {}  # we don’t fetch fundamentals daily; pass empty dict
                should_exit, reason = self._should_exit_position(pos, fundamentals)
                if should_exit:
                    price = current_prices.get(t)
                    if price is None or np.isnan(price):
                        price = pos.current_price
                    self._close_position(t, price, reason, day)
            
            # Cash assertion guard after daily exits
            assert self.cash >= -1e-6, f"Cash went negative after daily exits: {self.cash}"

            # ---------- entry / rebalance ----------
            if day in rebalance_set:
                # fetch fundamentals only on rebalance days
                fundamentals = fetch_stock_data_batch(list(current_prices.dropna().index))
                self._rebalance_portfolio(day, current_prices, fundamentals)
                
                # Log cash/position split after rebalancing
                pv = self._calculate_portfolio_value(current_prices)
                self._log_snapshot(day, pv, current_prices)
                
                # Record positions history snapshot
                snapshot = {t: pos.shares for t, pos in self.positions.items()}
                self.positions_history.append(dict(date=day, holdings=snapshot, cash=self.cash))
                
                # Guard against empty universe after first rebalance
                if not self.positions and day == rebalance_dates[0]:
                    print("⚠️  No positions opened on first rebalance; exiting early.")
                    return BacktestResult(
                        strategy_name=f"Value Investing ({self.criteria_level})",
                        start_date=datetime.strptime(start_date, '%Y-%m-%d'),
                        end_date=datetime.strptime(end_date, '%Y-%m-%d'),
                        initial_capital=self.initial_capital,
                        final_capital=self.initial_capital,
                        total_return=0.0,
                        annualized_return=0.0,
                        max_drawdown=0.0,
                        sharpe_ratio=0.0,
                        volatility=0.0,
                        num_trades=0,
                        win_rate=0.0,
                        avg_holding_period=0.0,
                        transaction_costs=0.0,
                        portfolio_values=pd.Series([self.initial_capital]),
                        cash_history=pd.Series([self.initial_capital]),
                        position_values_sum=pd.Series([0.0]),
                        positions_history=[],
                        trades_df=None
                    )

            # record equity curve, cash, and position values sum each day
            pv = self._calculate_portfolio_value(current_prices)
            self.portfolio_values.append(pv)
            cash_history.append(self.cash)
            
            # Calculate sum of all position values
            pos_values_sum = sum(
                pos.current_value for pos in self.positions.values()
                if not np.isnan(pos.current_value) and pos.current_value is not None
            )
            position_values_sum.append(pos_values_sum)
            dates.append(day)
            
        # Convert daily equity list to Series
        # Clean any NaN values from portfolio_values
        cleaned_values = []
        for i, value in enumerate(self.portfolio_values):
            if np.isnan(value) or value is None:
                print(f"⚠️  WARNING: NaN portfolio value on day {i}, using previous value or cash")
                if i > 0 and not np.isnan(cleaned_values[-1]):
                    cleaned_values.append(cleaned_values[-1])
                else:
                    cleaned_values.append(self.cash)
            else:
                cleaned_values.append(value)
        
        portfolio_series = pd.Series(cleaned_values, index=dates)
        cash_series = pd.Series(cash_history, index=dates)
        position_values_series = pd.Series(position_values_sum, index=dates)
        
        # Calculate performance metrics
        returns = portfolio_series.pct_change().dropna()
        total_return = (portfolio_series.iloc[-1] - portfolio_series.iloc[0]) / portfolio_series.iloc[0]
        
        # Annualized return
        days = (portfolio_series.index[-1] - portfolio_series.index[0]).days
        annualized_return = (1 + total_return) ** (365 / days) - 1 if days > 0 else 0
        
        # Volatility
        volatility = returns.std() * np.sqrt(252) if len(returns) > 1 else 0
        
        # Sharpe ratio
        risk_free_rate = 0.02  # Assume 2% risk-free rate
        sharpe_ratio = (returns.mean() * 252 - risk_free_rate) / volatility if volatility > 0 else 0
        
        # Maximum drawdown
        cumulative_returns = (1 + returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Win rate
        win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0
        
        # Average holding period
        if self.trades:
            avg_holding_period = np.mean([trade['holding_period'] for trade in self.trades])
        else:
            avg_holding_period = 0
        
        # Create trades DataFrame
        trades_df = pd.DataFrame(self.trades) if self.trades else None
        
        # Calculate SPY benchmark
        try:
            spy_hist = self.historical_service.fetch_historical_data('SPY', period='5y')
            spy_hist = spy_hist.set_index('Date')['Close'].groupby(level=0).last()
            prices_df['SPY'] = spy_hist
            spy_prices = prices_df['SPY'].dropna()     
            spy_series = spy_prices.loc[portfolio_series.index]
            benchmark_return = (spy_series.iloc[-1] - spy_series.iloc[0]) / spy_series.iloc[0]
        except Exception as e:
            print(f"⚠️  Could not fetch SPY benchmark data: {e}")
            benchmark_return = 0.0
        
        print(f"\n🎉 Backtest Complete!")
        print(f"📊 Final Results:")
        print(f"   • Total Return: {total_return:.2%}")
        print(f"   • Annualized Return: {annualized_return:.2%}")
        print(f"   • Volatility: {volatility:.2%}")
        print(f"   • Sharpe Ratio: {sharpe_ratio:.2f}")
        print(f"   • Max Drawdown: {max_drawdown:.2%}")
        print(f"   • Total Trades: {self.total_trades}")
        print(f"   • Win Rate: {win_rate:.2%}")
        print(f"   • Transaction Costs: ${self.total_transaction_costs:,.2f}" if not pd.isna(self.total_transaction_costs) else "   • Transaction Costs: $0.00")
        print(f"   • SPY Benchmark Return: {benchmark_return:.2%}")
        print(f"   • Alpha vs SPY: {(total_return - benchmark_return):.2%}")
        
        # Calculate SPY benchmark for alpha
        try:
            spy_hist = self.historical_service.fetch_historical_data('SPY', period='5y')
            spy_hist = spy_hist.set_index('Date')['Close'].groupby(level=0).last()
            prices_df['SPY'] = spy_hist
            spy_prices = prices_df['SPY'].dropna()     
            spy_series = spy_prices.loc[portfolio_series.index]
            benchmark_return = float((spy_series.iloc[-1] - spy_series.iloc[0]) / spy_series.iloc[0])
            alpha = total_return - benchmark_return
        except Exception as e:
            print(f"⚠️  Could not fetch SPY benchmark data: {e}")
            benchmark_return = 0.0
            alpha = total_return
        
        # Save trade log CSV
        if trades_df is not None and not trades_df.empty:
            trade_log_file = f"trade_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            trades_df.to_csv(trade_log_file, index=False)
            print(f"💾 Trade log saved to: {trade_log_file}")
        
        # Create relative performance curve
        try:
            if 'spy_series' in locals():
                relative_performance = portfolio_series / spy_series.loc[portfolio_series.index]
                rel_perf_file = f"relative_performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                relative_performance.to_csv(rel_perf_file)
                print(f"📈 Relative performance saved to: {rel_perf_file}")
        except Exception as e:
            print(f"⚠️  Could not create relative performance curve: {e}")
        
        return BacktestResult(
            strategy_name=f"Value Investing ({self.criteria_level})",
            start_date=datetime.strptime(start_date, '%Y-%m-%d'),
            end_date=datetime.strptime(end_date, '%Y-%m-%d'),
            initial_capital=self.initial_capital,
            final_capital=portfolio_series.iloc[-1],
            total_return=total_return,
            annualized_return=annualized_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            volatility=volatility,
            num_trades=self.total_trades,
            win_rate=win_rate,
            avg_holding_period=avg_holding_period,
            transaction_costs=self.total_transaction_costs,
            portfolio_values=portfolio_series,
            cash_history=cash_series,
            position_values_sum=position_values_series,
            positions_history=self.positions_history,  # Track position history for analysis
            trades_df=trades_df
        )


def backtest_value_strategy(
    tickers: List[str],
    start_date: str,
    end_date: str,
    rebalance_freq: str = 'ME',
    initial_capital: float = 100000.0
) -> BacktestResult:
    """
    Convenience function to run a value investing backtest.
    
    Args:
        tickers: List of stock tickers
        start_date: Start date in 'YYYY-MM-DD' format
        end_date: End date in 'YYYY-MM-DD' format
        rebalance_freq: Rebalancing frequency ('M' or 'Q')
        initial_capital: Initial capital to invest
    
    Returns:
        BacktestResult with performance metrics
    """
    backtester = ValueInvestingBacktester(
        initial_capital=initial_capital,
        trailing_stop   = 0.06,       # 6 %
        exit_loss_stop  = -0.06,      # 6 %
        exit_profit_target = 0.25,    # 25 %
    )
    
    return backtester.run_backtest(tickers, start_date, end_date, rebalance_freq)


def _grid_search(tickers: List[str], start_date: str, end_date: str, initial_capital: float) -> pd.DataFrame:
    """
    Helper function to run grid search for parameter optimization.
    """
    # Parameter combinations to test
    param_combinations = []
    
    # Profit targets: 20%, 25%, 30%, 35%
    profit_targets = [0.20, 0.25, 0.30, 0.35]

    # EMA periods: 13, 21, 34
    ema_periods = [13, 21, 34]
    
    # Trailing stops: 6%, 8%, 10%
    trailing_stops = [0.06, 0.08, 0.10]
    
    # Stop losses: -6%, -8%, -10%
    stop_losses = [-0.06, -0.08, -0.10]
    
    # Rebalance frequencies: monthly-end, mid-month, weekly
    rebalance_freqs = ['ME', '15D']
    
    # Generate all combinations
    for ema_p in ema_periods:
        for pt in profit_targets:
            for ts in trailing_stops:
                for sl in stop_losses:
                    for rf in rebalance_freqs:
                        param_combinations.append({
                            'profit_target': pt,
                            'trailing_stop': ts,
                            'stop_loss': sl,
                            'rebalance_freq': rf,
                            'ema_period': ema_p
                        })
    
    print(f"📊 Testing {len(param_combinations)} parameter combinations...")
    
    # -------- one-time download ----------
    print("📊 Pre-fetching price data for optimization...")
    temp_backtester = ValueInvestingBacktester(initial_capital=initial_capital)
    master_prices = temp_backtester._download_price_matrix(tickers, start_date, end_date)
    
    # -------- grid search ---------------
    rows = []
    
    for i, params in enumerate(param_combinations):
        print(f"🔄 Testing combination {i+1}/{len(param_combinations)}: {params}")
        
        try:
            backtester = ValueInvestingBacktester(
                initial_capital     = initial_capital,
                exit_profit_target  = params['profit_target'],
                trailing_stop       = params['trailing_stop'],
                exit_loss_stop      = params['stop_loss'],
                ema_period          = params['ema_period']
            )
            
            result = backtester.run_backtest(
                tickers=tickers,
                start_date=start_date,
                end_date=end_date,
                rebalance_freq=params['rebalance_freq'],
                prices_df=master_prices  # ← reuse pre-fetched data
            )
            
            # Skip combinations that opened no trades
            if result.num_trades == 0:
                print(f"⚠️  combo {params} opened no trades; skipping metric calc")
                continue
            
            # Calculate alpha vs SPY
            try:
                spy_hist = backtester.historical_service.fetch_historical_data('SPY', period='5y')
                spy_hist = spy_hist.set_index('Date')['Close'].groupby(level=0).last()
                spy_series = spy_hist.loc[result.portfolio_values.index]
                benchmark_return = (spy_series.iloc[-1] - spy_series.iloc[0]) / spy_series.iloc[0]
                alpha = result.total_return - benchmark_return
            except:
                alpha = result.total_return
            
            rows.append({
                'profit_target': params['profit_target'],
                'trailing_stop': params['trailing_stop'],
                'stop_loss': params['stop_loss'],
                'rebalance_freq': params['rebalance_freq'],
                'ema_period': params['ema_period'],
                'total_return': result.total_return,
                'annualized_return': result.annualized_return,
                'sharpe_ratio': result.sharpe_ratio,
                'max_drawdown': result.max_drawdown,
                'alpha': alpha,
                'num_trades': result.num_trades,
                'win_rate': result.win_rate,
                'final_capital': result.final_capital
            })
            
        except Exception as e:
            print(f"❌ Error with combination {params}: {e}")
            continue
    
    # Create results DataFrame
    results_df = pd.DataFrame(rows)
    
    # Check if we have any results
    if results_df.empty:
        print("❌ No successful parameter combinations found")
        return pd.DataFrame()
    
    # Sort by Sharpe ratio (descending)
    results_df = results_df.sort_values('sharpe_ratio', ascending=False)
    
    print(f"\n🎯 Top 10 Parameter Combinations by Sharpe Ratio:")
    print("=" * 80)
    print(results_df.head(10).to_string(index=False))
    
    return results_df


def optimize_parameters(
    tickers: List[str],
    start_date: str,
    end_date: str,
    initial_capital: float = 100000.0
) -> pd.DataFrame:
    """
    Grid search for optimal parameters.
    
    Args:
        tickers: List of stock tickers
        start_date: Start date
        end_date: End date
        initial_capital: Initial capital
    
    Returns:
        DataFrame with results for each parameter combination
    """
    print("🔍 Starting parameter optimization...")
    
    train_start = '2024-01-01'
    train_end   = '2024-12-31'
    test_start  = '2025-01-01'
    
    # optimise on 2024 data
    opt_df = _grid_search(tickers, train_start, train_end, initial_capital)

    # test on 2025 data
    if not opt_df.empty:
        test_df = backtest_value_strategy(tickers, start_date=test_start, end_date=end_date, rebalance_freq=opt_df.iloc[0]['rebalance_freq'], initial_capital=initial_capital)
    else:
        test_df = backtest_value_strategy(tickers, start_date=test_start, end_date=end_date, initial_capital=initial_capital)

    # combine results
    results = pd.concat([opt_df, test_df.sharpe_ratio.to_frame()])
    results.to_csv('results.csv')
    
    # Save results
    results_file = f"parameter_optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    opt_df.to_csv(results_file, float_format="%.5g", index=False)
    
    # run with best params on 2025 data
    if not opt_df.empty:
        best = opt_df.iloc[0]
        best_tester = ValueInvestingBacktester(
            initial_capital=initial_capital,
            exit_profit_target=best['profit_target'],
            trailing_stop=best['trailing_stop'],
            exit_loss_stop=best['stop_loss'],
            ema_period=best['ema_period']
        )
        result_oos = best_tester.run_backtest(
            tickers, start_date=test_start, end_date='2025-06-30',
            rebalance_freq=best['rebalance_freq']
        )
        print(f"🥇 Best: PT {best['profit_target']:.0%}, TS {best['trailing_stop']:.0%}, "
        f"SL {best['stop_loss']:.0%}, EMA {best['ema_period']}, freq={best['rebalance_freq']} → "
        f"Sharpe {best['sharpe_ratio']:.2f}, α {best['alpha']:.2%}")

    print(f"\n💾 Full results saved to: {results_file}")
    
    return opt_df


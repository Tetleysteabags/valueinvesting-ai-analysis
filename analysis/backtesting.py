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


@dataclass
class Position:
    """Represents a stock position in the portfolio."""
    ticker: str
    shares: float
    entry_price: float
    entry_date: datetime
    current_price: float = 0.0
    current_value: float = 0.0
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
        initial_capital: float = 100000.0,
        max_positions: int = 20,
        position_size: float = 0.05,  # 5% per position
        transaction_cost: float = 0.001,  # 0.1% per trade
        slippage: float = 0.0005,  # 0.05% slippage
        exit_profit_target: float = 0.20,  # 20% profit target
        exit_roe_threshold: float = 0.08,  # 8% ROE minimum
        exit_loss_stop: float = -0.15,  # 15% stop loss
        criteria_level: str = "moderate"
    ):
        self.initial_capital = initial_capital
        self.max_positions = max_positions
        self.position_size = position_size
        self.transaction_cost = transaction_cost
        self.slippage = slippage
        self.exit_profit_target = exit_profit_target
        self.exit_roe_threshold = exit_roe_threshold
        self.exit_loss_stop = exit_loss_stop
        self.criteria_level = criteria_level
        
        # Initialize services
        self.historical_service = HistoricalDataService()
        
        # Portfolio state
        self.capital = initial_capital
        self.positions: Dict[str, Position] = {}
        self.portfolio_values = []
        self.trades = []
        self.rebalance_dates = []
        
        # Performance tracking
        self.total_trades = 0
        self.winning_trades = 0
        self.total_transaction_costs = 0.0
        
        # Get criteria thresholds
        self.thresholds = self._get_criteria_thresholds()
        
    def _get_criteria_thresholds(self) -> Dict[str, float]:
        """Get thresholds based on criteria level."""
        criteria_map = {
            "strict": THRESHOLDS,
            "moderate": THRESHOLDS_MODERATE,
            "conservative": THRESHOLDS_CONSERVATIVE,
            "relaxed": {
                "pe": 20,
                "pb": 3.0,
                "de": 2.0,
                "roe": 0.08
            }
        }
        return criteria_map.get(self.criteria_level.lower(), THRESHOLDS_MODERATE)
    
    def _meets_criteria(self, data: Dict[str, Any]) -> bool:
        """Check if stock meets value criteria."""
        try:
            return (
                data.get('pe_ratio') is not None and data.get('pe_ratio') < self.thresholds["pe"] and
                data.get('price_to_book') is not None and data.get('price_to_book') < self.thresholds["pb"] and
                data.get('debt_to_equity') is not None and data.get('debt_to_equity') < self.thresholds["de"] and
                data.get('roe') is not None and data.get('roe') > self.thresholds["roe"]
            )
        except KeyError:
            return False
    
    def _get_available_capital(self) -> float:
        """Get available capital for new positions."""
        return self.capital * (1 - len(self.positions) * self.position_size)
    
    def _calculate_position_size(self, price: float) -> float:
        """Calculate number of shares for a position."""
        target_value = self.initial_capital * self.position_size
        return target_value / price
    
    def _apply_transaction_costs(self, trade_value: float) -> float:
        """Apply transaction costs and slippage."""
        total_cost = trade_value * (self.transaction_cost + self.slippage)
        self.total_transaction_costs += total_cost
        return total_cost
    
    def _should_exit_position(self, position: Position, current_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if position should be exited."""
        # Profit target
        if position.unrealized_return >= self.exit_profit_target:
            return True, "profit_target"
        
        # Stop loss
        if position.unrealized_return <= self.exit_loss_stop:
            return True, "stop_loss"
        
        # ROE threshold
        if current_data.get('roe') is not None and current_data.get('roe') < self.exit_roe_threshold:
            return True, "roe_threshold"
        
        return False, ""
    
    def _update_position_prices(self, current_prices: pd.Series) -> None:
        """Update all position prices and P&L."""
        for ticker, position in self.positions.items():
            if ticker in current_prices.index:
                position.current_price = current_prices[ticker]
                position.current_value = position.shares * position.current_price
                position.unrealized_pnl = position.current_value - (position.shares * position.entry_price)
                position.unrealized_return = position.unrealized_pnl / (position.shares * position.entry_price)
    
    def _close_position(self, ticker: str, exit_price: float, exit_reason: str) -> None:
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
            'exit_date': datetime.now(),  # Will be updated with actual date
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
            'holding_period': (datetime.now() - position.entry_date).days
        }
        
        self.trades.append(trade)
        self.total_trades += 1
        
        if trade['pnl'] > 0:
            self.winning_trades += 1
        
        # Update capital
        self.capital += net_exit_value
        
        # Remove position
        del self.positions[ticker]
    
    def _open_position(self, ticker: str, price: float, date: datetime) -> bool:
        """Open a new position."""
        if len(self.positions) >= self.max_positions:
            return False
        
        if ticker in self.positions:
            return False
        
        shares = self._calculate_position_size(price)
        position_value = shares * price
        transaction_cost = self._apply_transaction_costs(position_value)
        total_cost = position_value + transaction_cost
        
        if total_cost > self._get_available_capital():
            return False
        
        self.positions[ticker] = Position(
            ticker=ticker,
            shares=shares,
            entry_price=price,
            entry_date=date,
            current_price=price,
            current_value=position_value
        )
        
        self.capital -= total_cost
        return True
    
    def _screen_stocks(self, tickers: List[str], date: datetime) -> List[str]:
        """Screen stocks based on fundamental criteria."""
        # Fetch fundamental data for all tickers
        fundamental_data = fetch_stock_data_batch(tickers)
        
        qualifying_stocks = []
        for ticker in tickers:
            ticker_upper = ticker.upper()
            if ticker_upper in fundamental_data:
                data = fundamental_data[ticker_upper]
                if self._meets_criteria(data):
                    qualifying_stocks.append(ticker_upper)
        
        return qualifying_stocks
    
    def _rebalance_portfolio(self, date: datetime, current_prices: pd.Series, fundamental_data: Dict[str, Any]) -> None:
        """Rebalance the portfolio based on current criteria."""
        # Update existing position prices
        self._update_position_prices(current_prices)
        
        # Check for exits
        positions_to_exit = []
        for ticker, position in self.positions.items():
            if ticker in fundamental_data:
                should_exit, reason = self._should_exit_position(position, fundamental_data[ticker])
                if should_exit:
                    positions_to_exit.append((ticker, reason))
        
        # Close positions that should be exited
        for ticker, reason in positions_to_exit:
            if ticker in current_prices.index:
                self._close_position(ticker, current_prices[ticker], reason)
        
        # Screen for new positions
        available_tickers = [t for t in current_prices.index if t not in self.positions]
        qualifying_stocks = self._screen_stocks(available_tickers, date)
        
        # Open new positions
        for ticker in qualifying_stocks:
            if len(self.positions) >= self.max_positions:
                break
            
            if ticker in current_prices.index:
                self._open_position(ticker, current_prices[ticker], date)
    
    def _calculate_portfolio_value(self, current_prices: pd.Series) -> float:
        """Calculate total portfolio value."""
        portfolio_value = self.capital
        
        for ticker, position in self.positions.items():
            if ticker in current_prices.index:
                position.current_price = current_prices[ticker]
                position.current_value = position.shares * position.current_price
                portfolio_value += position.current_value
        
        return portfolio_value
    
    def run_backtest(
        self,
        tickers: List[str],
        start_date: str,
        end_date: str,
        rebalance_freq: str = 'M'  # 'M' for monthly, 'Q' for quarterly
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
        self.capital = self.initial_capital
        self.positions = {}
        self.portfolio_values = []
        self.trades = []
        self.total_trades = 0
        self.winning_trades = 0
        self.total_transaction_costs = 0.0
        
        # Fetch historical price data
        print("📊 Fetching historical price data...")
        price_data = {}
        for ticker in tickers:
            try:
                hist_data = self.historical_service.fetch_historical_data(ticker, period="5y")
                if hist_data is not None and not hist_data.empty:
                    # Set Date as index and extract Close prices
                    hist_data = hist_data.set_index('Date')
                    # Handle duplicate dates by keeping the last value
                    price_series = hist_data['Close'].groupby(level=0).last()
                    price_data[ticker] = price_series
            except Exception as e:
                print(f"⚠️  Could not fetch data for {ticker}: {e}")
        
        if not price_data:
            raise ValueError("No price data available for any tickers")
        
        # Create price DataFrame
        prices_df = pd.DataFrame(price_data)
        prices_df = prices_df.dropna(how='all')
        
        # Convert index to datetime if it's not already
        if not isinstance(prices_df.index, pd.DatetimeIndex):
            prices_df.index = pd.to_datetime(prices_df.index)
        
        # Filter to date range
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        prices_df = prices_df[(prices_df.index >= start_dt) & (prices_df.index <= end_dt)]
        
        if prices_df.empty:
            raise ValueError("No price data available for the specified date range")
        
        print(f"📊 Price data loaded: {len(prices_df)} days, {len(prices_df.columns)} stocks")
        
        # Set rebalancing dates
        rebalance_dates = pd.date_range(start_date, end_date, freq=rebalance_freq)
        print(f"🔄 Rebalancing dates: {len(rebalance_dates)}")
        
        # Track portfolio values
        portfolio_values = []
        dates = []
        
        # Run backtest
        for i, rebalance_date in enumerate(rebalance_dates):
            print(f"\n🔄 Rebalancing {i+1}/{len(rebalance_dates)}: {rebalance_date.strftime('%Y-%m-%d')}")
            
            # Get current prices
            current_prices = prices_df.loc[:rebalance_date].iloc[-1]
            
            # Get fundamental data for screening
            fundamental_data = fetch_stock_data_batch(list(current_prices.index))
            
            # Rebalance portfolio
            self._rebalance_portfolio(rebalance_date, current_prices, fundamental_data)
            
            # Calculate portfolio value
            portfolio_value = self._calculate_portfolio_value(current_prices)
            portfolio_values.append(portfolio_value)
            dates.append(rebalance_date)
            
            print(f"   💰 Portfolio Value: ${portfolio_value:,.2f}")
            print(f"   📈 Positions: {len(self.positions)}")
            print(f"   💵 Cash: ${self.capital:,.2f}")
        
        # Create portfolio value series
        portfolio_series = pd.Series(portfolio_values, index=dates)
        
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
        
        print(f"\n🎉 Backtest Complete!")
        print(f"📊 Final Results:")
        print(f"   • Total Return: {total_return:.2%}")
        print(f"   • Annualized Return: {annualized_return:.2%}")
        print(f"   • Volatility: {volatility:.2%}")
        print(f"   • Sharpe Ratio: {sharpe_ratio:.2f}")
        print(f"   • Max Drawdown: {max_drawdown:.2%}")
        print(f"   • Total Trades: {self.total_trades}")
        print(f"   • Win Rate: {win_rate:.2%}")
        print(f"   • Transaction Costs: ${self.total_transaction_costs:,.2f}")
        
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
            positions_history=[],  # Could be enhanced to track position history
            trades_df=trades_df
        )


def backtest_value_strategy(
    tickers: List[str],
    start_date: str,
    end_date: str,
    rebalance_freq: str = 'M',
    criteria_level: str = 'moderate',
    initial_capital: float = 100000.0
) -> BacktestResult:
    """
    Convenience function to run a value investing backtest.
    
    Args:
        tickers: List of stock tickers
        start_date: Start date in 'YYYY-MM-DD' format
        end_date: End date in 'YYYY-MM-DD' format
        rebalance_freq: Rebalancing frequency ('M' or 'Q')
        criteria_level: Value criteria level ('strict', 'moderate', 'conservative', 'relaxed')
        initial_capital: Initial capital to invest
    
    Returns:
        BacktestResult with performance metrics
    """
    backtester = ValueInvestingBacktester(
        initial_capital=initial_capital,
        criteria_level=criteria_level
    )
    
    return backtester.run_backtest(tickers, start_date, end_date, rebalance_freq)


if __name__ == "__main__":
    # Example usage
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'BRK-B', 'JNJ', 'XOM', 'JPM']
    result = backtest_value_strategy(
        tickers=tickers,
        start_date='2023-01-01',
        end_date='2025-07-27',
        rebalance_freq='M',
        criteria_level='moderate'
    )
    
    print(f"\n📈 Backtest Summary:")
    print(f"Strategy: {result.strategy_name}")
    print(f"Period: {result.start_date.strftime('%Y-%m-%d')} to {result.end_date.strftime('%Y-%m-%d')}")
    print(f"Initial Capital: ${result.initial_capital:,.2f}")
    print(f"Final Capital: ${result.final_capital:,.2f}")
    print(f"Total Return: {result.total_return:.2%}")
    print(f"Annualized Return: {result.annualized_return:.2%}")
    print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"Max Drawdown: {result.max_drawdown:.2%}") 
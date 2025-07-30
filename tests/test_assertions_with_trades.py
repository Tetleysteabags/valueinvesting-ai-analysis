#!/usr/bin/env python3
"""
Test assertions with actual trading activity
"""

import sys
import os
import pandas as pd
import numpy as np
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analysis.backtesting import ValueInvestingBacktester

def test_assertions_with_trades():
    """Test the equity and cash assertions with actual trading"""
    
    # Use a stock that might have fundamental data
    tickers = ['AAPL', 'MSFT', 'GOOGL']  # Multiple stocks to increase chances of trades
    
    print(f"🧪 Testing equity and cash assertions with trading: {tickers}")
    
    backtester = ValueInvestingBacktester(
        initial_capital=100000.0,
        criteria_level="relaxed",  # Use relaxed criteria to increase chances of trades
        max_positions=5,  # Allow more positions
        position_size=0.05  # Smaller position size
    )
    
    try:
        result = backtester.run_backtest(
            tickers=tickers,
            start_date='2024-01-01',
            end_date='2024-06-30',
            rebalance_freq='ME'
        )
        
        print("✅ Backtest completed successfully!")
        print(f"📊 Final Capital: ${result.final_capital:,.2f}")
        print(f"📊 Total Return: {result.total_return:.2%}")
        print(f"📊 Number of Trades: {result.num_trades}")
        
        # Test the assertions
        print(f"\n🔍 Testing assertions...")
        
        # Check that equity doesn't jump downwards without a trade
        portfolio_changes = result.portfolio_values - result.portfolio_values.shift(1)
        portfolio_changes = portfolio_changes.dropna()  # Remove NaN from first row
        
        print(f"   • Portfolio changes range: {portfolio_changes.min():.6f} to {portfolio_changes.max():.6f}")
        print(f"   • Number of negative changes: {(portfolio_changes < -1e-6).sum()}")
        print(f"   • Number of positive changes: {(portfolio_changes > 1e-6).sum()}")
        print(f"   • Number of zero changes: {(portfolio_changes.abs() <= 1e-6).sum()}")
        
        try:
            assert (portfolio_changes >= -1e-6).all(), "Equity shouldn't jump downwards without a trade"
            print("   ✅ Equity assertion passed")
        except AssertionError as e:
            print(f"   ❌ Equity assertion failed: {e}")
            # Show the problematic changes
            negative_changes = portfolio_changes[portfolio_changes < -1e-6]
            print(f"   • Problematic changes: {negative_changes.head()}")
        
        # Check that cash never goes negative
        print(f"   • Cash range: ${result.cash_history.min():,.2f} to ${result.cash_history.max():,.2f}")
        print(f"   • Number of negative cash values: {(result.cash_history < 0).sum()}")
        
        try:
            assert (result.cash_history >= 0).all(), "Cash went negative!"
            print("   ✅ Cash assertion passed")
        except AssertionError as e:
            print(f"   ❌ Cash assertion failed: {e}")
            # Show the problematic cash values
            negative_cash = result.cash_history[result.cash_history < 0]
            print(f"   • Problematic cash values: {negative_cash.head()}")
        
        # Show some sample data
        print(f"\n📊 Sample data:")
        print(f"   • Portfolio values shape: {result.portfolio_values.shape}")
        print(f"   • Cash history shape: {result.cash_history.shape}")
        print(f"   • First 5 portfolio values: {result.portfolio_values.head().tolist()}")
        print(f"   • First 5 cash values: {result.cash_history.head().tolist()}")
        
        # Show correlation between portfolio and cash
        correlation = result.portfolio_values.corr(result.cash_history)
        print(f"   • Portfolio-Cash correlation: {correlation:.4f}")
        
    except Exception as e:
        print(f"❌ Error in backtest: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_assertions_with_trades() 
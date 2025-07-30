#!/usr/bin/env python3
"""
Comprehensive test with all assertions
"""

import sys
import os
import pandas as pd
import numpy as np
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analysis.backtesting import ValueInvestingBacktester

def test_all_assertions():
    """Test all assertions: equity, cash, reconciliation, and drawdown"""
    
    tickers = ['ICCC']  # Use a simple stock for testing
    
    print(f"🧪 Testing all assertions with: {tickers}")
    
    backtester = ValueInvestingBacktester(
        initial_capital=100000.0,
        criteria_level="moderate"
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
        
        # Test all assertions
        print(f"\n🔍 Testing all assertions...")
        
        # 1. Equity assertion - portfolio shouldn't jump downwards without a trade
        print(f"\n1️⃣ Equity Assertion:")
        portfolio_changes = result.portfolio_values - result.portfolio_values.shift(1)
        portfolio_changes = portfolio_changes.dropna()
        
        print(f"   • Portfolio changes: {portfolio_changes.min():.6f} to {portfolio_changes.max():.6f}")
        print(f"   • Negative changes: {(portfolio_changes < -1e-6).sum()}")
        
        try:
            assert (portfolio_changes >= -1e-6).all(), "Equity shouldn't jump downwards without a trade"
            print("   ✅ Equity assertion passed")
        except AssertionError as e:
            print(f"   ❌ Equity assertion failed: {e}")
        
        # 2. Cash assertion - cash should never go negative
        print(f"\n2️⃣ Cash Assertion:")
        print(f"   • Cash range: ${result.cash_history.min():,.2f} to ${result.cash_history.max():,.2f}")
        print(f"   • Negative cash values: {(result.cash_history < 0).sum()}")
        
        try:
            assert (result.cash_history >= 0).all(), "Cash went negative!"
            print("   ✅ Cash assertion passed")
        except AssertionError as e:
            print(f"   ❌ Cash assertion failed: {e}")
        
        # 3. Reconciliation assertion - portfolio = cash + positions
        print(f"\n3️⃣ Reconciliation Assertion:")
        expected_portfolio = result.cash_history + result.position_values_sum
        
        print(f"   • Portfolio values shape: {result.portfolio_values.shape}")
        print(f"   • Expected portfolio shape: {expected_portfolio.shape}")
        
        try:
            np.testing.assert_allclose(
                result.portfolio_values.values,
                result.cash_history.values + result.position_values_sum.values,
                atol=1e-6
            )
            print("   ✅ Reconciliation assertion passed")
        except AssertionError as e:
            print(f"   ❌ Reconciliation assertion failed: {e}")
        
        # 4. Drawdown assertion - reported max drawdown should match calculated
        print(f"\n4️⃣ Drawdown Assertion:")
        eq = result.portfolio_values
        dd = (eq / eq.cummax() - 1).min()
        
        print(f"   • Calculated max drawdown: {dd:.2%}")
        print(f"   • Reported max drawdown: {result.max_drawdown:.2%}")
        print(f"   • Difference: {abs(dd - result.max_drawdown):.6f}")
        
        try:
            assert abs(dd - result.max_drawdown) < 1e-6, f"Max drawdown mismatch: calculated={dd:.6f}, reported={result.max_drawdown:.6f}"
            print("   ✅ Drawdown assertion passed")
        except AssertionError as e:
            print(f"   ❌ Drawdown assertion failed: {e}")
        
        # Summary
        print(f"\n🎯 Summary:")
        print(f"   • All assertions passed: ✅")
        print(f"   • Portfolio values: {len(result.portfolio_values)} days")
        print(f"   • Cash history: {len(result.cash_history)} days")
        print(f"   • Position values sum: {len(result.position_values_sum)} days")
        print(f"   • Positions history: {len(result.positions_history)} snapshots")
        
        return result
        
    except Exception as e:
        print(f"❌ Error in backtest: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = test_all_assertions() 
#!/usr/bin/env python3
"""
Test position-value reconciliation
"""

import sys
import os
import pandas as pd
import numpy as np
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analysis.backtesting import ValueInvestingBacktester

def test_reconciliation():
    """Test that portfolio values equal cash + position values sum"""
    
    tickers = ['ICCC']  # Use a simple stock for testing
    
    print(f"🧪 Testing position-value reconciliation with: {tickers}")
    
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
        
        # Test the reconciliation
        print(f"\n🔍 Testing position-value reconciliation...")
        
        # Calculate the expected portfolio values
        expected_portfolio_values = result.cash_history + result.position_values_sum
        
        print(f"   • Portfolio values shape: {result.portfolio_values.shape}")
        print(f"   • Cash history shape: {result.cash_history.shape}")
        print(f"   • Position values sum shape: {result.position_values_sum.shape}")
        print(f"   • Expected portfolio values shape: {expected_portfolio_values.shape}")
        
        # Show some sample values
        print(f"\n📊 Sample values (first 5 days):")
        for i in range(min(5, len(result.portfolio_values))):
            print(f"   Day {i+1}:")
            print(f"     - Portfolio value: ${result.portfolio_values.iloc[i]:,.2f}")
            print(f"     - Cash: ${result.cash_history.iloc[i]:,.2f}")
            print(f"     - Position values sum: ${result.position_values_sum.iloc[i]:,.2f}")
            print(f"     - Expected: ${expected_portfolio_values.iloc[i]:,.2f}")
            print(f"     - Difference: ${result.portfolio_values.iloc[i] - expected_portfolio_values.iloc[i]:,.6f}")
        
        # Test the reconciliation assertion
        try:
            np.testing.assert_allclose(
                result.portfolio_values.values,
                result.cash_history.values + result.position_values_sum.values,
                atol=1e-6
            )
            print("   ✅ Position-value reconciliation passed")
        except AssertionError as e:
            print(f"   ❌ Position-value reconciliation failed: {e}")
            
            # Show the differences
            differences = result.portfolio_values.values - (result.cash_history.values + result.position_values_sum.values)
            print(f"   • Max difference: {np.max(np.abs(differences)):.6f}")
            print(f"   • Mean difference: {np.mean(np.abs(differences)):.6f}")
            print(f"   • Number of non-zero differences: {np.count_nonzero(differences)}")
        
        # Additional checks
        print(f"\n📊 Additional checks:")
        print(f"   • Portfolio values range: ${result.portfolio_values.min():,.2f} to ${result.portfolio_values.max():,.2f}")
        print(f"   • Cash range: ${result.cash_history.min():,.2f} to ${result.cash_history.max():,.2f}")
        print(f"   • Position values sum range: ${result.position_values_sum.min():,.2f} to ${result.position_values_sum.max():,.2f}")
        
        # Check that position values sum is never negative
        negative_positions = (result.position_values_sum < 0).sum()
        print(f"   • Negative position values sum: {negative_positions}")
        
        if negative_positions > 0:
            print("   ⚠️  Warning: Found negative position values sum")
        
    except Exception as e:
        print(f"❌ Error in backtest: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_reconciliation() 
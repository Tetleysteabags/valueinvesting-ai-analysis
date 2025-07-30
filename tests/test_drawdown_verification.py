#!/usr/bin/env python3
"""
Test max drawdown verification
"""

import sys
import os
import pandas as pd
import numpy as np
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analysis.backtesting import ValueInvestingBacktester

def test_drawdown_verification():
    """Test that the reported max drawdown matches the calculated drawdown"""
    
    tickers = ['ICCC']  # Use a simple stock for testing
    
    print(f"🧪 Testing max drawdown verification with: {tickers}")
    
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
        print(f"📊 Reported Max Drawdown: {result.max_drawdown:.2%}")
        
        # Test the drawdown verification
        print(f"\n🔍 Testing max drawdown verification...")
        
        # Recompute max drawdown locally
        eq = result.portfolio_values
        dd = (eq / eq.cummax() - 1).min()
        
        print(f"   • Portfolio values shape: {eq.shape}")
        print(f"   • Portfolio values range: ${eq.min():,.2f} to ${eq.max():,.2f}")
        print(f"   • Calculated max drawdown: {dd:.2%}")
        print(f"   • Reported max drawdown: {result.max_drawdown:.2%}")
        print(f"   • Difference: {abs(dd - result.max_drawdown):.6f}")
        
        # Test the assertion
        try:
            assert abs(dd - result.max_drawdown) < 1e-6, f"Max drawdown mismatch: calculated={dd:.6f}, reported={result.max_drawdown:.6f}"
            print("   ✅ Max drawdown verification passed")
        except AssertionError as e:
            print(f"   ❌ Max drawdown verification failed: {e}")
        
        # Show drawdown curve analysis
        print(f"\n📊 Drawdown curve analysis:")
        drawdown_curve = (eq / eq.cummax() - 1)
        print(f"   • Drawdown curve range: {drawdown_curve.min():.2%} to {drawdown_curve.max():.2%}")
        print(f"   • Number of drawdown periods: {(drawdown_curve < 0).sum()}")
        print(f"   • Average drawdown: {drawdown_curve[drawdown_curve < 0].mean():.2%}")
        
        # Show the worst drawdown period
        worst_dd_idx = drawdown_curve.idxmin()
        worst_dd_value = drawdown_curve.min()
        if hasattr(worst_dd_idx, 'strftime'):
            print(f"   • Worst drawdown date: {worst_dd_idx.strftime('%Y-%m-%d')}")
        else:
            print(f"   • Worst drawdown index: {worst_dd_idx}")
        print(f"   • Worst drawdown value: {worst_dd_value:.2%}")
        
        # Show portfolio values around the worst drawdown
        if len(eq) > 1:
            worst_idx = drawdown_curve.argmin()
            start_idx = max(0, worst_idx - 2)
            end_idx = min(len(eq), worst_idx + 3)
            
            print(f"\n📊 Portfolio values around worst drawdown:")
            for i in range(start_idx, end_idx):
                date = eq.index[i]
                value = eq.iloc[i]
                dd_val = drawdown_curve.iloc[i]
                if hasattr(date, 'strftime'):
                    print(f"   {date.strftime('%Y-%m-%d')}: ${value:,.2f} (DD: {dd_val:.2%})")
                else:
                    print(f"   Day {i}: ${value:,.2f} (DD: {dd_val:.2%})")
        
    except Exception as e:
        print(f"❌ Error in backtest: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_drawdown_verification() 
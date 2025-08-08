#!/usr/bin/env python3
"""
Test script for the combined backtesting system
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from analysis.combined_backtesting import run_combined_backtest, print_backtest_results

def test_combined_backtesting():
    """Test the combined backtesting system with a small set of tickers"""
    
    # Small set of tickers for testing
    TEST_TICKERS = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", 
        "META", "NVDA", "NFLX", "JPM", "JNJ"
    ]
    
    print("Testing Combined Backtesting System")
    print("=" * 50)
    
    try:
        # Test VectorBT implementation
        print("\n1. Testing VectorBT implementation...")
        vbt_result = run_combined_backtest(
            tickers=TEST_TICKERS,
            start_date="2023-01-01",
            end_date="2023-12-31",
            rebalance_freq="ME",
            initial_capital=100_000.0,
            use_vectorbt=True
        )
        print_backtest_results(vbt_result)
        
        # Test Custom implementation
        print("\n2. Testing Custom implementation...")
        custom_result = run_combined_backtest(
            tickers=TEST_TICKERS,
            start_date="2023-01-01",
            end_date="2023-12-31",
            rebalance_freq="ME",
            initial_capital=100_000.0,
            use_vectorbt=False
        )
        print_backtest_results(custom_result)
        
        # Compare results
        print("\n3. Comparison Summary:")
        print("-" * 30)
        print(f"VectorBT Total Return: {vbt_result.total_return:.2%}")
        print(f"Custom Total Return: {custom_result.total_return:.2%}")
        print(f"VectorBT Sharpe: {vbt_result.sharpe_ratio:.3f}")
        print(f"Custom Sharpe: {custom_result.sharpe_ratio:.3f}")
        print(f"VectorBT Max DD: {vbt_result.max_drawdown:.2%}")
        print(f"Custom Max DD: {custom_result.max_drawdown:.2%}")
        
        print("\n✅ Combined backtesting system test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_combined_backtesting() 
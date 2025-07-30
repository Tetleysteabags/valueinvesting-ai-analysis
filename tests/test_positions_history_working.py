#!/usr/bin/env python3
"""
Test positions history with a stock that has fundamental data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analysis.backtesting import ValueInvestingBacktester

def test_positions_history_working():
    """Test positions history with a stock that has fundamental data"""
    
    # Use a stock that we know has fundamental data
    tickers = ['AAPL']  # Apple should have fundamental data
    
    print(f"🧪 Testing positions history with: {tickers}")
    
    backtester = ValueInvestingBacktester(
        initial_capital=100000.0,
        criteria_level="relaxed"  # Use relaxed criteria to ensure qualification
    )
    
    try:
        result = backtester.run_backtest(
            tickers=tickers,
            start_date='2024-01-01',
            end_date='2024-06-30',  # Shorter period for testing
            rebalance_freq='ME'
        )
        
        print("✅ Backtest completed successfully!")
        print(f"📊 Final Capital: ${result.final_capital:,.2f}")
        print(f"📊 Total Return: {result.total_return:.2%}")
        print(f"📊 Number of Trades: {result.num_trades}")
        
        # Check positions history
        print(f"\n📋 Positions History:")
        print(f"   • Number of snapshots: {len(result.positions_history)}")
        
        for i, snapshot in enumerate(result.positions_history):
            print(f"   • Snapshot {i+1}: {snapshot['date'].strftime('%Y-%m-%d')}")
            print(f"     - Cash: ${snapshot['cash']:,.2f}")
            print(f"     - Holdings: {snapshot['holdings']}")
        
        # Verify the structure
        if result.positions_history:
            first_snapshot = result.positions_history[0]
            print(f"\n🔍 First snapshot structure:")
            print(f"   • Keys: {list(first_snapshot.keys())}")
            print(f"   • Date type: {type(first_snapshot['date'])}")
            print(f"   • Holdings type: {type(first_snapshot['holdings'])}")
            print(f"   • Cash type: {type(first_snapshot['cash'])}")
        else:
            print("⚠️  No positions history recorded (no positions opened)")
        
    except Exception as e:
        print(f"❌ Error in backtest: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_positions_history_working() 
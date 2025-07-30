#!/usr/bin/env python3
"""
Test Parameter Optimization
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analysis.backtesting import optimize_parameters

def main():
    # Top 26 stocks with score 9
    tickers = ['AIFU', 'ASC', 'ATHS', 'CIVI', 'EHLD', 'EMO', 'ESNT', 'EVT', 'EXG', 'FOF', 'GDO', 'GFR', 'GSL', 'HTD', 'ICCC', 'JCE', 'MHI', 'MTG', 'NXG', 'PDT', 'SITC', 'SPLP', 'STNG', 'TYG', 'UNMA', 'VIASP']
    
    print(f"🧪 Testing parameter optimization with {len(tickers)} top-scoring stocks")
    print("=" * 60)
    
    try:
        results = optimize_parameters(
            tickers=tickers,
            start_date='2024-01-01',
            end_date='2025-06-30',
            initial_capital=100000.0
        )
        
        if results.empty:
            print("❌ No successful parameter combinations found")
            return
        
        print(f"\n✅ Parameter optimization completed!")
        print(f"📊 Tested {len(results)} parameter combinations")
        
        # Show best parameters
        best_params = results.iloc[0]
        print(f"\n🏆 Best Parameters (by Sharpe Ratio):")
        print(f"   • Profit Target: {best_params['profit_target']:.1%}")
        print(f"   • Trailing Stop: {best_params['trailing_stop']:.1%}")
        print(f"   • Stop Loss: {best_params['stop_loss']:.1%}")
        print(f"   • Rebalance Freq: {best_params['rebalance_freq']}")
        print(f"   • Sharpe Ratio: {best_params['sharpe_ratio']:.2f}")
        print(f"   • Total Return: {best_params['total_return']:.2%}")
        print(f"   • Alpha: {best_params['alpha']:.2%}")
        
    except Exception as e:
        print(f"❌ Error running parameter optimization: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 
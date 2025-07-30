#!/usr/bin/env python3
"""
Robust Parameter Optimization with Larger Stock List
"""

import sys
import os
import pandas as pd
import gc
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analysis.backtesting import ValueInvestingBacktester

def load_tickers_from_file(filename):
    """Load tickers from a text file"""
    with open(filename, 'r') as f:
        tickers = [line.strip() for line in f if line.strip()]
    return tickers

def robust_optimization():
    """Run optimization with better resource management"""
    
    # Load tickers from file
    tickers = load_tickers_from_file('high_score_tickers_9_tickers.txt')
    print(f"📋 Loaded {len(tickers)} tickers from file")
    
    # Reduced parameter combinations for testing
    test_combinations = [
        # Monthly-end rebalancing
        {'profit_target': 0.25, 'trailing_stop': 0.08, 'stop_loss': -0.06, 'rebalance_freq': 'ME'},
        {'profit_target': 0.30, 'trailing_stop': 0.10, 'stop_loss': -0.08, 'rebalance_freq': 'ME'},
        {'profit_target': 0.35, 'trailing_stop': 0.06, 'stop_loss': -0.10, 'rebalance_freq': 'ME'},
        
        # Weekly rebalancing
        {'profit_target': 0.25, 'trailing_stop': 0.08, 'stop_loss': -0.06, 'rebalance_freq': 'W'},
        {'profit_target': 0.30, 'trailing_stop': 0.10, 'stop_loss': -0.08, 'rebalance_freq': 'W'},
        {'profit_target': 0.35, 'trailing_stop': 0.06, 'stop_loss': -0.10, 'rebalance_freq': 'W'},
        
        # 15-day rebalancing
        {'profit_target': 0.25, 'trailing_stop': 0.08, 'stop_loss': -0.06, 'rebalance_freq': '15D'},
        {'profit_target': 0.30, 'trailing_stop': 0.10, 'stop_loss': -0.08, 'rebalance_freq': '15D'},
        {'profit_target': 0.35, 'trailing_stop': 0.06, 'stop_loss': -0.10, 'rebalance_freq': '15D'},
    ]
    
    print(f"🧪 Testing {len(test_combinations)} parameter combinations")
    
    results = []
    successful_runs = 0
    
    for i, params in enumerate(test_combinations):
        print(f"\n🔄 Testing combination {i+1}/{len(test_combinations)}: {params}")
        
        try:
            # Create fresh backtester instance for each test
            backtester = ValueInvestingBacktester(
                initial_capital=100000.0,
                exit_profit_target=params['profit_target'],
                trailing_stop=params['trailing_stop'],
                exit_loss_stop=params['stop_loss']
            )
            
            result = backtester.run_backtest(
                tickers=tickers,
                start_date='2024-01-01',
                end_date='2025-06-30',
                rebalance_freq=params['rebalance_freq']
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
            
            results.append({
                'profit_target': params['profit_target'],
                'trailing_stop': params['trailing_stop'],
                'stop_loss': params['stop_loss'],
                'rebalance_freq': params['rebalance_freq'],
                'total_return': result.total_return,
                'annualized_return': result.annualized_return,
                'sharpe_ratio': result.sharpe_ratio,
                'max_drawdown': result.max_drawdown,
                'alpha': alpha,
                'num_trades': result.num_trades,
                'win_rate': result.win_rate,
                'final_capital': result.final_capital
            })
            
            successful_runs += 1
            print(f"✅ Combination {i+1} successful! (Return: {result.total_return:.2%}, Trades: {result.num_trades})")
            
            # Force garbage collection to free memory
            gc.collect()
            
        except Exception as e:
            print(f"❌ Error with combination {params}: {e}")
            continue
    
    if results:
        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values('sharpe_ratio', ascending=False)
        
        print(f"\n🎯 Optimization Results ({successful_runs}/{len(test_combinations)} successful):")
        print("=" * 80)
        print(results_df.to_string(index=False))
        
        # Show best parameters
        best_params = results_df.iloc[0]
        print(f"\n🏆 Best Parameters (by Sharpe Ratio):")
        print(f"   • Profit Target: {best_params['profit_target']:.1%}")
        print(f"   • Trailing Stop: {best_params['trailing_stop']:.1%}")
        print(f"   • Stop Loss: {best_params['stop_loss']:.1%}")
        print(f"   • Rebalance Freq: {best_params['rebalance_freq']}")
        print(f"   • Sharpe Ratio: {best_params['sharpe_ratio']:.2f}")
        print(f"   • Total Return: {best_params['total_return']:.2%}")
        print(f"   • Alpha: {best_params['alpha']:.2%}")
        
        # Save results
        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        results_df.to_csv(f'optimization_results_{timestamp}.csv', index=False)
        print(f"\n💾 Results saved to: optimization_results_{timestamp}.csv")
        
    else:
        print("❌ No successful parameter combinations found")

if __name__ == "__main__":
    robust_optimization() 
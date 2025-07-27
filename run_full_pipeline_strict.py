#!/usr/bin/env python3
"""
Full Pipeline with Strict Thresholds - Value Investing AI
Runs the complete workflow from stock screening to backtesting using STRICT criteria.
"""

import sys
import os
import json
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.value_analysis import run_stock_analysis
from analysis.backtesting import backtest_value_strategy

def load_tickers():
    """Load tickers from the stock_tickers.json file."""
    try:
        with open('tickers/stock_tickers.json', 'r') as f:
            tickers = json.load(f)
        return tickers
    except Exception as e:
        print(f"❌ Error loading tickers: {e}")
        return []

def run_full_pipeline_strict():
    """Run the complete value investing pipeline with strict thresholds."""
    
    print("🚀 FULL PIPELINE - STRICT THRESHOLDS")
    print("=" * 60)
    print(f"📅 Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Load tickers
    print("📋 STEP 1: Loading Tickers")
    print("-" * 30)
    tickers = load_tickers()
    if not tickers:
        print("❌ No tickers loaded. Exiting.")
        return False
    
    print(f"📊 Loaded {len(tickers)} tickers from stock_tickers.json")
    print(f"🎯 First 10 tickers: {', '.join(tickers[:10])}")
    print()
    
    # Step 2: Run value analysis with strict criteria
    print("🔍 STEP 2: Value Analysis (STRICT)")
    print("-" * 30)
    print("📊 Running value analysis with STRICT criteria...")
    print("🎯 Criteria: P/E < 15, P/B < 1.5, D/E < 1.0, ROE > 12%")
    print()
    
    try:
        # Run analysis with strict criteria
        df_results = run_stock_analysis(
            symbol_list=tickers,
            output_path="strict_analysis_results.csv",
            criteria_level="strict",
            batch_size=50,  # Process in batches of 50
            max_openai_calls=4,  # Full AI analysis for qualifying stocks
            checkpoint_interval=25
        )
        
        qualifying_stocks = df_results['symbol'].tolist() if not df_results.empty else []
        print(f"✅ Value analysis completed!")
        print(f"📈 Found {len(qualifying_stocks)} qualifying stocks out of {len(tickers)}")
        print(f"📊 Success rate: {len(qualifying_stocks)/len(tickers)*100:.2f}%")
        
        if qualifying_stocks:
            print(f"🎯 Qualifying stocks: {', '.join(qualifying_stocks)}")
        print()
        
    except Exception as e:
        print(f"❌ Value analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 3: Run backtest on qualifying stocks
    if qualifying_stocks:
        print("📊 STEP 3: Backtesting")
        print("-" * 30)
        print(f"🔄 Running backtest on {len(qualifying_stocks)} qualifying stocks")
        print(f"📅 Period: 2023-01-01 to 2025-07-27 (2.5+ years)")
        print(f"🔄 Rebalancing: Monthly")
        print(f"💰 Initial Capital: $100,000")
        print()
        
        try:
            # Run backtest
            backtest_result = backtest_value_strategy(
                tickers=qualifying_stocks,
                start_date='2023-01-01',
                end_date='2025-07-27',
                rebalance_freq='M',
                criteria_level='strict',
                initial_capital=100000.0
            )
            
            print("✅ Backtest completed successfully!")
            print()
            
        except Exception as e:
            print(f"❌ Backtest failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # Step 4: Summary
    print("📋 STEP 4: Pipeline Summary")
    print("-" * 30)
    print("🎉 FULL PIPELINE COMPLETED!")
    print()
    print("📊 Results Summary:")
    print(f"   • Total stocks screened: {len(tickers)}")
    print(f"   • Qualifying stocks: {len(qualifying_stocks)}")
    print(f"   • Success rate: {len(qualifying_stocks)/len(tickers)*100:.2f}%")
    
    if qualifying_stocks:
        print(f"   • Backtest period: 2.5+ years (2023-2025)")
        print(f"   • Initial capital: $100,000")
        print(f"   • Final capital: ${backtest_result.final_capital:,.2f}")
        print(f"   • Total return: {backtest_result.total_return:.2%}")
        print(f"   • Annualized return: {backtest_result.annualized_return:.2%}")
        print(f"   • Sharpe ratio: {backtest_result.sharpe_ratio:.2f}")
        print(f"   • Max drawdown: {backtest_result.max_drawdown:.2%}")
        print(f"   • Total trades: {backtest_result.num_trades}")
        print(f"   • Win rate: {backtest_result.win_rate:.2%}")
        print(f"   • Transaction costs: ${backtest_result.transaction_costs:,.2f}")
    
    print()
    print("📁 Output Files:")
    print(f"   • Value analysis: strict_analysis_results.csv")
    print()
    print(f"⏱️  End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("✅ Pipeline completed successfully!")
    
    return True

def show_strict_criteria():
    """Show the strict criteria thresholds."""
    print("📊 STRICT CRITERIA THRESHOLDS:")
    print("   • P/E Ratio < 15")
    print("   • Price/Book < 1.5")
    print("   • Debt/Equity < 1.0")
    print("   • ROE > 12%")
    print()

if __name__ == "__main__":
    show_strict_criteria()
    success = run_full_pipeline_strict()
    
    if success:
        print("\n🎯 NEXT STEPS:")
        print("   • Review strict_analysis_results.csv for detailed analysis")
        print("   • Compare with relaxed criteria results")
        print("   • Analyze individual stock performance")
        print("   • Optimize strategy parameters")
    else:
        print("\n❌ Pipeline failed. Check the error messages above.") 
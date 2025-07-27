#!/usr/bin/env python3
"""
Test script for the Value Investing Backtesting System.
"""

import sys
import os
import logging
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.historical_data_service import historical_data_service
from analysis.backtesting import run_value_investing_backtest, ValueInvestingBacktester
from utils.logging_setup import setup_logging

def test_historical_data_service():
    """Test the historical data service."""
    print("🔧 Testing Historical Data Service")
    print("=" * 50)
    
    # Test fetching data
    print("📊 Fetching historical data for AAPL...")
    df = historical_data_service.fetch_historical_data("AAPL", period="1y", source="fmp")
    
    if df is not None:
        print(f"✅ Successfully fetched {len(df)} records for AAPL")
        print(f"   Date range: {df['Date'].min()} to {df['Date'].max()}")
        print(f"   Latest price: ${df['Close'].iloc[-1]:.2f}")
    else:
        print("❌ Failed to fetch data for AAPL")
        return False
    
    # Test database operations
    print("\n📊 Testing database operations...")
    
    # Get data from database
    db_df = historical_data_service.get_historical_data("AAPL", start_date="2023-01-01")
    if db_df is not None:
        print(f"✅ Retrieved {len(db_df)} records from database")
    else:
        print("❌ Failed to retrieve data from database")
    
    # Get summary
    summary = historical_data_service.get_data_summary()
    print(f"📈 Database summary: {summary}")
    
    return True

def test_backtesting_system():
    """Test the backtesting system."""
    print("\n🚀 Testing Backtesting System")
    print("=" * 50)
    
    # Test tickers (small set for testing)
    test_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    
    # Fetch historical data for test tickers
    print("📊 Fetching historical data for test tickers...")
    for ticker in test_tickers:
        df = historical_data_service.fetch_historical_data(ticker, period="2y")
        if df is not None:
            print(f"✅ {ticker}: {len(df)} records")
        else:
            print(f"❌ {ticker}: Failed to fetch data")
    
    # Run a small backtest
    print("\n📈 Running backtest...")
    try:
        result = run_value_investing_backtest(
            tickers=test_tickers,
            start_date="2023-01-01",
            end_date="2023-12-31",
            criteria="moderate"
        )
        
        print(f"\n✅ Backtest completed successfully!")
        print(f"   Final Capital: ${result.final_capital:,.2f}")
        print(f"   Total Return: {result.total_return:.2%}")
        print(f"   Number of Trades: {result.num_trades}")
        
        # Plot results
        backtester = ValueInvestingBacktester()
        backtester.plot_results(result, "test_backtest_results.png")
        
        return True
        
    except Exception as e:
        print(f"❌ Backtest failed: {e}")
        logging.error(f"Backtest error: {e}", exc_info=True)
        return False

def test_value_screening():
    """Test value screening functionality."""
    print("\n🔍 Testing Value Screening")
    print("=" * 50)
    
    # Test with a few stocks
    test_tickers = ["AAPL", "MSFT", "BRK-B", "JNJ", "PG"]
    
    for ticker in test_tickers:
        print(f"\n📊 Screening {ticker}...")
        
        # Get current data
        from services.stock_service_free_tier import fetch_stock_data_free_tier
        data = fetch_stock_data_free_tier(ticker)
        
        if data:
            print(f"   P/E: {data.get('pe_ratio', 'N/A')}")
            print(f"   P/B: {data.get('price_to_book', 'N/A')}")
            print(f"   D/E: {data.get('de_ratio', 'N/A')}")
            print(f"   ROE: {data.get('roe_ratio', 'N/A')}")
            
            # Check if meets moderate criteria
            from config import THRESHOLDS_MODERATE
            meets_criteria = (
                data.get('pe_ratio', 999) < THRESHOLDS_MODERATE['pe'] and
                data.get('price_to_book', 999) < THRESHOLDS_MODERATE['pb'] and
                data.get('de_ratio', 999) < THRESHOLDS_MODERATE['de'] and
                data.get('roe_ratio', 0) > THRESHOLDS_MODERATE['roe']
            )
            
            print(f"   Meets moderate criteria: {'✅' if meets_criteria else '❌'}")
        else:
            print(f"   ❌ No data available")

def main():
    """Main test function."""
    print("🧪 Value Investing Backtesting System Test")
    print("=" * 60)
    
    # Set up logging
    setup_logging()
    
    # Test historical data service
    if not test_historical_data_service():
        print("❌ Historical data service test failed")
        return
    
    # Test value screening
    test_value_screening()
    
    # Test backtesting system
    if not test_backtesting_system():
        print("❌ Backtesting system test failed")
        return
    
    print("\n✅ All tests completed successfully!")
    print("\n📁 Generated files:")
    print("   - data/historical_data.db (SQLite database)")
    print("   - test_backtest_results.png (Backtest charts)")
    
    print("\n🎯 Next steps:")
    print("   1. Review the backtest results")
    print("   2. Adjust value criteria in config.py")
    print("   3. Run backtests with different parameters")
    print("   4. Analyze historical value screening results")

if __name__ == "__main__":
    main() 
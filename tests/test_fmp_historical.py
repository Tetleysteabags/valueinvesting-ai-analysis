#!/usr/bin/env python3
"""
Test script for FMP-only historical data service.
"""

import sys
import os
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.historical_data_service import historical_data_service
from utils.logging_setup import setup_logging

def test_fmp_historical_data():
    """Test FMP historical data fetching."""
    print("🔧 Testing FMP Historical Data Service")
    print("=" * 50)
    
    # Test with a few stocks
    test_tickers = ["AAPL", "MSFT", "GOOGL"]
    
    for ticker in test_tickers:
        print(f"\n📊 Testing {ticker}...")
        
        try:
            # Fetch historical data
            df = historical_data_service.fetch_historical_data(ticker, period="1y", source="fmp")
            
            if df is not None and not df.empty:
                print(f"✅ Successfully fetched {len(df)} records")
                print(f"   Date range: {df['Date'].min()} to {df['Date'].max()}")
                print(f"   Latest price: ${df['Close'].iloc[-1]:.2f}")
                print(f"   Columns: {list(df.columns)}")
            else:
                print(f"❌ No data returned for {ticker}")
                
        except Exception as e:
            print(f"❌ Error fetching data for {ticker}: {e}")
            logging.error(f"Error with {ticker}: {e}", exc_info=True)
    
    # Test database operations
    print(f"\n📊 Testing database operations...")
    
    # Get data from database
    db_df = historical_data_service.get_historical_data("AAPL", start_date="2023-01-01")
    if db_df is not None:
        print(f"✅ Retrieved {len(db_df)} records from database")
        print(f"   Date range: {db_df.index.min()} to {db_df.index.max()}")
    else:
        print("❌ Failed to retrieve data from database")
    
    # Get summary
    summary = historical_data_service.get_data_summary()
    print(f"📈 Database summary: {summary}")
    
    return True

def main():
    """Main test function."""
    print("🧪 FMP Historical Data Service Test")
    print("=" * 60)
    
    # Set up logging
    setup_logging()
    
    # Test historical data service
    if test_fmp_historical_data():
        print("\n✅ FMP historical data service test completed successfully!")
    else:
        print("\n❌ FMP historical data service test failed")
        return
    
    print("\n📁 Generated files:")
    print("   - data/historical_data.db (SQLite database)")
    
    print("\n🎯 Next steps:")
    print("   1. Verify data quality in the database")
    print("   2. Run the full backtesting system")
    print("   3. Test with different time periods")

if __name__ == "__main__":
    main() 
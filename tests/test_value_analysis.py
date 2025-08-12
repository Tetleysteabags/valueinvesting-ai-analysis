#!/usr/bin/env python3
"""
Test script for value_analysis.py caching optimization
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from value_analysis import run_stock_analysis

def test_caching_optimization():
    """Test the caching optimization with a small set of tickers"""
    
    # Small test set of tickers
    test_tickers = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
        "META", "NVDA", "NFLX", "JPM", "JNJ"
    ]
    
    print("🧪 Testing Value Analysis Caching Optimization")
    print("=" * 50)
    print(f"📋 Test tickers: {len(test_tickers)}")
    print(f"📊 Tickers: {', '.join(test_tickers)}")
    print("=" * 50)
    
    try:
        # Run analysis with minimal OpenAI calls to focus on caching
        results = run_stock_analysis(
            symbol_list=test_tickers,
            output_path="test_value_analysis.csv",
            criteria_level="moderate",  # Use moderate criteria for better test coverage
            batch_size=3,  # Small batch size to test caching across multiple batches
            max_openai_calls=0,  # No OpenAI calls for this test
            checkpoint_interval=2
        )
        
        print("\n✅ Test completed successfully!")
        print(f"📊 Results shape: {results.shape}")
        print(f"📈 Qualifying stocks: {len(results)}")
        
        if len(results) > 0:
            print(f"🏆 Top qualifying stocks:")
            for _, row in results.head(3).iterrows():
                print(f"   • {row['symbol']}: PE={row.get('pe_ratio', 'N/A')}, ROE={row.get('roe', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_caching_optimization()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Test script with stocks more likely to meet value investing criteria.
"""

import json
import logging
import pandas as pd
import csv
import os
from utils.logging_setup import setup_logging
from services.stock_service_free_tier import fetch_stock_data_free_tier
from services.openai_service import sentiment_analysis, earnings_call, stock_insights, value_investing
from analysis.financial_analysis import meets_value_criteria
from config import FMP_API_KEY, OPENAI_API_KEY

def validate_api_keys():
    """Validate that API keys are set."""
    if not FMP_API_KEY:
        print("❌ FMP_API_KEY not found in environment variables")
        return False
    
    if not OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY not found in environment variables")
        return False
    
    print("✅ API keys found")
    return True

def main():
    """Main function to test value stocks."""
    print("🚀 Value Stocks Test")
    print("=" * 50)
    
    # Set up logging
    setup_logging()
    
    # Validate API keys
    if not validate_api_keys():
        return
    
    # Stocks more likely to meet value criteria (lower P/E, P/B ratios)
    value_stocks = [
        "BRK-B",  # Berkshire Hathaway - often undervalued
        "JNJ",    # Johnson & Johnson - defensive stock
        "PG",     # Procter & Gamble - consumer staples
        "KO",     # Coca-Cola - defensive
        "WMT",    # Walmart - low P/E
        "JPM",    # JPMorgan Chase - financial
        "BAC",    # Bank of America - financial
        "C",      # Citigroup - financial
        "XOM",    # Exxon Mobil - energy
        "CVX",    # Chevron - energy
    ]
    
    print(f"\n📊 Testing {len(value_stocks)} value-oriented stocks")
    print(f"📈 Estimated API calls: {len(value_stocks) * 8} (safe within 250/day limit)")
    print(f"🎯 Test stocks: {', '.join(value_stocks[:5])}{'...' if len(value_stocks) > 5 else ''}")
    
    results = []
    
    for i, ticker in enumerate(value_stocks, 1):
        print(f"\n{'='*50}")
        print(f"Processing {i}/{len(value_stocks)}: {ticker}")
        print(f"{'='*50}")
        
        try:
            # Fetch data
            data = fetch_stock_data_free_tier(ticker)
            if data is None:
                print(f"❌ No data available for {ticker}")
                continue
            
            # Show metrics regardless of criteria
            print(f"\n📊 Metrics for {ticker}:")
            print(f"   P/E Ratio: {data.get('pe_ratio', 'N/A')}")
            print(f"   Price/Book: {data.get('price_to_book', 'N/A')}")
            print(f"   ROE: {data.get('roe_ratio', 'N/A')}")
            print(f"   Debt/Equity: {data.get('de_ratio', 'N/A')}")
            print(f"   Analyst Rating: {data.get('analyst_rating', 'N/A')}")
            
            # Check value criteria
            if meets_value_criteria(data):
                print(f"✅ {ticker} meets value criteria!")
                
                # Add AI insights
                print("🤖 Generating AI insights...")
                result = {
                    **data,
                    'sentiment_insight': sentiment_analysis(ticker),
                    'earnings_insight': earnings_call(ticker),
                    'stock_insight': stock_insights(ticker),
                    'value_insight': value_investing(ticker),
                }
                results.append(result)
                
            else:
                print(f"❌ {ticker} does not meet value criteria")
                print(f"   P/E: {data.get('pe_ratio', 'N/A')} (need < 10)")
                print(f"   P/B: {data.get('price_to_book', 'N/A')} (need < 1.5)")
                print(f"   ROE: {data.get('roe_ratio', 'N/A')} (need > 0.12)")
                print(f"   D/E: {data.get('de_ratio', 'N/A')} (need < 1)")
                
        except Exception as e:
            print(f"❌ Error processing {ticker}: {e}")
            logging.error(f"Error processing {ticker}: {e}", exc_info=True)
    
    # Save results
    if results:
        df = pd.DataFrame(results)
        output_file = "value_stocks_results.csv"
        df.to_csv(output_file, index=False, quoting=csv.QUOTE_ALL)
        print(f"\n✅ Test completed successfully!")
        print(f"📁 Results saved to: {output_file}")
        print(f"📊 Found {len(results)} stocks meeting value criteria")
        
        # Show summary
        print(f"\n📋 Value Stocks Found:")
        for result in results:
            print(f"   • {result['symbol']}: {result['company']}")
            print(f"     P/E: {result.get('pe_ratio', 'N/A'):.2f}, P/B: {result.get('price_to_book', 'N/A'):.2f}")
            print(f"     ROE: {result.get('roe_ratio', 'N/A'):.2%}, Rating: {result.get('analyst_rating', 'N/A')}")
    else:
        print(f"\n❌ No stocks met the strict value criteria")
        print("💡 Consider relaxing the criteria or testing more stocks!")

if __name__ == "__main__":
    main() 
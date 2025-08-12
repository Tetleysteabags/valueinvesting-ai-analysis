#!/usr/bin/env python3
"""
Value Analysis Module - Optimized batch processing for value investing.
"""

import pandas as pd
import csv
import os
import logging
import argparse
import sys
import time
from typing import List, Dict, Any, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.stock_service_v2 import fetch_stock_data_batch
from services.openai_service import (
    sentiment_analysis, earnings_call, stock_insights, value_investing
)
from analysis.financial_analysis import meets_value_criteria
from config import THRESHOLDS, THRESHOLDS_MODERATE, THRESHOLDS_CONSERVATIVE
from utils.monitoring import create_monitor
from analysis.value_initial_filters import value_initial_filter, FieldMap
from config import (
    REPORTING_LAG_DAYS, MIN_PRICE, MIN_ADV_USD, MIN_MARKET_CAP,
    TOP_N, SECTOR_CAP, COMPOSITE_MIN_PCTL, MAX_PB, MIN_EY
)


def get_criteria_thresholds(criteria_level: str = "strict") -> Dict[str, float]:
    """Get the appropriate thresholds based on criteria level."""
    criteria_map = {
        "strict": THRESHOLDS,
        "moderate": THRESHOLDS_MODERATE,
        "conservative": THRESHOLDS_CONSERVATIVE,
        "relaxed": {
            "pe": 20,
            "pb": 3.0,
            "de": 2.0,
            "roe": 0.08
        }
    }
    return criteria_map.get(criteria_level.lower(), THRESHOLDS)


def meets_criteria_with_level(data: Dict[str, Any], criteria_level: str = "strict") -> bool:
    """Check if stock meets value criteria with specified level."""
    thresholds = get_criteria_thresholds(criteria_level)
    
    try:
        roe_display = f"{data.get('roe', 0):.2%}" if data.get('roe') is not None else 'N/A'
        print(
            f"Checking {criteria_level.upper()}: PE {data.get('pe_ratio', 'N/A')} < {thresholds['pe']} and "
            f"P/B {data.get('price_to_book', 'N/A')} < {thresholds['pb']} and "
            f"D/E {data.get('debt_to_equity', 'N/A')} < {thresholds['de']} and "
            f"ROE {roe_display} > {thresholds['roe']:.2%}"
        )
        return (
            data.get('pe_ratio') is not None and data.get('pe_ratio') < thresholds["pe"] and
            data.get('price_to_book') is not None and data.get('price_to_book') < thresholds["pb"] and
            data.get('debt_to_equity') is not None and data.get('debt_to_equity') < thresholds["de"] and
            data.get('roe') is not None and data.get('roe') > thresholds["roe"]
        )
    except KeyError as e:
        print(f"Missing key in data: {e}")
        return False


def add_ai_insights(ticker: str, data: Dict[str, Any], max_openai_calls: int = 4) -> Dict[str, Any]:
    """Add AI insights to stock data, respecting call limits."""
    result = {**data}
    
    # Add insights based on available calls
    if max_openai_calls >= 1:
        result['sentiment_insight'] = sentiment_analysis(ticker)
    if max_openai_calls >= 2:
        result['earnings_insight'] = earnings_call(ticker)
    if max_openai_calls >= 3:
        result['stock_insight'] = stock_insights(ticker)
    if max_openai_calls >= 4:
        result['value_insight'] = value_investing(ticker)
    
    return result


def run_stock_analysis(
    symbol_list: List[str], 
    output_path: str = "stock_analysis.csv", 
    criteria_level: str = "strict",
    batch_size: int = 50,
    max_openai_calls: int = 4,
    checkpoint_interval: int = 10
) -> pd.DataFrame:
    """
    Run optimized stock analysis with batch processing.
    
    Args:
        symbol_list: List of stock tickers to analyze
        output_path: Path to save results CSV
        criteria_level: "strict", "moderate", "conservative", or "relaxed"
        batch_size: Number of stocks to fetch in each batch
        max_openai_calls: Maximum number of OpenAI API calls per stock (1-4)
        checkpoint_interval: Save progress every N qualifying stocks
    
    Returns:
        DataFrame with analysis results
    """
    # Initialize monitoring
    monitor = create_monitor(len(symbol_list), batch_size)
    monitor.start()
    
    print(f"🚀 Starting Value Analysis")
    print(f"📊 Criteria Level: {criteria_level.upper()}")
    print(f"📈 Batch Size: {batch_size}")
    print(f"🤖 Max OpenAI Calls: {max_openai_calls}")
    print(f"💾 Checkpoint Interval: {checkpoint_interval}")
    print(f"📋 Total Stocks: {len(symbol_list)}")
    print("=" * 60)
    
    # Define columns based on available data
    base_columns = [
        'company', 'symbol', 'current_price', 'pe_ratio', 'market_cap', 
        'price_to_book', 'debt_to_equity', 'roe', 'peg_ratio', 'fcf_yield', 
        'enterprise_value', 'beta', 'forward_pe', 'price_to_sales_ratio', 
        'ebitda', 'ebitda_margin', 'gross_margin', 'operating_margin', 
        'net_income', 'revenue', 'net_margin', 'roa', 'free_cash_flow', 
        'operating_cash_flow', 'insider_ownership', 'short_ratio', 
        'short_percent_float', 'fifty_two_week_low', 'fifty_two_week_high', 
        'target_high_price', 'target_low_price', 'target_mean_price', 
        'target_median_price', 'total_debt', 'total_cash', 'total_equity', 'info'
    ]
    
    ai_columns = []
    if max_openai_calls >= 1:
        ai_columns.append('sentiment_insight')
    if max_openai_calls >= 2:
        ai_columns.append('earnings_insight')
    if max_openai_calls >= 3:
        ai_columns.append('stock_insight')
    if max_openai_calls >= 4:
        ai_columns.append('value_insight')
    
    columns = base_columns + ai_columns
    
    # Resume logic
    if os.path.exists(output_path):
        df_existing = pd.read_csv(output_path)
        processed_symbols = set(df_existing['symbol'].tolist())
        print(f"📂 Resuming analysis. Already processed: {len(processed_symbols)} tickers")
        df_portfolio = df_existing
    else:
        df_portfolio = pd.DataFrame(columns=columns)
        processed_symbols = set()
    
    # Filter tickers to process only unprocessed ones
    tickers_to_process = [t for t in symbol_list if t.upper() not in processed_symbols]
    total_tickers = len(tickers_to_process)
    
    if total_tickers == 0:
        print("✅ All tickers already processed!")
        return df_portfolio
    
    asof_date = pd.Timestamp.utcnow().normalize().tz_localize(None)

    # Initialize cache to avoid double API fetching
    all_data_cache: Dict[str, Dict[str, Any]] = {}
    fmp_dict: Dict[str, pd.DataFrame] = {}
    # We'll also collect a minimal price snapshot. If you don't have volume history handy,
    # we'll disable the ADV check below by passing MIN_ADV_USD=None.
    price_last = {}

    # Pull fundamentals in batches (reuse your existing batch fetch)
    print("📊 Fetching initial data for value screening...")
    
    for j in range(0, len(symbol_list), batch_size):
        b = symbol_list[j:j+batch_size]
        bdata = fetch_stock_data_batch(b)  # your existing call
        # Cache the data for later use
        all_data_cache.update(bdata)
        for tkr, rec in bdata.items():
            # Wrap into a one-row DataFrame; if you have multiple filings,
            # you can append more rows per ticker (better PIT fidelity).
            row = dict(rec)
            # Ensure a PIT date column exists for the selector
            row.setdefault("filingDate", rec.get("filingDate") or rec.get("fiscalDateEnding") or rec.get("date"))
            fmp_dict[tkr.upper()] = pd.DataFrame([row])
            # Minimal price for price>MIN_PRICE check
            price_last[tkr.upper()] = rec.get("current_price") or rec.get("price") or np.nan

    # Build a minimal prices_df; if you have a proper price/volume matrix, plug it in here.
    px_close = pd.DataFrame(price_last, index=[asof_date])
    prices_df_min = {"close": px_close, "volume": None}

    # If you do NOT have recent volume matrix available, turn off ADV gate:
    min_adv = MIN_ADV_USD if MIN_ADV_USD is not None else None
    if prices_df_min["volume"] is None:
        min_adv = None

    screened, panel = value_initial_filter(
        fmp_dict=fmp_dict,
        prices_df=prices_df_min,           
        asof_date=asof_date,
        field_map=FieldMap(),               
        REPORTING_LAG_DAYS=REPORTING_LAG_DAYS,
        MIN_PRICE=MIN_PRICE,
        MIN_ADV_USD=min_adv,                # disables ADV check if no volume
        MIN_MARKET_CAP=MIN_MARKET_CAP,
        TOP_N=TOP_N,
        SECTOR_CAP=SECTOR_CAP,
        COMPOSITE_MIN_PCTL=COMPOSITE_MIN_PCTL,
        MAX_PB=MAX_PB,
        MIN_EY=MIN_EY,
    )

    allowed_tickers = set([t.upper() for t in screened])
    # Optional: save the diagnostic panel to inspect ranks/guardrails
    try:
        panel.to_csv(os.path.splitext(output_path)[0] + "_value_screen_panel.csv", index=True)
        print(f"🧾 Saved value screen panel with {len(panel)} rows")
    except Exception as e:
        print(f"⚠️ Could not save panel: {e}")

    if not allowed_tickers:
        print("⚠️ Value screen returned no names. Falling back to legacy criteria for this run.")
    else:
        print(f"✅ Value screen produced {len(allowed_tickers)} tickers (cap {TOP_N}). Proceeding...")
    
    print(f"🔄 Processing {total_tickers} new tickers...")
    
    tickers_processed = 0
    tickers_added = 0
    failed_stocks = 0
    
    # Process in batches
    for i in range(0, len(tickers_to_process), batch_size):
        batch_start_time = time.time()
        batch = tickers_to_process[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(tickers_to_process) + batch_size - 1) // batch_size
        
        # Update monitor with batch info
        monitor.update_progress(
            processed=tickers_processed,
            qualifying=tickers_added,
            failed=failed_stocks,
            current_stock="",
            batch_num=batch_num
        )
        
        print(f"\n📦 Processing batch {batch_num}/{total_batches} ({len(batch)} stocks)")
        
        # Use cached data to avoid double API fetching
        batch_data = {t: all_data_cache.get(t.upper()) for t in batch if t.upper() in all_data_cache}
        missing = [t for t in batch if t.upper() not in all_data_cache]
        
        if missing:
            print(f"📊 Fetching missing data for {len(missing)} stocks...")
            missing_data = fetch_stock_data_batch(missing)
            batch_data.update(missing_data)
            all_data_cache.update(missing_data)  # Cache the new data too
        
        print(f"📊 Using data for {len(batch_data)} stocks (cached: {len(batch_data) - len(missing)}, fetched: {len(missing)})")
        
        # Process each stock in the batch
        for ticker in batch:
            tickers_processed += 1
            ticker_upper = ticker.upper()
            
            # Update monitor with current stock
            monitor.update_progress(
                processed=tickers_processed,
                qualifying=tickers_added,
                failed=failed_stocks,
                current_stock=ticker,
                batch_num=batch_num
            )
            
            print(f"🔍 [{tickers_processed}/{total_tickers}] Analyzing {ticker}...")
            
            if ticker_upper in batch_data:
                data = batch_data[ticker_upper]
                
                # Check if meets value criteria
                if allowed_tickers and ticker_upper not in allowed_tickers:
                    print(f"⏭️  {ticker} skipped (did not pass value screen).")
                    failed_stocks += 1
                    monitor.add_failed_stock(ticker, "Value screen")
                    continue
                
                # keep your legacy criteria as a secondary check/logging
                if meets_criteria_with_level(data, criteria_level):
                    print(f"✅ {ticker} passes value screen + {criteria_level} thresholds")
                    
                    # Add AI insights
                    result = add_ai_insights(ticker, data, max_openai_calls)
                    
                    # Add to portfolio
                    df_portfolio = pd.concat([df_portfolio, pd.DataFrame([result])], ignore_index=True)
                    tickers_added += 1
                    
                    # Update monitor with qualifying stock
                    monitor.add_qualifying_stock(ticker)
                    
                    print(f"📈 Added {ticker} | Total qualifying: {tickers_added}")
                    
                    # Checkpoint save
                    if tickers_added % checkpoint_interval == 0:
                        try:
                            # Save to temporary file first, then rename (atomic operation)
                            temp_path = output_path + ".tmp"
                            df_portfolio.to_csv(temp_path, index=False, quoting=csv.QUOTE_ALL)
                            os.replace(temp_path, output_path)
                            print(f"💾 Checkpoint saved after {tickers_added} qualifying stocks")
                        except Exception as e:
                            print(f"⚠️  Checkpoint save failed: {e}")
                            # Try direct save as fallback
                            try:
                                df_portfolio.to_csv(output_path, index=False, quoting=csv.QUOTE_ALL)
                                print(f"💾 Fallback save successful")
                            except Exception as e2:
                                print(f"❌ Critical: Could not save checkpoint: {e2}")
                else:
                    print(f"❌ {ticker} does not meet {criteria_level} criteria")
                    failed_stocks += 1
                    monitor.add_failed_stock(ticker, "Does not meet criteria")
            else:
                print(f"⚠️  No data available for {ticker}")
                failed_stocks += 1
                monitor.add_failed_stock(ticker, "No data available")
        
        # Record batch time
        batch_time = time.time() - batch_start_time
        monitor.record_batch_time(batch_time)
    
    # Final save with safety mechanism
    try:
        temp_path = output_path + ".tmp"
        df_portfolio.to_csv(temp_path, index=False, quoting=csv.QUOTE_ALL)
        os.replace(temp_path, output_path)
        print(f"💾 Final results saved successfully")
    except Exception as e:
        print(f"⚠️  Final save failed: {e}")
        # Try direct save as fallback
        try:
            df_portfolio.to_csv(output_path, index=False, quoting=csv.QUOTE_ALL)
            print(f"💾 Fallback final save successful")
        except Exception as e2:
            print(f"❌ Critical: Could not save final results: {e2}")
    
    # Complete monitoring
    monitor.complete()
    
    print(f"\n🎉 Analysis Complete!")
    print(f"📊 Summary:")
    print(f"   • Tickers processed: {tickers_processed}")
    print(f"   • Qualifying stocks: {tickers_added}")
    print(f"   • Success rate: {tickers_added/tickers_processed*100:.1f}%" if tickers_processed > 0 else "   • Success rate: 0%")
    print(f"   • Data cache hits: {len(all_data_cache)} tickers")
    print(f"   • Output saved to: {output_path}")
    
    return df_portfolio


def main():
    """Command-line interface for stock analysis."""
    parser = argparse.ArgumentParser(description="Value Investing Stock Analysis")
    parser.add_argument("--tickers", nargs="+", help="List of stock tickers to analyze")
    parser.add_argument("--file", help="File containing ticker list (one per line)")
    parser.add_argument("--output", default="stock_analysis.csv", help="Output CSV file path")
    parser.add_argument("--criteria", choices=["strict", "moderate", "conservative", "relaxed"], 
                       default="strict", help="Value criteria level")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for API calls")
    parser.add_argument("--max-openai-calls", type=int, default=4, choices=[0,1,2,3,4], 
                       help="Maximum OpenAI API calls per stock (0 for testing)")
    parser.add_argument("--checkpoint-interval", type=int, default=10, 
                       help="Save progress every N qualifying stocks")
    
    args = parser.parse_args()
    
    # Get ticker list
    if args.tickers:
        symbol_list = args.tickers
    elif args.file:
        with open(args.file, 'r') as f:
            symbol_list = [line.strip() for line in f if line.strip()]
    else:
        print("Error: Must provide either --tickers or --file")
        return
    
    # Run analysis
    run_stock_analysis(
        symbol_list=symbol_list,
        output_path=args.output,
        criteria_level=args.criteria,
        batch_size=args.batch_size,
        max_openai_calls=args.max_openai_calls,
        checkpoint_interval=args.checkpoint_interval
    )


if __name__ == "__main__":
    main()

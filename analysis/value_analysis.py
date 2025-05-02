import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import csv
import os
import logging
from services.stock_service import fetch_stock_data
from services.openai_service import (
    sentiment_analysis, earnings_call, stock_insights, value_investing
)
from analysis.financial_analysis import meets_value_criteria


def process_stock(ticker):
    try:
        data = fetch_stock_data(ticker)
        if data is None:
            print(f"Stock {ticker} does not meet value criteria")
            return None  # ← Make sure to return None if it fails
        if not meets_value_criteria(data):
            print(f"Stock {ticker} does not meet value criteria")
            return None  # ← Make sure to return None if it fails

        print(f"Stock {ticker} passed value criteria")
        return {
            **data,
            'sentiment_insight': sentiment_analysis(ticker),
            'earnings_insight': earnings_call(ticker),
            'stock_insight': stock_insights(ticker),
            'value_insight': value_investing(ticker),
 
        }

    except Exception as e:
        logging.error(f"Error processing {ticker}: {e}")
        return None


def run_stock_analysis(symbol_list_us, output_path="stock_analysis.csv", checkpoint_interval=10):
    columns = ['company', 'symbol', 'current_price', 'pe_ratio', 'sentiment_insight', 'earnings_insight','stock_insight', 'value_insight','market_cap', 'price_to_book_ratio', 'de_ratio', 'roe_ratio', 'forward_pe', 'price_to_sales_ratio', 'ebitda', 'ebitda_margin', 'gross_margin', 'operating_margin', 'net_income', 'revenue', 'net_margin', 'roa', 'free_cash_flow', 'operating_cash_flow', 'insider_ownership', 'short_ratio', 'short_percent_float', 'fifty_two_week_low', 'fifty_two_week_high', 'target_high_price', 'target_low_price', 'target_mean_price', 'target_median_price', 'total_debt', 'total_cash','total_equity','info']
    
    
    # Resume logic
    if os.path.exists(output_path):
        df_portfolio = pd.read_csv(output_path)
        processed_symbols = set(df_portfolio['company'].tolist())
        print(f"Resuming. Already processed: {len(processed_symbols)} tickers.")
    else:
        df_portfolio = pd.DataFrame(columns=columns)
        processed_symbols = set()

    # Filter tickers to process only unprocessed ones
    tickers_to_process = [t for t in symbol_list_us if t not in processed_symbols]
    total_tickers = len(tickers_to_process)
    tickers_processed = 0
    tickers_added = 0

    with ThreadPoolExecutor() as executor:
        for ticker, result in zip(tickers_to_process, executor.map(process_stock, tickers_to_process)):
            tickers_processed += 1
            print(f"Processed: {tickers_processed}/{total_tickers} - {ticker}")
            if result:
                df_portfolio = pd.concat([df_portfolio, pd.DataFrame([result])], ignore_index=True)
                tickers_added += 1
                print(f"✅ Added: {ticker} | Total Added: {tickers_added}")
                
            # Autosave every N additions
            if tickers_added > 0 and tickers_added % checkpoint_interval == 0:
                df_portfolio.to_csv(output_path, index=False, quoting=csv.QUOTE_ALL)
                print(f"💾 Autosaved after {tickers_added} additions — here's a preview:")
                print(df_portfolio.tail(5))    # show the last 5 rows in memory

    df_portfolio.to_csv(output_path, index=False, quoting=csv.QUOTE_ALL)
    print(f"\n=== Final Summary ===")
    print(f"Tickers processed this run: {tickers_processed}")
    print(f"Tickers added this run: {tickers_added}")
    print(f"Output saved to: {output_path}")

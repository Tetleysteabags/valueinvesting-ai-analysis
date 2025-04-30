# === Imports ===
import os
import json
import time
import hashlib
import logging
import pandas as pd
import yfinance as yf
import openai
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAIError, RateLimitError, APIError, Timeout

# === Configuration ===
NEWS_API_KEY = "API_KEY"
OPENAI_API_KEY = "API_KEY"
openai.api_key = "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"

# === Stock Symbols ===
with open('stock_tickers.json', 'r') as f:
    symbol_list_us = json.load(f)

print(symbol_list_us)

# Value Investing Thresholds
THRESHOLDS = {
    "pe": 10,
    "pb": 1.5,
    "de": 1,
    "roe": 0.12
}

# === Logging Setup ===
logging.basicConfig(filename='stock_selection.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')
logging.getLogger().addHandler(logging.StreamHandler())  # Log to console too


# === Cache Utilities ===
CACHE_FILE = "openai_cache.json"

def load_cache():
    return json.load(open(CACHE_FILE)) if os.path.exists(CACHE_FILE) else {}

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)

def get_cache_key(messages):
    return hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest()

# === OpenAI Utility ===
def ask_openai(messages, temperature=0.2, max_tokens=250, max_retries=3):
    cache = load_cache()
    cache_key = get_cache_key(messages)

    if cache_key in cache:
        print("Cache hit 🔥")
        return cache[cache_key]

    print("Cache miss ❄️. Calling OpenAI API...")
    for attempt in range(max_retries):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            content = response['choices'][0]['message']['content'].strip()
            cache[cache_key] = content
            save_cache(cache)
            return content
        except (RateLimitError, APIError, Timeout) as e:
            wait = 2 ** (attempt + 1)
            print(f"OpenAI API error: {e}. Retrying in {wait} seconds...")
            time.sleep(wait)
        except Exception as e:
            print(f"Unexpected error: {e}")
            break

    return None

# === OpenAI Analyses ===
def sentiment_analysis(ticker):
    prompt = f"Provide a sentiment analysis for stock {ticker} based on recent news and social media posts. Is the sentiment positive, negative, or neutral? Focus on key drivers (e.g., earnings reports, news events, market sentiment)."
    result = ask_openai([
        {"role": "system", "content": "You are a market sentiment analyst. Focus on key factors like news, earnings, and market sentiment."},
        {"role": "user", "content": prompt}
    ])
    if result is None:
        return "No sentiment analysis available"
    return result


# Analyse earnings calls for the stock using OpenAI
def earnings_call(ticker):
    prompt = f"Summarize the latest earnings call for stock {ticker}. Highlight key points such as management outlook, risks, opportunities, and financial performance."
    result = ask_openai([
        {"role": "system", "content": "You are a financial analyst. Provide key insights from the earnings call."},
        {"role": "user", "content": prompt}
    ])
    if result is None:
        return "No earnings call analysis available"
    return result


# Stock analysis using OpenAI
def stock_insights(ticker):
    prompt = f"Analyze stock {ticker}. Include its business model, growth prospects, financial performance, and risks. Provide key investment takeaways."
    result = ask_openai([
        {"role": "system", "content": "You are a financial analyst. Provide a summary of key investment insights."},
        {"role": "user", "content": prompt}
    ])
    if result is None:
        return "No stock insights available"
    return result


# Value investing analysis using OpenAI
def value_investing(ticker):
    prompt = f"Evaluate stock {ticker} from a value investor's perspective. Compare key metrics (PE ratio, PB ratio, ROE) to the industry average and provide investment recommendations."
    result = ask_openai([
        {"role": "system", "content": "You are a value investor. Compare key financial metrics with the industry and provide an investment recommendation."},
        {"role": "user", "content": prompt}
    ])
    if result is None:
        return "No value investing analysis available"
    return result

# === Financial Data Fetch ===
def fetch_stock_data(ticker):
    time.sleep(1) 
    try:
        stock = yf.Ticker(ticker)
        info = stock.info      
        
        # Handle invalid ticker symbols or non-stock tickers like ETFs or preferred shares
        if 'regularMarketPrice' not in info or 'symbol' not in info:
            print(f"Skipping {ticker}: Invalid ticker or not a regular stock.")
            return None
        
        # Fallback calculation of P/E ratio if not directly provided
        try:
            pe_ratio = info.get("pe_ratio")
            if pe_ratio is None:
                eps = info.get("trailingEps")
                price = info.get("currentPrice")
                if eps is not None and eps > 0:
                    pe_ratio = price / eps
                else:
                    print(f"Skipping {ticker.ticker}: no P/E ratio or positive EPS available.")
                    return None  # Reject stock if no valid P/E
        except Exception as e:
            print(f"Error calculating P/E for {ticker.ticker}: {e}")
            return None

        # Check if essential fields exist and aren't empty
        required_keys = ['currentPrice', 'marketCap', 'priceToBook', 'totalDebt', 'totalCash']
        missing_keys = [key for key in required_keys if key not in info or info[key] is None]

        if missing_keys:
            logging.warning(f"[{ticker}] Missing data fields: {missing_keys}")
            logging.debug(f"[{ticker}] Full data: {info}")
            return None  # or return a fallback dict if preferred

        # Optional: Check if the returned data is suspicious (e.g., prices are zero)
        if info['currentPrice'] <= 0:
            logging.warning(f"[{ticker}] Suspicious price value: {info['currentPrice']}")
            logging.debug(f"[{ticker}] Full data: {info}")
            return None

        equity_metrics = calculate_equity_metrics(ticker)
                
        return {
            "symbol": ticker.upper(),
            "current_price": info['currentPrice'],
            "market_cap": info['marketCap'],
            "roe_ratio": info.get('returnOnEquity'),
            "price_to_book_ratio": info.get('priceToBook'),
            "forward_pe": info.get('forwardPE'),
            "price_to_sales_ratio": info.get('priceToSalesTrailing12Months'),
            "pe_ratio": pe_ratio,
            "de_ratio": equity_metrics.get('de_ratio'),
            "net_income": equity_metrics.get('net_income'),
            "total_equity": equity_metrics.get('total_equity'),
            "total_debt": equity_metrics.get('total_debt'),
            "ebitda": info.get('ebitda'),
            "ebitda_margin": info.get('ebitdaMargins'),
            "gross_margin": info.get('grossMargins'),
            "operating_margin": info.get('operatingMargins'),
            "net_income": info.get('netIncomeToCommon'),
            "revenue": info.get('totalRevenue'),
            "net_margin": (info.get('netIncomeToCommon') / info.get('totalRevenue')) if info.get('netIncomeToCommon') and info.get('totalRevenue') else None,
            "roa": info.get('returnOnAssets'),
            "free_cash_flow": info.get('freeCashflow'),
            "operating_cash_flow": info.get('operatingCashflow'),
            "insider_ownership": info.get('heldPercentInsiders'),  # Often a good sign when high
            "short_ratio": info.get('shortRatio'),
            "short_percent_float": info.get('shortPercentOfFloat'),
            "fifty_two_week_low": info.get('fiftyTwoWeekLow'),
            "fifty_two_week_high": info.get('fiftyTwoWeekHigh'),
            "target_high_price": info.get('targetHighPrice'),
            "target_low_price": info.get('targetLowPrice'),
            "target_mean_price": info.get('targetMeanPrice'),
            "target_median_price": info.get('targetMedianPrice'),
            "total_debt": info.get('totalDebt'),
            "total_cash": info.get('totalCash'),
            "info": info
        }


    except Exception as e:
        logging.error(f"Error fetching data for {ticker}: {e}")
        logging.error(f"Stack trace:", exc_info=True)  # This will include the full stack trace
        return None


def calculate_equity_metrics(ticker_symbol):
    if isinstance(ticker_symbol, yf.Ticker):
        ticker = ticker_symbol  # Use the existing Ticker object
    else:
        ticker = yf.Ticker(ticker_symbol)  # Create new Ticker object
    
    info = ticker.info
    balance_sheet = ticker.balance_sheet

    metrics = {
        "de_ratio": None,
        "net_income": None,
        "total_equity": None,
        "total_debt": info.get("totalDebt", None),
    }

    # Try to extract Total Assets and Total Liabilities from the balance sheet
    try:
        latest_col = balance_sheet.columns[0]
        total_assets = balance_sheet.loc['Total Assets', latest_col]
        total_liab = balance_sheet.loc['Total Liabilities Net Minority Interest', latest_col]
        total_equity = total_assets - total_liab
        metrics["total_equity"] = total_equity
    except KeyError as e:
        logging.warning(f"Missing key in balance sheet for {ticker_symbol}: {e}")
    except Exception as e:
        logging.warning(f"Balance sheet data unavailable or incomplete for {ticker_symbol}: {e}")

    # Net income from info
    net_income = info.get("netIncomeToCommon", None)
    metrics["net_income"] = net_income

    # D/E = Total Debt / Total Equity
    if metrics["total_debt"] and metrics["total_equity"] and metrics["total_equity"] != 0:
        metrics["de_ratio"] = metrics["total_debt"] / metrics["total_equity"]

    return metrics


# === Analysis Logic ===
def meets_value_criteria(data):
    try:
        print(f"Checking: {data['pe_ratio']} < {THRESHOLDS['pe']} and {data['price_to_book_ratio']} < {THRESHOLDS['pb']} and {data['de_ratio']} < {THRESHOLDS['de']} and {data['roe_ratio']} > {THRESHOLDS['roe']}")
        return (
            data['pe_ratio'] is not None and data['pe_ratio'] < THRESHOLDS["pe"] and
            data['price_to_book_ratio'] is not None and data['price_to_book_ratio'] < THRESHOLDS["pb"] and
            data['de_ratio'] is not None and data['de_ratio'] < THRESHOLDS["de"] and
            data['roe_ratio'] is not None and data['roe_ratio'] > THRESHOLDS["roe"]
        )
    except KeyError as e:
        print(f"Missing key in data: {e}")
        return None


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
    columns = ['company', 'market_price', 'pe_ratio',
               'sentiment_insight', 'earnings_insight',
               'stock_insight', 'value_insight',
               'market_cap', 'price_to_book_ratio', 'de_ratio', 'roe_ratio', 'forward_pe', 'price_to_sales_ratio', 'ebitda', 'ebitda_margin', 'gross_margin', 
               'operating_margin', 'net_income', 'revenue', 'net_margin', 'roa', 'free_cash_flow', 'operating_cash_flow', 'insider_ownership', 'short_ratio', 'short_percent_float', 
               'fifty_two_week_low', 'fifty_two_week_high', 'target_high_price', 'target_low_price', 'target_mean_price', 'target_median_price', 'total_debt', 'total_cash']
    
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
                df_portfolio.to_csv(output_path, index=False)
                print(f"💾 Autosaved after {tickers_added} additions — here's a preview:")
                print(df_portfolio.tail(5))    # show the last 5 rows in memory

    df_portfolio.to_csv(output_path, index=False)
    print(f"\n=== Final Summary ===")
    print(f"Tickers processed this run: {tickers_processed}")
    print(f"Tickers added this run: {tickers_added}")
    print(f"Output saved to: {output_path}")


if __name__ == "__main__":
    run_stock_analysis(symbol_list_us)

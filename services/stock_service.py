import yfinance as yf
import logging
import time

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
                    print(f"Skipping {ticker}: no P/E ratio or positive EPS available.")
                    return None  # Reject stock if no valid P/E
        except Exception as e:
            print(f"Error calculating P/E for {ticker}: {e}")
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
            "company": info.get('longName'),
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

import os
import json
import time
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime, timedelta
import random
from typing import Dict, Any, Optional, List, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
import threading
from tqdm import tqdm

# Configuration
REQUEST_DELAY        = 2.0
MAX_RETRIES          = 3
BACKOFF_FACTOR       = 2
RATE_LIMIT_DELAY     = 60
BATCH_SIZE           = 5
CACHE_DIR            = "cache"
CACHE_FILE           = os.path.join(CACHE_DIR, "stock_data_cache.json")
CACHE_EXPIRY         = 24 * 60 * 60
MAX_WORKERS          = 3  # Number of parallel workers
MAX_QUEUE_SIZE       = 1000  # Maximum size of the retry queue
last_request_time    = 0
rate_limit_hit       = False
request_count        = 0
window_start         = time.time()
WINDOW_SIZE          = 60
MAX_REQUESTS_PER_WINDOW = 30

# FMP Configuration
FMP_API_KEY = os.getenv("FMP_API_KEY")
FMP_BASE    = "https://financialmodelingprep.com/api/v3"

def ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

def load_cache():
    ensure_cache_dir()
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                now = time.time()
                return {k: v for k, v in data.items()
                        if now - v.get('timestamp', 0) < CACHE_EXPIRY}
        except Exception as e:
            logging.error(f"Error loading cache: {e}")
    return {}

def save_cache(cache_data):
    ensure_cache_dir()
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f)
    except Exception as e:
        logging.error(f"Error saving cache: {e}")

# Initialize cache
stock_cache = load_cache()

def create_session():
    session = requests.Session()
    retry = Retry(
        total=MAX_RETRIES,
        backoff_factor=BACKOFF_FACTOR,
        status_forcelist=[429,500,502,503,504],
        respect_retry_after_header=True
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=1, pool_maxsize=1)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

session = create_session()

def validate_api_key() -> bool:
    """Validate FMP API key by making a test request."""
    if not FMP_API_KEY:
        raise ValueError("FMP_API_KEY environment variable is not set")
    
    try:
        # Test the API key with a simple request
        test_url = f"{FMP_BASE}/profile/AAPL"
        params = {"apikey": FMP_API_KEY}
        response = requests.get(test_url, params=params)
        
        if response.status_code == 401:
            raise ValueError("Invalid FMP API key")
        elif response.status_code == 429:
            logging.warning("FMP API rate limit reached during validation")
            return False
        elif response.status_code != 200:
            raise ValueError(f"FMP API test request failed with status {response.status_code}")
        
        return True
    except Exception as e:
        logging.error(f"Error validating FMP API key: {e}")
        return False

def validate_response_data(data: Any, endpoint: str) -> bool:
    """Validate the structure and content of FMP API responses."""
    if not data:
        logging.warning(f"Empty response from {endpoint}")
        return False
    
    # Extract the base endpoint name
    base_endpoint = endpoint.split('/')[0]
    
    if base_endpoint == "profile":
        if not isinstance(data, list) or len(data) == 0:
            logging.warning(f"Invalid profile data structure: {data}")
            return False
        required_fields = ["symbol", "price", "mktCap"]
        if not all(field in data[0] for field in required_fields):
            logging.warning(f"Missing required fields in profile data: {data[0]}")
            return False
    
    elif base_endpoint in ["balance-sheet-statement", "income-statement", "cash-flow-statement"]:
        if not isinstance(data, list) or len(data) == 0:
            logging.warning(f"Invalid {base_endpoint} data structure: {data}")
            return False
            
    elif base_endpoint == "key-metrics-ttm":
        if not isinstance(data, list) or len(data) == 0:
            logging.warning(f"Invalid key metrics TTM data structure: {data}")
            return False
        required_fields = ["peRatio", "pbRatio", "roe"]
        if not any(field in data[0] for field in required_fields):
            logging.warning(f"Missing all key metrics fields: {data[0]}")
            return False
            
    elif base_endpoint == "ratios-ttm":
        if not isinstance(data, list) or len(data) == 0:
            logging.warning(f"Invalid ratios TTM data structure: {data}")
            return False
        required_fields = ["priceEarningsRatio", "priceToBookRatio", "returnOnEquity"]
        if not any(field in data[0] for field in required_fields):
            logging.warning(f"Missing all ratio fields: {data[0]}")
            return False
            
    elif base_endpoint == "market-sentiment":
        if not isinstance(data, list) or len(data) == 0:
            logging.warning(f"Invalid market sentiment data structure: {data}")
            return False
        required_fields = ["rating", "targetPrice", "recommendation"]
        if not any(field in data[0] for field in required_fields):
            logging.warning(f"Missing all sentiment fields: {data[0]}")
            return False
            
    elif base_endpoint == "financial-growth-ttm":
        if not isinstance(data, list) or len(data) == 0:
            logging.warning(f"Invalid financial growth TTM data structure: {data}")
            return False
        required_fields = ["revenueGrowth", "netIncomeGrowth", "epsgrowth"]
        if not any(field in data[0] for field in required_fields):
            logging.warning(f"Missing all growth fields: {data[0]}")
            return False
            
    elif base_endpoint == "enterprise-values":
        if not isinstance(data, list) or len(data) == 0:
            logging.warning(f"Invalid enterprise values data structure: {data}")
            return False
        required_fields = ["enterpriseValue", "enterpriseValueMultiple"]
        if not any(field in data[0] for field in required_fields):
            logging.warning(f"Missing all enterprise value fields: {data[0]}")
            return False
    
    return True

def handle_rate_limit():
    global rate_limit_hit, last_request_time, request_count, window_start
    now = time.time()
    if now - window_start >= WINDOW_SIZE:
        window_start = now
        request_count = 0
        logging.info("Rate limit window reset")
    if request_count >= MAX_REQUESTS_PER_WINDOW:
        sleep = WINDOW_SIZE - (now - window_start)
        if sleep > 0:
            logging.warning(f"Rate limit reached, sleeping {sleep:.2f} seconds")
            time.sleep(sleep)
            window_start = time.time()
            request_count = 0
            logging.info("Cooldown complete")
    jitter = random.uniform(0, 1)
    sleep = REQUEST_DELAY + jitter
    logging.info(f"Waiting {sleep:.2f} seconds before next request")
    time.sleep(sleep)
    last_request_time = now
    request_count += 1
    logging.info(f"Request count in current window: {request_count}/{MAX_REQUESTS_PER_WINDOW}")

def _fmp_get(endpoint: str, params: dict = None) -> Optional[Dict]:
    """Helper to GET and cache FMP JSON data with improved error handling."""
    if params is None:
        params = {}
    params["apikey"] = FMP_API_KEY
    
    # Check cache
    key = f"{endpoint}|{json.dumps(params, sort_keys=True)}"
    if key in stock_cache:
        cache_entry = stock_cache[key]
        if time.time() - cache_entry['timestamp'] < CACHE_EXPIRY:
            return cache_entry['data']
    
    try:
        handle_rate_limit()
        url = f"{FMP_BASE}/{endpoint}"
        response = session.get(url, params=params)
        
        # Handle specific FMP error codes
        if response.status_code == 401:
            raise ValueError("Invalid FMP API key")
        elif response.status_code == 429:
            logging.warning("FMP API rate limit reached")
            time.sleep(RATE_LIMIT_DELAY)
            return None
        elif response.status_code == 404:
            logging.warning(f"Endpoint not found: {endpoint}")
            return None
        elif response.status_code != 200:
            raise requests.exceptions.HTTPError(f"HTTP {response.status_code}: {response.text}")
        
        data = response.json()
        
        # Log response for debugging
        logging.debug(f"Response from {endpoint}: {json.dumps(data, indent=2)}")
        
        # Validate response data
        if not validate_response_data(data, endpoint):
            return None
        
        # Cache the result
        stock_cache[key] = {
            'data': data,
            'timestamp': time.time()
        }
        save_cache(stock_cache)
        
        return data
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error for {endpoint}: {e}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON response for {endpoint}: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error for {endpoint}: {e}")
        return None

def fetch_stock_data(ticker: str) -> Dict[str, Any]:
    """
    Fetch comprehensive stock data from FMP API.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Dictionary containing stock data and metrics
    """
    try:
        # Fetch data from various endpoints
        profile_data = _fmp_get(f"profile/{ticker}")
        balance_sheet = _fmp_get(f"balance-sheet-statement/{ticker}")
        income_stmt = _fmp_get(f"income-statement/{ticker}")
        cash_flow = _fmp_get(f"cash-flow-statement/{ticker}")
        key_metrics = _fmp_get(f"key-metrics-ttm/{ticker}")
        ratios = _fmp_get(f"ratios-ttm/{ticker}")
        sentiment = _fmp_get(f"market-sentiment/{ticker}")
        growth = _fmp_get(f"financial-growth-ttm/{ticker}")
        
        # Extract and map metrics
        data = {
            # Valuation Metrics
            'pe_ratio': key_metrics[0].get('peRatioTTM'),
            'forward_pe': key_metrics[0].get('forwardPE'),
            'price_to_book': key_metrics[0].get('pbRatioTTM'),
            'price_to_sales': key_metrics[0].get('priceToSalesRatioTTM'),
            'market_cap': key_metrics[0].get('marketCapTTM'),
            'ev_ebitda': key_metrics[0].get('enterpriseValueOverEBITDATTM'),
            
            # Profitability Metrics
            'roe': ratios[0].get('returnOnEquityTTM'),
            'roa': ratios[0].get('returnOnAssetsTTM'),
            'net_margin': ratios[0].get('netProfitMarginTTM'),
            'operating_margin': ratios[0].get('operatingProfitMarginTTM'),
            'gross_margin': ratios[0].get('grossProfitMarginTTM'),
            'ebitda_margin': key_metrics[0].get('ebitdaMarginTTM'),
            
            # Financial Health
            'debt_to_equity': ratios[0].get('debtEquityRatioTTM'),
            'total_debt': balance_sheet[0].get('totalDebt') if balance_sheet else None,
            'total_cash': balance_sheet[0].get('cashAndCashEquivalents') if balance_sheet else None,
            'total_equity': balance_sheet[0].get('totalStockholdersEquity') if balance_sheet else None,
            'current_ratio': ratios[0].get('currentRatioTTM'),
            'quick_ratio': ratios[0].get('quickRatioTTM'),
            'interest_coverage': ratios[0].get('interestCoverageTTM'),
            
            # Cash Flow Metrics
            'free_cash_flow': cash_flow[0].get('freeCashFlow') if cash_flow else None,
            'operating_cash_flow': cash_flow[0].get('operatingCashFlow') if cash_flow else None,
            'fcf_yield': key_metrics[0].get('freeCashFlowYieldTTM'),
            'dividend_yield': ratios[0].get('dividendYielTTM'),
            'payout_ratio': ratios[0].get('payoutRatioTTM'),
            
            # Growth Metrics
            'revenue_growth_ttm': growth[0].get('revenueGrowth') if growth else None,
            'net_income_growth_ttm': growth[0].get('netIncomeGrowth') if growth else None,
            'eps_growth_ttm': growth[0].get('epsGrowth') if growth else None,
            'fcf_growth_ttm': growth[0].get('freeCashFlowGrowth') if growth else None,
            'dividend_growth_ttm': growth[0].get('dividendGrowth') if growth else None,
            'book_value_growth_ttm': growth[0].get('bookValueGrowth') if growth else None,
            'roe_growth_ttm': growth[0].get('roeGrowth') if growth else None,
            'roa_growth_ttm': growth[0].get('roaGrowth') if growth else None,
            
            # Market Sentiment
            'analyst_rating': sentiment[0].get('rating') if sentiment else None,
            'price_target': sentiment[0].get('targetPrice') if sentiment else None,
            'price_target_high': sentiment[0].get('targetHighPrice') if sentiment else None,
            'price_target_low': sentiment[0].get('targetLowPrice') if sentiment else None,
            'price_target_mean': sentiment[0].get('targetMeanPrice') if sentiment else None,
            'price_target_median': sentiment[0].get('targetMedianPrice') if sentiment else None,
            'analyst_recommendation': sentiment[0].get('recommendation') if sentiment else None,
            'rating_score': sentiment[0].get('ratingScore') if sentiment else None,
            'insider_ownership': sentiment[0].get('insiderOwnership') if sentiment else None,
            'institutional_ownership': sentiment[0].get('institutionalOwnership') if sentiment else None,
            'short_ratio': sentiment[0].get('shortRatio') if sentiment else None,
            'rsi': sentiment[0].get('rsi') if sentiment else None,
            'beta': key_metrics[0].get('beta'),
            
            # Raw data for reference
            'raw_data': {
                'profile': profile_data,
                'balance_sheet': balance_sheet,
                'income_statement': income_stmt,
                'cash_flow': cash_flow,
                'key_metrics': key_metrics,
                'ratios': ratios,
                'sentiment': sentiment,
                'growth': growth
            }
        }
        
        return data
        
    except Exception as e:
        logging.error(f"Error fetching data for {ticker}: {str(e)}")
        return None

# Thread-safe rate limiting
class RateLimiter:
    def __init__(self, max_requests: int, window_size: int):
        self.max_requests = max_requests
        self.window_size = window_size
        self.requests = []
        self.lock = threading.Lock()
    
    def wait_if_needed(self):
        with self.lock:
            now = time.time()
            # Remove old requests
            self.requests = [req_time for req_time in self.requests 
                           if now - req_time < self.window_size]
            
            if len(self.requests) >= self.max_requests:
                sleep_time = self.window_size - (now - self.requests[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
                self.requests = self.requests[1:]
            
            self.requests.append(now)

# Initialize rate limiter
rate_limiter = RateLimiter(MAX_REQUESTS_PER_WINDOW, WINDOW_SIZE)

class BatchProcessor:
    def __init__(self):
        self.retry_queue = Queue(maxsize=MAX_QUEUE_SIZE)
        self.processed_tickers = set()
        self.failed_tickers = set()
        self.lock = threading.Lock()
        self.progress_bar = None
    
    def process_ticker(self, ticker: str) -> Optional[Dict]:
        """Process a single ticker with rate limiting and error handling."""
        try:
            rate_limiter.wait_if_needed()
            data = fetch_stock_data(ticker)
            
            with self.lock:
                if data:
                    self.processed_tickers.add(ticker)
                    if self.progress_bar:
                        self.progress_bar.update(1)
                    return {ticker: data}
                else:
                    self.failed_tickers.add(ticker)
                    self.retry_queue.put(ticker)
                    if self.progress_bar:
                        self.progress_bar.update(1)
                    return None
                    
        except Exception as e:
            logging.error(f"Error processing {ticker}: {str(e)}")
            with self.lock:
                self.failed_tickers.add(ticker)
                self.retry_queue.put(ticker)
                if self.progress_bar:
                    self.progress_bar.update(1)
            return None

    def process_batch(self, tickers: List[str], max_retries: int = 3) -> Dict[str, Dict]:
        """Process a batch of tickers with parallel processing and retry logic."""
        results = {}
        retry_count = 0
        
        # Initialize progress bar
        self.progress_bar = tqdm(total=len(tickers), desc="Processing stocks")
        
        while tickers and retry_count < max_retries:
            # Process current batch
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                future_to_ticker = {
                    executor.submit(self.process_ticker, ticker): ticker 
                    for ticker in tickers
                }
                
                for future in as_completed(future_to_ticker):
                    result = future.result()
                    if result:
                        results.update(result)
            
            # Get failed tickers for retry
            tickers = []
            while not self.retry_queue.empty():
                tickers.append(self.retry_queue.get())
            
            if tickers:
                retry_count += 1
                logging.info(f"Retry {retry_count}: Processing {len(tickers)} failed tickers")
                time.sleep(RATE_LIMIT_DELAY)  # Wait before retry
        
        self.progress_bar.close()
        return results

    def get_statistics(self) -> Dict:
        """Get processing statistics."""
        return {
            "processed": len(self.processed_tickers),
            "failed": len(self.failed_tickers),
            "success_rate": len(self.processed_tickers) / 
                          (len(self.processed_tickers) + len(self.failed_tickers)) 
                          if (len(self.processed_tickers) + len(self.failed_tickers)) > 0 
                          else 0
        }

def fetch_stock_data_batch(tickers: List[str], batch_size: int = BATCH_SIZE) -> Dict[str, Dict]:
    """Fetch data for multiple tickers using efficient batch processing."""
    processor = BatchProcessor()
    all_results = {}
    
    # Split tickers into batches
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        logging.info(f"Processing batch {i//batch_size + 1} of {(len(tickers) + batch_size - 1)//batch_size}")
        
        batch_results = processor.process_batch(batch)
        all_results.update(batch_results)
        
        # Save intermediate results
        save_cache(all_results)
        
        # Log progress
        stats = processor.get_statistics()
        logging.info(f"Progress: {stats['processed']} processed, {stats['failed']} failed "
                    f"({stats['success_rate']*100:.1f}% success rate)")
    
    return all_results

def test_fmp_connection() -> bool:
    """
    Test the FMP API connection and data quality using a few well-known stocks.
    Returns True if all tests pass, False otherwise.
    """
    test_stocks = ["AAPL", "MSFT", "GOOGL"]  # Well-known stocks with reliable data
    logging.info("Starting FMP API connection test...")
    
    # Test 1: API Key Validation
    if not validate_api_key():
        logging.error("❌ API key validation failed")
        return False
    logging.info("✅ API key validation passed")
    
    # Test 2: Basic Profile Data
    for ticker in test_stocks:
        logging.info(f"\nTesting {ticker}...")
        try:
            # Test profile endpoint
            profile = _fmp_get(f"profile/{ticker}")
            if not profile:
                logging.error(f"❌ Failed to fetch profile for {ticker}")
                return False
                
            prof = profile[0]
            required_fields = ["symbol", "price", "mktCap", "companyName"]
            missing_fields = [field for field in required_fields if field not in prof]
            
            if missing_fields:
                logging.error(f"❌ Missing required fields for {ticker}: {missing_fields}")
                return False
                
            logging.info(f"✅ {ticker} profile data:")
            logging.info(f"   Company: {prof.get('companyName')}")
            logging.info(f"   Price: ${prof.get('price'):.2f}")
            logging.info(f"   Market Cap: ${prof.get('mktCap'):,.0f}")
            
            # Test financial statements
            bs = _fmp_get(f"balance-sheet-statement/{ticker}", {"limit": 1})
            inc = _fmp_get(f"income-statement/{ticker}", {"limit": 1})
            cf = _fmp_get(f"cash-flow-statement/{ticker}", {"limit": 1})
            
            if not all([bs, inc, cf]):
                logging.error(f"❌ Failed to fetch financial statements for {ticker}")
                return False
                
            logging.info(f"✅ Financial statements retrieved for {ticker}")
            
            # Test historical prices (using the correct endpoint)
            hist = _fmp_get(f"historical-price-full/{ticker}", {"serietype": "line"})
            if not hist:
                logging.error(f"❌ Failed to fetch historical prices for {ticker}")
                return False
                
            logging.info(f"✅ Historical prices retrieved for {ticker}")
            
            # Print some sample data to verify quality
            if hist and 'historical' in hist:
                latest_price = hist['historical'][0] if hist['historical'] else None
                if latest_price:
                    logging.info(f"   Latest historical price: ${latest_price.get('close', 'N/A')}")
            
        except Exception as e:
            logging.error(f"❌ Error testing {ticker}: {e}")
            return False
    
    logging.info("\n✅ All tests passed successfully!")
    return True

def test_value_metrics(ticker: str) -> None:
    """Test if we have all necessary data for value investing metrics."""
    logging.info(f"\nTesting value metrics for {ticker}...")
    
    data = fetch_stock_data(ticker)
    if not data:
        logging.error(f"❌ Failed to fetch data for {ticker}")
        return
    
    # Define all metrics we need with their sources
    metrics_check = {
        "Valuation Metrics": {
            "P/E Ratio": data.get("pe_ratio"),
            "Forward P/E": data.get("forward_pe"),
            "Price/Book": data.get("price_to_book"),
            "Price/Sales": data.get("price_to_sales"),
            "Market Cap": data.get("market_cap"),
            "EV/EBITDA": data.get("ev_ebitda")
        },
        "Profitability Metrics": {
            "ROE": data.get("roe"),
            "ROA": data.get("roa"),
            "Net Margin": data.get("net_margin"),
            "Operating Margin": data.get("operating_margin"),
            "Gross Margin": data.get("gross_margin"),
            "EBITDA Margin": data.get("ebitda_margin")
        },
        "Financial Health": {
            "Debt/Equity": data.get("debt_to_equity"),
            "Total Debt": data.get("total_debt"),
            "Total Cash": data.get("total_cash"),
            "Total Equity": data.get("total_equity"),
            "Current Ratio": data.get("current_ratio"),
            "Quick Ratio": data.get("quick_ratio"),
            "Interest Coverage": data.get("interest_coverage")
        },
        "Cash Flow Metrics": {
            "Free Cash Flow": data.get("free_cash_flow"),
            "Operating Cash Flow": data.get("operating_cash_flow"),
            "FCF Yield": data.get("fcf_yield"),
            "Dividend Yield": data.get("dividend_yield"),
            "Payout Ratio": data.get("payout_ratio")
        },
        "Growth Metrics": {
            "Revenue Growth (TTM)": data.get("revenue_growth_ttm"),
            "Net Income Growth (TTM)": data.get("net_income_growth_ttm"),
            "EPS Growth (TTM)": data.get("eps_growth_ttm"),
            "FCF Growth (TTM)": data.get("fcf_growth_ttm"),
            "Dividend Growth (TTM)": data.get("dividend_growth_ttm"),
            "Book Value Growth (TTM)": data.get("book_value_growth_ttm"),
            "ROE Growth (TTM)": data.get("roe_growth_ttm"),
            "ROA Growth (TTM)": data.get("roa_growth_ttm")
        },
        "Market Sentiment": {
            "Analyst Rating": data.get("analyst_rating"),
            "Price Target": data.get("price_target"),
            "Price Target High": data.get("price_target_high"),
            "Price Target Low": data.get("price_target_low"),
            "Price Target Mean": data.get("price_target_mean"),
            "Price Target Median": data.get("price_target_median"),
            "Analyst Recommendation": data.get("analyst_recommendation"),
            "Rating Score": data.get("rating_score"),
            "Insider Ownership": data.get("insider_ownership"),
            "Institutional Ownership": data.get("institutional_ownership"),
            "Short Ratio": data.get("short_ratio"),
            "RSI": data.get("rsi"),
            "Beta": data.get("beta")
        }
    }
    
    # Check and display metrics availability
    missing_metrics = []
    available_metrics = []
    
    for category, metrics in metrics_check.items():
        logging.info(f"\n{category}:")
        for metric_name, value in metrics.items():
            if value is not None:
                available_metrics.append(metric_name)
                if isinstance(value, (int, float)):
                    if abs(value) >= 1e9:  # For large numbers like market cap
                        logging.info(f"✅ {metric_name}: ${value/1e9:.2f}B")
                    elif abs(value) >= 1e6:  # For medium numbers
                        logging.info(f"✅ {metric_name}: ${value/1e6:.2f}M")
                    else:
                        logging.info(f"✅ {metric_name}: {value:,.2f}")
                else:
                    logging.info(f"✅ {metric_name}: {value}")
            else:
                missing_metrics.append(metric_name)
                logging.warning(f"❌ {metric_name}: Missing")
    
    # Summary
    total_metrics = len([m for metrics in metrics_check.values() for m in metrics])
    available_count = len(available_metrics)
    missing_count = len(missing_metrics)
    
    logging.info(f"\nMetrics Summary for {ticker}:")
    logging.info(f"Available: {available_count}/{total_metrics} ({available_count/total_metrics*100:.1f}%)")
    if missing_metrics:
        logging.warning("Missing metrics:")
        for metric in missing_metrics:
            logging.warning(f"- {metric}")
    
    # Check if we have enough data for core value analysis
    core_metrics = [
        "pe_ratio", "price_to_book", "roe", "debt_to_equity", "net_margin",
        "free_cash_flow", "revenue_growth_ttm", "analyst_rating"
    ]
    missing_core = [m for m in core_metrics if data.get(m) is None]
    
    if not missing_core:
        logging.info("✅ All core value metrics available!")
    else:
        logging.error("❌ Missing core metrics: " + ", ".join(missing_core))

def clear_cache():
    """Clear the cache file and reset the cache dictionary."""
    global stock_cache
    stock_cache = {}
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
    logging.info("Cache cleared")

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Clear cache before testing
    clear_cache()
    
    # First test API connection
    if not test_fmp_connection():
        print("\nFMP API connection test failed! Please check the logs above for details.")
        exit(1)
    
    # Test a diverse set of stocks
    test_stocks = [
        "AAPL",    # Large cap tech
        "MSFT",    # Large cap tech
        "BRK-B",   # Value stock
        "JNJ",     # Healthcare
        "JPM",     # Financial
        "KO",      # Consumer staples
        "XOM",     # Energy
        "PG",      # Consumer goods
        "V",       # Financial services
        "WMT"      # Retail
    ]
    
    print("\nTesting batch processing with a diverse set of stocks...")
    results = fetch_stock_data_batch(test_stocks)
    
    # Print summary
    print("\nProcessing Summary:")
    print(f"Total stocks processed: {len(results)}")
    print(f"Successfully processed: {len([r for r in results.values() if r])}")
    print(f"Failed to process: {len([r for r in results.values() if not r])}")

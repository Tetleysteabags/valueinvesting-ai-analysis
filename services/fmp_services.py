import os
import requests
from utils.cache import load_cache, save_cache, get_cache_key

API_KEY = os.getenv("FMP_API_KEY")
BASE_URL = "https://financialmodelingprep.com/api/v3"
CACHE_FILE = "fmp_cache.json"

cache = load_cache(CACHE_FILE)

def _get(endpoint: str, params: dict = None):
    if params is None:
        params = {}
    params["apikey"] = API_KEY
    key = get_cache_key([endpoint, params])
    if key in cache:
        return cache[key]
    url = f"{BASE_URL}/{endpoint}"
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()
    cache[key] = data
    save_cache(cache, CACHE_FILE)
    return data

def get_profile(symbol: str) -> dict:
    """Company profile: price, beta, marketCap, priceToBook, etc."""
    data = _get(f"profile/{symbol}")  # :contentReference[oaicite:0]{index=0}
    return data[0] if data else {}

def get_balance_sheet(symbol: str, limit: int = 1) -> dict:
    """Returns the most recent balance sheet statement."""
    data = _get(f"balance-sheet-statement/{symbol}", {"limit": limit})  # :contentReference[oaicite:1]{index=1}
    return data[0] if data else {}

def get_income_statement(symbol: str, limit: int = 1) -> dict:
    """Returns the most recent income statement."""
    data = _get(f"income-statement/{symbol}", {"limit": limit})  # :contentReference[oaicite:2]{index=2}
    return data[0] if data else {}

def get_cash_flow(symbol: str, limit: int = 1) -> dict:
    """Returns the most recent cash flow statement."""
    data = _get(f"cash-flow-statement/{symbol}", {"limit": limit})  # :contentReference[oaicite:3]{index=3}
    return data[0] if data else {}

def get_historical_price(symbol: str, timeseries: str = "full") -> list:
    """EOD OHLCV data."""
    return _get(f"historical-price-eod/{timeseries}", {"symbol": symbol})  # :contentReference[oaicite:4]{index=4}

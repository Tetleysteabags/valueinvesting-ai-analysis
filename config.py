import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
FMP_API_KEY = os.getenv("FMP_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Value Investing Thresholds - STRICT (Original)
THRESHOLDS = {
    "pe": 10,
    "pb": 1.5,
    "de": 1,
    "roe": 0.12
}

# Value Investing Thresholds - MODERATE (More flexible)
THRESHOLDS_MODERATE = {
    "pe": 15,
    "pb": 2.5,
    "de": 1.5,
    "roe": 0.10
}

# Value Investing Thresholds - CONSERVATIVE (Very flexible)
THRESHOLDS_CONSERVATIVE = {
    "pe": 20,
    "pb": 3.0,
    "de": 2.0,
    "roe": 0.08
}

# Cache configuration
CACHE_FILE = "openai_cache.json"

# For testing with FMP free tier (250 calls/day limit)
# Each stock requires ~8 API calls, so we can process ~30 stocks per day
TEST_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "BRK-B", 
    "JNJ", "JPM", "V", "PG", "UNH", "HD", "MA", "DIS", "PYPL", "ADBE",
    "CRM", "NFLX", "INTC", "CMCSA", "PFE", "TMO", "ABT", "KO", "PEP",
    "AVGO", "COST", "DHR", "ABBV", "WMT", "ACN", "LLY", "TXN"
]
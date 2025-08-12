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

# PIT / hygiene
REPORTING_LAG_DAYS = 60
MIN_PRICE = 5.0
MIN_ADV_USD = 2_000_000.0   # set to None to disable; fallback uses MIN_MARKET_CAP
MIN_MARKET_CAP = 750_000_000.0

# Selection size & sector control
TOP_N = 25
SECTOR_CAP = 0.25           # 25% max of final picks from any one sector
COMPOSITE_MIN_PCTL = 0.0    # e.g., 0.70 to require >= 70th pct within sector

# Legacy thresholds you may keep (optional)
MAX_PB = None               # e.g., 2.0
MIN_EY = None               # e.g., 0.03  (>=3% earnings yield)

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


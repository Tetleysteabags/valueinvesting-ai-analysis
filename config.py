import os
from dotenv import load_dotenv

load_dotenv()


FMP_API_KEY = os.getenv("FMP_API_KEY")

THRESHOLDS = {
    "pe": 10,
    "pb": 1.5,
    "de": 1,
    "roe": 0.12
}

CACHE_FILE = "openai_cache.json"
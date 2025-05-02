import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set")

THRESHOLDS = {
    "pe": 10,
    "pb": 1.5,
    "de": 1,
    "roe": 0.12
}

CACHE_FILE = "openai_cache.json"
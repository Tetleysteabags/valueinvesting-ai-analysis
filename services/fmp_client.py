#!/usr/bin/env python3
"""Financial Modeling Prep API client with built-in caching and rate-limiting.

Usage
-----
>>> from services.fmp_client import FMPClient
>>> client = FMPClient()
>>> data = client.get("profile/AAPL")

The client is thread-safe and keeps an in-memory cache for 24 h (or the TTL you
specify).  All logic is encapsulated in the class – no module-level globals –
so it’s easy to mock in unit tests.
"""
from __future__ import annotations

import os
import time
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
FMP_API_KEY = os.getenv("FMP_API_KEY")
FMP_BASE = "https://financialmodelingprep.com/api/v3"

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)
DEFAULT_CACHE_FILE = CACHE_DIR / "fmp_cache.json"
CACHE_TTL = 60 * 60 * 24  # 24 h

MAX_REQUESTS_PER_MIN = 50  # paid tier; adjust if needed
RATE_WINDOW = 60  # seconds

# ---------------------------------------------------------------------------
# Helper – simple time-bucket rate limiter
# ---------------------------------------------------------------------------
class _RateLimiter:
    def __init__(self, max_requests: int = MAX_REQUESTS_PER_MIN, window: int = RATE_WINDOW):
        self.max_requests = max_requests
        self.window = window
        self._count = 0
        self._window_start = time.time()

    def wait_if_needed(self) -> None:
        now = time.time()
        if now - self._window_start > self.window:
            # new window
            self._window_start = now
            self._count = 0
        if self._count >= self.max_requests:
            sleep_for = self.window - (now - self._window_start)
            logging.info(f"Rate limit hit – sleeping {sleep_for:.1f}s")
            time.sleep(max(sleep_for, 0))
            # reset afterwards
            self._window_start = time.time()
            self._count = 0
        self._count += 1

# ---------------------------------------------------------------------------
class FMPClient:
    """Encapsulated FMP HTTP client with caching & rate-limiting."""

    def __init__(self, *, cache_file: Path = DEFAULT_CACHE_FILE, ttl: int = CACHE_TTL):
        if not FMP_API_KEY:
            raise EnvironmentError("FMP_API_KEY not set in environment")

        self.ttl = ttl
        self.cache_file = cache_file
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load_cache()
        self._rate_limiter = _RateLimiter()
        self._session = self._create_session()

    # ------------------------------------------------------------------
    @staticmethod
    def _create_session() -> requests.Session:
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    # ------------------------------------------------------------------
    # Caching helpers
    # ------------------------------------------------------------------
    def _load_cache(self) -> None:
        if self.cache_file.exists():
            try:
                with self.cache_file.open("r", encoding="utf-8") as fh:
                    raw = json.load(fh)
                now = time.time()
                # keep only fresh items
                self._cache = {k: v for k, v in raw.items() if now - v["ts"] < self.ttl}
            except Exception as exc:
                logging.warning(f"Failed loading FMP cache: {exc}")
                self._cache = {}

    def _save_cache(self) -> None:
        try:
            tmp = {k: v for k, v in self._cache.items()}
            with self.cache_file.open("w", encoding="utf-8") as fh:
                json.dump(tmp, fh)
        except Exception as exc:
            logging.warning(f"Failed saving FMP cache: {exc}")

    # ------------------------------------------------------------------
    def get(self, endpoint: str, *, params: Optional[Dict[str, Any]] = None, use_cache: bool = True) -> Any:
        """GET an endpoint, returning parsed JSON."""
        if params is None:
            params = {}
        params.setdefault("apikey", FMP_API_KEY)

        key = f"{endpoint}|{json.dumps(params, sort_keys=True)}"
        now = time.time()

        if use_cache and key in self._cache and now - self._cache[key]["ts"] < self.ttl:
            return self._cache[key]["data"]

        # Respect rate limit
        self._rate_limiter.wait_if_needed()

        url = f"{FMP_BASE}/{endpoint}"
        resp = self._session.get(url, params=params, timeout=15)
        if resp.status_code == 404:
            data = None
        else:
            resp.raise_for_status()
            data = resp.json()

        # Save to cache
        if use_cache:
            self._cache[key] = {"ts": now, "data": data}
            self._save_cache()
        return data

# Singleton instance most code will use
client = FMPClient() 
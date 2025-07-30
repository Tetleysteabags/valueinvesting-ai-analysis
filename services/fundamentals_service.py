# services/fundamental_service.py

import pandas as pd
from pathlib import Path
from typing import List, Dict

class FundamentalService:
    """
    Load and cache per‑ticker fundamental histories,
    then for any as‑of date return the last published record.
    """

    def __init__(self, fundamentals_dir: Path):
        self.fundamentals_dir = fundamentals_dir
        self._cache: Dict[str, pd.DataFrame] = {}

    def _load_history(self, ticker: str) -> pd.DataFrame:
        """Lazy‑load and cache a ticker’s fundamentals history CSV."""
        if ticker in self._cache:
            return self._cache[ticker]

        path = self.fundamentals_dir / f"{ticker}_fundamentals_history.csv"
        if not path.exists():
            raise FileNotFoundError(f"No fundamentals file for {ticker} at {path}")

        df = pd.read_csv(path, parse_dates=["report_date"])
        # ensure sorted by date
        df = df.sort_values("report_date")
        self._cache[ticker] = df
        return df

    def fundamentals_asof(
        self,
        tickers: List[str],
        asof: pd.Timestamp
    ) -> Dict[str, Dict]:
        """
        For each ticker, pick the most‐recent row whose report_date ≤ asof.
        Returns a dict: { ticker: { field: value, … }, … }
        """
        out: Dict[str, Dict] = {}
        for t in tickers:
            try:
                hist = self._load_history(t)
            except FileNotFoundError:
                continue

            valid = hist[hist["report_date"] <= asof]
            if valid.empty:
                # no fundamentals published yet as of this date
                continue

            latest = valid.iloc[-1]  # last row
            out[t] = latest.drop("report_date").to_dict()
        return out

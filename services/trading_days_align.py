import pandas as pd

def trading_days_aligner(index: pd.DatetimeIndex):
    cache = {}
    def _align(dates: pd.DatetimeIndex):
        key = (dates[0], dates[-1], dates.freqstr)
        if key in cache:                              #  <‑‑ cache hit
            return cache[key]
        aligned = index[index.searchsorted(dates, side="right") - 1]
        cache[key] = aligned
        return aligned
    return _align
#!/usr/bin/env python3
"""Stock data service v2 – uses the new FMPClient and batch endpoints.

Key changes vs previous services
--------------------------------
* Encapsulated caching/rate-limiting via `services.fmp_client.FMPClient` (no globals)
* Uses FMP *batch* endpoints (`quote`, `profile`, `key-metrics-ttm`, `ratios-ttm`) to fetch
  many tickers in one HTTP request → fewer calls, faster.
* Returns field names aligned with our new naming convention:
    roe → float      # Return on equity TTM
    debt_to_equity → float
    price_to_book   → float
  plus extra metrics such as `fcf_yield`, `peg_ratio`, `enterprise_value`.
* Provides two main helpers:
    fetch_stock_data(ticker: str) -> dict | None
    fetch_stock_data_batch(tickers: list[str]) -> dict[str, dict]
"""
from __future__ import annotations

from typing import Dict, Any, List
import logging

from services.fmp_client import client as fmp

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _parse_numeric(value):
    try:
        return float(value) if value not in (None, "", "null") else None
    except Exception:
        return None

# ---------------------------------------------------------------------------
# Core fetch helpers
# ---------------------------------------------------------------------------

def _fetch_endpoint_batch(endpoint: str, tickers: List[str]):
    """Fetch a batch endpoint and return list[dict]."""
    joined = ",".join(tickers)
    return fmp.get(f"{endpoint}/{joined}") or []


def _build_lookup(data: list[dict]):
    """Convert list[dict] to dict[str, dict] keyed by symbol upper()"""
    out: Dict[str, Dict[str, Any]] = {}
    for item in data or []:
        symbol = item.get("symbol") or item.get("ticker")
        if symbol:
            out[symbol.upper()] = item
    return out

# ---------------------------------------------------------------------------

def _merge_datasets(tickers: List[str]) -> Dict[str, Dict[str, Any]]:
    """Fetch quote + profile + metrics + ratios for a batch and merge per ticker."""
    quote_raw   = _fetch_endpoint_batch("quote", tickers)
    profile_raw = _fetch_endpoint_batch("profile", tickers)
    metrics_raw = _fetch_endpoint_batch("key-metrics-ttm", tickers)
    ratios_raw  = _fetch_endpoint_batch("ratios-ttm", tickers)

    quote   = _build_lookup(quote_raw)
    profile = _build_lookup(profile_raw)
    
    # For metrics and ratios, the batch endpoint returns list without symbols
    # We need to map them by index to the tickers
    metrics = {}
    ratios = {}
    if len(metrics_raw) == len(tickers):
        for i, ticker in enumerate(tickers):
            metrics[ticker.upper()] = metrics_raw[i] if i < len(metrics_raw) else {}
    else:
        # Fallback to individual calls if batch fails
        for ticker in tickers:
            individual_metrics = fmp.get(f"key-metrics-ttm/{ticker}")
            metrics[ticker.upper()] = individual_metrics[0] if individual_metrics else {}
            
    if len(ratios_raw) == len(tickers):
        for i, ticker in enumerate(tickers):
            ratios[ticker.upper()] = ratios_raw[i] if i < len(ratios_raw) else {}
    else:
        # Fallback to individual calls if batch fails
        for ticker in tickers:
            individual_ratios = fmp.get(f"ratios-ttm/{ticker}")
            ratios[ticker.upper()] = individual_ratios[0] if individual_ratios else {}

    merged: Dict[str, Dict[str, Any]] = {}

    for t in tickers:
        sym = t.upper()
        q   = quote.get(sym, {})
        p   = profile.get(sym, {})
        m   = metrics.get(sym, {})
        r   = ratios.get(sym, {})

        if not p:  # need at least profile
            continue

        merged[sym] = {
            "symbol": sym,
            "company": p.get("companyName"),
            "current_price": _parse_numeric(q.get("price") or p.get("price")),
            "market_cap": _parse_numeric(p.get("mktCap")),
            "beta": _parse_numeric(p.get("beta")),

            # Valuation ratios (renamed)
            "pe_ratio": _parse_numeric(m.get("peRatioTTM")),
            "price_to_book": _parse_numeric(m.get("pbRatioTTM")),
            "peg_ratio": _parse_numeric(r.get("pegRatioTTM")),
            "fcf_yield": _parse_numeric(m.get("freeCashFlowYieldTTM")),

            # Financial ratios (renamed)
            "debt_to_equity": _parse_numeric(r.get("debtEquityRatioTTM")),
            "roe": _parse_numeric(r.get("returnOnEquityTTM")),
            "roa": _parse_numeric(r.get("returnOnAssetsTTM")),
            "net_margin": _parse_numeric(r.get("netProfitMarginTTM")),
            "gross_margin": _parse_numeric(r.get("grossProfitMarginTTM")),
            "operating_margin": _parse_numeric(r.get("operatingProfitMarginTTM")),

            # Enterprise metrics
            "enterprise_value": _parse_numeric(q.get("enterpriseValue")),
            "ev_to_ebitda": _parse_numeric(q.get("enterpriseValueToEbitda")),

            # Cash-flow figures
            "free_cash_flow": _parse_numeric(p.get("freeCashFlow")),
        }

    return merged

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_stock_data(ticker: str) -> Dict[str, Any] | None:
    data_map = fetch_stock_data_batch([ticker])
    return data_map.get(ticker.upper())


def fetch_stock_data_batch(tickers: List[str], batch_size: int = 50) -> Dict[str, Dict[str, Any]]:
    """Fetch many tickers. FMP batch endpoints accept up to 100 symbols."""
    results: Dict[str, Dict[str, Any]] = {}
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        logging.info(f"Fetching batch {i//batch_size + 1} / {(len(tickers)+batch_size-1)//batch_size}")
        merged = _merge_datasets(batch)
        results.update(merged)
    return results 
# analysis/value_initial_filter.py
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Union
import numpy as np
import pandas as pd

@dataclass
class FieldMap:
    market_cap: str = "marketCap"
    enterprise_value: str = "enterpriseValue"
    net_income_ttm: str = "netIncomeTTM"
    free_cash_flow_ttm: str = "freeCashFlowTTM"
    ebit_ttm: str = "ebitTTM"
    ebitda_ttm: str = "ebitdaTTM"
    revenue_ttm: str = "revenueTTM"
    operating_cf_ttm: str = "operatingCashFlowTTM"
    total_assets_ttm: str = "totalAssetsTTM"
    interest_expense_ttm: str = "interestExpenseTTM"  # often negative in feeds
    price_to_book: str = "priceToBook"
    tangible_book_ps: str = "tangibleBookValuePerShare"
    book_value_ps: str = "bookValuePerShare"
    shares_out: str = "sharesOutstanding"
    sector: str = "sector"
    filing_date: str = "filingDate"
    fiscal_date: str = "fiscalDateEnding"

def _pick_pit_row(df: pd.DataFrame, asof: pd.Timestamp, lag_days: int, fm: FieldMap) -> Optional[pd.Series]:
    """Return latest row with filingDate/fiscalDateEnding <= asof - lag_days."""
    if df is None or len(df) == 0:
        return None
    d = df.copy()
    cutoff = pd.Timestamp(asof).tz_localize("UTC") - pd.Timedelta(days=lag_days)
    if fm.filing_date in d:
        d[fm.filing_date] = pd.to_datetime(d[fm.filing_date], errors="coerce", utc=True)
        d = d[d[fm.filing_date] <= cutoff]
    elif fm.fiscal_date in d:
        d[fm.fiscal_date] = pd.to_datetime(d[fm.fiscal_date], errors="coerce", utc=True)
        d = d[d[fm.fiscal_date] <= cutoff]
    else:
        return None
    if len(d) == 0:
        return None
    key = fm.filing_date if fm.filing_date in d else fm.fiscal_date
    return d.sort_values(by=key).iloc[-1]

def _safe_div(num, denom):
    try:
        if denom is None:
            return np.nan
        denom = float(denom)
        if denom == 0.0 or np.isnan(denom):
            return np.nan
        v = float(num) / denom
        return np.nan if not np.isfinite(v) else v
    except Exception:
        return np.nan

def _winsorize(s: pd.Series, p1=0.01, p99=0.99):
    if s.dropna().empty:
        return s
    lo, hi = s.quantile(p1), s.quantile(p99)
    return s.clip(lower=lo, upper=hi)

def _pct_rank(s: pd.Series) -> pd.Series:
    return s.rank(pct=True, method="average")

def value_initial_filter(
    fmp_dict: Dict[str, pd.DataFrame],
    prices_df: Union[pd.DataFrame, Dict[str, pd.DataFrame]],
    asof_date: Union[str, pd.Timestamp],
    *,
    field_map: FieldMap = FieldMap(),
    # thresholds (read from config; these defaults are sensible fallbacks)
    MIN_PRICE: float = 5.0,
    MIN_ADV_USD: Optional[float] = 2_000_000.0,   # set None to disable ADV check
    MIN_MARKET_CAP: Optional[float] = 750_000_000.0,  # used only if ADV unavailable
    REPORTING_LAG_DAYS: int = 60,
    TOP_N: int = 25,
    SECTOR_CAP: float = 0.25,
    COMPOSITE_MIN_PCTL: float = 0.0,  # e.g., 0.70 to require >= 70th pct within sector
    # legacy value thresholds you may keep (optional; set to None to ignore)
    MAX_PB: Optional[float] = None,
    MIN_EY: Optional[float] = None,   # earnings yield floor, e.g., 0.03 for >=3%
) -> Tuple[List[str], pd.DataFrame]:
    """
    Step-3 'value tickers' selector (PIT-safe, sector-neutral).
    Applies hard filters, computes value/quality metrics, sector-neutral ranks,
    enforces sector cap, and returns up to TOP_N tickers.

    Returns
    -------
    tickers : list[str]
        Selected tickers for Step 4 backtest.
    panel : DataFrame
        Diagnostic table with metrics, scores, and ranks.
    """
    asof = pd.Timestamp(asof_date).normalize()

    # Extract price/volume
    if isinstance(prices_df, dict):
        px = prices_df.get("close")
        vol = prices_df.get("volume")
    else:
        px, vol = prices_df, None
    if px is None or px.empty:
        return [], pd.DataFrame()

    # Liquidity panel
    px_slice = px.loc[:asof].tail(22)  # ~1 month window
    last_px = px_slice.tail(1).T.squeeze().rename("price")
    adv_usd = None
    if vol is not None and not vol.empty:
        v = vol.loc[px_slice.index]
        adv_usd = (v.tail(20).mean() * px_slice.tail(20).mean()).rename("adv_usd")

    # PIT row per ticker
    rows = []
    for tkr, df in fmp_dict.items():
        pit = _pick_pit_row(pd.DataFrame(df), asof, REPORTING_LAG_DAYS, field_map)
        if pit is not None:
            rows.append({"ticker": tkr, **pit.to_dict()})
    if not rows:
        return [], pd.DataFrame()
    F = pd.DataFrame(rows).set_index("ticker")

    # Attach sector, price, liquidity
    F["sector"] = F.get(field_map.sector)
    F = F.join(last_px, how="left")
    if adv_usd is not None:
        F = F.join(adv_usd, how="left")

    # Hard liquidity/price filters (initial filter)
    F = F[F["price"] >= float(MIN_PRICE)]
    if adv_usd is not None and MIN_ADV_USD is not None:
        F = F[F["adv_usd"] >= float(MIN_ADV_USD)]
    elif MIN_MARKET_CAP is not None and field_map.market_cap in F:
        F = F[F[field_map.market_cap] >= float(MIN_MARKET_CAP)]
    if F.empty:
        return [], pd.DataFrame()

    # Core fields
    mc   = F.get(field_map.market_cap)
    ev   = F.get(field_map.enterprise_value)
    ni   = F.get(field_map.net_income_ttm)
    fcf  = F.get(field_map.free_cash_flow_ttm)
    ebit = F.get(field_map.ebit_ttm)
    ebitda = F.get(field_map.ebitda_ttm)
    sales  = F.get(field_map.revenue_ttm)
    pb     = F.get(field_map.price_to_book)
    ocf    = F.get(field_map.operating_cf_ttm)
    assets = F.get(field_map.total_assets_ttm)
    int_exp = F.get(field_map.interest_expense_ttm)

    # Build metrics (initial filter stage)
    ey        = ni.combine(mc, _safe_div) if ni is not None and mc is not None else pd.Series(index=F.index, dtype=float)
    fcfy      = fcf.combine(mc, _safe_div) if fcf is not None and mc is not None else pd.Series(index=F.index, dtype=float)
    ebit_ev   = ebit.combine(ev, _safe_div) if ebit is not None and ev is not None else pd.Series(index=F.index, dtype=float)
    ebitda_ev = ebitda.combine(ev, _safe_div) if ebitda is not None and ev is not None else pd.Series(index=F.index, dtype=float)
    ev_sales  = ev.combine(sales, _safe_div) if ev is not None and sales is not None else pd.Series(index=F.index, dtype=float)
    accruals  = (ni - ocf).combine(assets, _safe_div) if (ni is not None and ocf is not None and assets is not None) else pd.Series(index=F.index, dtype=float)
    
    pe = F.get("pe_ratio")
    if (ey.isna().all() or ey is None) and pe is not None:
        ey = 1.0 / pd.to_numeric(pe, errors="coerce").replace(0, np.nan)

    if (fcfy.isna().all() or fcfy is None) and "fcf_yield" in F:
        fcfy = pd.to_numeric(F["fcf_yield"], errors="coerce")

    if (ebitda_ev.isna().all() or ebitda_ev is None) and "ebitda" in F and ev is not None:
        ebitda_ev = pd.to_numeric(F["ebitda"], errors="coerce").combine(ev, _safe_div)

    # If interest expense missing, skip the >2x guard instead of dropping everything
    if int_exp is None or int_exp.dropna().empty:
        int_exp = pd.Series(np.nan, index=F.index)

    # Financials exception
    sector_str = F["sector"].astype(str)
    is_fin = sector_str.str.contains("Financial|Bank|Insurance", case=False, na=False)

    # Guardrails (initial filter gate)
    # interest expense can be negative; take absolute for coverage denominator
    interest_cov = None
    if ebit is not None and int_exp is not None:
        interest_cov = ebit.combine(int_exp, lambda x, y: _safe_div(x, abs(y) if (y is not None) else y))
    guard = pd.Series(True, index=F.index)
    guard &= (ebit > 0).fillna(False)
    guard &= (fcf > 0).fillna(False)
    guard &= (interest_cov > 2).fillna(False)
    # optional ROE > 0 if you have equity; skipped here unless present

    # Legacy thresholds from config (optional)
    if MAX_PB is not None and pb is not None:
        guard &= (pb <= float(MAX_PB)).fillna(False)
    if MIN_EY is not None:
        guard &= (ey >= float(MIN_EY)).fillna(False)

    F = F[guard]
    if F.empty:
        return [], pd.DataFrame()

    # Winsorize + percentile ranks (sector-neutral)
    def wrank(s: pd.Series):
        return _pct_rank(_winsorize(pd.to_numeric(s, errors="coerce")))

    val_parts = {
        "ey": wrank(ey.loc[F.index]),
        "fcfy": wrank(fcfy.loc[F.index]),
        "inv_pb": wrank(1.0 / pb.replace(0, np.nan).loc[F.index]) if pb is not None else pd.Series(index=F.index, dtype=float),
    }
    # EV-based metrics excluded for Financials
    val_parts["ebit_ev"]   = wrank(ebit_ev.loc[F.index & (~is_fin)]) if not ebit_ev.loc[~is_fin].empty else pd.Series(index=F.index, dtype=float)
    val_parts["ebitda_ev"] = wrank(ebitda_ev.loc[F.index & (~is_fin)]) if not ebitda_ev.loc[~is_fin].empty else pd.Series(index=F.index, dtype=float)
    val_parts["ev_sales"]  = wrank(ev_sales.loc[F.index & (~is_fin)]) if not ev_sales.loc[~is_fin].empty else pd.Series(index=F.index, dtype=float)
    # reindex all to F.index
    val_parts = {k: s.reindex(F.index) for k, s in val_parts.items()}

    qual_parts = {
        "interest_cov": wrank(interest_cov.loc[F.index]) if interest_cov is not None else pd.Series(index=F.index, dtype=float),
        "neg_accruals": wrank((-accruals).loc[F.index]) if not accruals.dropna().empty else pd.Series(index=F.index, dtype=float),
    }

    # Combine per stock, then sector-neutralize (rank within sector)
    def combine(parts: Dict[str, pd.Series]) -> pd.Series:
        M = pd.concat(list(parts.values()), axis=1).replace([np.inf, -np.inf], np.nan)
        M = M.dropna(how="all", axis=1)
        if M.shape[1] == 0:
            return pd.Series(index=F.index, dtype=float)
        raw = M.mean(axis=1, skipna=True)
        return raw.groupby(F["sector"]).transform(lambda x: x.rank(pct=True))

    F["value_score"] = combine(val_parts)
    F["quality_score"] = combine(qual_parts)
    F["composite"] = 0.60 * F["value_score"] + 0.40 * F["quality_score"]

    # Optional composite floor (within-sector percentile)
    if COMPOSITE_MIN_PCTL > 0:
        F = F[F["composite"] >= COMPOSITE_MIN_PCTL]
        if F.empty:
            return [], pd.DataFrame()

    # Sector-proportional pick then sector-cap
    picks = []
    sector_counts = F["sector"].fillna("Unknown").value_counts(normalize=True)
    for sec, frac in sector_counts.items():
        n_sec = max(1, int(round(frac * TOP_N)))
        sub = F[F["sector"] == sec].sort_values("composite", ascending=False).head(n_sec)
        picks.append(sub)
    C = pd.concat(picks).sort_values("composite", ascending=False)

    max_per_sector = max(1, int(math.ceil(SECTOR_CAP * TOP_N)))
    out = []
    used = {}
    for tkr, row in C.iterrows():
        s = str(row.get("sector", "Unknown"))
        used[s] = used.get(s, 0) + 1
        if used[s] <= max_per_sector:
            out.append(tkr)
        if len(out) >= TOP_N:
            break

    panel = F.loc[out].sort_values("composite", ascending=False)
    return out, panel

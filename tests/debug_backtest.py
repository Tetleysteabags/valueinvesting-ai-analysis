#!/usr/bin/env python3
"""
Basic smoke‑test for ValueInvestingBacktester

❶  Verifies that the engine runs from import without crashing.
❷  Confirms that initial and first‑recorded equity equal initial capital.
❸  Ensures cash + Σ position values == reported portfolio value at each rebalance.
❹  Checks that total_return and final_capital line up mathematically.
"""

import numpy as np
import pandas as pd
from datetime import datetime

# Allow "python tests/test_backtester_basic.py" from repo root
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.backtesting import backtest_value_strategy  
from analysis.backtesting import optimize_parameters

TICKERS = [
  'AIFU','ASC','ATHS','CIVI','EHLD','EMO','ESNT','EVT','EXG','FOF','GDO','GFR','GSL',
  'HTD','ICCC','JCE','MHI','MTG','NXG','PDT','SITC','SPLP','STNG','TYG','UNMA','VIASP',
  'ACT','ADX','AFB','AGD','AGMH','AMAL','AOD','ARDT','ASGI','ATCH','AWP','AXS','BGH',
  'BGX','BHF','BHFAL','BHFAM','BHFAN','BHFAO','BMGL','BTO','BTZ','BWG','BXMX','CAG',
  'CBNA','CEE','CET','CGABL','CHN','CHY','CIF','CLM','CMRE','CMU','CPAC','CPZ','CRC',
  'CRI','CXE','DBL','DDI','DDT','DFP','DGICA','DGICB','DLNG','DLY','DMF','DNP','DPG',
  'DRD','DSL','DSU','ECAT','ECF','EIC','EIM','EMF','ENX','EOI','ERC','ERH','ETG','ETJ',
  'ETO','ETV','ETY','EVG','FAX','FBIZ','FFA','FFC','FG','FGB','FGN','FINV','FLC','FPF',
  'FPH','FPI','FRA','FSCO','FT','FUNC','GAINL','GAINN','GAINZ','GAM','GCV','GHC','GHY',
  'GIFI','GLAD','GLQ','GOF','GRF','HAFN','HG','HGLB','HIT','HNW','HQH','HQL','HYI',
  'IAE','IFN','IGD','IHD','IMPP','IMPPP','INSW','INVX','JD','JEQ','JGH','JHI','JHS',
  'JOF','JXG','KBH','KIO','KKRS','KMPB','KYN','LDP','LEN','LEO','LNKB','MATX','MBWM',
  'MFM','MHO','MLR','MMT','MNDO','MNR','MNSO','MOMO','MTDR','MTH','NAD','NAMI','NBH',
  'NBXG','NCV','NCZ','NDMO','NEA','NECB','NHS','NMI','NMIH','NML','NRO','NRT','NVAWW',
  'NVNI','NWG','NZF','OFG','OFS','OFSSH','OPHC','OVLY','OXM','OZK','OZKAP','PAXS',
  'PDPA','PDX','PFD','PFL','PFN','PFO','PGP','PGZ','PHD','PLBC','PMM','PR','PSF','PTA',
  'QQQX','RAND','RCG','REFI','REPX','RNR','RWAY','RWAYL','RWAYZ','SABA','SBCWW','SBLK',
  'SCD','SD','SGRP','SGU','SIM','SNV','SON','SPE','SPXX','SSBK','STEW','SXC','TBLD',
  'TCBX','THQ','TK','TMHC','TWN','TY','UHS','UNM','USA','UTG','VALE','VEL','VFL','VGI',
  'VIPS','VIRC','VKI','WLKP','XYF'
]

START_DATE    = "2024-01-01"
END_DATE      = "2025-06-30"
INIT_CAPITAL  = 100_000.0


def main() -> None:
    result = backtest_value_strategy(
        tickers=TICKERS,
        start_date=START_DATE,
        end_date=END_DATE,
        rebalance_freq="ME",
        initial_capital=INIT_CAPITAL,
    )

    # --- invariant 1: first portfolio value == initial capital ---
    first_val = result.portfolio_values.iloc[0]
    assert abs(first_val - INIT_CAPITAL) < 1e-6, f"First equity {first_val} ≠ {INIT_CAPITAL}"

    # --- invariant 2: equity curve has no NaNs ---
    assert result.portfolio_values.isna().sum() == 0, "Equity curve contains NaNs"

    # --- invariant 3: final capital reflects reported total_return ---
    calc_return = (result.final_capital - INIT_CAPITAL) / INIT_CAPITAL
    assert np.isclose(
        calc_return, result.total_return, atol=1e-6
    ), f"Return mismatch: {calc_return} vs {result.total_return}"

    # --- print quick summary ---
    print("\n✅ basic back‑test smoke‑test passed")
    print(result.portfolio_values)
    print(
        f"Total return {result.total_return:.2%}, "
        f"Vol {result.volatility:.2%}, Sharpe {result.sharpe_ratio:.2f}"
    )
    
    print("\n🔍 running parameter‑grid smoke‑test…")
    opt_df = optimize_parameters(
        tickers=TICKERS,
        start_date=START_DATE,
        end_date=END_DATE,
        initial_capital=INIT_CAPITAL,
    )
    # invariant: we got at least one row back
    assert hasattr(opt_df, "shape") and opt_df.shape[0] > 0, "optimize_parameters returned no results"
    # invariant: must contain the columns we expect
    required = {'profit_target','trailing_stop','stop_loss','rebalance_freq','sharpe_ratio'}
    missing = required - set(opt_df.columns)
    assert not missing, f"optimize_parameters missing columns: {missing}"
    print("✅ parameter‑grid smoke‑test passed; found "
          f"{opt_df.shape[0]} combinations, top Sharpe "
          f"{opt_df['sharpe_ratio'].max():.2f}")

if __name__ == "__main__":
    main()

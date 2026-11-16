"""Central configuration: account, risk limits, study windows and session times."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time

import pandas as pd

# ---------------------------------------------------------------- study windows
STUDY_START = pd.Timestamp("2024-11-18")  # first tradable session (warm-up data starts Sep 2024)
STUDY_END = pd.Timestamp("2026-11-13")  # last completed session before the blueprint date
HOLDOUT_START = pd.Timestamp("2026-05-18")  # final ~6 months, untouched until the end
DEV_END = HOLDOUT_START - pd.Timedelta(days=1)

# Walk-forward inside the development period: 6-month train, 3-month test, rolling by 3 months.
WALK_FORWARD = [
    # (train_start, train_end, test_start, test_end)
    ("2024-11-18", "2025-05-16", "2025-05-19", "2025-08-14"),
    ("2025-02-17", "2025-08-14", "2025-08-18", "2025-11-14"),
    ("2025-05-19", "2025-11-14", "2025-11-17", "2026-02-13"),
    ("2025-08-18", "2026-02-13", "2026-02-16", "2026-05-15"),
]

# ---------------------------------------------------------------- session
SESSION_OPEN = time(9, 15)
ENTRY_START = time(9, 30)
ENTRY_END = time(14, 45)
FLAT_TIME = time(15, 15)  # blueprint's initial flat time
# Broker reality (Upstox): MIS auto square-off at 15:15 until Jun 2026 (15:20 after), and for F&O stocks
# after NSE's closing-auction session went live on 3 Aug 2026, at 15:05 (later 15:10). We flat at the
# close of the bar ending 15:10, and 15:00 from 3 Aug 2026, to avoid broker auto square-off.
CAS_START = "2026-08-03"
FLAT_MIN_PRE_CAS = 15 * 60 + 10
FLAT_MIN_CAS = 15 * 60


@dataclass(frozen=True)
class RiskConfig:
    capital: float = 300_000.0
    risk_per_trade: float = 3_000.0
    daily_loss_limit: float = 6_000.0
    weekly_loss_limit: float = 12_000.0
    max_open_risk: float = 6_000.0
    max_notional_per_stock: float = 75_000.0  # blueprint: cash-equity allocation per stock (25%)
    intraday_margin_rate: float = 0.20  # MIS: 5x leverage on cash equity
    min_trade_risk: float = 500.0  # skip if the risk budget left is below this
    max_per_industry_direction: int = 1  # correlated exposure control
    # Interpretation switch: if True, the ₹75k cap is applied to *margin* for intraday (=> ₹3.75L notional)
    intraday_cap_is_margin: bool = False


@dataclass(frozen=True)
class SlippageConfig:
    equity_bps: float = 5.0  # per side, on top of the modelled fill price
    stop_extra_bps: float = 3.0  # extra adverse slippage when a stop order is hit
    option_half_spread_liquid: float = 0.010  # fraction of premium paid per side for liquid contracts
    option_half_spread_illiquid: float = 0.025
    option_tick: float = 0.05


@dataclass(frozen=True)
class ScoreWeights:
    ema: float = 25.0
    htf: float = 20.0
    adx: float = 20.0
    vwap_structure: float = 15.0
    rvol: float = 10.0
    sector_rs: float = 10.0


@dataclass(frozen=True)
class RegimeConfig:
    adx_trend: float = 22.0
    adx_sideways: float = 18.0
    sep_trend: float = 0.5  # |EMA20-EMA50| / ATR
    sep_sideways: float = 0.25


@dataclass
class StudyConfig:
    risk: RiskConfig = field(default_factory=RiskConfig)
    slippage: SlippageConfig = field(default_factory=SlippageConfig)
    weights: ScoreWeights = field(default_factory=ScoreWeights)
    regime: RegimeConfig = field(default_factory=RegimeConfig)

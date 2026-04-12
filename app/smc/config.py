from __future__ import annotations

from dataclasses import dataclass

DEFAULT_NIFTY50 = [
    "ADANIENT",
    "ADANIPORTS",
    "APOLLOHOSP",
    "ASIANPAINT",
    "AXISBANK",
    "BAJAJ-AUTO",
    "BAJFINANCE",
    "BAJAJFINSV",
    "BEL",
    "BHARTIARTL",
    "BPCL",
    "BRITANNIA",
    "CIPLA",
    "COALINDIA",
    "DRREDDY",
    "EICHERMOT",
    "GRASIM",
    "HCLTECH",
    "HDFCBANK",
    "HDFCLIFE",
    "HEROMOTOCO",
    "HINDALCO",
    "HINDUNILVR",
    "ICICIBANK",
    "INDUSINDBK",
    "INFY",
    "ITC",
    "JSWSTEEL",
    "KOTAKBANK",
    "LT",
    "M&M",
    "MARUTI",
    "NESTLEIND",
    "NTPC",
    "ONGC",
    "POWERGRID",
    "RELIANCE",
    "SBILIFE",
    "SBIN",
    "SHRIRAMFIN",
    "SUNPHARMA",
    "TATACONSUM",
    "TATAMOTORS",
    "TATASTEEL",
    "TCS",
    "TECHM",
    "TITAN",
    "TRENT",
    "ULTRACEMCO",
    "WIPRO",
]

DEFAULT_BANKNIFTY = [
    "HDFCBANK",
    "ICICIBANK",
    "SBIN",
    "AXISBANK",
    "KOTAKBANK",
    "INDUSINDBK",
    "BANKBARODA",
    "PNB",
    "FEDERALBNK",
    "AUBANK",
    "IDFCFIRSTB",
    "CANBK",
]

TIMEFRAME_OPTIONS = {
    "5m": {"download_interval": "5m", "resample_rule": None, "max_period": "60d"},
    "15m": {"download_interval": "15m", "resample_rule": None, "max_period": "60d"},
    "1h": {"download_interval": "60m", "resample_rule": None, "max_period": "730d"},
    "4h": {"download_interval": "60m", "resample_rule": "4H", "max_period": "730d"},
    "1d": {"download_interval": "1d", "resample_rule": None, "max_period": "10y"},
}

PERIOD_ORDER = {
    "5d": 5,
    "1mo": 30,
    "3mo": 90,
    "6mo": 180,
    "1y": 365,
    "2y": 730,
    "5y": 1825,
    "10y": 3650,
}


@dataclass(slots=True)
class SMCAnalyzerConfig:
    """User-configurable knobs for BOS/FVG analysis."""

    timeframe: str = "1d"
    history_period: str = "5y"
    lookback_bars: int = 300
    pivot_left_bars: int = 3
    pivot_right_bars: int = 3
    breakout_lookback: int = 20
    close_breakout_confirmation: bool = True
    breakout_buffer_pct: float = 0.3
    min_fvg_size_pct: float = 0.2
    use_atr_gap_filter: bool = True
    use_volume_filter: bool = False
    near_zone_threshold_pct: float = 1.0
    direction_filter: str = "all"
    fresh_fvg_only: bool = True
    volume_spike_multiple: float = 1.2
    atr_gap_multiplier: float = 0.25


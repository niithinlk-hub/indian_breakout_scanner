from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _get_streamlit_secret(key: str) -> str | None:
    try:
        import streamlit as st
    except Exception:
        return None
    try:
        value: Any = st.secrets.get(key)
    except Exception:
        return None
    return None if value in {None, ""} else str(value)


def _setting(key: str, default: str | None = None) -> str | None:
    env_value = os.getenv(key)
    if env_value not in {None, ""}:
        return env_value
    secret_value = _get_streamlit_secret(key)
    if secret_value not in {None, ""}:
        return secret_value
    return default


@dataclass(slots=True)
class StockAlerterConfig:
    """Central config for the bullish breakout alerter page."""

    project_root: Path
    universe_name: str = "NIFTY LargeMidcap 250"
    timeframe: str = "1d"
    period: str = "2y"
    breakout_lookback: int = 40
    breakout_buffer_pct: float = 0.5
    minimum_volume_multiple: float = 1.5
    rsi_lower: float = 55.0
    rsi_upper: float = 72.0
    adx_threshold: float = 20.0
    atr_expansion_required: bool = False
    atr_expansion_threshold: float = 1.05
    retest_required: bool = False
    retest_candle_count: int = 3
    bos_required: bool = False
    fvg_required: bool = False
    breakout_follow_through_enabled: bool = True
    breakout_follow_through_window: int = 3
    relative_strength_filter: bool = True
    require_52week_high_module: bool = True
    range_lookback: int = 30
    triangle_tolerance_pct: float = 0.8
    flag_consolidation_depth_pct: float = 12.0
    swing_lookback: int = 20
    score_alert_threshold: int = 8
    category_aplus_min: int = 8
    category_a_min: int = 6
    category_watch_min: int = 4
    signal_weights: dict[str, int] = field(
        default_factory=lambda: {
            "breakout_confirmed": 2,
            "volume_expansion": 2,
            "ema_trend_alignment": 1,
            "rsi_bullish": 1,
            "adx_trend_strength": 1,
            "strong_candle": 1,
            "retest_confirmation": 2,
            "bos_present": 1,
            "bullish_fvg_present": 1,
            "relative_strength_positive": 1,
            "atr_expansion": 1,
            "not_extended_from_ema20": 1,
        },
    )
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    alert_history_path: Path | None = None
    benchmark_symbol: str = "^NSEI"
    custom_universe_text: str = ""
    max_symbols: int = 250


def load_stock_alerter_config(project_root: Path) -> StockAlerterConfig:
    """Load alert config from env/secrets with safe defaults."""

    return StockAlerterConfig(
        project_root=project_root,
        telegram_bot_token=_setting("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_setting("TELEGRAM_CHAT_ID"),
        alert_history_path=Path(
            _setting("STOCK_ALERTER_ALERT_HISTORY_PATH", str(project_root / "data" / "stock_alerter_alerts.json"))
            or project_root / "data" / "stock_alerter_alerts.json",
        ),
    )

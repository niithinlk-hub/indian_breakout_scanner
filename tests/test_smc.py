from __future__ import annotations

import pandas as pd

from app.smc.breakout import analyze_breakout
from app.smc.config import SMCAnalyzerConfig
from app.smc.fvg import detect_fvgs
from app.smc.screener import analyze_symbol, screen_watchlist
from app.smc.structure import analyze_structure


def test_detect_fvgs_finds_bullish_gap() -> None:
    frame = pd.DataFrame(
        {
            "datetime": pd.date_range("2025-01-01", periods=5, freq="D"),
            "open": [100, 102, 107, 108, 109],
            "high": [101, 103, 108, 109, 110],
            "low": [99, 101, 106, 107, 108],
            "close": [100.5, 102.5, 107.5, 108.5, 109.5],
            "volume": [1000, 1100, 1200, 1300, 1400],
            "symbol": ["TEST"] * 5,
        },
    )

    fvgs = detect_fvgs(frame, min_gap_size_pct=1.0, use_atr_filter=False)
    assert not fvgs.empty
    assert "bullish" in set(fvgs["direction"])


def test_analyze_structure_and_breakout_return_latest_context(breakout_stock_df) -> None:
    structure = analyze_structure(breakout_stock_df, left_bars=2, right_bars=2)
    breakout = analyze_breakout(breakout_stock_df, breakout_lookback=20, close_confirmation=True, buffer_pct=0.0)

    assert structure["latest_bias"] in {"bullish", "bearish", "neutral"}
    assert breakout["status"] in {
        "Bullish Breakout",
        "Bearish Breakdown",
        "Near Bullish Breakout",
        "Near Bearish Breakdown",
        "In Range",
    }


def test_screen_watchlist_returns_conviction_fields(breakout_stock_df) -> None:
    config = SMCAnalyzerConfig(
        timeframe="1d",
        history_period="1y",
        breakout_buffer_pct=0.0,
        min_fvg_size_pct=0.0,
        use_atr_gap_filter=False,
        fresh_fvg_only=False,
    )
    analysis = analyze_symbol("RELIANCE", breakout_stock_df, config)
    assert analysis.setup["symbol"] == "RELIANCE"

    results, analyses = screen_watchlist({"RELIANCE": breakout_stock_df}, config)
    assert "RELIANCE" in analyses
    if not results.empty:
        assert {"conviction_score", "conviction_tag", "latest_structure_event"}.issubset(results.columns)

from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.stock_alerter import data_loader
from app.stock_alerter.config import StockAlerterConfig
from app.stock_alerter.indicators import calculate_indicators
from app.stock_alerter.pattern_detectors import detect_major_swing_breakout, detect_range_breakout
from app.stock_alerter.scanner import scan_stock
from app.stock_alerter.structure_logic import detect_bos


def _config() -> StockAlerterConfig:
    return StockAlerterConfig(project_root=Path.cwd(), require_52week_high_module=False)


def test_calculate_indicators_adds_expected_columns(breakout_stock_df, benchmark_df) -> None:
    frame = calculate_indicators(breakout_stock_df, benchmark_df)
    assert {"ema20", "ema50", "rsi14", "adx14", "atr14", "relative_volume"}.issubset(frame.columns)


def test_detect_major_swing_breakout_and_bos(breakout_stock_df, benchmark_df) -> None:
    frame = calculate_indicators(breakout_stock_df, benchmark_df)
    pattern = detect_major_swing_breakout(frame, _config())
    bos = detect_bos(frame, _config())
    assert pattern["pattern_name"] == "Major swing high breakout"
    assert bos["pattern_name"] == "Bullish BOS"


def test_scan_stock_returns_structured_signal_rows(breakout_stock_df, benchmark_df) -> None:
    signals = scan_stock(
        breakout_stock_df,
        "RELIANCE",
        _config(),
        benchmark_df=benchmark_df,
        company_name="Reliance Industries",
    )
    assert isinstance(signals, list)
    if signals:
        signal = signals[0]
        assert {"symbol", "pattern_name", "score", "category", "reasoning"}.issubset(signal.keys())


def test_load_universe_symbols_keeps_nasdaq_tickers_unmodified(monkeypatch) -> None:
    config = _config()
    config.universe_name = "NASDAQ Top 250"
    monkeypatch.setattr(
        data_loader,
        "load_universe_frame",
        lambda _: pd.DataFrame({"Symbol": ["AAPL", "MSFT", "NVDA"]}),
    )

    assert data_loader.load_universe_symbols(config) == ["AAPL", "MSFT", "NVDA"]

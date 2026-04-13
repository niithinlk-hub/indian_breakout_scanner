from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import pandas as pd
import streamlit as st

from app.smc.config import TIMEFRAME_OPTIONS
from app.smc.utils import clamp_period, denormalize_nse_ticker, normalize_nse_ticker, unique_preserving_order

logging.getLogger("yfinance").setLevel(logging.CRITICAL)


@dataclass(slots=True)
class HistoryLoadResult:
    """Container for loaded history plus fetch diagnostics."""

    data: dict[str, pd.DataFrame]
    failures: dict[str, str]
    notices: list[str]


def _standardize_history(frame: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume", "symbol"])

    history = frame.reset_index().rename(
        columns={
            "Datetime": "datetime",
            "Date": "datetime",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        },
    )
    history["datetime"] = pd.to_datetime(history["datetime"], errors="coerce")
    for column in ["open", "high", "low", "close", "volume"]:
        history[column] = pd.to_numeric(history[column], errors="coerce")
    history["symbol"] = denormalize_nse_ticker(symbol)
    return history[["datetime", "open", "high", "low", "close", "volume", "symbol"]].dropna(
        subset=["datetime", "open", "high", "low", "close"],
    )


def _resample_history(frame: pd.DataFrame, rule: str) -> pd.DataFrame:
    if frame.empty:
        return frame

    indexed = frame.set_index(pd.to_datetime(frame["datetime"]))
    resampled = indexed.resample(
        rule,
        label="right",
        closed="right",
    ).agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
            "symbol": "last",
        },
    )
    return resampled.reset_index(names="datetime").dropna(subset=["open", "high", "low", "close"])


@st.cache_data(ttl=900, show_spinner=False)
def _download_history_cached(symbol: str, interval: str, period: str) -> pd.DataFrame:
    import yfinance as yf

    frame = yf.download(
        tickers=symbol,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False,
        group_by="column",
    )
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    return frame


def _friendly_failure_message(exc: Exception) -> str:
    message = str(exc).strip()
    lowered = message.lower()
    if "rate limit" in lowered or "too many requests" in lowered:
        return "Yahoo Finance rate limit hit. Wait a bit and try again."
    return message or exc.__class__.__name__


def load_symbol_history(symbol: str, timeframe: str, period: str) -> tuple[pd.DataFrame, list[str]]:
    """Load one symbol from Yahoo Finance with interval-aware period clamping."""

    normalized_symbol = normalize_nse_ticker(symbol)
    timeframe_meta = TIMEFRAME_OPTIONS[timeframe]
    effective_period, was_clamped = clamp_period(period, timeframe_meta["max_period"])
    notices: list[str] = []
    if was_clamped:
        notices.append(
            f"{denormalize_nse_ticker(normalized_symbol)}: Yahoo returned {timeframe} data using {effective_period} instead of {period}.",
        )

    try:
        raw = _download_history_cached(normalized_symbol, timeframe_meta["download_interval"], effective_period)
    except Exception as exc:
        raise RuntimeError(_friendly_failure_message(exc)) from exc
    history = _standardize_history(raw, normalized_symbol)
    if timeframe_meta["resample_rule"]:
        history = _resample_history(history, timeframe_meta["resample_rule"])
    return history.sort_values("datetime").reset_index(drop=True), notices


def load_watchlist_history(symbols: list[str], timeframe: str, period: str) -> HistoryLoadResult:
    """Load a set of symbols with per-symbol failure handling."""

    data: dict[str, pd.DataFrame] = {}
    failures: dict[str, str] = {}
    notices: list[str] = []
    for symbol in unique_preserving_order(symbols):
        try:
            history, symbol_notices = load_symbol_history(symbol, timeframe, period)
        except Exception as exc:
            failures[denormalize_nse_ticker(symbol)] = str(exc)
            continue

        notices.extend(symbol_notices)
        if history.empty:
            failures[denormalize_nse_ticker(symbol)] = "No data returned."
            continue
        data[denormalize_nse_ticker(symbol)] = history

    return HistoryLoadResult(data=data, failures=failures, notices=notices)


def parse_uploaded_csv(file: Any) -> pd.DataFrame:
    """Best-effort parse for uploaded watchlist CSVs."""

    if file is None:
        return pd.DataFrame()
    try:
        return pd.read_csv(file)
    except Exception:
        return pd.DataFrame()

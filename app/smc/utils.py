from __future__ import annotations

from typing import Iterable

import pandas as pd

from app.smc.config import PERIOD_ORDER


def normalize_nse_ticker(symbol: str) -> str:
    """Normalize a user-entered symbol into a Yahoo Finance NSE ticker."""

    cleaned = str(symbol).strip().upper()
    if not cleaned:
        return ""
    if cleaned.startswith("^") or "." in cleaned:
        return cleaned
    return f"{cleaned}.NS"


def denormalize_nse_ticker(symbol: str) -> str:
    """Strip the Yahoo Finance suffix for display."""

    cleaned = str(symbol).strip().upper()
    return cleaned[:-3] if cleaned.endswith(".NS") else cleaned


def parse_custom_tickers(raw: str) -> list[str]:
    """Parse comma-separated ticker input."""

    symbols = [normalize_nse_ticker(item) for item in str(raw).replace("\n", ",").split(",")]
    return [symbol for symbol in symbols if symbol]


def parse_uploaded_watchlist(frame: pd.DataFrame | None) -> list[str]:
    """Extract tickers from an uploaded CSV-like dataframe."""

    if frame is None or frame.empty:
        return []
    first_column = frame.columns[0]
    return [symbol for symbol in (normalize_nse_ticker(value) for value in frame[first_column].tolist()) if symbol]


def clamp_period(requested_period: str, max_period: str) -> tuple[str, bool]:
    """Clamp a requested Yahoo period to the interval-specific maximum."""

    requested = PERIOD_ORDER.get(requested_period, PERIOD_ORDER["5y"])
    maximum = PERIOD_ORDER.get(max_period, requested)
    if requested <= maximum:
        return requested_period, False
    for candidate, days in PERIOD_ORDER.items():
        if days == maximum:
            return candidate, True
    return max_period, True


def latest_valid_value(series: pd.Series) -> float | None:
    """Return the last non-null numeric value when available."""

    cleaned = pd.to_numeric(series, errors="coerce").dropna()
    if cleaned.empty:
        return None
    return float(cleaned.iloc[-1])


def as_percentage(distance: float | None, base: float | None) -> float | None:
    """Safely calculate percentage distance."""

    if distance is None or base in {None, 0}:
        return None
    return round((distance / base) * 100.0, 4)


def unique_preserving_order(symbols: Iterable[str]) -> list[str]:
    """Deduplicate while preserving input order."""

    seen: set[str] = set()
    ordered: list[str] = []
    for raw in symbols:
        symbol = normalize_nse_ticker(raw)
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        ordered.append(symbol)
    return ordered

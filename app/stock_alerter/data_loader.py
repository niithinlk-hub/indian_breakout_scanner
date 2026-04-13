from __future__ import annotations

import logging
import time
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st

from app.stock_alerter.config import StockAlerterConfig
from app.stock_alerter.utils import ensure_ohlcv_schema, normalize_symbol, parse_symbol_input, strip_exchange_suffix
from app.utils.logging import get_logger

LOGGER = get_logger(__name__)
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

_UNIVERSE_URLS = {
    "NIFTY 100": "https://archives.nseindia.com/content/indices/ind_nifty100list.csv",
    "NIFTY Midcap 150": "https://archives.nseindia.com/content/indices/ind_niftymidcap150list.csv",
    "NASDAQ Screener": "https://api.nasdaq.com/api/screener/stocks?tableonly=true&download=true&exchange=nasdaq&limit=5000&offset=0",
}
_BUNDLED_FALLBACKS = {
    "NIFTY LargeMidcap 250": "config/nifty_largemidcap250_fallback.csv",
    "NASDAQ Top 250": "config/nasdaq_top250_fallback.csv",
}


def _cache_path(config: StockAlerterConfig, universe_name: str) -> Path:
    slug = universe_name.lower().replace(" ", "_").replace("/", "_")
    return config.project_root / "data" / f"{slug}_universe_cache.csv"


def _bundled_fallback_path(config: StockAlerterConfig, universe_name: str) -> Path | None:
    relative = _BUNDLED_FALLBACKS.get(universe_name)
    if not relative:
        return None
    return config.project_root / relative


def _load_best_available_universe(config: StockAlerterConfig, universe_name: str) -> pd.DataFrame:
    cache_file = _cache_path(config, universe_name)
    if cache_file.exists():
        return pd.read_csv(cache_file)

    bundled = _bundled_fallback_path(config, universe_name)
    if bundled is not None and bundled.exists():
        return pd.read_csv(bundled)

    return pd.DataFrame(columns=["Company Name", "Industry", "Symbol", "Series", "ISIN Code"])


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def _fetch_universe_csv(url: str) -> pd.DataFrame:
    response = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    return pd.read_csv(StringIO(response.text))


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def _fetch_nasdaq_top250_frame() -> pd.DataFrame:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.nasdaq.com",
        "Referer": "https://www.nasdaq.com/market-activity/stocks/screener",
    }
    response = requests.get(_UNIVERSE_URLS["NASDAQ Screener"], headers=headers, timeout=45)
    response.raise_for_status()
    payload = response.json()
    rows = payload.get("data", {}).get("rows", [])
    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame(columns=["Symbol", "Company Name", "Sector", "Industry", "Market Cap", "Country"])

    frame["marketCap"] = pd.to_numeric(frame["marketCap"], errors="coerce").fillna(0.0)
    name_upper = frame["name"].fillna("").astype(str).str.upper()
    exclude_patterns = [" ETF", " FUND", " TRUST", " ACQUISITION", " WARRANT", " RIGHTS", " UNITS", "UNIT ", " PREFERRED", " DEPOSITARY", " ADR "]
    filtered = frame.loc[
        (frame["marketCap"] > 0)
        & (~name_upper.str.contains("|".join(exclude_patterns), regex=True))
    ].copy()
    filtered = filtered.sort_values("marketCap", ascending=False).head(250)
    return filtered.rename(
        columns={
            "symbol": "Symbol",
            "name": "Company Name",
            "sector": "Sector",
            "industry": "Industry",
            "marketCap": "Market Cap",
            "country": "Country",
        },
    )[["Symbol", "Company Name", "Sector", "Industry", "Market Cap", "Country"]]


def load_universe_frame(config: StockAlerterConfig) -> pd.DataFrame:
    """Load the selected universe as a dataframe with symbol metadata."""

    if config.universe_name == "Custom":
        symbols = [symbol for symbol in parse_symbol_input(config.custom_universe_text, default_suffix=None) if symbol][: config.max_symbols]
        return pd.DataFrame({"Symbol": [strip_exchange_suffix(symbol) for symbol in symbols], "Company Name": [strip_exchange_suffix(symbol) for symbol in symbols]})

    if config.universe_name == "NIFTY LargeMidcap 250":
        combined = _load_best_available_universe(config, config.universe_name)
        try:
            nifty100 = _fetch_universe_csv(_UNIVERSE_URLS["NIFTY 100"])
            midcap150 = _fetch_universe_csv(_UNIVERSE_URLS["NIFTY Midcap 150"])
            combined = pd.concat([nifty100, midcap150], ignore_index=True).drop_duplicates(subset=["Symbol"])
            combined.to_csv(_cache_path(config, config.universe_name), index=False)
        except Exception as exc:
            if combined.empty:
                LOGGER.warning("Universe live fetch failed for %s and no fallback was cached: %s", config.universe_name, exc)
        return combined.head(config.max_symbols).reset_index(drop=True)

    if config.universe_name == "NASDAQ Top 250":
        combined = _load_best_available_universe(config, config.universe_name)
        try:
            combined = _fetch_nasdaq_top250_frame()
            combined.to_csv(_cache_path(config, config.universe_name), index=False)
        except Exception as exc:
            if combined.empty:
                LOGGER.warning("Universe live fetch failed for %s and no fallback was cached: %s", config.universe_name, exc)
        return combined.head(config.max_symbols).reset_index(drop=True)

    raise ValueError(f"Unsupported universe: {config.universe_name}")


def load_universe_symbols(config: StockAlerterConfig) -> list[str]:
    """Load symbols for the selected universe with live fetch and local cache fallback."""

    frame = load_universe_frame(config)
    default_suffix = ".NS" if config.universe_name == "NIFTY LargeMidcap 250" else None
    symbols = [normalize_symbol(symbol, default_suffix) for symbol in frame.get("Symbol", pd.Series(dtype=str)).dropna().tolist()]
    return symbols[: config.max_symbols]


@st.cache_data(ttl=60 * 30, show_spinner=False)
def _download_batch(symbols: tuple[str, ...], period: str, interval: str) -> Any:
    import yfinance as yf

    return yf.download(
        tickers=list(symbols),
        period=period,
        interval=interval,
        group_by="ticker",
        auto_adjust=False,
        progress=False,
        threads=False,
    )


def _friendly_failure_message(exc: Exception) -> str:
    message = str(exc).strip()
    lowered = message.lower()
    if "rate limit" in lowered or "too many requests" in lowered:
        return "Yahoo Finance rate limit hit. Wait a bit and scan again."
    return message or exc.__class__.__name__


def fetch_universe_data(symbol_list: list[str], config: StockAlerterConfig) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    """Fetch OHLCV data for a symbol list with batch downloads and graceful failures."""

    data: dict[str, pd.DataFrame] = {}
    failures: dict[str, str] = {}
    if not symbol_list:
        return data, failures

    batch_size = 15
    for start in range(0, len(symbol_list), batch_size):
        batch = tuple(symbol_list[start : start + batch_size])
        try:
            downloaded = _download_batch(batch, config.period, config.timeframe)
        except Exception as exc:
            failure_message = _friendly_failure_message(exc)
            for symbol in batch:
                failures[strip_exchange_suffix(symbol)] = failure_message
            continue

        if not isinstance(downloaded, pd.DataFrame) or downloaded.empty:
            for symbol in batch:
                failures[strip_exchange_suffix(symbol)] = "No data returned."
            continue

        multi_symbol = isinstance(downloaded.columns, pd.MultiIndex)
        for symbol in batch:
            try:
                if multi_symbol:
                    if symbol not in downloaded.columns.get_level_values(0):
                        failures[strip_exchange_suffix(symbol)] = "Symbol missing from batch response."
                        continue
                    raw = downloaded[symbol]
                else:
                    raw = downloaded
                history = ensure_ohlcv_schema(raw, symbol)
                if history.empty:
                    failures[strip_exchange_suffix(symbol)] = "No valid OHLCV rows."
                else:
                    data[strip_exchange_suffix(symbol)] = history.sort_values("datetime").reset_index(drop=True)
            except Exception as exc:
                failures[strip_exchange_suffix(symbol)] = _friendly_failure_message(exc)
        if start + batch_size < len(symbol_list):
            time.sleep(0.5)
    return data, failures


def fetch_benchmark_data(config: StockAlerterConfig) -> pd.DataFrame:
    """Fetch benchmark data used for relative-strength comparison."""

    data, failures = fetch_universe_data([config.benchmark_symbol], config)
    if failures:
        LOGGER.warning("Benchmark fetch issue: %s", failures)
    return data.get(strip_exchange_suffix(config.benchmark_symbol), pd.DataFrame())

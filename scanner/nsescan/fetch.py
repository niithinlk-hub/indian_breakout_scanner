"""Yahoo Finance fetch: batched `yf.download` with retry and exponential backoff.

Same approach as niithinlk-hub/stock-pattern-screener (one threaded multi-ticker
`yf.download`, `group_by="ticker"`, `auto_adjust=True`), split into chunks of
`data.fetch_chunk_size` tickers. Tickers that come back empty or error are retried
in smaller chunks after 2s, 4s, 8s, 16s (`data.fetch_backoff_base_sec` doubling).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Sequence

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

OHLCV = ["open", "high", "low", "close", "volume"]
PRICE_DECIMALS = 4


@dataclass
class FetchResult:
    frames: dict[str, pd.DataFrame]  # ticker -> canonical OHLCV indexed by date
    failed: dict[str, str]  # ticker -> last error seen
    attempts: int
    elapsed_sec: float = 0.0
    retried: list[str] = field(default_factory=list)


def canonicalize(frame: pd.DataFrame) -> pd.DataFrame:
    """Lower-case OHLCV columns, date index, prices rounded to 4 dp, volume as nullable int.

    Rows without a complete OHLC are dropped (volume may be null; QA flags it).
    Rounding happens once, here, so every downstream computation (live scan, backtest,
    re-verification from stored prices) sees identical numbers.
    """

    if frame is None or frame.empty:
        return pd.DataFrame(columns=OHLCV, index=pd.DatetimeIndex([], name="date"))
    renamed = frame.rename(columns={col: str(col).strip().lower() for col in frame.columns})
    missing = [col for col in OHLCV if col not in renamed.columns]
    if missing:
        raise ValueError(f"missing columns {missing}")
    out = renamed[OHLCV].copy()
    index = pd.DatetimeIndex(out.index)
    if index.tz is not None:
        index = index.tz_localize(None)
    out.index = index.normalize().rename("date")
    out = out.loc[~out.index.duplicated(keep="last")].sort_index()
    out = out.dropna(subset=["open", "high", "low", "close"])
    out[["open", "high", "low", "close"]] = out[["open", "high", "low", "close"]].astype(float).round(PRICE_DECIMALS)
    out["volume"] = pd.array(np.round(out["volume"].astype(float)), dtype="Int64")
    return out


def split_download(raw: pd.DataFrame | None, tickers: Sequence[str]) -> dict[str, pd.DataFrame]:
    """Split a `yf.download(group_by="ticker")` frame into per-ticker canonical frames."""

    if raw is None or raw.empty:
        return {}
    frames: dict[str, pd.DataFrame] = {}
    if isinstance(raw.columns, pd.MultiIndex):
        level0 = set(raw.columns.get_level_values(0))
        level1 = set(raw.columns.get_level_values(1))
        for ticker in tickers:
            if ticker in level0:
                sub = raw[ticker]
            elif ticker in level1:
                sub = raw.xs(ticker, axis=1, level=1)
            else:
                continue
            sub = sub.dropna(how="all")
            if not sub.empty:
                frames[ticker] = canonicalize(sub)
    elif len(tickers) == 1:
        sub = raw.dropna(how="all")
        if not sub.empty:
            frames[tickers[0]] = canonicalize(sub)
    return {ticker: frame for ticker, frame in frames.items() if not frame.empty}


def _chunks(items: Sequence[str], size: int) -> Iterable[list[str]]:
    for start in range(0, len(items), size):
        yield list(items[start : start + size])


def _yf_download(tickers: list[str], **kwargs: Any) -> tuple[pd.DataFrame | None, dict[str, str]]:
    import yfinance as yf
    import yfinance.shared as yf_shared

    raw = yf.download(tickers, **kwargs)
    errors = {str(key): str(value) for key, value in getattr(yf_shared, "_ERRORS", {}).items()}
    return raw, errors


def download_ohlcv(
    tickers: Sequence[str],
    *,
    start: str | None = None,
    end: str | None = None,
    period: str | None = None,
    chunk_size: int = 100,
    max_retries: int = 4,
    backoff_base: float = 2.0,
    threads: bool = True,
    timeout: int = 30,
    downloader: Callable[..., tuple[pd.DataFrame | None, dict[str, str]]] = _yf_download,
    sleep: Callable[[float], None] = time.sleep,
) -> FetchResult:
    """Download daily OHLCV (auto-adjusted) for many tickers.

    `end` is exclusive (yfinance convention). Pass either start/end or period.
    """

    started = time.monotonic()
    pending = list(dict.fromkeys(tickers))
    frames: dict[str, pd.DataFrame] = {}
    last_error: dict[str, str] = {}
    retried: list[str] = []
    kwargs: dict[str, Any] = {
        "interval": "1d",
        "auto_adjust": True,
        "group_by": "ticker",
        "threads": threads,
        "progress": False,
        "timeout": timeout,
    }
    if period:
        kwargs["period"] = period
    else:
        kwargs["start"], kwargs["end"] = start, end

    attempt = 0
    for attempt in range(max_retries + 1):
        if not pending:
            break
        if attempt:
            delay = backoff_base * 2 ** (attempt - 1)
            LOGGER.info("retry %d for %d tickers after %.0fs", attempt, len(pending), delay)
            retried.extend(t for t in pending if t not in retried)
            sleep(delay)
        size = max(1, chunk_size // (2**attempt))
        next_pending: list[str] = []
        for chunk in _chunks(pending, size):
            try:
                raw, errors = downloader(chunk, **kwargs)
            except Exception as exc:  # network / rate limit: whole chunk retried
                for ticker in chunk:
                    last_error[ticker] = f"{type(exc).__name__}: {str(exc)[:200]}"
                next_pending.extend(chunk)
                continue
            got = split_download(raw, chunk)
            for ticker in chunk:
                if ticker in got:
                    frames[ticker] = got[ticker]
                    last_error.pop(ticker, None)
                else:
                    last_error[ticker] = errors.get(ticker, "empty response")
                    next_pending.append(ticker)
        pending = next_pending

    return FetchResult(
        frames=frames,
        failed={ticker: last_error.get(ticker, "unknown") for ticker in pending},
        attempts=attempt + 1,
        elapsed_sec=time.monotonic() - started,
        retried=retried,
    )


def frames_to_long(frames: dict[str, pd.DataFrame], ticker_to_symbol: dict[str, str]) -> pd.DataFrame:
    """Per-ticker frames -> long `prices_daily` rows (symbol, date, open, high, low, close, volume)."""

    parts = []
    for ticker, frame in frames.items():
        if frame.empty:
            continue
        part = frame.reset_index()
        part.insert(0, "symbol", ticker_to_symbol.get(ticker, ticker))
        parts.append(part)
    if not parts:
        return pd.DataFrame(columns=["symbol", "date", *OHLCV])
    long = pd.concat(parts, ignore_index=True)
    long["date"] = pd.to_datetime(long["date"]).dt.normalize()
    return long[["symbol", "date", *OHLCV]]

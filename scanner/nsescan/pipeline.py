"""Data pipeline: full-history load, incremental update, benchmarks."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from .config import Config
from .fetch import FetchResult, download_ohlcv, frames_to_long

LOGGER = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


@dataclass
class LoadSummary:
    kind: str
    started_at: str
    finished_at: str = ""
    requested: dict[str, int] = field(default_factory=dict)  # per segment
    ok: dict[str, int] = field(default_factory=dict)
    failed: dict[str, dict[str, str]] = field(default_factory=dict)  # segment -> {symbol: reason}
    rows_written: int = 0
    refetched_full: list[str] = field(default_factory=list)
    elapsed_sec: float = 0.0
    notes: dict[str, Any] = field(default_factory=dict)

    def record(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "tickers_ok": int(sum(self.ok.values())),
            "tickers_failed": int(sum(len(v) for v in self.failed.values())),
            "notes": {
                "requested": self.requested,
                "ok": self.ok,
                "failed": self.failed,
                "rows_written": self.rows_written,
                "refetched_full": self.refetched_full,
                "elapsed_sec": round(self.elapsed_sec, 1),
                **self.notes,
            },
        }


def now_ist() -> datetime:
    return datetime.now(IST)


def last_complete_session_end(now: datetime | None, cutoff_hour: int) -> pd.Timestamp:
    """Exclusive end date for yf.download so a still-forming bar for today is never stored."""

    now = now or now_ist()
    today = pd.Timestamp(now.date())
    return today + timedelta(days=1) if now.hour >= cutoff_hour else today


def _summarize(kind: str, started: datetime, universe: pd.DataFrame, result: FetchResult) -> LoadSummary:
    summary = LoadSummary(kind=kind, started_at=started.isoformat())
    by_ticker = universe.set_index("yahoo_ticker")
    for segment, group in universe.groupby("segment"):
        tickers = set(group["yahoo_ticker"])
        summary.requested[segment] = len(tickers)
        summary.ok[segment] = len(tickers & set(result.frames))
        summary.failed[segment] = {
            by_ticker.at[t, "symbol"]: reason for t, reason in result.failed.items() if t in tickers
        }
    summary.elapsed_sec = result.elapsed_sec
    summary.notes["attempts"] = result.attempts
    summary.notes["retried"] = len(result.retried)
    return summary


def load_history(store: Any, cfg: Config, *, symbols: list[str] | None = None, now: datetime | None = None) -> LoadSummary:
    """Fetch `data.history_years` of daily bars for the universe (or `symbols`) and replace their history."""

    started = now_ist()
    universe = store.read_universe()
    if symbols is not None:
        universe = universe.loc[universe["symbol"].isin(symbols)]
    end = last_complete_session_end(now, int(cfg["data.eod_cutoff_hour_ist"]))
    start = end - pd.DateOffset(years=int(cfg["data.history_years"])) - pd.Timedelta(days=1)
    result = download_ohlcv(
        universe["yahoo_ticker"].tolist(),
        start=start.date().isoformat(),
        end=end.date().isoformat(),
        chunk_size=int(cfg["data.fetch_chunk_size"]),
        max_retries=int(cfg["data.fetch_max_retries"]),
        backoff_base=float(cfg["data.fetch_backoff_base_sec"]),
    )
    ticker_to_symbol = dict(zip(universe["yahoo_ticker"], universe["symbol"]))
    rows = frames_to_long(result.frames, ticker_to_symbol)
    fetched_symbols = sorted(rows["symbol"].unique().tolist())
    store.upsert_prices(rows, replace_symbols=fetched_symbols)
    summary = _summarize("history", started, universe, result)
    summary.rows_written = len(rows)
    summary.notes["window"] = [start.date().isoformat(), (end - pd.Timedelta(days=1)).date().isoformat()]
    summary.finished_at = now_ist().isoformat()
    return summary


def material_changes(fresh: pd.DataFrame, stored: pd.DataFrame, tolerance: float) -> pd.DataFrame:
    """Rows of `fresh` that are new, or differ from the stored bar beyond `tolerance` / in volume."""

    merged = fresh.merge(stored, on=["symbol", "date"], how="left", suffixes=("", "_stored"), indicator=True)
    changed = merged["_merge"].eq("left_only").to_numpy()
    for col in ("open", "high", "low", "close"):
        rel = (merged[col] / merged[f"{col}_stored"] - 1.0).abs()
        changed |= rel.gt(tolerance).fillna(False).to_numpy()
    volume, stored_volume = merged["volume"].astype("Float64"), merged["volume_stored"].astype("Float64")
    changed |= (volume.ne(stored_volume) & ~(volume.isna() & stored_volume.isna())).fillna(True).to_numpy()
    return fresh.loc[changed]


def update_prices(store: Any, cfg: Config, *, now: datetime | None = None) -> LoadSummary:
    """Incremental update: re-fetch the last `data.update_overlap_sessions` plus new bars.

    If the median |relative difference| between re-fetched and stored closes (newest
    stored bar excluded, since Yahoo may still revise it) exceeds
    `data.adjustment_tolerance`, Yahoo has re-adjusted the series (split, bonus,
    dividend): that symbol's full history is re-fetched and replaced. Otherwise only
    new bars and material revisions (`data.revision_tolerance`) are written. Symbols
    with no stored history, or none in the last `data.stale_refetch_days` days, get the
    full load.
    """

    started = now_ist()
    universe = store.read_universe()
    end = last_complete_session_end(now, int(cfg["data.eod_cutoff_hour_ist"]))
    last_dates = store.last_price_dates()
    fresh_enough = last_dates.index[last_dates >= end - pd.Timedelta(days=int(cfg["data.stale_refetch_days"]))]
    have = universe.loc[universe["symbol"].isin(fresh_enough)]
    new = universe.loc[~universe["symbol"].isin(fresh_enough), "symbol"].tolist()
    overlap = int(cfg["data.update_overlap_sessions"])
    # calendar days covering the overlap sessions (weekends + holidays), from the oldest last bar
    oldest = last_dates.loc[have["symbol"]].min() if len(have) else end
    start = min(oldest, end - pd.Timedelta(days=1)) - pd.Timedelta(days=int(np.ceil(overlap * 7 / 5)) + 7)
    result = download_ohlcv(
        have["yahoo_ticker"].tolist(),
        start=start.date().isoformat(),
        end=end.date().isoformat(),
        chunk_size=int(cfg["data.fetch_chunk_size"]),
        max_retries=int(cfg["data.fetch_max_retries"]),
        backoff_base=float(cfg["data.fetch_backoff_base_sec"]),
    )
    ticker_to_symbol = dict(zip(universe["yahoo_ticker"], universe["symbol"]))
    fresh = frames_to_long(result.frames, ticker_to_symbol)
    stored = store.read_prices(symbols=fresh["symbol"].unique().tolist(), start=start.date().isoformat())
    merged = fresh.merge(stored[["symbol", "date", "close"]], on=["symbol", "date"], suffixes=("", "_stored"))
    # the newest stored bar may legitimately be revised (official close); judge re-adjustment on older bars
    merged = merged.loc[merged["date"] < merged["symbol"].map(last_dates)]
    merged["rel"] = (merged["close"] / merged["close_stored"] - 1.0).abs()
    median_rel = merged.groupby("symbol")["rel"].median()
    readjusted = sorted(median_rel.index[median_rel > float(cfg["data.adjustment_tolerance"])].tolist())
    keep = material_changes(fresh.loc[~fresh["symbol"].isin(readjusted)], stored,
                            float(cfg["data.revision_tolerance"]))
    written = store.upsert_prices(keep) if len(keep) else 0
    summary = _summarize("update", started, have, result)
    summary.rows_written = written
    existing = keep.set_index(["symbol", "date"]).index.isin(stored.set_index(["symbol", "date"]).index)
    summary.notes["revised_bars"] = int(existing.sum())
    summary.notes["new_bars"] = int((~existing).sum())
    refetch = sorted(set(readjusted) | set(new))
    if refetch:
        LOGGER.info("full-history refetch for %d symbols (re-adjusted: %s; new: %s)", len(refetch), readjusted, new)
        full = load_history(store, cfg, symbols=refetch, now=now)
        summary.rows_written += full.rows_written
        for segment, failures in full.failed.items():
            summary.failed.setdefault(segment, {}).update(failures)
    summary.refetched_full = refetch
    summary.notes["readjusted"] = readjusted
    summary.notes["new_symbols"] = new
    summary.finished_at = now_ist().isoformat()
    return summary


def load_benchmarks(store: Any, cfg: Config, *, now: datetime | None = None, full: bool = True) -> dict[str, dict[str, Any]]:
    """Fetch benchmark closes; returns a verification record per benchmark."""

    end = last_complete_session_end(now, int(cfg["data.eod_cutoff_hour_ist"]))
    years = int(cfg["data.history_years"]) if full else 1
    start = end - pd.DateOffset(years=years) - pd.Timedelta(days=1)
    tickers = list(cfg["data.benchmarks"].values())
    result = download_ohlcv(
        tickers,
        start=start.date().isoformat(),
        end=end.date().isoformat(),
        chunk_size=len(tickers),
        max_retries=int(cfg["data.fetch_max_retries"]),
        backoff_base=float(cfg["data.fetch_backoff_base_sec"]),
    )
    verification: dict[str, dict[str, Any]] = {}
    parts = []
    for name, ticker in cfg["data.benchmarks"].items():
        frame = result.frames.get(ticker)
        if frame is None or frame.empty:
            verification[name] = {"ticker": ticker, "ok": False, "error": result.failed.get(ticker, "empty")}
            continue
        parts.append(pd.DataFrame({"ticker": ticker, "date": frame.index, "close": frame["close"].to_numpy()}))
        verification[name] = {
            "ticker": ticker,
            "ok": True,
            "bars": int(len(frame)),
            "first": frame.index.min().date().isoformat(),
            "last": frame.index.max().date().isoformat(),
        }
    if parts:
        store.upsert_benchmarks(pd.concat(parts, ignore_index=True))
    return verification

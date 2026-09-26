"""Universe: Nifty 500 + Nifty Microcap 250 constituents from NSE's published CSVs.

NSE serves the same files from several hosts, and each host intermittently answers
403 to the same request, so every URL is tried in turn over a few rounds. Each
successful download is saved under `universe_snapshots/<segment>/<date>.csv`; if every
host fails, the newest snapshot is used and the result says so.
"""

from __future__ import annotations

import io
import logging
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable

import pandas as pd
import requests

LOGGER = logging.getLogger(__name__)

SOURCE_URLS: dict[str, list[str]] = {
    "N500": [
        "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
        "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv",
        "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",
    ],
    "MICRO250": [
        "https://nsearchives.nseindia.com/content/indices/ind_niftymicrocap250_list.csv",
        "https://archives.nseindia.com/content/indices/ind_niftymicrocap250_list.csv",
        "https://www.niftyindices.com/IndexConstituent/ind_niftymicrocap250_list.csv",
    ],
}
# Row-count sanity bounds: the lists carry a few extra rows around demergers.
EXPECTED_ROWS: dict[str, tuple[int, int]] = {"N500": (480, 530), "MICRO250": (235, 275)}
REQUIRED_COLUMNS = ["Company Name", "Industry", "Symbol", "Series", "ISIN Code"]
SEGMENT_PRIORITY = ("N500", "MICRO250")  # a symbol listed in both keeps the first
# NSE lists a demerged entity as a placeholder ("DUMMYxxx") until it trades; Yahoo has no data for it.
PLACEHOLDER_PREFIX = "DUMMY"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/csv,text/plain,*/*",
    "Referer": "https://www.nseindia.com/",
}


@dataclass
class UniverseLoad:
    frame: pd.DataFrame
    sources: dict[str, str]  # segment -> URL or snapshot path used
    from_snapshot: dict[str, bool]
    duplicates: list[str] = field(default_factory=list)
    placeholders: dict[str, list[str]] = field(default_factory=dict)  # segment -> excluded DUMMY symbols


def parse_constituents(text: str, segment: str) -> pd.DataFrame:
    """Parse and validate one NSE constituent CSV."""

    frame = pd.read_csv(io.StringIO(text))
    frame.columns = [str(col).strip().lstrip("﻿") for col in frame.columns]
    missing = [col for col in REQUIRED_COLUMNS if col not in frame.columns]
    if missing:
        raise ValueError(f"{segment}: CSV missing columns {missing}")
    frame = frame[REQUIRED_COLUMNS].copy()
    for col in REQUIRED_COLUMNS:
        frame[col] = frame[col].astype(str).str.strip()
    frame = frame.loc[frame["Symbol"].ne("") & frame["Symbol"].ne("nan")]
    low, high = EXPECTED_ROWS[segment]
    if not low <= len(frame) <= high:
        raise ValueError(f"{segment}: {len(frame)} rows outside expected range {low}-{high}")
    return frame


def fetch_segment(
    segment: str,
    *,
    rounds: int = 3,
    pause_sec: float = 2.0,
    get: Callable[..., requests.Response] = requests.get,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[str, str]:
    """Return (csv_text, url) for a segment, trying every mirror each round."""

    errors: list[str] = []
    for round_no in range(rounds):
        if round_no:
            sleep(pause_sec * 2 ** (round_no - 1))
        for url in SOURCE_URLS[segment]:
            try:
                response = get(url, headers=HEADERS, timeout=30)
            except requests.RequestException as exc:
                errors.append(f"{url}: {type(exc).__name__}")
                continue
            if response.status_code != 200:
                errors.append(f"{url}: HTTP {response.status_code}")
                continue
            try:
                parse_constituents(response.text, segment)
            except ValueError as exc:
                errors.append(f"{url}: {exc}")
                continue
            return response.text, url
    raise RuntimeError(f"{segment}: all constituent sources failed: {errors[-6:]}")


def latest_snapshot(snapshot_dir: Path, segment: str) -> Path | None:
    files = sorted((snapshot_dir / segment).glob("*.csv"))
    return files[-1] if files else None


def combine(frames: dict[str, pd.DataFrame], added_at: str) -> tuple[pd.DataFrame, list[str]]:
    """Stack segments into the `universe` schema, deduping on symbol by segment priority."""

    parts = []
    for segment in SEGMENT_PRIORITY:
        if segment not in frames:
            continue
        part = frames[segment].rename(
            columns={
                "Company Name": "company",
                "Industry": "industry",
                "Symbol": "symbol",
                "Series": "series",
                "ISIN Code": "isin",
            }
        )
        part["segment"] = segment
        parts.append(part)
    stacked = pd.concat(parts, ignore_index=True)
    duplicated = stacked.loc[stacked["symbol"].duplicated(keep="first"), "symbol"].tolist()
    universe = stacked.drop_duplicates(subset="symbol", keep="first").copy()
    universe["yahoo_ticker"] = universe["symbol"] + ".NS"
    universe["active"] = True
    universe["added_at"] = added_at
    columns = ["symbol", "yahoo_ticker", "company", "industry", "segment", "series", "isin", "active", "added_at"]
    return universe[columns].sort_values(["segment", "symbol"]).reset_index(drop=True), duplicated


def load_universe(snapshot_dir: Path, *, refresh: bool = True, today: date | None = None) -> UniverseLoad:
    """Fetch (or fall back to snapshots for) both segments and build the universe table."""

    today = today or date.today()
    frames: dict[str, pd.DataFrame] = {}
    sources: dict[str, str] = {}
    from_snapshot: dict[str, bool] = {}
    for segment in SEGMENT_PRIORITY:
        text: str | None = None
        if refresh:
            try:
                text, url = fetch_segment(segment)
                target = snapshot_dir / segment / f"{today.isoformat()}.csv"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
                sources[segment], from_snapshot[segment] = url, False
            except RuntimeError as exc:
                LOGGER.warning("%s; falling back to the latest snapshot", exc)
        if text is None:
            snapshot = latest_snapshot(snapshot_dir, segment)
            if snapshot is None:
                raise RuntimeError(f"{segment}: no live source and no snapshot available")
            text = snapshot.read_text(encoding="utf-8")
            sources[segment], from_snapshot[segment] = str(snapshot), True
        frames[segment] = parse_constituents(text, segment)
    placeholders: dict[str, list[str]] = {}
    for segment, frame in frames.items():
        is_placeholder = frame["Symbol"].str.upper().str.startswith(PLACEHOLDER_PREFIX)
        placeholders[segment] = sorted(frame.loc[is_placeholder, "Symbol"].tolist())
        frames[segment] = frame.loc[~is_placeholder]
    universe, duplicates = combine(frames, added_at=today.isoformat())
    if duplicates:
        LOGGER.warning("Symbols in more than one segment (kept %s): %s", SEGMENT_PRIORITY[0], duplicates)
    return UniverseLoad(
        frame=universe, sources=sources, from_snapshot=from_snapshot, duplicates=duplicates, placeholders=placeholders
    )

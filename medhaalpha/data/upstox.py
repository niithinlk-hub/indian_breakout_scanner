"""Upstox V3 historical candle downloader (public endpoint, corporate-action adjusted).

Upstox serves history keyed by the *current* ISIN and back-adjusts prices for
splits/bonuses (verified on BAJFINANCE's June-2025 1:2 split + 4:1 bonus).
Intraday minute candles are limited to one calendar month per request.

Usage:
  python -m medhaalpha.data.upstox --symbols-file data/medhaalpha/universe_symbols.txt \
      --intervals days,minutes5,minutes3 --start 2024-09-01 --end 2026-11-13
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import gzip
import json
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests

from medhaalpha.paths import CANDLE_DIR, RAW_DIR

BASE = "https://api.upstox.com/v3/historical-candle/{key}/{unit}/{n}/{to}/{frm}"
INSTRUMENTS_URL = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
INTERVALS = {"days": ("days", 1), "minutes5": ("minutes", 5), "minutes3": ("minutes", 3), "minutes15": ("minutes", 15)}
INDEX_KEYS = {"NIFTY50": "NSE_INDEX|Nifty 50", "NIFTYBANK": "NSE_INDEX|Nifty Bank"}

_session = requests.Session()
_session.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "application/json"})


def load_instruments() -> pd.DataFrame:
    path = RAW_DIR / "upstox_NSE.json.gz"
    if not path.exists() or time.time() - path.stat().st_mtime > 86400 * 3:
        r = _session.get(INSTRUMENTS_URL, timeout=120)
        r.raise_for_status()
        path.write_bytes(r.content)
    with gzip.open(path, "rt") as fh:
        rows = json.load(fh)
    return pd.DataFrame(rows)


def equity_keys() -> dict[str, str]:
    inst = load_instruments()
    eq = inst[(inst["segment"] == "NSE_EQ") & (inst["instrument_type"].isin(["EQ", "BE"]))]
    return dict(zip(eq["trading_symbol"], eq["instrument_key"]))


def _get(url: str, retries: int = 6) -> list:
    for attempt in range(retries):
        try:
            r = _session.get(url, timeout=60)
            if r.status_code == 200:
                return r.json().get("data", {}).get("candles", [])
            if r.status_code in (400, 404):
                return []
            if r.status_code == 429:
                time.sleep(3 * (attempt + 1))
                continue
        except (requests.RequestException, ValueError):
            pass
        time.sleep(1.0 * (attempt + 1))
    raise RuntimeError(f"failed: {url}")


def _month_chunks(start: date, end: date) -> list[tuple[date, date]]:
    chunks = []
    cur = start
    while cur <= end:
        nxt = (cur.replace(day=1) + timedelta(days=32)).replace(day=1)
        chunks.append((cur, min(end, nxt - timedelta(days=1))))
        cur = nxt
    return chunks


def fetch_symbol(symbol: str, key: str, interval: str, start: date, end: date) -> int:
    out = CANDLE_DIR / interval / f"{symbol}.parquet"
    if out.exists():
        return -1
    unit, n = INTERVALS[interval]
    enc = quote(key, safe="")
    rows: list = []
    if unit == "days":
        rows = _get(BASE.format(key=enc, unit=unit, n=n, to=end.isoformat(), frm=start.isoformat()))
    else:
        for a, b in _month_chunks(start, end):
            rows.extend(_get(BASE.format(key=enc, unit=unit, n=n, to=b.isoformat(), frm=a.isoformat())))
    if not rows:
        return 0
    df = pd.DataFrame(rows).iloc[:, :6]
    df.columns = ["datetime", "open", "high", "low", "close", "volume"]
    df["datetime"] = pd.to_datetime(df["datetime"]).dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    df = df.drop_duplicates("datetime").sort_values("datetime").reset_index(drop=True)
    for c in ("open", "high", "low", "close"):
        df[c] = df[c].astype("float64")
    df["volume"] = df["volume"].astype("float64")
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    return len(df)


def resolve_symbols(symbols: list[str]) -> pd.DataFrame:
    """Map bhavcopy symbols to Upstox keys via ISIN (handles renames like ZOMATO->ETERNAL).

    Returns a frame with columns: symbol (bhavcopy name), canonical (file name), key.
    """
    inst = load_instruments()
    eq = inst[inst["segment"] == "NSE_EQ"]
    isin2key = dict(zip(eq["isin"], eq["instrument_key"]))
    key2sym = dict(zip(eq["instrument_key"], eq["trading_symbol"]))
    sym2key = dict(zip(eq["trading_symbol"], eq["instrument_key"]))
    fallback = _isin_fallback()
    rows = []
    for s in symbols:
        if s in INDEX_KEYS:
            rows.append((s, s, INDEX_KEYS[s]))
            continue
        isin = fallback.get(s)
        key = isin2key.get(isin) or sym2key.get(s)
        if key:
            rows.append((s, key2sym.get(key, s), key))
        elif isin:
            rows.append((s, s, f"NSE_EQ|{isin}"))
    frame = pd.DataFrame(rows, columns=["symbol", "canonical", "key"])
    from medhaalpha.paths import DATA_DIR

    frame.to_csv(DATA_DIR / "symbol_map.csv", index=False)
    return frame


def run(symbols: list[str], intervals: list[str], start: date, end: date, daily_start: date, workers: int) -> None:
    mapping = resolve_symbols(symbols)
    resolved = dict(zip(mapping["canonical"], mapping["key"]))
    print(f"resolved {len(mapping)} symbols -> {len(resolved)} unique instruments")
    for interval in intervals:
        s0 = daily_start if interval == "days" else start
        t0 = time.time()
        with cf.ThreadPoolExecutor(workers) as ex:
            futs = {ex.submit(fetch_symbol, s, k, interval, s0, end): s for s, k in resolved.items()}
            empty = []
            for f in cf.as_completed(futs):
                try:
                    if f.result() == 0:
                        empty.append(futs[f])
                except Exception as exc:  # noqa: BLE001
                    print("ERR", futs[f], exc)
        print(f"{interval}: done in {time.time() - t0:.0f}s, empty={empty}")


def _isin_fallback() -> dict[str, str]:
    """Latest ISIN per symbol from the cash bhavcopies (covers since-delisted names)."""
    from medhaalpha.paths import BHAV_DIR

    path = BHAV_DIR / "cm_all.parquet"
    if not path.exists():
        return {}
    cm = pd.read_parquet(path, columns=["date", "symbol", "isin"]).sort_values("date")
    return cm.drop_duplicates("symbol", keep="last").set_index("symbol")["isin"].to_dict()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--symbols-file", required=True)
    p.add_argument("--intervals", default="days,minutes5")
    p.add_argument("--start", default="2024-09-01")
    p.add_argument("--daily-start", default="2023-01-01")
    p.add_argument("--end", default="2026-11-13")
    p.add_argument("--workers", type=int, default=6)
    a = p.parse_args()
    syms = [s.strip() for s in Path(a.symbols_file).read_text().split() if s.strip()]
    run(syms, a.intervals.split(","), date.fromisoformat(a.start), date.fromisoformat(a.end),
        date.fromisoformat(a.daily_start), a.workers)

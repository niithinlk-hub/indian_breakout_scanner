"""Historical quarterly-results dates (Yahoo Finance earnings calendar) for the positional
engine's earnings blackout. Indian listed companies must pre-announce results board meetings
(SEBI LODR Reg. 29), so these dates are known before the session in which they occur.

Usage: python -m medhaalpha.data.earnings
"""
from __future__ import annotations

import time

import pandas as pd
import requests

from medhaalpha.data import loader
from medhaalpha.paths import RAW_DIR

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def _session() -> tuple[requests.Session, str]:
    for attempt in range(10):
        s = requests.Session()
        s.headers["User-Agent"] = UA
        try:
            s.get("https://fc.yahoo.com", timeout=20)
            crumb = s.get("https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=20).text.strip()
        except requests.RequestException:
            crumb = ""
        if crumb and " " not in crumb and len(crumb) < 20:
            return s, crumb
        time.sleep(3 * (attempt + 1))
    raise RuntimeError("could not obtain a Yahoo crumb")


def fetch(symbol: str, s: requests.Session, crumb: str) -> tuple[list[dict], int]:
    """Returns (rows, http_status)."""
    body = {
        "size": 100,
        "query": {"operator": "and", "operands": [
            {"operator": "eq", "operands": ["ticker", f"{symbol}.NS"]},
            {"operator": "eq", "operands": ["eventtype", "2"]}]},
        "sortField": "startdatetime", "sortType": "DESC", "entityIdType": "earnings",
        "includeFields": ["startdatetime", "timeZoneShortName"],
    }
    try:
        r = s.post(f"https://query1.finance.yahoo.com/v1/finance/visualization?crumb={crumb}&lang=en-US&region=US",
                   json=body, timeout=30)
    except requests.RequestException:
        return [], 0
    if r.status_code != 200:
        return [], r.status_code
    try:
        res = r.json()["finance"]["result"]
        docs = res[0].get("documents", []) if res else []
        if not docs:
            return [], 200
        cols = [c.get("id") or c.get("field") for c in docs[0]["columns"]]
        return [dict(zip(cols, row), symbol=symbol) for row in docs[0]["rows"]], 200
    except (ValueError, KeyError, IndexError):
        return [], 200


def run() -> pd.DataFrame:
    s, crumb = _session()
    syms = loader.canonical_symbols()
    parts, missing = [], []
    for i, sym in enumerate(syms):
        rows, status = [], 0
        for attempt in range(4):
            rows, status = fetch(sym, s, crumb)
            if status == 200:
                break
            if status in (401, 403):
                s, crumb = _session()
            else:
                time.sleep(2 * (attempt + 1))
        if not rows:
            missing.append(sym)
        parts.append(rows)
        if i % 25 == 0:
            print(i, sym, status, len(rows), flush=True)
        time.sleep(0.25)
    df = pd.DataFrame([r for p in parts for r in p])
    if not df.empty:
        ts = pd.to_datetime(df["startdatetime"], utc=True).dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
        df["date"] = ts.dt.normalize()
        df = df[["symbol", "date"]].drop_duplicates()
    df.to_parquet(RAW_DIR / "earnings_dates.parquet", index=False)
    print(len(df), "rows;", df["symbol"].nunique() if not df.empty else 0, "symbols; missing:", missing, flush=True)
    return df


def load() -> pd.DataFrame:
    p = RAW_DIR / "earnings_dates.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame(columns=["symbol", "date"])


def blackout_windows(end_quarter: str = "2026Q4", hold_days: int = 7, proj_before: int = 7,
                     proj_after: int = 14) -> pd.DataFrame:
    """Entry-date windows in which a new positional trade is not opened, per symbol.

    * Actual results dates (Yahoo; coverage ends around mid-2025): block entries on [date - hold_days, date].
    * Later quarters: results date projected as the same quarter one (or two) years earlier + 52 weeks
      (median absolute error 4 days, 80% within 8 days on 2024->2025), blocked on
      [projected - proj_after, projected + proj_before] to absorb that uncertainty.
    Only information available more than a year in advance is used for projections.
    """
    e = load()
    if e.empty:
        return pd.DataFrame(columns=["symbol", "start", "end", "kind"])
    e = e[e["date"] >= "2023-04-01"].copy()
    e["q"] = e["date"].dt.to_period("Q")
    rows = []
    last_q = pd.Period(end_quarter)
    for sym, g in e.groupby("symbol"):
        known = dict(zip(g["q"], g["date"]))
        for q, d in known.items():
            rows.append((sym, d - pd.Timedelta(days=hold_days), d, "actual"))
        q = max(known) + 1
        while q <= last_q:
            base = None
            for k in (1, 2, 3):
                if (q - 4 * k) in known:
                    base = known[q - 4 * k] + pd.Timedelta(days=364 * k)
                    break
            if base is not None:
                rows.append((sym, base - pd.Timedelta(days=proj_after), base + pd.Timedelta(days=proj_before), "projected"))
            q += 1
    return pd.DataFrame(rows, columns=["symbol", "start", "end", "kind"])


if __name__ == "__main__":
    run()

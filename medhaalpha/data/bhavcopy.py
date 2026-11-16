"""Download and parse NSE UDiFF bhavcopies (F&O and cash market).

These files are the point-in-time source of truth for:
* which stocks had listed derivatives on each day (F&O eligibility),
* option contract prices / OI / volume / lot size (for the options module),
* daily traded value and ISIN per equity (liquidity filter, instrument keys).

Usage:  python -m medhaalpha.data.bhavcopy --start 2024-10-01 --end 2026-11-13
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import io
import time
import zipfile
from datetime import date, timedelta

import pandas as pd
import requests

from medhaalpha.paths import BHAV_DIR

FO_URL = "https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{d}_F_0000.csv.zip"
CM_URL = "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{d}_F_0000.csv.zip"
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.nseindia.com/"}

OPT_COLS = {
    "TradDt": "date", "TckrSymb": "symbol", "XpryDt": "expiry", "StrkPric": "strike", "OptnTp": "opt_type",
    "OpnPric": "open", "HghPric": "high", "LwPric": "low", "ClsPric": "close", "LastPric": "last",
    "UndrlygPric": "underlying", "SttlmPric": "settle", "OpnIntrst": "oi", "ChngInOpnIntrst": "chg_oi",
    "TtlTradgVol": "volume", "TtlTrfVal": "turnover", "TtlNbOfTxsExctd": "n_trades", "NewBrdLotQty": "lot",
}
FUT_COLS = {
    "TradDt": "date", "TckrSymb": "symbol", "XpryDt": "expiry", "ClsPric": "close", "UndrlygPric": "underlying",
    "SttlmPric": "settle", "OpnIntrst": "oi", "TtlTradgVol": "volume", "TtlTrfVal": "turnover", "NewBrdLotQty": "lot",
}
CM_COLS = {
    "TradDt": "date", "TckrSymb": "symbol", "SctySrs": "series", "ISIN": "isin", "OpnPric": "open", "HghPric": "high",
    "LwPric": "low", "ClsPric": "close", "PrvsClsgPric": "prev_close", "TtlTradgVol": "volume",
    "TtlTrfVal": "turnover", "TtlNbOfTxsExctd": "n_trades",
}


def _fetch(session: requests.Session, url: str, retries: int = 4) -> bytes | None:
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=60)
            if r.status_code == 404:
                return None
            if r.status_code == 200 and r.content[:2] == b"PK":
                return r.content
        except requests.RequestException:
            pass
        time.sleep(1.5 * (attempt + 1))
    return None


def _read_zip_csv(blob: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        name = zf.namelist()[0]
        with zf.open(name) as fh:
            return pd.read_csv(fh, low_memory=False)


def process_day(d: date, session: requests.Session) -> str:
    tag = d.strftime("%Y%m%d")
    out_opt = BHAV_DIR / "options" / f"{tag}.parquet"
    out_fut = BHAV_DIR / "futures" / f"{tag}.parquet"
    out_cm = BHAV_DIR / "cm" / f"{tag}.parquet"
    if out_opt.exists() and out_fut.exists() and out_cm.exists():
        return "cached"
    fo_blob = _fetch(session, FO_URL.format(d=tag))
    if fo_blob is None:
        return "holiday"
    cm_blob = _fetch(session, CM_URL.format(d=tag))
    fo = _read_zip_csv(fo_blob)
    opt = fo.loc[fo["FinInstrmTp"] == "STO", list(OPT_COLS)].rename(columns=OPT_COLS)
    fut = fo.loc[fo["FinInstrmTp"] == "STF", list(FUT_COLS)].rename(columns=FUT_COLS)
    # keep index futures/options closes too (NIFTY context / not traded)
    for frame in (opt, fut):
        frame["date"] = pd.to_datetime(frame["date"])
        frame["expiry"] = pd.to_datetime(frame["expiry"])
    # Trim the option chain to what an ATM-ish buyer could select: +-30% moneyness, first 3 expiries.
    opt = opt[(opt["strike"] / opt["underlying"]).between(0.7, 1.3)]
    expiries = sorted(opt["expiry"].unique())[:3]
    opt = opt[opt["expiry"].isin(expiries)]
    out_opt.parent.mkdir(parents=True, exist_ok=True)
    out_fut.parent.mkdir(parents=True, exist_ok=True)
    out_cm.parent.mkdir(parents=True, exist_ok=True)
    opt.to_parquet(out_opt, index=False)
    fut.to_parquet(out_fut, index=False)
    if cm_blob is not None:
        cm = _read_zip_csv(cm_blob)
        cm = cm.loc[cm["SctySrs"].isin(["EQ", "BE", "BZ", "SM", "ST"]), list(CM_COLS)].rename(columns=CM_COLS)
        cm["date"] = pd.to_datetime(cm["date"])
        cm.to_parquet(out_cm, index=False)
    return "ok"


def run(start: date, end: date, workers: int = 4) -> None:
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    days = [d for d in days if d.weekday() < 5]
    session = requests.Session()
    session.headers.update(HEADERS)
    stats: dict[str, int] = {}
    with cf.ThreadPoolExecutor(workers) as ex:
        for d, status in zip(days, ex.map(lambda x: process_day(x, session), days)):
            stats[status] = stats.get(status, 0) + 1
    print("bhavcopy download:", stats)
    consolidate()


def consolidate() -> None:
    for kind in ("options", "futures", "cm"):
        files = sorted((BHAV_DIR / kind).glob("*.parquet"))
        if not files:
            continue
        frame = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
        frame.to_parquet(BHAV_DIR / f"{kind}_all.parquet", index=False)
        print(kind, len(files), "days", len(frame), "rows")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2024-10-01")
    p.add_argument("--end", default="2026-11-13")
    p.add_argument("--workers", type=int, default=4)
    a = p.parse_args()
    run(date.fromisoformat(a.start), date.fromisoformat(a.end), a.workers)

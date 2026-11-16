"""Load candles, resample to higher timeframes and build the point-in-time universe."""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd

from medhaalpha.paths import BHAV_DIR, CANDLE_DIR, DATA_DIR, RAW_DIR

SESSION_START_MIN = 9 * 60 + 15
SESSION_END_MIN = 15 * 60 + 30


@lru_cache(maxsize=1)
def symbol_map() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "symbol_map.csv")


def canonical_symbols() -> list[str]:
    m = symbol_map()
    syms = sorted(set(m["canonical"]) - {"NIFTY50", "NIFTYBANK"})
    return [s for s in syms if (CANDLE_DIR / "minutes5" / f"{s}.parquet").exists()]


@lru_cache(maxsize=1)
def industry_map() -> dict[str, str]:
    n500 = pd.read_csv(RAW_DIR / "ind_nifty500list.csv")
    base = dict(zip(n500["Symbol"], n500["Industry"]))
    out = {}
    for _, row in symbol_map().iterrows():
        ind = base.get(row["canonical"]) or base.get(row["symbol"])
        if ind:
            out[row["canonical"]] = ind
    for s in canonical_symbols():
        out.setdefault(s, "Other")
    return out


def load_intraday(symbol: str, interval: str = "minutes5") -> pd.DataFrame:
    df = pd.read_parquet(CANDLE_DIR / interval / f"{symbol}.parquet")
    mins = df["datetime"].dt.hour * 60 + df["datetime"].dt.minute
    df = df[(mins >= SESSION_START_MIN) & (mins < SESSION_END_MIN)].copy()
    df["date"] = df["datetime"].dt.normalize()
    # From 3 Aug 2026 (NSE closing-auction session) the 15:15/15:20 bars are zero-volume fillers with no
    # trading; drop them so they do not distort ATR/ADX/EMA (the last bar keeps the auction print as close).
    from medhaalpha.config import CAS_START

    mins = df["datetime"].dt.hour * 60 + df["datetime"].dt.minute
    filler = (df["date"] >= pd.Timestamp(CAS_START)) & (mins >= 15 * 60 + 15) & (df["volume"] <= 0) & (
        mins < 15 * 60 + 25)
    df = df[~filler]
    # drop special/short sessions (e.g. Muhurat trading) — fewer than 80% of normal bars
    step = 3 if interval == "minutes3" else 5
    full = (SESSION_END_MIN - SESSION_START_MIN) // step
    counts = df.groupby("date")["datetime"].transform("size")
    df = df[counts >= 0.8 * full].reset_index(drop=True)
    return df


# Muhurat (Diwali evening) sessions: ~1 hour, not representative daily candles.
SPECIAL_SESSIONS = pd.DatetimeIndex(["2023-11-12", "2024-11-01", "2025-10-21", "2026-11-08"])


def load_daily(symbol: str) -> pd.DataFrame:
    df = pd.read_parquet(CANDLE_DIR / "days" / f"{symbol}.parquet")
    df["date"] = df["datetime"].dt.normalize()
    df = df[~df["date"].isin(SPECIAL_SESSIONS)]
    return df.reset_index(drop=True)


def resample_intraday(df: pd.DataFrame, minutes: int) -> pd.DataFrame:
    """Resample session bars to `minutes` buckets anchored at 09:15 (NSE convention).

    Returns columns: datetime (bucket start), end (bucket end, i.e. when the bar is known), o/h/l/c/v, date.
    """
    mins = df["datetime"].dt.hour * 60 + df["datetime"].dt.minute - SESSION_START_MIN
    bucket = (mins // minutes).astype(int)
    key = df["date"].values.astype("datetime64[ns]").astype(np.int64) // 60_000_000_000 + bucket.values
    g = df.groupby(key, sort=True)
    out = pd.DataFrame(
        {
            "datetime": g["datetime"].first(),
            "open": g["open"].first(),
            "high": g["high"].max(),
            "low": g["low"].min(),
            "close": g["close"].last(),
            "volume": g["volume"].sum(),
            "date": g["date"].first(),
        }
    ).reset_index(drop=True)
    start_min = out["datetime"].dt.hour * 60 + out["datetime"].dt.minute
    end_min = np.minimum(
        SESSION_START_MIN + ((start_min - SESSION_START_MIN) // minutes + 1) * minutes, SESSION_END_MIN
    )
    out["end"] = out["date"] + pd.to_timedelta(end_min, unit="m")
    return out


def add_end(df: pd.DataFrame, minutes: int) -> pd.DataFrame:
    start_min = df["datetime"].dt.hour * 60 + df["datetime"].dt.minute
    end_min = np.minimum(start_min + minutes, SESSION_END_MIN)
    df = df.copy()
    df["end"] = df["date"] + pd.to_timedelta(end_min, unit="m")
    return df


# ------------------------------------------------------------------ universe
@lru_cache(maxsize=1)
def trading_days() -> pd.DatetimeIndex:
    d = pd.read_parquet(CANDLE_DIR / "days" / "RELIANCE.parquet")
    days = pd.DatetimeIndex(d["datetime"].dt.normalize().unique()).sort_values()
    return days[~days.isin(SPECIAL_SESSIONS)]


@lru_cache(maxsize=1)
def universe_membership() -> pd.DataFrame:
    """Boolean frame (date x canonical symbol): tradable on `date` using only info known before the open.

    Rules (all evaluated with data up to the previous session):
      * stock had listed stock futures/options in the previous session's F&O bhavcopy (point-in-time F&O list)
      * 20-session average cash-market traded value >= ₹20 crore
      * at least 200 completed daily sessions of history
    Market-cap (> ₹1,000 cr) is implied by NSE F&O eligibility and is not separately available historically.
    """
    smap = symbol_map()
    alias = dict(zip(smap["symbol"], smap["canonical"]))
    fut = pd.read_parquet(BHAV_DIR / "futures_all.parquet", columns=["date", "symbol"]).drop_duplicates()
    fut["canonical"] = fut["symbol"].map(alias)
    fno = fut.dropna().assign(v=True).pivot_table(index="date", columns="canonical", values="v", aggfunc="any")
    fno = fno.fillna(False).astype(bool)

    cm = pd.read_parquet(BHAV_DIR / "cm_all.parquet", columns=["date", "symbol", "series", "turnover"])
    cm = cm[cm["series"] == "EQ"]
    cm["canonical"] = cm["symbol"].map(alias)
    cm = cm.dropna(subset=["canonical"])
    tv = cm.pivot_table(index="date", columns="canonical", values="turnover", aggfunc="sum")
    adtv = tv.rolling(20, min_periods=15).mean()

    days = trading_days()
    hist = {}
    for s in fno.columns:
        p = CANDLE_DIR / "days" / f"{s}.parquet"
        if not p.exists():
            continue
        d = pd.read_parquet(p, columns=["datetime"])["datetime"].dt.normalize()
        hist[s] = pd.Series(1, index=pd.DatetimeIndex(d)).reindex(days, fill_value=0).cumsum()
    hist = pd.DataFrame(hist)

    cols = sorted(set(fno.columns) & set(hist.columns))
    fno = fno.reindex(index=days, columns=cols).ffill().fillna(False).astype(bool)
    adtv = adtv.reindex(index=days, columns=cols).ffill()
    hist = hist.reindex(index=days, columns=cols)
    ok = fno & (adtv >= 20e7) & (hist >= 200)
    # shift by one session: decision for date D uses information through D-1
    return ok.shift(1).fillna(False).astype(bool)


def lot_sizes() -> pd.DataFrame:
    fut = pd.read_parquet(BHAV_DIR / "futures_all.parquet", columns=["date", "symbol", "lot"])
    alias = dict(zip(symbol_map()["symbol"], symbol_map()["canonical"]))
    fut["canonical"] = fut["symbol"].map(alias)
    return fut.groupby(["date", "canonical"])["lot"].first().unstack()

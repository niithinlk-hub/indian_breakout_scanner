"""Pre-trade session-noise classifier used to choose the intraday signal timeframe.

For each (symbol, session) we decide *before* new entries are allowed (09:30) whether the
session looks noisy, using only:
  * the previous session's 5-minute efficiency ratio |close-open| / sum|dclose| compared
    with its own trailing 20-session median, and
  * today's opening range (09:15-09:30) relative to the previous daily ATR.
Noisy sessions -> 15-minute signals with 60-minute confirmation; orderly -> 5-minute signals.
"""
from __future__ import annotations

import multiprocessing as mp

import numpy as np
import pandas as pd

from medhaalpha import indicators as ind
from medhaalpha.data import loader


def _flags(sym: str) -> pd.DataFrame:
    b = loader.load_intraday(sym, "minutes5")
    g = b.groupby("date")
    er = (g["close"].last() - g["open"].first()).abs() / g["close"].apply(lambda x: x.diff().abs().sum())
    er_prev = er.shift(1)
    er_med = er_prev.rolling(20, min_periods=10).median()
    first3 = b[b["datetime"].dt.time < pd.Timestamp("09:30").time()].groupby("date")
    orng = first3["high"].max() - first3["low"].min()
    d = loader.load_daily(sym)
    datr = pd.Series(ind.atr(d["high"].to_numpy(), d["low"].to_numpy(), d["close"].to_numpy(), 14), index=d["date"])
    datr_prev = datr.shift(1).reindex(er.index)
    or_ratio = orng.reindex(er.index) / datr_prev
    noisy = (er_prev < er_med) & (or_ratio > 0.35) | (or_ratio > 0.6)
    return pd.DataFrame({"symbol": sym, "date": er.index, "noisy": noisy.fillna(False).to_numpy(),
                         "er_prev": er_prev.to_numpy(), "or_ratio": or_ratio.to_numpy()})


def noise_flags(symbols: list[str], workers: int = 4) -> pd.DataFrame:
    with mp.get_context("fork").Pool(workers) as pool:
        parts = pool.map(_flags, symbols)
    return pd.concat(parts, ignore_index=True)


def combine(trades: pd.DataFrame, flags: pd.DataFrame, entry: str, side: int,
            orderly_tf: str = "5/15", noisy_tf: str = "15/60") -> pd.DataFrame:
    t = trades[(trades["engine"] == "intraday") & (trades["entry"] == entry) & (trades["side"] == side)
               & trades["tf"].isin([orderly_tf, noisy_tf])]
    t = t.merge(flags[["symbol", "date", "noisy"]], on=["symbol", "date"], how="left")
    t["noisy"] = t["noisy"].fillna(False).astype(bool)
    keep = ((t["tf"] == orderly_tf) & ~t["noisy"]) | ((t["tf"] == noisy_tf) & t["noisy"])
    out = t[keep].copy()
    out["tf"] = "ADAPTIVE-TF"
    return out

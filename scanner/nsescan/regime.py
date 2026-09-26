"""Market regime (section 3e), one row per session, point-in-time.

Inputs:
  bench_above_50  Nifty 500 (^CRSLDX) close > SMA(regime.bench_sma) of its own bars
  breadth         share of universe symbols with a bar whose close > SMA(regime.breadth_sma)
                  is >= regime.min_breadth
  vix             India VIX close < its regime.max_vix_pctile quantile over the last
                  regime.vix_lookback VIX bars
State: RISK_ON (3/3), NEUTRAL (2/3), RISK_OFF (<= 1/3); UNDEFINED until every input
has enough history. Benchmarks missing a session on Yahoo carry their last value forward.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import Config
from .panel import Panel, sma


def _series(bench: pd.DataFrame, ticker: str) -> pd.Series:
    frame = bench.loc[bench["ticker"].eq(ticker)]
    return pd.Series(frame["close"].to_numpy(dtype=float), index=pd.DatetimeIndex(frame["date"])).sort_index()


def compute_regime(panel: Panel, bench: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    tickers = cfg["data.benchmarks"]
    dates = panel.dates

    nifty500 = _series(bench, tickers["nifty500"])
    bench_sma = nifty500.rolling(int(cfg["regime.bench_sma"]), min_periods=int(cfg["regime.bench_sma"])).mean()
    bench_close = nifty500.reindex(dates, method="ffill")
    bench_sma = bench_sma.reindex(dates, method="ffill")
    bench_above = (bench_close > bench_sma).where(bench_sma.notna())

    sym_sma = sma(panel.close, int(cfg["regime.breadth_sma"]))
    valid = panel.has_bar & sym_sma.notna()
    above = (panel.close > sym_sma) & valid
    breadth_n = valid.sum(axis=1)
    breadth_pct = (above.sum(axis=1) / breadth_n.where(breadth_n > 0)).astype(float)
    breadth_ok = (breadth_pct >= float(cfg["regime.min_breadth"])).where(breadth_pct.notna())

    vix = _series(bench, tickers["vix"])
    lookback = int(cfg["regime.vix_lookback"])
    vix_threshold = vix.rolling(lookback, min_periods=lookback).quantile(float(cfg["regime.max_vix_pctile"]))
    vix_pctile = vix.rolling(lookback, min_periods=lookback).rank(pct=True)
    vix_close = vix.reindex(dates, method="ffill")
    vix_threshold = vix_threshold.reindex(dates, method="ffill")
    vix_pctile = vix_pctile.reindex(dates, method="ffill")
    vix_ok = (vix_close < vix_threshold).where(vix_threshold.notna())

    inputs = pd.DataFrame({"bench": bench_above, "breadth": breadth_ok, "vix": vix_ok})
    defined = inputs.notna().all(axis=1)
    inputs_true = inputs.astype("boolean").fillna(False).astype(int).sum(axis=1)
    state = np.select([inputs_true >= 3, inputs_true == 2], ["RISK_ON", "NEUTRAL"], default="RISK_OFF")
    state = pd.Series(state, index=dates).where(defined, "UNDEFINED")
    return pd.DataFrame(
        {
            "state": state,
            "bench_above_50": bench_above.astype("boolean"),
            "breadth_pct": breadth_pct,
            "vix_pctile": vix_pctile,
            "bench_close": bench_close,
            "bench_sma": bench_sma,
            "vix_close": vix_close,
            "vix_threshold": vix_threshold,
            "breadth_n": breadth_n.astype(int),
            "inputs_true": inputs_true.where(defined),
        },
        index=pd.DatetimeIndex(dates, name="date"),
    )

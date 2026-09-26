"""Price panel: NSE session calendar and wide (date x symbol) OHLCV frames.

The calendar is derived from the data: a date is a session when at least
`data.calendar_min_coverage` of the symbols listed on that date have a bar.

Yahoo emits "stub" bars (zero volume, open = high = low = close = previous close):
  * on NSE holidays for nearly every symbol (e.g. 2026-05-01). Nifty 50 (^NSEI) has
    no bar on those dates, so they are not sessions and their bars are dropped;
  * on at least one real session for nearly every symbol (2025-03-18: Nifty 50 +1.45%,
    99% of stock bars stubbed; the next bar carries both days' move). Such a date stays
    a session and its stub bars are dropped, so they count as missing, not as
    zero-volume days.
A date is a stub date when at least `data.stub_date_min_share` of its bars are stubs.
Every dropped bar is kept in `Panel.dropped` with its reason and reported by QA.

Indicators are computed on each symbol's own bar sequence (a "session" for a symbol
is one of its bars), then placed back on the calendar grid, so a value at date T
only ever uses bars dated <= T.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

FIELDS = ("open", "high", "low", "close", "volume")


@dataclass
class Panel:
    dates: pd.DatetimeIndex
    symbols: pd.Index
    open: pd.DataFrame
    high: pd.DataFrame
    low: pd.DataFrame
    close: pd.DataFrame
    volume: pd.DataFrame  # float, NaN = no bar or null volume
    has_bar: pd.DataFrame  # bool
    segment: pd.Series  # symbol -> N500 / MICRO250
    industry: pd.Series  # symbol -> NSE industry
    dropped: pd.DataFrame  # bars removed from the panel, with `reason`
    date_kinds: pd.DataFrame  # per raw date: bars, coverage, stub_share, kind

    def symbols_in(self, segment: str) -> pd.Index:
        return self.segment.index[self.segment.eq(segment)].intersection(self.symbols)


def stub_share(prices: pd.DataFrame) -> pd.Series:
    """Per date: share of bars that are holiday stubs (zero volume, flat OHLC)."""

    stub = (
        prices["volume"].fillna(0).eq(0)
        & prices["open"].eq(prices["high"])
        & prices["high"].eq(prices["low"])
        & prices["low"].eq(prices["close"])
    )
    return stub.groupby(prices["date"]).mean().sort_index()


def is_stub(prices: pd.DataFrame) -> pd.Series:
    return (
        prices["volume"].fillna(0).eq(0)
        & prices["open"].eq(prices["high"])
        & prices["high"].eq(prices["low"])
        & prices["low"].eq(prices["close"])
    )


def classify_dates(
    prices: pd.DataFrame, min_coverage: float, stub_min_share: float, reference_dates: pd.DatetimeIndex
) -> pd.DataFrame:
    """Per date: coverage, stub share and kind (session | gap_session | holiday_stub | thin)."""

    counts = prices.groupby("date").size().sort_index()
    spans = prices.groupby("symbol")["date"].agg(["min", "max"])
    all_dates = counts.index
    starts = spans["min"].value_counts().reindex(all_dates, fill_value=0).cumsum()
    ends_before = spans["max"].value_counts().reindex(all_dates, fill_value=0).cumsum().shift(1, fill_value=0)
    coverage = counts / (starts - ends_before).clip(lower=1)
    stubs = is_stub(prices).groupby(prices["date"]).mean().reindex(all_dates, fill_value=0.0)
    stub_date = stubs >= stub_min_share
    in_reference = pd.Series(all_dates.isin(reference_dates), index=all_dates)
    kind = pd.Series("session", index=all_dates)
    kind[coverage < min_coverage] = "thin"
    kind[stub_date & in_reference] = "gap_session"
    kind[stub_date & ~in_reference] = "holiday_stub"
    return pd.DataFrame({"bars": counts, "coverage": coverage, "stub_share": stubs, "kind": kind})


def build_panel(
    prices: pd.DataFrame,
    universe: pd.DataFrame,
    min_coverage: float,
    stub_min_share: float,
    reference_dates: pd.DatetimeIndex,
) -> Panel:
    prices = prices.copy()
    prices["date"] = pd.to_datetime(prices["date"]).dt.normalize()
    dates = classify_dates(prices, min_coverage, stub_min_share, pd.DatetimeIndex(reference_dates))
    calendar = pd.DatetimeIndex(dates.index[dates["kind"].isin(["session", "gap_session"])], name="date")
    kind = prices["date"].map(dates["kind"])
    drop_reason = pd.Series(pd.NA, index=prices.index, dtype="object")
    drop_reason[kind.isin(["holiday_stub", "thin"])] = "off_calendar_" + kind[kind.isin(["holiday_stub", "thin"])]
    drop_reason[kind.eq("gap_session") & is_stub(prices)] = "gap_session_stub"
    dropped = prices.loc[drop_reason.notna()].assign(reason=drop_reason[drop_reason.notna()]).reset_index(drop=True)
    prices = prices.loc[drop_reason.isna()]
    wide = {
        field: prices.pivot(index="date", columns="symbol", values=field).reindex(calendar).sort_index(axis=1).astype(float)
        for field in FIELDS
    }
    symbols = wide["close"].columns
    meta = universe.set_index("symbol")
    return Panel(
        dates=calendar,
        symbols=symbols,
        open=wide["open"],
        high=wide["high"],
        low=wide["low"],
        close=wide["close"],
        volume=wide["volume"],
        has_bar=wide["close"].notna(),
        segment=meta["segment"].reindex(symbols),
        industry=meta["industry"].reindex(symbols),
        dropped=dropped,
        date_kinds=dates,
    )


def per_symbol(frame: pd.DataFrame, func: Callable[[pd.Series], pd.Series]) -> pd.DataFrame:
    """Apply `func` to each column's own bars (NaN rows dropped) and re-grid the result."""

    out = {}
    for symbol in frame.columns:
        series = frame[symbol].dropna()
        out[symbol] = func(series).reindex(frame.index) if len(series) else pd.Series(np.nan, index=frame.index)
    return pd.DataFrame(out, index=frame.index)[frame.columns]


def rolling_median(frame: pd.DataFrame, window: int) -> pd.DataFrame:
    return per_symbol(frame, lambda s: s.rolling(window, min_periods=window).median())


def sma(frame: pd.DataFrame, window: int) -> pd.DataFrame:
    return per_symbol(frame, lambda s: s.rolling(window, min_periods=window).mean())


def ema(frame: pd.DataFrame, span: int) -> pd.DataFrame:
    return per_symbol(frame, lambda s: s.ewm(span=span, adjust=False, min_periods=span).mean())


def panel_from_store(store, cfg) -> Panel:
    """Build the panel for the active universe from stored prices."""

    universe = store.read_universe()
    prices = store.read_prices(symbols=universe["symbol"].tolist())
    bench = store.read_benchmarks()
    reference = pd.DatetimeIndex(bench.loc[bench["ticker"].eq(cfg["data.benchmarks"]["nifty50"]), "date"])
    return build_panel(
        prices,
        universe,
        float(cfg["data.calendar_min_coverage"]),
        float(cfg["data.stub_date_min_share"]),
        reference,
    )

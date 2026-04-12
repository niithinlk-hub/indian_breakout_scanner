from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def _make_history(symbol: str, *, breakout: bool) -> pd.DataFrame:
    periods = 260
    dates = pd.date_range("2024-01-01", periods=periods, freq="B")
    base = np.linspace(100, 150, periods)
    close = base.copy()
    high = close + 1.5
    low = close - 1.5
    open_ = close - 0.4
    volume = np.full(periods, 1_000_000.0)

    if breakout:
        close[-25:-1] = np.linspace(142, 149, 24)
        high[-25:-1] = close[-25:-1] + 1.0
        low[-25:-1] = close[-25:-1] - 1.0
        close[-1] = 158.0
        high[-1] = 160.0
        low[-1] = 155.5
        open_[-1] = 156.0
        volume[-1] = 3_000_000.0
    else:
        close[-1] = 149.0
        high[-1] = 150.0
        low[-1] = 147.5
        open_[-1] = 148.0

    return pd.DataFrame(
        {
            "datetime": dates,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "symbol": symbol,
        },
    )


@pytest.fixture()
def breakout_stock_df() -> pd.DataFrame:
    return _make_history("RELIANCE", breakout=True)


@pytest.fixture()
def benchmark_df() -> pd.DataFrame:
    return _make_history("^NSEI", breakout=False)

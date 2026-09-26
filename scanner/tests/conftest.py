from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def make_prices(symbols: dict[str, str], sessions: int = 400, seed: int = 7) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Synthetic long prices + universe. symbols: {symbol: segment}."""

    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2022-01-03", periods=sessions)
    rows = []
    for k, symbol in enumerate(symbols):
        close = 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.02, sessions)))
        open_ = close * (1 + rng.normal(0, 0.005, sessions))
        high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.01, sessions)))
        low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.01, sessions)))
        volume = rng.integers(200_000, 2_000_000, sessions).astype(float)
        rows.append(pd.DataFrame({"symbol": symbol, "date": dates, "open": open_.round(4), "high": high.round(4),
                                  "low": low.round(4), "close": close.round(4), "volume": volume}))
    prices = pd.concat(rows, ignore_index=True)
    prices["volume"] = prices["volume"].astype("Int64")
    universe = pd.DataFrame({"symbol": list(symbols), "segment": list(symbols.values()),
                             "industry": ["Ind" + str(i % 3) for i in range(len(symbols))]})
    return prices, universe


@pytest.fixture
def synthetic():
    symbols = {f"N{i}": "N500" for i in range(6)} | {f"M{i}": "MICRO250" for i in range(4)}
    return make_prices(symbols)

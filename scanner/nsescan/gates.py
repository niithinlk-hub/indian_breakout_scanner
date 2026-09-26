"""Gates evaluated point-in-time on the panel. Step 2 needs only the liquidity gate;
the remaining section-3a gates are added with the rules engine (step 3).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config import CRORE, SEGMENTS, Config
from .panel import Panel, rolling_median


@dataclass
class LiquidityGate:
    passed: pd.DataFrame  # bool (dates x symbols)
    median_tv_cr: pd.DataFrame  # median traded value over liquidity.tv_window bars, INR crore
    zero_volume_recent: pd.DataFrame  # zero/null-volume bars in the segment's lookback (NaN if not applied)


def traded_value(panel: Panel) -> pd.DataFrame:
    """close x volume on bars; a null volume counts as zero traded value."""

    return (panel.close * panel.volume.fillna(0.0)).where(panel.has_bar)


def liquidity_gate(panel: Panel, cfg: Config) -> LiquidityGate:
    window = int(cfg["liquidity.tv_window"])
    median_tv_cr = rolling_median(traded_value(panel), window) / CRORE
    zero = (panel.has_bar & panel.volume.fillna(0.0).eq(0)).astype(float)
    passed = pd.DataFrame(False, index=panel.dates, columns=panel.symbols)
    zero_recent = pd.DataFrame(float("nan"), index=panel.dates, columns=panel.symbols)
    for segment in SEGMENTS:
        cols = panel.symbols_in(segment)
        ok = (
            panel.has_bar[cols]
            & median_tv_cr[cols].ge(float(cfg.seg("liquidity.min_median_tv_cr", segment)))
            & panel.close[cols].ge(float(cfg.seg("liquidity.min_close", segment)))
        )
        lookback = cfg.seg("liquidity.zero_volume_lookback", segment)
        if lookback is not None:
            zero_recent[cols] = zero[cols].rolling(int(lookback), min_periods=1).sum()
            ok &= zero_recent[cols].eq(0)
        passed[cols] = ok
    return LiquidityGate(passed=passed, median_tv_cr=median_tv_cr, zero_volume_recent=zero_recent)

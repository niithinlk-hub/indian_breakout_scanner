"""No-lookahead: QA, liquidity and regime values at date T must not change when bars
after T are perturbed."""

from __future__ import annotations

import numpy as np
import pandas as pd

from nsescan.config import default_config
from nsescan.gates import liquidity_gate
from nsescan.panel import build_panel
from nsescan.qa import qa_metrics, qa_pass_mask
from nsescan.regime import compute_regime

CFG = default_config().with_overrides({
    "qa.min_bars": {"N500": 60, "MICRO250": 60},
    "qa.lookback_sessions": 60,
    "liquidity.min_median_tv_cr": {"N500": 0.5, "MICRO250": 0.2},
    "regime.vix_lookback": 60,
})


def _bench(dates, seed=1):
    rng = np.random.default_rng(seed)
    n = len(dates)
    rows = [pd.DataFrame({"ticker": "^CRSLDX", "date": dates, "close": 10000 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))}),
            pd.DataFrame({"ticker": "^INDIAVIX", "date": dates, "close": 15 + np.cumsum(rng.normal(0, 0.3, n))}),
            pd.DataFrame({"ticker": "^NSEI", "date": dates, "close": 1.0})]
    return pd.concat(rows, ignore_index=True)


def _perturb_after(prices, bench, cutoff, seed=99):
    rng = np.random.default_rng(seed)
    prices = prices.copy()
    later = prices["date"] > cutoff
    shock = rng.uniform(0.3, 3.0, later.sum())
    for col in ("open", "high", "low", "close"):
        prices.loc[later, col] = (prices.loc[later, col] * shock).round(4)
    prices.loc[later, "volume"] = (prices.loc[later, "volume"].astype(float) * rng.uniform(0, 5, later.sum())).round().astype("Int64")
    bench = bench.copy()
    bench.loc[bench["date"] > cutoff, "close"] *= rng.uniform(0.5, 2.0, (bench["date"] > cutoff).sum())
    return prices, bench


def test_masks_and_regime_do_not_look_ahead(synthetic):
    prices, universe = synthetic
    dates = pd.DatetimeIndex(sorted(prices["date"].unique()))
    bench = _bench(dates)
    cutoff = dates[250]
    results = []
    for p, b in ((prices, bench), _perturb_after(prices, bench, cutoff)):
        panel = build_panel(p, universe, 0.5, 0.10, dates)
        liq = liquidity_gate(panel, CFG)
        results.append({
            "qa": qa_pass_mask(panel, CFG),
            "big": qa_metrics(panel, CFG)["big_n"],
            "liq": liq.passed,
            "tv": liq.median_tv_cr,
            "regime": compute_regime(panel, b, CFG),
        })
    base, perturbed = results
    for key in ("qa", "big", "liq", "tv", "regime"):
        pd.testing.assert_frame_equal(base[key].loc[:cutoff], perturbed[key].loc[:cutoff])
    # the masks are not degenerate before the cutoff
    for key in ("qa", "liq"):
        values = base[key].loc[:cutoff].to_numpy()
        assert values.any() and not values.all()
    assert base["regime"]["state"].loc[:cutoff].nunique() > 1
    # the perturbation is real: values after the cutoff do change
    assert not base["tv"].loc[cutoff:].iloc[1:].equals(perturbed["tv"].loc[cutoff:].iloc[1:])
    assert not base["regime"]["bench_close"].loc[cutoff:].iloc[1:].equals(perturbed["regime"]["bench_close"].loc[cutoff:].iloc[1:])

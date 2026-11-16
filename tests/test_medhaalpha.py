from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("numba")

from medhaalpha import indicators as ind  # noqa: E402
from medhaalpha.costs import equity_costs, option_costs  # noqa: E402
from medhaalpha.portfolio import PortfolioRules, run_portfolio  # noqa: E402
from medhaalpha.simulate import simulate  # noqa: E402


def test_ema_matches_pandas_after_warmup():
    x = np.cumsum(np.random.default_rng(0).normal(size=300)) + 100
    ours = ind.ema(x, 20)
    ref = pd.Series(x).ewm(span=20, adjust=False).mean().to_numpy()
    assert np.isnan(ours[:20]).all()
    np.testing.assert_allclose(ours[20:], ref[20:])


def test_atr_constant_range():
    n = 50
    h = np.full(n, 101.0)
    l = np.full(n, 99.0)
    c = np.full(n, 100.0)
    a = ind.atr(h, l, c, 14)
    assert np.isnan(a[:13]).all()
    np.testing.assert_allclose(a[13:], 2.0)


def _bars(o, h, l, c, days=None):
    n = len(o)
    days = np.zeros(n, np.int64) if days is None else np.asarray(days, np.int64)
    last = np.r_[days[1:] != days[:-1], True]
    return dict(bo=np.asarray(o, float), bh=np.asarray(h, float), bl=np.asarray(l, float), bc=np.asarray(c, float),
                bday=days, entry_ok=np.ones(n, bool), flat_bar=last.copy(), last_bar=last)


def _run(b, side=1, etype=0, level=0.0, stop_abs=95.0, atr=5.0, intraday=True, max_sessions=5, stop_mode=0,
         target_r=2.0, trail_k=0.0, ema_mode=0, partial_r=0.0, act=0, tfc=None):
    n = len(b["bo"])
    nanarr = np.full(n, np.nan)
    tfc = tfc or (nanarr, nanarr, nanarr, nanarr)
    res = simulate(b["bo"], b["bh"], b["bl"], b["bc"], b["bday"], b["entry_ok"], b["flat_bar"], b["last_bar"],
                   *tfc, np.array([act]), np.array([side]), np.array([etype]), np.array([level]), np.array([3]),
                   np.array([stop_abs]), np.array([atr]), np.array([intraday]), max_sessions, stop_mode, 1.5,
                   target_r, trail_k, ema_mode, partial_r, 0.5, 0.5, 3.0)
    return [r[0] for r in res]


def test_long_stop_hit_is_minus_one_r():
    b = _bars([100, 99, 97], [101, 100, 98], [99, 96, 94], [100, 97, 95])
    fi, fill, stop, ei, ex, reason, nexit, mfe, mae = _run(b)
    assert fill == 100 and stop == 95 and ex == 95 and reason == 1


def test_target_hit_and_conservative_same_bar_ordering():
    b = _bars([100, 105, 108], [101, 111, 112], [99, 104, 90], [100, 110, 95])
    *_, ex, reason, _, _, _ = _run(b)
    assert ex == 110 and reason == 2  # 2R target = 110 on bar 1
    b2 = _bars([100, 100], [101, 111], [99, 94], [100, 100])
    *_, ex2, reason2, _, _, _ = _run(b2)
    assert ex2 == 95 and reason2 == 1  # bar touches both -> stop first


def test_gap_through_stop_fills_at_open():
    b = _bars([100, 90], [101, 91], [99, 89], [100, 90], days=[0, 1])
    *_, ex, reason, _, _, _ = _run(b, intraday=False)
    assert ex == 90 and reason == 1


def test_intraday_flat_exit_at_last_bar_close():
    b = _bars([100, 100.5, 101], [100.5, 101, 101.5], [99.5, 100, 100.5], [100.2, 100.8, 101.2])
    *_, ex, reason, _, _, _ = _run(b)
    assert reason == 5 and ex == 101.2


def test_short_symmetry():
    b = _bars([100, 101, 103], [101, 104, 106], [99, 100, 102], [100, 103, 105])
    *_, ex, reason, _, _, _ = _run(b, side=-1, stop_abs=105.0)
    assert ex == 105 and reason == 1


def test_stop_entry_bar_can_only_stop_out():
    # buy-stop at 102 triggers on bar 1, same bar also trades down to 94 (< stop 95) -> stopped
    b = _bars([100, 101, 103], [101, 103, 120], [99, 94, 102], [100, 96, 110])
    fi, fill, stop, ei, ex, reason, *_ = _run(b, etype=1, level=102.0, act=1)
    assert fi == 1 and fill == 102 and reason == 1


def test_positional_max_sessions():
    days = [0, 0, 1, 1, 2, 2]
    b = _bars([100] * 6, [100.5] * 6, [99.5] * 6, [100.1] * 6, days=days)
    *_, ei, ex, reason, _, _, _ = _run(b, intraday=False, max_sessions=2)
    assert reason == 5 and ei == 3


def test_partial_then_breakeven():
    b = _bars([100, 103, 104, 100], [101, 106, 105, 101], [99, 102, 103, 99], [100, 105, 104, 100])
    fi, fill, stop, ei, ex, reason, nexit, *_ = _run(b, target_r=0.0, partial_r=1.0)
    assert nexit == 2 and reason == 7
    assert ex == pytest.approx(0.5 * 105 + 0.5 * 100)


def test_equity_cost_example():
    # ₹75,000 intraday round trip
    c = equity_costs(["2025-06-02"], [75_000], [75_000], [True], [2])[0]
    brokerage = 2 * min(20, 0.001 * 75_000)
    stt = 0.00025 * 75_000
    exch = 0.0000307 * 150_000
    sebi = 0.000001 * 150_000
    stamp = 0.00003 * 75_000
    gst = 0.18 * (brokerage + exch + sebi)
    assert c == pytest.approx(brokerage + stt + exch + sebi + stamp + gst)


def test_option_stt_regime_change():
    before = option_costs(["2026-03-31"], [0.0], [100_000.0], [1])[0]
    after = option_costs(["2026-04-01"], [0.0], [100_000.0], [1])[0]
    assert after > before


def _cand(sym, t0, t1, pnl_sign=-1, side=1, engine="intraday", industry="X"):
    fill = 100.0
    exit_ = fill + pnl_sign * side * 1.0
    return dict(symbol=sym, industry=industry, engine=engine, side=side, fill_time=pd.Timestamp(t0),
                exit_time=pd.Timestamp(t1), fill=fill, exit=exit_, risk_ps=1.0, reason="stop", n_exit=1,
                score=50.0, sessions=1, date=pd.Timestamp(t0).normalize(), datr_pct=0.02, R=-1.0)


def test_portfolio_blocks_same_symbol_and_daily_limit():
    rows = [
        _cand("AAA", "2025-06-02 10:00", "2025-06-02 11:00"),
        _cand("AAA", "2025-06-02 10:30", "2025-06-02 12:00"),  # same symbol still open -> rejected
    ]
    acc, rej = run_portfolio(pd.DataFrame(rows), PortfolioRules())
    assert len(acc) == 1
    assert rej.set_index("reason").loc["symbol_open", "count"] == 1
    # qty capped by ₹75k notional: 750 shares x ₹1 risk = ₹750 planned risk
    assert acc["units"].iloc[0] == 750


def test_portfolio_daily_loss_limit():
    from dataclasses import replace

    rules = PortfolioRules()
    rules = replace(rules, risk=replace(rules.risk, max_notional_per_stock=1e9, max_per_industry_direction=99),
                    max_intraday_per_day=99)
    rows = [_cand(f"S{i}", f"2025-06-02 10:{i:02d}", f"2025-06-02 10:{i:02d}:30", industry=f"I{i}") for i in range(5)]
    rows.append(_cand("LATE", "2025-06-02 11:00", "2025-06-02 11:30", industry="Z"))
    acc, rej = run_portfolio(pd.DataFrame(rows), rules)
    # each loses ~₹3,000 + costs; after two losses the ₹6,000 daily limit blocks new entries
    assert len(acc) == 2
    assert "daily_limit" in set(rej["reason"])


def test_same_day_positional_uses_intraday_statutory_rates():
    deliv = equity_costs(["2025-06-02"], [75_000], [75_000], [False], [2])[0]
    same = equity_costs(["2025-06-02"], [75_000], [75_000], [False], [2], same_day=[True])[0]
    assert same < deliv - 100  # no 0.1% two-sided STT, no DP charge


def test_open_risk_includes_gap_allowance():
    from dataclasses import replace

    rules = PortfolioRules()
    rules = replace(rules, risk=replace(rules.risk, max_per_industry_direction=99))
    rows = []
    for i in range(5):
        r = _cand(f"P{i}", "2025-06-02 10:00", "2025-06-05 15:25", pnl_sign=1, engine="positional", industry=f"I{i}")
        r.update(risk_ps=1.5, datr_pct=0.04, sessions=4)
        rows.append(r)
    acc, rej = run_portfolio(pd.DataFrame(rows), rules)
    assert acc["booked_risk"].sum() <= rules.risk.max_open_risk + 1e-6

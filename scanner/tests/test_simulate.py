"""Exit-rule tests for the section-4 trade simulator, on hand-built bars.

Bars are (open, high, low, close). Bar 0..4 are history, bar 5 is the signal day T,
bar 6 is the entry bar (session 1).
"""

from __future__ import annotations

import math
from dataclasses import replace

import pytest

from nsescan.config import default_config
from nsescan.simulate import PlanParams, ema_series, simulate_trade, triple_barrier

import numpy as np

CFG = default_config()
BASE = replace(PlanParams.from_config(CFG, "N500"), cost_side=0.0, slip_side=0.0)  # frictionless unless stated
T = 5
HISTORY = [(100, 101, 99, 100)] * 5 + [(100, 101, 99, 100)]  # bars 0..5, signal close 100


def run(bars, stop=95.0, pivot=None, params=BASE, trail=None, big=None):
    all_bars = HISTORY + bars
    o, h, l, c = (list(x) for x in zip(*all_bars))
    trail = trail if trail is not None else [0.0] * len(c)  # EMA far below: never triggers
    big = big if big is not None else [False] * len(c)
    return simulate_trade(o, h, l, c, trail, big, T, stop, pivot, params)


def flat(n, px=100.0):
    return [(px, px + 1, px - 1, px)] * n


def test_stop_hit_intraday_exits_at_stop():
    trade = run([(100, 101, 94, 96)])
    assert trade.status == "CLOSED" and trade.exit_reason == "STOP"
    assert trade.exit_idx == T + 1 and trade.sessions == 1
    assert trade.r_net == pytest.approx(-1.0)
    assert trade.mae_pct == pytest.approx(-0.05)


def test_gap_below_stop_exits_at_open():
    trade = run([(100, 101, 99, 100), (90, 92, 88, 91)])
    assert trade.exit_reason == "STOP_GAP"
    assert trade.ret_gross == pytest.approx(-0.10)
    assert trade.r_net == pytest.approx(-2.0)


def test_same_bar_stop_and_target_assumes_stop_first():
    trade = run([(100, 120, 94, 110)])
    assert trade.exit_reason == "STOP" and trade.partial_idx == -1
    assert trade.r_net == pytest.approx(-1.0)


def test_partial_at_target_then_trail_exit_next_open():
    bars = [(100, 116, 99, 114), (114, 118, 113, 117), (117, 117, 108, 109), (108, 109, 106, 107)]
    trail = [0.0] * 8 + [112.0, 112.0]  # close 109 < EMA 112 on bar 8 -> exit at bar 9 open (108)
    trade = run(bars, trail=trail)
    assert trade.partial_idx == T + 1
    assert trade.exit_reason == "TRAIL_EMA" and trade.exit_idx == T + 4
    assert trade.ret_gross == pytest.approx(0.5 * 0.15 + 0.5 * 0.08)


def test_gap_open_above_target_fills_partial_at_open():
    trail = [0.0] * 7 + [200.0]
    trade = run([(100, 101, 99, 100), (120, 121, 118, 119), (119, 120, 118, 119)], trail=trail)
    assert trade.partial_idx == T + 2
    assert trade.exit_reason == "TRAIL_EMA"
    assert trade.ret_gross == pytest.approx(0.5 * 0.20 + 0.5 * 0.19)


def test_breakeven_takes_effect_next_session_not_same_bar():
    # session 1 reaches +10% and dips to 97 (above the 95 stop): stop not yet at breakeven
    # session 2 trades down to 99 -> breakeven stop (100) hit
    trade = run([(100, 111, 97, 105), (104, 105, 99, 100)])
    assert trade.exit_reason == "BREAKEVEN_STOP" and trade.exit_idx == T + 2
    assert trade.ret_gross == pytest.approx(0.0)


def test_stall_exit_after_seven_sessions():
    trade = run(flat(7, 101.0) + flat(3, 101.0))
    assert trade.exit_reason == "STALL"
    assert trade.exit_idx == T + 8  # decided at session 7 close, filled at session 8 open
    assert trade.sessions == 8


def test_stall_can_be_disabled_and_time_exit_applies():
    params = replace(BASE, stall_enabled=False)
    trade = run(flat(25, 101.0), params=params)
    assert trade.exit_reason == "TIME"
    assert trade.exit_idx == T + params.time_exit_sessions


def test_failed_breakout_uses_pivot_only_in_first_sessions():
    trade = run([(100, 101, 99, 100.5), (100, 101, 97, 98), (99, 100, 98, 99)], pivot=99.0)
    assert trade.exit_reason == "FAILED_BREAKOUT" and trade.exit_idx == T + 3
    late = run([(100, 104, 99, 104)] * 3 + [(104, 104, 97, 98)] + flat(20, 104.0), pivot=99.0)
    assert late.exit_reason != "FAILED_BREAKOUT"


def test_no_failed_breakout_without_pivot():
    trade = run([(100, 101, 97, 98), (98, 99, 97, 98)] + flat(20, 104.0))
    assert trade.exit_reason != "FAILED_BREAKOUT"


def test_skips():
    assert run(flat(3), stop=90.0).skip_reason == "stop_too_wide"
    assert run(flat(3), stop=100.0).skip_reason == "stop_not_below_close"
    assert run([(94, 95, 90, 93)]).skip_reason == "open_at_or_below_stop"
    assert run([(103, 104, 102, 103)], stop=94.5).skip_reason == "stop_too_wide_at_entry"


def test_costs_and_slippage():
    params = replace(BASE, cost_side=0.00125, slip_side=0.001)
    trade = run(flat(25, 100.0), params=replace(params, stall_enabled=False))
    fill = 100 * 1.001
    paid = fill * 1.00125
    proceeds = 100 * (1 - 0.001) * (1 - 0.00125)
    assert trade.entry_fill == pytest.approx(fill)
    assert trade.ret_net == pytest.approx(proceeds / paid - 1)
    assert trade.r_net == pytest.approx((proceeds - paid) / (fill - 95.0))


def test_open_trade_is_censored():
    trade = run(flat(3, 101.0))
    assert trade.status == "OPEN" and math.isnan(trade.ret_net)


def test_spans_big_move_flag():
    big = [False] * 8 + [True] + [False] * 30
    trade = run(flat(25, 101.0), big=big)
    assert trade.spans_big_move


def test_triple_barrier_labels():
    o = [100.0] * 30
    h = [101.0] * 30
    l = [99.0] * 30
    c = [100.0] * 30
    label, s, ret, touched = triple_barrier(o, h, l, c, 5, 100.0, 95.0, 0.15, 20)
    assert (label, s, touched) == (0.0, 20, 0.0) and ret == pytest.approx(0.0)
    h2 = h.copy(); h2[8] = 116.0
    assert triple_barrier(o, h2, l, c, 5, 100.0, 95.0, 0.15, 20)[:2] == (1.0, 3)
    l2 = l.copy(); l2[7] = 94.0
    assert triple_barrier(o, h2, l2, c, 5, 100.0, 95.0, 0.15, 20)[:2] == (-1.0, 2)
    l3 = l.copy(); l3[8] = 94.0  # same bar as the upper touch -> lower wins
    label, s, _, touched = triple_barrier(o, h2, l3, c, 5, 100.0, 95.0, 0.15, 20)
    assert (label, s, touched) == (-1.0, 3, 1.0)


def test_ema_series_matches_pandas():
    import pandas as pd

    close = np.linspace(100, 130, 60) + np.sin(np.arange(60))
    ours = ema_series(close, 10)
    theirs = pd.Series(close).ewm(span=10, adjust=False, min_periods=10).mean().to_numpy()
    assert np.allclose(ours[9:], theirs[9:]) and np.isnan(ours[:9]).all()

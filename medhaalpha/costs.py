"""Indian transaction-cost model (Upstox Basic-plan retail account), date-aware.

Sources (verified Nov 2026, see docs/medhaalpha/COST_ASSUMPTIONS.md): NSE/FATAX/63809 (9 Sep 2024),
NSE/FATAX/73524 (31 Mar 2026, F&O STT hike from 1 Apr 2026), NSE/FA/73061 (27 Feb 2026, IPFT split,
total unchanged), NSE stamp-duty page, Upstox charges page / notices (14 Feb & 15 Mar 2025 repricing).
Regime changes inside the study window are encoded as (effective_date, value) step functions.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


def _step(dates: np.ndarray, schedule: list[tuple[str, float]]) -> np.ndarray:
    out = np.full(len(dates), schedule[0][1], dtype=float)
    d = pd.to_datetime(dates).values
    for start, val in schedule[1:]:
        out[d >= np.datetime64(pd.Timestamp(start))] = val
    return out


@dataclass(frozen=True)
class CostSchedule:
    # brokerage per executed order (₹) — Upstox Basic plan
    brokerage_intraday: float = 20.0
    # "₹20 or x% of order value, whichever is lower": 0.05% until the 15 Mar 2025 repricing, 0.1% after
    brokerage_intraday_pct: tuple = (("2000-01-01", 0.0005), ("2025-03-15", 0.001))
    brokerage_delivery: float = 20.0
    brokerage_options: float = 20.0
    # Securities transaction tax
    stt_intraday_sell: tuple = (("2000-01-01", 0.00025),)
    stt_delivery: tuple = (("2000-01-01", 0.001),)  # buy and sell
    stt_option_sell: tuple = (("2000-01-01", 0.000625), ("2024-10-01", 0.001), ("2026-04-01", 0.0015))
    stt_option_exercise: tuple = (("2000-01-01", 0.00125), ("2026-04-01", 0.0015))
    # NSE transaction charges incl. IPFT contribution, each side (from 1 Oct 2024; total unchanged 1 Mar 2026)
    exch_equity: float = 0.0000307
    exch_options: float = 0.0003553
    sebi_fee: float = 0.000001  # ₹10 per crore
    stamp_intraday: float = 0.00003
    stamp_delivery: float = 0.00015
    stamp_options: float = 0.00003
    gst: float = 0.18
    # DP charge per scrip per delivery-sell day, incl. 18% GST: ₹18.50+GST, then ₹20+GST from ~15 Mar 2025
    dp_charge: tuple = (("2000-01-01", 21.83), ("2025-03-15", 23.60))


COSTS = CostSchedule()


def equity_costs(
    dates, buy_value: np.ndarray, sell_value: np.ndarray, intraday: np.ndarray, n_orders: np.ndarray,
    cs: CostSchedule = COSTS, same_day: np.ndarray | None = None,
) -> np.ndarray:
    """Round-trip statutory + broker costs (₹) for cash-equity trades.

    `buy_value`/`sell_value` are total ₹ traded on each side; `n_orders` = executed orders.
    `intraday` selects the broker's product (MIS vs CNC brokerage). `same_day` marks trades squared off in
    the session they were opened: the exchange treats those as non-delivery (intraday STT/stamp, no DP),
    even when booked as CNC. Defaults to `intraday`.
    """
    buy_value = np.asarray(buy_value, float)
    sell_value = np.asarray(sell_value, float)
    product_mis = np.asarray(intraday, bool)
    n_orders = np.asarray(n_orders, float)
    intraday = product_mis if same_day is None else (product_mis | np.asarray(same_day, bool))
    turnover = buy_value + sell_value
    per_order_value = turnover / np.maximum(n_orders, 1)
    pct = _step(dates, list(cs.brokerage_intraday_pct))
    brok_intra = n_orders * np.minimum(cs.brokerage_intraday, pct * per_order_value)
    brok = np.where(product_mis, brok_intra, n_orders * cs.brokerage_delivery)
    stt = np.where(
        intraday,
        _step(dates, list(cs.stt_intraday_sell)) * sell_value,
        _step(dates, list(cs.stt_delivery)) * turnover,
    )
    exch = cs.exch_equity * turnover
    sebi = cs.sebi_fee * turnover
    stamp = np.where(intraday, cs.stamp_intraday, cs.stamp_delivery) * buy_value
    gst = cs.gst * (brok + exch + sebi)
    dp = np.where(intraday, 0.0, _step(dates, list(cs.dp_charge)))
    return brok + stt + exch + sebi + stamp + gst + dp


def option_costs(dates, buy_premium: np.ndarray, sell_premium: np.ndarray, n_orders: np.ndarray,
                 cs: CostSchedule = COSTS) -> np.ndarray:
    """Costs for option legs closed before expiry (premium turnover based)."""
    buy_premium = np.asarray(buy_premium, float)
    sell_premium = np.asarray(sell_premium, float)
    turnover = buy_premium + sell_premium
    brok = np.asarray(n_orders, float) * cs.brokerage_options
    stt = _step(dates, list(cs.stt_option_sell)) * sell_premium
    exch = cs.exch_options * turnover
    sebi = cs.sebi_fee * turnover
    stamp = cs.stamp_options * buy_premium
    gst = cs.gst * (brok + exch + sebi)
    return brok + stt + exch + sebi + stamp + gst

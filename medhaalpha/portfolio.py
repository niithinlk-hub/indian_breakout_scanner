"""Portfolio-level risk manager and execution accounting for a ₹3,00,000 account.

Candidate trades (already simulated on price paths) are replayed chronologically. A
candidate is accepted only if every account rule passes at its fill time; P&L is realised
at its exit time. Rules (shared by intraday and positional engines):

* one open position per symbol; at most `max_per_industry_direction` per (industry, side)
* daily realised loss limit ₹6,000 and weekly limit ₹12,000 -> no new trades once hit
* total planned open risk <= ₹6,000; per-trade risk budget = min(₹3,000, remaining)
* cash-equity notional per stock <= ₹75,000 (or ₹75,000 of MIS margin in the "margin" reading)
* capital check: margin in use (MIS 20%, delivery 100%, option debit 100%) <= equity
* overnight equity risk includes a gap allowance (0.5 x daily ATR) in the sizing denominator
* optional cap on intraday entries per day (blueprint target 3-6)
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from medhaalpha.config import RiskConfig, SlippageConfig
from medhaalpha.costs import equity_costs, option_costs


@dataclass(frozen=True)
class PortfolioRules:
    risk: RiskConfig = RiskConfig()
    slip: SlippageConfig = SlippageConfig()
    gap_allowance_atr: float = 0.5
    max_intraday_per_day: int = 6
    allow_equity_short_overnight: bool = False


def _equity_cost_one(date, qty, fill, exit_px, side, intraday, n_exit, same_day) -> float:
    buy = qty * (fill if side > 0 else exit_px)
    sell = qty * (exit_px if side > 0 else fill)
    return float(equity_costs([date], [buy], [sell], [intraday], [1 + n_exit], same_day=[same_day])[0])


def run_portfolio(trades: pd.DataFrame, rules: PortfolioRules = PortfolioRules()) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Replay candidates. Returns (accepted trades with ₹ P&L, rejection log counts)."""
    if trades.empty:
        return trades.copy(), pd.DataFrame()
    r = rules.risk
    t = trades.sort_values(["fill_time", "score"], ascending=[True, False]).reset_index(drop=True)
    instrument = t["instrument"].to_numpy() if "instrument" in t else np.full(len(t), "equity", dtype=object)
    fill_time = t["fill_time"].to_numpy()
    exit_time = t["exit_time"].to_numpy()
    open_heap: list = []  # (exit_time, idx)
    open_syms: dict[str, int] = {}
    open_ind: dict[tuple, int] = {}
    open_risk = 0.0
    margin_used = 0.0
    realised = 0.0
    day_pnl: dict = {}
    week_pnl: dict = {}
    intraday_count: dict = {}
    rows = []
    rejects: dict[str, int] = {}

    def reject(reason):
        rejects[reason] = rejects.get(reason, 0) + 1

    pending: dict[int, dict] = {}

    def close_until(ts):
        nonlocal open_risk, margin_used, realised
        while open_heap and open_heap[0][0] <= ts:
            et, j = heapq.heappop(open_heap)
            p = pending.pop(j)
            open_risk -= p["risk"]
            margin_used -= p["margin"]
            realised += p["pnl_net"]
            d = pd.Timestamp(et).normalize()
            day_pnl[d] = day_pnl.get(d, 0.0) + p["pnl_net"]
            wk = d.to_period("W")
            week_pnl[wk] = week_pnl.get(wk, 0.0) + p["pnl_net"]
            open_syms[p["symbol"]] -= 1
            open_ind[p["ind_key"]] -= 1

    for i in range(len(t)):
        row = t.iloc[i]
        ts = fill_time[i]
        close_until(ts)
        d = pd.Timestamp(ts).normalize()
        wk = d.to_period("W")
        intraday = row["engine"] == "intraday"
        inst = instrument[i]
        side = int(row["side"])
        if open_syms.get(row["symbol"], 0) > 0:
            reject("symbol_open")
            continue
        if day_pnl.get(d, 0.0) <= -r.daily_loss_limit:
            reject("daily_limit")
            continue
        if week_pnl.get(wk, 0.0) <= -r.weekly_loss_limit:
            reject("weekly_limit")
            continue
        ind = str(row["industry"])
        ind_key = (ind if ind != "Other" else f"Other:{row['symbol']}", side)  # unmapped names are not one sector
        if open_ind.get(ind_key, 0) >= r.max_per_industry_direction:
            reject("industry_exposure")
            continue
        if intraday and intraday_count.get(d, 0) >= rules.max_intraday_per_day:
            reject("intraday_count")
            continue
        if inst == "equity" and not intraday and side < 0 and not rules.allow_equity_short_overnight:
            reject("no_overnight_equity_short")
            continue
        budget = min(r.risk_per_trade, r.max_open_risk - open_risk)
        if budget < r.min_trade_risk:
            reject("open_risk_cap")
            continue
        equity_now = r.capital + realised
        if inst == "equity":
            fill = float(row["fill"])
            unit_risk = float(row["risk_ps"])
            if not intraday:
                datr = float(row.get("datr_pct", np.nan)) * fill
                if not np.isfinite(datr):
                    datr = 0.02 * fill  # fallback when the prior daily ATR is unavailable
                unit_risk += rules.gap_allowance_atr * datr
            cap_notional = r.max_notional_per_stock / (r.intraday_margin_rate if (intraday and r.intraday_cap_is_margin) else 1.0)
            qty = int(min(budget // unit_risk, cap_notional // fill))
            if qty < 1:
                reject("size_zero")
                continue
            margin = qty * fill * (r.intraday_margin_rate if intraday else 1.0)
            if margin_used + margin > equity_now:
                qty = int((equity_now - margin_used) // (fill * (r.intraday_margin_rate if intraday else 1.0)))
                if qty < 1:
                    reject("capital")
                    continue
                margin = qty * fill * (r.intraday_margin_rate if intraday else 1.0)
            planned = qty * float(row["risk_ps"])
            booked = qty * unit_risk  # includes the overnight gap allowance for positional trades
            exit_px = float(row["exit"])
            gross = qty * side * (exit_px - fill)
            slip_bps = rules.slip.equity_bps * 2 + (rules.slip.stop_extra_bps if row["reason"] in ("stop", "trail", "breakeven") else 0.0)
            slippage = qty * (fill + exit_px) / 2 * slip_bps / 1e4
            costs = _equity_cost_one(d, qty, fill, exit_px, side, intraday, int(row["n_exit"]),
                                     bool(intraday or int(row["sessions"]) <= 1))
            units = qty
        else:  # option structures: per-lot economics precomputed by medhaalpha.options
            unit_risk = float(row["unit_risk"])
            if not np.isfinite(unit_risk) or unit_risk <= 0:
                reject("option_invalid")
                continue
            lots = int(budget // unit_risk)
            if lots < 1:
                reject("option_lot_exceeds_budget")
                continue
            margin = lots * float(row["unit_debit"])
            if margin_used + margin > equity_now:
                reject("capital")
                continue
            planned = lots * unit_risk
            booked = planned
            gross = lots * float(row["unit_pnl"])
            slippage = lots * float(row["unit_spread_cost"])
            costs = float(option_costs([d], [lots * row["unit_buy_prem"]], [lots * row["unit_sell_prem"]],
                                       [row["n_orders"]])[0])
            units = lots
        pnl_net = gross - slippage - costs
        rec = row.to_dict()
        rec.update(units=units, planned_risk=planned, booked_risk=booked, margin=margin, pnl_gross=gross, slippage=slippage,
                   costs=costs, pnl_net=pnl_net, R_net=pnl_net / planned if planned > 0 else np.nan,
                   risk_budget=budget)
        rows.append(rec)
        j = len(rows) - 1
        pending[j] = {"risk": booked, "margin": margin, "pnl_net": pnl_net, "symbol": row["symbol"], "ind_key": ind_key}
        heapq.heappush(open_heap, (exit_time[i], j))
        open_risk += booked
        margin_used += margin
        open_syms[row["symbol"]] = open_syms.get(row["symbol"], 0) + 1
        open_ind[ind_key] = open_ind.get(ind_key, 0) + 1
        if intraday:
            intraday_count[d] = intraday_count.get(d, 0) + 1
    close_until(np.datetime64("2100-01-01"))
    acc = pd.DataFrame(rows)
    rej = pd.DataFrame(sorted(rejects.items(), key=lambda x: -x[1]), columns=["reason", "count"])
    return acc, rej


def with_margin_reading(rules: PortfolioRules) -> PortfolioRules:
    return replace(rules, risk=replace(rules.risk, intraday_cap_is_margin=True))

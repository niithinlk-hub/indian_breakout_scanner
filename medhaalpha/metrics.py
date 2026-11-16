"""Signal-level and portfolio-level performance statistics."""
from __future__ import annotations

import numpy as np
import pandas as pd

from medhaalpha.config import RiskConfig, SlippageConfig
from medhaalpha.costs import equity_costs

GROUP = ["engine", "tf", "entry", "side", "exit_spec", "daily_thr"]


def non_overlapping(trades: pd.DataFrame, keys=GROUP) -> pd.DataFrame:
    """Within each config and symbol keep trades sequentially (no new entry while one is open)."""
    if trades.empty:
        return trades
    t = trades.sort_values(keys + ["symbol", "fill_time"]).reset_index(drop=True)
    grp = t.groupby(keys + ["symbol"], sort=False, dropna=False).ngroup().to_numpy()
    ft = t["fill_time"].to_numpy()
    et = t["exit_time"].to_numpy()
    keep = np.zeros(len(t), bool)
    last_g, last_exit = -1, np.datetime64("1970-01-01")
    for i in range(len(t)):
        if grp[i] != last_g:
            last_g, last_exit = grp[i], np.datetime64("1970-01-01")
        if ft[i] >= last_exit:
            keep[i] = True
            last_exit = et[i]
    return t[keep].reset_index(drop=True)


def standalone_net(trades: pd.DataFrame, risk: RiskConfig = RiskConfig(), slip: SlippageConfig = SlippageConfig(),
                   cap_is_margin: bool = False, keep_zero: bool = False) -> pd.DataFrame:
    """Size every trade on its own (₹3,000 risk, ₹75k notional cap) and compute net P&L and net R.

    This isolates signal quality from portfolio interactions (limits, overlaps)."""
    t = trades.copy()
    intraday = (t["engine"] == "intraday").to_numpy()
    fill = t["fill"].to_numpy()
    exit_ = t["exit"].to_numpy()
    side = t["side"].to_numpy()
    unit_risk = t["risk_ps"].to_numpy().copy()
    gap = 0.5 * np.nan_to_num(t.get("datr_pct", pd.Series(np.nan, index=t.index)).to_numpy(), nan=0.02) * fill
    unit_risk = np.where(intraday, unit_risk, unit_risk + gap)
    cap = np.where(intraday & cap_is_margin, risk.max_notional_per_stock / risk.intraday_margin_rate,
                   risk.max_notional_per_stock)
    qty = np.floor(np.minimum(risk.risk_per_trade / unit_risk, cap / fill))
    qty = np.maximum(qty, 0)
    gross = qty * side * (exit_ - fill)
    stopish = t["reason"].isin(["stop", "trail", "breakeven"]).to_numpy()
    slippage = qty * (fill + exit_) / 2 * (slip.equity_bps * 2 + np.where(stopish, slip.stop_extra_bps, 0)) / 1e4
    buy = qty * np.where(side > 0, fill, exit_)
    sell = qty * np.where(side > 0, exit_, fill)
    same_day = intraday | (t["sessions"].to_numpy() <= 1)
    costs = equity_costs(t["date"].to_numpy(), buy, sell, intraday, 1 + t["n_exit"].to_numpy(), same_day=same_day)
    costs = np.where(qty > 0, costs, 0.0)
    planned = qty * t["risk_ps"].to_numpy()
    t["qty"] = qty
    t["notional"] = qty * fill
    t["planned_risk"] = planned
    t["pnl_gross"] = gross
    t["friction"] = slippage + costs
    t["pnl_net"] = gross - slippage - costs
    with np.errstate(divide="ignore", invalid="ignore"):
        t["R_net"] = np.where(planned > 0, t["pnl_net"] / planned, np.nan)
        t["cost_R"] = np.where(planned > 0, t["friction"] / planned, np.nan)
    if keep_zero:
        for c in ("pnl_net", "R_net", "cost_R"):
            t.loc[qty <= 0, c] = np.nan
        return t
    return t[qty > 0]


def summarize(trades: pd.DataFrame, keys=GROUP, n_days: int | None = None) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()

    def agg(g):
        r = g["R"].to_numpy()
        rn = g["R_net"].to_numpy() if "R_net" in g else r
        pn = g["pnl_net"].to_numpy() if "pnl_net" in g else r
        wins = pn[pn > 0].sum()
        losses = -pn[pn < 0].sum()
        days = n_days or max(1, g["date"].nunique())
        return pd.Series({
            "trades": len(g),
            "trades_per_day": len(g) / days,
            "win_rate": float((pn > 0).mean()),
            "avg_R_gross": float(np.mean(r)),
            "avg_R_net": float(np.nanmean(rn)),
            "t_stat_net": float(np.nanmean(rn) / (np.nanstd(rn, ddof=1) + 1e-12) * np.sqrt(len(rn))) if len(rn) > 2 else np.nan,
            "profit_factor": float(wins / losses) if losses > 0 else np.inf,
            "net_pnl": float(pn.sum()),
            "avg_cost_R": float(np.nanmean(g["cost_R"])) if "cost_R" in g else np.nan,
            "avg_hold_min": float((g["exit_time"] - g["fill_time"]).dt.total_seconds().mean() / 60),
            "avg_sessions": float(g["sessions"].mean()),
        })

    return trades.groupby(keys, dropna=False).apply(agg, include_groups=False).reset_index()


# ------------------------------------------------------------------ portfolio statistics
def _mtm_adjustments(acc: pd.DataFrame) -> pd.Series:
    """Daily mark-to-market shifts for multi-session trades: unrealised P&L at each intermediate close is
    booked on that day and reversed on the exit day, so the curve shows open losses (realised total unchanged)."""
    from medhaalpha.data import loader

    adj: dict = {}
    multi = acc[(acc["sessions"] > 1) & (acc.get("instrument", "equity") == "equity")] if "instrument" in acc else acc[acc["sessions"] > 1]
    closes: dict = {}
    for row in multi.itertuples(index=False):
        if row.symbol not in closes:
            d = loader.load_daily(row.symbol)
            closes[row.symbol] = d.set_index("date")["close"]
        cl = closes[row.symbol]
        d0, d1 = pd.Timestamp(row.fill_time).normalize(), pd.Timestamp(row.exit_time).normalize()
        path = cl[(cl.index >= d0) & (cl.index < d1)]
        prev = 0.0
        units = getattr(row, "units", np.nan)
        for day, c in path.items():
            u = units * row.side * (c - row.fill)
            adj[day] = adj.get(day, 0.0) + (u - prev)
            prev = u
        adj[d1] = adj.get(d1, 0.0) - prev
    return pd.Series(adj, dtype=float)


def equity_curve(acc: pd.DataFrame, start, end, capital: float, mtm: bool = True) -> pd.DataFrame:
    days = pd.bdate_range(start, end)
    if acc.empty:
        return pd.DataFrame({"date": days, "pnl": 0.0, "equity": capital})
    pnl = acc.groupby(acc["exit_time"].dt.normalize())["pnl_net"].sum()
    if mtm and "units" in acc:
        pnl = pnl.add(_mtm_adjustments(acc), fill_value=0.0)
    # real calendar: weekday sessions plus any special weekend sessions and every exit date
    days = days.union(pd.DatetimeIndex(pnl.index)).sort_values()
    pnl = pnl.reindex(days, fill_value=0.0)
    eq = capital + pnl.cumsum()
    assert abs(pnl.sum() - acc["pnl_net"].sum()) < 1e-6 * max(1.0, abs(acc["pnl_net"].sum())) + 1e-3
    return pd.DataFrame({"date": days, "pnl": pnl.to_numpy(), "equity": eq.to_numpy()})


def longest_losing_streak(pnl: np.ndarray) -> int:
    best = cur = 0
    for x in pnl:
        cur = cur + 1 if x < 0 else 0
        best = max(best, cur)
    return best


def portfolio_stats(acc: pd.DataFrame, start, end, capital: float = 300_000.0) -> dict:
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    ec = equity_curve(acc, start, end, capital)
    end = max(end, ec["date"].iloc[-1])
    years = max((end - start).days / 365.25, 1e-9)
    final = ec["equity"].iloc[-1]
    peak = ec["equity"].cummax()
    dd = ec["equity"] - peak
    mdd = float(dd.min())
    mdd_pct = float((dd / peak).min() * 100)
    daily_ret = ec["pnl"] / ec["equity"].shift(1).fillna(capital)
    sharpe = float(daily_ret.mean() / (daily_ret.std() + 1e-12) * np.sqrt(250))
    n_tr = len(acc)
    out = {
        "start": str(start.date()), "end": str(end.date()), "trades": n_tr,
        "net_profit": float(final - capital), "return_pct": float((final / capital - 1) * 100),
        "cagr_pct": float(((final / capital) ** (1 / years) - 1) * 100) if final > 0 else -100.0,
        "max_drawdown": mdd, "max_drawdown_pct": mdd_pct, "sharpe_daily": sharpe,
    }
    if n_tr == 0:
        return out
    pn = acc["pnl_net"].to_numpy()
    wins, losses = pn[pn > 0], pn[pn < 0]
    trading_days = len(ec)
    order = acc.sort_values("exit_time")["pnl_net"].to_numpy()
    top_n = max(1, int(round(0.05 * n_tr)))
    sorted_pn = np.sort(pn)[::-1]
    hold = (acc["exit_time"] - acc["fill_time"]).dt.total_seconds() / 60
    out.update({
        "profit_factor": float(wins.sum() / -losses.sum()) if len(losses) else np.inf,
        "win_rate_pct": float(len(wins) / n_tr * 100),
        "avg_win": float(wins.mean()) if len(wins) else 0.0,
        "avg_loss": float(losses.mean()) if len(losses) else 0.0,
        "realised_reward_risk": float(wins.mean() / -losses.mean()) if len(wins) and len(losses) else np.nan,
        "expectancy_per_trade": float(pn.mean()),
        "expectancy_R": float(acc["R_net"].mean()),
        "avg_planned_risk": float(acc["planned_risk"].mean()),
        "trades_per_day": float(n_tr / trading_days),
        "avg_hold_minutes": float(hold.mean()),
        "avg_sessions": float(acc["sessions"].mean()),
        "longest_losing_streak": longest_losing_streak(order),
        "total_costs": float(acc["costs"].sum()), "total_slippage": float(acc["slippage"].sum()),
        "gross_pnl": float(acc["pnl_gross"].sum()),
        "pnl_ex_top5pct": float(sorted_pn[top_n:].sum()),
        "top5pct_share_of_net": float(sorted_pn[:top_n].sum() / pn.sum()) if pn.sum() != 0 else np.nan,
        "intraday_pnl": float(acc.loc[acc["engine"] == "intraday", "pnl_net"].sum()),
        "positional_pnl": float(acc.loc[acc["engine"] == "positional", "pnl_net"].sum()),
        "worst_day": float(ec["pnl"].min()),
        "best_day": float(ec["pnl"].max()),
    })
    return out


def monthly_returns(acc: pd.DataFrame, capital: float = 300_000.0) -> pd.DataFrame:
    if acc.empty:
        return pd.DataFrame()
    m = acc.groupby(acc["exit_time"].dt.to_period("M"))["pnl_net"].agg(["sum", "count"])
    m["return_pct_of_capital"] = m["sum"] / capital * 100
    return m.reset_index().rename(columns={"exit_time": "month", "sum": "net_pnl", "count": "trades"})

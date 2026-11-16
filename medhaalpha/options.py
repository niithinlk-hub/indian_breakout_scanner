"""Stock-option instrument selection and pricing from real NSE bhavcopy chains.

Signals come from the underlying; this module maps each underlying trade to an option
structure and prices it:

* Contract universe: the previous session's F&O bhavcopy (known before the trade) — actual
  strikes, expiries, lot sizes, closing prices, volume and OI.
* Expiry: intraday >= 7 calendar days to expiry; positional >= 14 days (never hold into the
  physically-settled expiry week).
* Strike: delta closest to 0.55 within 0.40-0.65 (calls for longs, puts for shorts) among
  contracts that traded >= 10 contracts in the prior session.
* Debit spread: buy that strike, sell the liquid strike nearest the 2R underlying target
  (at least one strike further OTM).
* Pricing: Black-Scholes with the contract's own implied volatility from the latest completed
  session before the pricing moment (sticky strike), on the underlying's actual intraday
  price at the entry/exit timestamps. Bid-ask: half-spread of 1% of premium (2.5% if the
  contract traded < 200 lots the prior day), at least one tick, paid on every leg/side.
* Positional cross-check: the same contracts re-priced with actual bhavcopy closing prices
  (entry at the entry-day close, exit at the exit-day close).

Sizing (portfolio.py) uses `unit_risk` per lot:
  strict  -> maximum possible loss per lot (premium or spread debit + spread costs + fees)
  relaxed -> modelled loss per lot if the underlying stop is hit (INFORMATION ONLY: this
             breaks the blueprint's hard ₹3,000 maximum-loss rule).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import ndtr

from medhaalpha.config import SlippageConfig
from medhaalpha.data import loader
from medhaalpha.paths import BHAV_DIR

R_FREE = 0.06
YEAR_MIN = 365.0 * 24 * 60


def bs_price(S, K, T, sigma, call):
    S, K, T, sigma = (np.asarray(x, float) for x in (S, K, T, sigma))
    T = np.maximum(T, 1e-6)
    sq = sigma * np.sqrt(T)
    d1 = (np.log(S / K) + (R_FREE + 0.5 * sigma**2) * T) / sq
    d2 = d1 - sq
    df = np.exp(-R_FREE * T)
    c = S * ndtr(d1) - K * df * ndtr(d2)
    p = K * df * ndtr(-d2) - S * ndtr(-d1)
    return np.where(call, c, p)


def bs_delta(S, K, T, sigma, call):
    T = np.maximum(np.asarray(T, float), 1e-6)
    d1 = (np.log(S / K) + (R_FREE + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    return np.where(call, ndtr(d1), ndtr(d1) - 1.0)


def implied_vol(price, S, K, T, call, lo=0.01, hi=3.0, iters=60):
    price, S, K, T = (np.asarray(x, float) for x in (price, S, K, T))
    lo_a = np.full(price.shape, lo)
    hi_a = np.full(price.shape, hi)
    pmin = bs_price(S, K, T, lo_a, call)
    pmax = bs_price(S, K, T, hi_a, call)
    ok = (price > pmin) & (price < pmax)
    for _ in range(iters):
        mid = 0.5 * (lo_a + hi_a)
        pm = bs_price(S, K, T, mid, call)
        up = pm < price
        lo_a = np.where(up, mid, lo_a)
        hi_a = np.where(up, hi_a, mid)
    iv = 0.5 * (lo_a + hi_a)
    return np.where(ok, iv, np.nan)


# ------------------------------------------------------------------ chain loading
def load_chains(symbols: set[str]) -> pd.DataFrame:
    smap = loader.symbol_map()
    alias = dict(zip(smap["symbol"], smap["canonical"]))
    cols = ["date", "symbol", "expiry", "strike", "opt_type", "close", "settle", "underlying", "volume", "oi", "lot"]
    ch = pd.read_parquet(BHAV_DIR / "options_all.parquet", columns=cols)
    ch["canonical"] = ch["symbol"].map(alias)
    ch = ch[ch["canonical"].isin(symbols)].copy()
    ch["call"] = ch["opt_type"] == "CE"
    ch["exp_ts"] = ch["expiry"] + pd.Timedelta(hours=15, minutes=30)
    t = (ch["exp_ts"] - (ch["date"] + pd.Timedelta(hours=15, minutes=30))).dt.total_seconds() / 60 / YEAR_MIN
    px = ch["close"].where(ch["volume"] > 0, ch["settle"])
    ch["iv"] = implied_vol(px.to_numpy(), ch["underlying"].to_numpy(), ch["strike"].to_numpy(), t.to_numpy(),
                           ch["call"].to_numpy())
    return ch


def _prev_session(days: pd.DatetimeIndex, d: pd.Timestamp) -> pd.Timestamp | None:
    i = days.searchsorted(d) - 1
    return days[i] if i >= 0 else None


def build_option_trades(trades: pd.DataFrame, chains: pd.DataFrame, structure: str, target_r: float = 2.0,
                        slip: SlippageConfig = SlippageConfig()) -> pd.DataFrame:
    """Map underlying trades to option structures. structure: 'long' (call/put) or 'spread' (debit)."""
    days = pd.DatetimeIndex(sorted(chains["date"].unique()))
    by_key = {k: g for k, g in chains.groupby(["canonical", "date"], sort=False)}
    daily_close = {}
    out = []
    for row in trades.itertuples(index=False):
        d = pd.Timestamp(row.fill_time).normalize()
        prev = _prev_session(days, d)
        info = {"opt_status": "no_chain"}
        if prev is None or (row.symbol, prev) not in by_key:
            out.append(info)
            continue
        chain = by_key[(row.symbol, prev)]
        call = row.side > 0
        # scale between adjusted candles and the bhavcopy's unadjusted underlying
        if row.symbol not in daily_close:
            dd = loader.load_daily(row.symbol)
            daily_close[row.symbol] = dd.set_index("date")["close"]
        ucl = daily_close[row.symbol].get(prev, np.nan)
        und = float(chain["underlying"].iloc[0])
        ratio = und / ucl if np.isfinite(ucl) and ucl > 0 else 1.0
        s_in = row.fill * ratio
        s_out = row.exit * ratio
        min_days = 7 if row.engine == "intraday" else 14
        exps = sorted(e for e in chain["expiry"].unique() if (e - d).days >= min_days)
        if not exps:
            info["opt_status"] = "no_expiry"
            out.append(info)
            continue
        exp = exps[0]
        c = chain[(chain["expiry"] == exp) & (chain["call"] == call) & (chain["volume"] >= 10)
                  & chain["iv"].notna()]
        if c.empty:
            info["opt_status"] = "illiquid"
            out.append(info)
            continue
        t_in = (pd.Timestamp(exp) + pd.Timedelta(hours=15, minutes=30) - pd.Timestamp(row.fill_time)).total_seconds() / 60 / YEAR_MIN
        delta = np.abs(bs_delta(s_in, c["strike"].to_numpy(), t_in, c["iv"].to_numpy(), call))
        okd = (delta >= 0.40) & (delta <= 0.65)
        if not okd.any():
            info["opt_status"] = "no_delta_strike"
            out.append(info)
            continue
        j = np.flatnonzero(okd)[np.argmin(np.abs(delta[okd] - 0.55))]
        leg = c.iloc[j]
        lot = float(leg["lot"])
        x_day = pd.Timestamp(row.exit_time).normalize()
        x_prev = _prev_session(days, x_day) if x_day > d else prev
        t_out = (pd.Timestamp(exp) + pd.Timedelta(hours=15, minutes=30) - pd.Timestamp(row.exit_time)).total_seconds() / 60 / YEAR_MIN

        def iv_on(day, strike):
            g = by_key.get((row.symbol, day))
            if g is None:
                return np.nan
            m = g[(g["expiry"] == exp) & (g["strike"] == strike) & (g["call"] == call)]
            return float(m["iv"].iloc[0]) if len(m) and np.isfinite(m["iv"].iloc[0]) else np.nan

        def leg_prices(strike, iv0, liquid_vol):
            iv1 = iv_on(x_prev, strike)
            iv1 = iv0 if not np.isfinite(iv1) else iv1
            p_in = float(bs_price(s_in, strike, t_in, iv0, call))
            p_out = float(bs_price(s_out, strike, t_out, iv1, call))
            hs = slip.option_half_spread_liquid if liquid_vol >= 200 else slip.option_half_spread_illiquid
            spr_in = max(hs * p_in, slip.option_tick)
            spr_out = max(hs * p_out, slip.option_tick)
            # premium at the underlying stop (for the relaxed risk reading), 1 hour after entry
            s_stop = row.stop * ratio
            p_stop = float(bs_price(s_stop, strike, max(t_in - 60 / YEAR_MIN, 1e-6), iv0, call))
            return p_in, p_out, spr_in, spr_out, p_stop

        p_in, p_out, si, so, p_stop = leg_prices(float(leg["strike"]), float(leg["iv"]), float(leg["volume"]))
        info.update(opt_status="ok", expiry=exp, strike=float(leg["strike"]), lot=lot, iv=float(leg["iv"]),
                    delta=float(delta[j]), prem_in=p_in, prem_out=p_out, days_to_expiry=(exp - d).days)
        fees_lot = 0.0  # brokerage/stat fees handled in portfolio cost function per order
        if structure == "long":
            unit_debit = (p_in + si) * lot
            info.update(
                instrument="call" if call else "put",
                unit_pnl=(p_out - p_in) * lot,
                unit_spread_cost=(si + so) * lot,
                unit_buy_prem=p_in * lot, unit_sell_prem=p_out * lot,
                unit_debit=unit_debit,
                unit_risk_strict=unit_debit + 45.0 + fees_lot,
                unit_risk_relaxed=max((p_in - p_stop) * lot + (si + so) * lot + 45.0, 1.0),
                n_orders=2,
            )
        else:
            target = s_in + (1 if call else -1) * target_r * abs(row.fill - row.stop) * ratio
            k1 = float(leg["strike"])
            shorts = c[(c["strike"] > k1) if call else (c["strike"] < k1)]
            if shorts.empty:
                info["opt_status"] = "no_short_leg"
                out.append(info)
                continue
            k2row = shorts.iloc[np.argmin(np.abs(shorts["strike"].to_numpy() - target))]
            k2 = float(k2row["strike"])
            q_in, q_out, ti, to, q_stop = leg_prices(k2, float(k2row["iv"]), float(k2row["volume"]))
            debit = p_in - q_in
            if debit <= 0:
                info["opt_status"] = "bad_spread"
                out.append(info)
                continue
            width = abs(k2 - k1)
            unit_debit = (debit + si + ti) * lot
            info.update(
                instrument="bull_call_spread" if call else "bear_put_spread", strike2=k2, width=width,
                prem2_in=q_in, prem2_out=q_out,
                unit_pnl=((p_out - q_out) - (p_in - q_in)) * lot,
                unit_spread_cost=(si + so + ti + to) * lot,
                unit_buy_prem=(p_in + q_out) * lot, unit_sell_prem=(p_out + q_in) * lot,
                unit_debit=unit_debit,
                unit_risk_strict=unit_debit + 90.0,
                unit_risk_relaxed=max(((p_in - q_in) - (p_stop - q_stop)) * lot + (si + so + ti + to) * lot + 90.0, 1.0),
                n_orders=4,
            )
        # EOD cross-check (positional only): actual bhavcopy closes vs the model at the same closes
        if row.engine == "positional" and x_day > d:
            g_in = by_key.get((row.symbol, d))
            g_out = by_key.get((row.symbol, x_day))
            cl = daily_close[row.symbol]
            if g_in is not None and g_out is not None and d in cl.index and x_day in cl.index:
                def close_of(g, k):
                    m = g[(g["expiry"] == exp) & (g["strike"] == k) & (g["call"] == call)]
                    return float(m["close"].iloc[0]) if len(m) else np.nan

                def model_at(day, k, iv_day):
                    iv = iv_on(iv_day, k)
                    tt = (pd.Timestamp(exp) - day).days / 365.0
                    return float(bs_price(cl[day] * ratio, k, tt, iv, call)) if np.isfinite(iv) else np.nan

                ks = [info["strike"]] + ([info["strike2"]] if structure == "spread" else [])
                act = [(close_of(g_out, k) - close_of(g_in, k)) for k in ks]
                mod = [(model_at(x_day, k, x_prev) - model_at(d, k, prev)) for k in ks]
                sign = [1.0, -1.0][: len(ks)]
                info["eod_actual_unit_pnl"] = sum(a * w for a, w in zip(act, sign)) * lot
                info["eod_model_unit_pnl"] = sum(m * w for m, w in zip(mod, sign)) * lot
        out.append(info)
    res = pd.DataFrame(out, index=trades.index)
    return pd.concat([trades, res], axis=1)

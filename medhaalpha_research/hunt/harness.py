"""Shared test bench for the "better algorithm" hunt. Every candidate is judged here, the same way as the baselines.

Signal sets (each row = one scanner signal of setup A (long, trend breakout) or B (short, breakdown), with the
features known at the signal minute and the result of every exit policy, sized to risk Rs 15,000 a trade,
after charges and 0.02 % slippage a side):
  real    12 May - 11 Nov 2026, 126 sessions, REAL futures prices (the scanner's own six-month backtest).
  unseen  3 Nov 2025 - 11 May 2026, 131 sessions, cash-share stand-in prices (the scanner replayed on cash
          candles). No model here was built on these dates -> the fairest test.
  known   12 May - 19 Oct 2026, 115 sessions, cash-share stand-in for the same dates as `real` (cross-check).
Exit policies (columns net_<P>, r_<P>):  T1 (book all at 1.0R), T2 (1.9R), T3 (2.6R), CLOSE (stop only, square off
  at the close), T2_TR / T3_TR / CLOSE_TR (same, stop trails: to entry after T1, to T1 after T2, to T2 after T3).
  Stop is unchanged in T1/T2/T3/CLOSE. Positions that are still open at 15:29 are squared off.
Live rule (how the scanner trades): per day, in time order (ties: higher score, then symbol), take the first
  n=6 signals whose score >= threshold.  Baselines:
  opus_v3  T1 exit, score opus_v3 >= 75     fable_op  T3 exit, score fable_op >= 75
  switch1  fable_op T3 except on downtrend days (regime A) where opus_v3 T1 is used
Usage:  import harness as H;  D = H.load_all();  H.compare(D, {'my rule': (score_fn, thr, policy, n)})
  score_fn takes the DataFrame and returns a Series of scores (higher = better; NaN = never taken).
"""
import glob, json, os, pickle, sys
import numpy as np
import pandas as pd

SP = os.environ.get('MEDHA_SP', '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad')
POL = ['T1', 'T2', 'T3', 'CLOSE', 'T2_TR', 'T3_TR', 'CLOSE_TR']
COMMON = ['day_chg', 'gap', 'from_open', 'pos', 'beyond_pd', 'beyond_vwap', 'rel_vol', 'n_break', 'rsi14', 'vs20', 'ret5', 'ret20',
          'nifty_chg', 'mins_since_extreme', 'minutes_since_open', 'atr_pct', 'from_52w_high', 'from_52w_low', 'price', 'risk_pct', 'stop_atr']
# Feature meanings (all at the signal minute; "direction-adjusted" = sign flipped for shorts so bigger = further in the trade's way):
#  day_chg  % change vs previous close, direction-adjusted     gap  opening gap %, direction-adjusted
#  from_open % move from today's open, direction-adjusted      pos  position in today's range 0..1 (1 = at the extreme in trade direction)
#  beyond_pd % beyond previous day's high (long) / low (short)  beyond_vwap % beyond VWAP in trade direction
#  rel_vol  volume so far / normal volume by this time of day  n_break  number of prior bars broken (lookback breadth of the breakout)
#  rsi14  daily RSI(14) incl. today                            vs20 % vs 20-day average   ret5/ret20  5/20-day return %
#  nifty_chg  Nifty % change today (raw)                       mins_since_extreme  minutes since the day's extreme in trade direction
#  minutes_since_open                                          atr_pct  daily ATR(14) as % of price
#  from_52w_high / from_52w_low  % from 52-week high / low    risk_pct  stop distance % of price    stop_atr  stop distance in daily ATRs
REAL_ONLY = ['breadth_dir', 'breadth_med_dir', 'strong_dir', 'crowd_same', 'crowd_all', 'same_minute', 'range_atr', 'nifty_from_open', 'structure']
SETS = ('real', 'unseen', 'known')
SPAN = {'real': ('2026-05-12', '2026-11-11'), 'unseen': ('2025-11-03', '2026-05-11'), 'known': ('2026-05-12', '2026-10-19')}


def _scores(d):
    lg = d['side'] == 'LONG'
    d['s_opus_v2'] = np.where(lg, d['s_fable_op'], d['s_opus'])
    d['s_opus_v3'] = np.where(lg, np.where(d['rel_vol'] < 1.0, 0.0, d['s_fable_op']), d['s_opus'])
    return d


def load_real():
    sys.path.insert(0, SP + '/v2')
    six = json.load(open(SP + '/six/pull.json'))['sig']
    PI = {p: i for i, p in enumerate(six['policies'])}
    rows = pickle.load(open(SP + '/v2/data/feat.pkl', 'rb'))
    recs = []
    for r in rows:
        if r['setup'] not in ('A', 'B') or r['net'][PI['T1']] is None:
            continue
        f = r['f']
        d = {'day': r['day'], 'time': r['time'], 'symbol': r['symbol'], 'setup': r['setup'], 'side': r['side'], 'stop_at': f.get('stop_at')}
        for k, v in f.items():
            if k not in ('prev_day', 'price_basis', 'stop_at'):
                d[k] = np.nan if v is None else float(v)
        d['stop_atr'] = d['risk_pct'] / d['atr_pct'] if d.get('atr_pct') else np.nan
        d['s_opus'], d['s_fable'], d['s_fable_op'] = r['true']['opus'], r['true']['fable'] - 5.0, r['true']['fable_op']
        for p in POL:
            d['net_' + p], d['r_' + p] = r['net'][PI[p]], r['r'][PI[p]]
        d['status_T1'] = {'hit': 'target', 'stop': 'stopped'}.get(r['out'], 'close')
        recs.append(d)
    return _scores(pd.DataFrame(recs))


def load_proxy(pdir):
    recs = []
    for p in sorted(glob.glob(pdir + '/proxy_*.json')):
        doc = json.load(open(p))
        for s in doc['signals']:
            if s['setup'] not in ('A', 'B') or s['fut']['T1']['status'] == 'no_data':
                continue
            d = {'day': doc['day'], 'time': s['time'], 'symbol': s['symbol'], 'setup': s['setup'], 'side': s['side'], 'stop_at': s.get('stop_at')}
            for k, v in s['snapshot'].items():
                d[k] = np.nan if v is None else float(v)
            d['risk_pct'], d['stop_atr'] = s.get('risk_pct'), s.get('stop_atr')
            d['entry_ref'], d['stop'], d['t1'], d['t2'], d['t3'], d['lot'], d['lots'] = s['entry_ref'], s['stop'], s['t1'], s['t2'], s['t3'], s['lot'], s['lots']
            for m in ('opus', 'fable', 'fable_op'):
                d['s_' + m] = s['scores'][m]
            d['s_fable'] -= 5.0
            for q in POL:
                o = s['fut'].get(q) or {}
                d['net_' + q], d['r_' + q] = o.get('net_rs', np.nan), o.get('r', np.nan)
            d['status_T1'] = s['fut']['T1']['status']
            recs.append(d)
    return _scores(pd.DataFrame(recs))


_REG = None


def regime():
    """Per day: label A (Uptrend / Downtrend / Sideways from Nifty's prev close vs 20- and 50-day averages, known before the open)
    plus prev, ma20, ma50, r20 (20-day % change to previous close), chg (that day's Nifty % change; hindsight)."""
    global _REG
    if _REG is None:
        nd = json.load(open(SP + '/v2/data/nifty_daily.json'))['data']['candles']
        N = pd.DataFrame(nd, columns=['ts', 'o', 'h', 'l', 'c', 'v', 'oi']).assign(day=lambda x: x.ts.str[:10]).sort_values('day').set_index('day')
        c = N.c
        prev, ma20, ma50 = c.shift(1), c.rolling(20).mean().shift(1), c.rolling(50).mean().shift(1)
        R = pd.DataFrame({'prev': prev, 'ma20': ma20, 'ma50': ma50, 'r20': (c.shift(1) / c.shift(21) - 1) * 100, 'chg': (c / prev - 1) * 100})
        R['A'] = np.where((prev > ma20) & (ma20 > ma50), 'Uptrend', np.where((prev < ma20) & (ma20 < ma50), 'Downtrend', 'Sideways'))
        _REG = R
    return _REG


def load_all(cache=True):
    f = SP + '/hunt/sets_opt.pkl'
    if cache and os.path.exists(f):
        return pickle.load(open(f, 'rb'))
    f0 = SP + '/hunt/sets.pkl'
    if os.path.exists(f0):
        D = pickle.load(open(f0, 'rb'))
    else:
        D = {'real': load_real(), 'unseen': load_proxy(SP + '/v2/proxy_unseen'), 'known': load_proxy(SP + '/v2/proxy_known')}
        R = regime()
        for k, d in D.items():
            d['regime'] = d['day'].map(R['A'])
            d.sort_values(['day', 'time', 'symbol'], inplace=True, kind='stable')
            d.reset_index(drop=True, inplace=True)
        pickle.dump(D, open(f0, 'wb'))
    fi = SP + '/hunt/opt_inputs.pkl'
    if os.path.exists(fi):
        I = pickle.load(open(fi, 'rb'))
        for k, d in D.items():
            X = I[k]
            for c in X.columns:
                d['o_' + c] = X[c].values
            for p in POL:
                d['opt_' + p] = option_net(d, p)
    if cache:
        pickle.dump(D, open(f, 'wb'))
    return D


# ---------------------------------------------------------------------------------------------- options
# The scanner buys the at-the-money call (long) or put (short) of the futures contract's monthly expiry, same number of
# lots as the future, enters the minute after the signal, and sells at the open of the minute after the FUTURES leg
# exits (stop, target, trail or 15:29 square-off). No stop on the premium. Charges as the scanner's costs.py for
# options plus 0.25 % slippage a side on the premium.
# Option prices are MODELLED (Black-76), calibrated on 1,960 real option exits the scanner recorded 21 Oct-13 Nov 2026:
#   IV = exp(-0.414 + 0.757 ln(rv) + 0.034 [put]), rv = atr_pct x sqrt(252) / 125 (stock's daily ATR as annual vol)
#   time decay during the session = 2.31 x calendar time (fitted so modelled total = real total)
#   check against the real legs: correlation 0.97 per trade, every exit policy's total within 1-7 %.
# Per-row inputs (columns o_*): o_F0 underlying at entry, o_entry_ts, o_F1_<P> / o_exit_ts_<P> underlying and time
#   at the futures exit for policy P, o_expiry (scanner's contract), o_next_expiry, o_qty (lots x lot), o_kind CE/PE,
#   o_iv. Ready-made columns opt_<P> = option net Rs for policy P with the scanner's defaults.
# Limits: no volatility skew (strikes away from the money use the same IV), IV is a fitted level not the day's real
#   IV, real set exit times come from a cash-candle replay. Treat option figures as estimates good to roughly +-10 %.
DECAY = 2.31


def _b76(F, K, T, s, call):
    from scipy.special import ndtr
    F, K, T, s = (np.asarray(x, float) for x in (F, K, T, s))
    Tp = np.maximum(T, 1e-9)
    v = s * np.sqrt(Tp)
    d1 = (np.log(F / K) + 0.5 * v * v) / v
    d2 = d1 - v
    c = F * ndtr(d1) - K * ndtr(d2)
    p = K * ndtr(-d2) - F * ndtr(-d1)
    val = np.where(call, c, p)
    intr = np.where(call, np.maximum(F - K, 0), np.maximum(K - F, 0))
    return np.where(T <= 0, intr, val)


def opt_costs(p0, p1, q, slip_pct=0.25):
    t0, t1 = p0 * q, p1 * q
    b0, b1 = np.where(t0 > 0, 20.0, 0.0), np.where(t1 > 0, 20.0, 0.0)
    ex0, ex1 = t0 * 0.03553 / 100, t1 * 0.03553 / 100
    se0, se1 = t0 * 1e-6, t1 * 1e-6
    return b0 + b1 + ex0 + ex1 + se0 + se1 + t0 * 0.003 / 100 + t1 * 0.15 / 100 + 0.18 * (b0 + b1 + ex0 + ex1 + se0 + se1) + (p0 + p1) * q * slip_pct / 100


def _years(ts, exp):
    t = pd.to_datetime(pd.Series(ts), utc=True)
    e = pd.to_datetime(pd.Series(exp) + ' 10:00', utc=True)      # 15:30 IST = 10:00 UTC
    return ((e - t).dt.total_seconds() / (365.0 * 86400)).to_numpy()


def option_net(df, pol, strike_pct=0.0, expiry='std', lots_mult=1.0, iv_mult=1.0, decay=DECAY, slip_pct=0.25, qty=None, exit_lag_min=1.0,
               detail=False):
    """Modelled option net Rs per row for exit policy `pol` (the option is sold when the futures leg exits under `pol`).
    strike_pct: strike distance from the money in % of price, + = in the money, - = out of the money.
    expiry: 'std' (the scanner's contract) or 'next' (one month further). lots_mult scales the lots; qty overrides quantity.
    detail=True returns a DataFrame with premium at entry/exit, quantity, outlay and net."""
    call = (df['o_kind'] == 'CE').to_numpy()
    F0, F1 = df['o_F0'].to_numpy(float), df['o_F1_' + pol].to_numpy(float)
    K = F0 * np.where(call, 1 - strike_pct / 100, 1 + strike_pct / 100)
    exp = df['o_expiry'] if expiry == 'std' else df['o_next_expiry']
    T0 = _years(df['o_entry_ts'], exp)
    hold = (pd.to_datetime(df['o_exit_ts_' + pol], utc=True) - pd.to_datetime(df['o_entry_ts'], utc=True)).dt.total_seconds().to_numpy() / 60 + exit_lag_min
    T1 = T0 - decay * hold / 525600
    s = df['o_iv'].to_numpy(float) * iv_mult
    p0, p1 = _b76(F0, K, T0, s, call), _b76(F1, K, T1, s, call)
    q = (df['o_qty'].fillna(0).to_numpy(float) * lots_mult) if qty is None else np.asarray(qty, float)
    net = q * (p1 - p0) - opt_costs(p0, p1, q, slip_pct)
    net = np.where(np.isfinite(net) & (q > 0), net, 0.0)
    if detail:
        return pd.DataFrame({'p0': p0, 'p1': p1, 'qty': q, 'outlay': p0 * q, 'net': net}, index=df.index)
    return pd.Series(net, index=df.index)


def pick(df, score, thr=75.0, n=6):
    """Live rule. score: column name or Series aligned to df. Returns the selected rows (a copy)."""
    s = df[score] if isinstance(score, str) else pd.Series(score, index=df.index)
    d = df.assign(_s=s.astype(float))
    d = d[d._s >= thr].sort_values(['day', 'time', '_s', 'symbol'], ascending=[True, True, False, True], kind='stable')
    return d.groupby('day', sort=True).head(n)


def summ(t, pol, days=None):
    """Totals for selected trades `t` under exit policy `pol`. days = list of all sessions in the set (for flat days)."""
    net = t['net_' + pol]
    byday = net.groupby(t['day']).sum()
    if days is not None:
        byday = byday.reindex(days).fillna(0.0)
    eq = byday.cumsum()
    n = len(t)
    return {'n': n, 'net': float(net.sum()), 'per_trade': float(net.mean()) if n else 0.0,
            'hit_T1%': 100.0 * float((t['status_T1'] == 'target').mean()) if n else 0.0,
            'stop%': 100.0 * float((t['r_' + pol] <= -0.97).mean()) if n else 0.0,
            'won%': 100.0 * float((net > 0).mean()) if n else 0.0,
            'days_up': int((byday > 0).sum()), 'days_dn': int((byday < 0).sum()), 'worst_day': float(byday.min()) if len(byday) else 0.0,
            'maxdd': float((eq - eq.cummax().clip(lower=0)).min()) if len(eq) else 0.0, 'longs': int((t['side'] == 'LONG').sum())}


METRIC = 'opt'     # 'opt' = option net (the client trades options), 'net' = futures net


def run(df, spec, metric=None):
    """spec = (score, thr, pol, n) or a callable df -> DataFrame of trades with a column 'pol' (per-row exit policy)
    or a callable returning (trades, pol). Returns the trades with a 'pnl' column (option net by default; a trade
    function may instead supply its own 'pnl' column, e.g. an option variant from option_net) and 'fut' (futures net)."""
    metric = metric or METRIC
    if callable(spec):
        out = spec(df)
        t, pol = out if isinstance(out, tuple) else (out, None)
    else:
        score, thr, pol, n = spec
        t = pick(df, score, thr, n)
    t = t.copy()
    if pol is not None:
        t['pol'] = pol
    t['fut'] = [r['net_' + p] for (_, r), p in zip(t.iterrows(), t['pol'])]
    if 'pnl' not in t.columns:
        t['pnl'] = [r[metric + '_' + p] for (_, r), p in zip(t.iterrows(), t['pol'])]
    t['stopped'] = [r['r_' + p] <= -0.97 for (_, r), p in zip(t.iterrows(), t['pol'])]
    return t


def stats(t, days):
    byday = t['pnl'].groupby(t['day']).sum().reindex(days).fillna(0.0)
    eq = byday.cumsum()
    n = len(t)
    return {'n': n, 'net': round(float(t.pnl.sum())), 'fut': round(float(t.fut.sum())) if 'fut' in t else 0, 'per_trade': round(float(t.pnl.mean())) if n else 0,
            'hit_T1%': round(100.0 * float((t['status_T1'] == 'target').mean()), 1) if n else 0.0,
            'stop%': round(100.0 * float(t['stopped'].mean()), 1) if n else 0.0,
            'days_up': int((byday > 0).sum()), 'days_dn': int((byday < 0).sum()), 'worst_day': round(float(byday.min())),
            'maxdd': round(float((eq - eq.cummax().clip(lower=0)).min())), 'longs': int((t['side'] == 'LONG').sum())}


def switch1(df):
    """Baseline: fable_op T3, except Downtrend days (regime A) where opus_v3 T1."""
    a = pick(df[df.regime != 'Downtrend'], 's_fable_op', 75).assign(pol='T3')
    b = pick(df[df.regime == 'Downtrend'], 's_opus_v3', 75).assign(pol='T1')
    return pd.concat([a, b]).sort_values(['day', 'time'])


BASE = {'Opus v3 (T1)': ('s_opus_v3', 75, 'T1', 6), 'Fable-OP (T3)': ('s_fable_op', 75, 'T3', 6), 'Switch-1': switch1}


def halves(name):
    return {'real': [('2026-05-12', '2026-08-31'), ('2026-09-01', '2026-11-11')],
            'unseen': [('2025-11-03', '2026-02-05'), ('2026-02-06', '2026-05-11')],
            'known': [('2026-05-12', '2026-07-31'), ('2026-08-01', '2026-10-19')]}[name]


def evaluate(D, cands, with_base=True, sets=SETS):
    """Returns {set: {name: {'all': stats, 'h1': stats, 'h2': stats, 'months': {YYYY-MM: net}}}}"""
    allc = dict(BASE) if with_base else {}
    allc.update(cands)
    res = {}
    for s in sets:
        df = D[s]
        days = sorted(df.day.unique())
        res[s] = {}
        for name, spec in allc.items():
            t = run(df, spec)
            r = {'all': stats(t, days)}
            for i, (lo, hi) in enumerate(halves(s)):
                dd = [d for d in days if lo <= d <= hi]
                r['h%d' % (i + 1)] = stats(t[(t.day >= lo) & (t.day <= hi)], dd)
            r['months'] = {k: round(float(v)) for k, v in t.groupby(t.day.str[:7])['pnl'].sum().items()}
            res[s][name] = r
    return res


def show(res):
    for s, rows in res.items():
        lo, hi = SPAN[s]
        print('\n== %s (%s to %s)%s | money columns = %s' % (s.upper(), lo, hi, '  real futures path' if s == 'real' else '  cash stand-in',
                                                          'OPTION net (modelled)' if METRIC == 'opt' else 'futures net'))
        print('  %-34s %5s %10s %8s %6s %6s %7s %10s %10s | %10s %10s | %10s' % ('model', 'n', 'net Rs', '/trade', 'T1%', 'stop%', 'd+/d-', 'worst day', 'max DD', '1st half', '2nd half', 'futures'))
        for name, r in rows.items():
            a = r['all']
            print('  %-34s %5d %+10d %+8d %6.1f %6.1f %3d/%-3d %+10d %+10d | %+10d %+10d | %+10d' % (name[:34], a['n'], a['net'], a['per_trade'], a['hit_T1%'], a['stop%'],
                                                                                 a['days_up'], a['days_dn'], a['worst_day'], a['maxdd'], r['h1']['net'], r['h2']['net'], a['fut']))


def compare(D, cands, sets=SETS):
    res = evaluate(D, cands, sets=sets)
    show(res)
    return res


# ---------------------------------------------------------------------------------------------- minute data
def minute_data():
    """Cash one-minute candles 15 Oct 2025 - 12 Nov 2026 for the ~218 F&O stocks, daily candles, Nifty index minutes.
    Returns (mins: {symbol: DataFrame[open,high,low,close,volume,oi] indexed by IST timestamps},
             daily: {symbol: DataFrame, from Jan 2024}, nifty: DataFrame (index minutes), lot: {symbol: (lot_size, tick)}).
    Uses about 3 GB of memory and 6 s; load once per process. Daily candles include today's: never use a day's own
    daily candle (or any minute after the signal minute) when deciding on that day."""
    sys.path.insert(0, SP + '/v2/patched')
    from scanner.series import merge_frames, candles_to_df
    D = SP + '/v2/data'
    parts = [pickle.load(open(D + '/' + f, 'rb')) for f in ('pre.pkl', 'early.pkl')]
    late = pickle.load(open(SP + '/replay_sep/minutes.pkl', 'rb'))
    keys = parts[-1]['keys']
    mins, daily = {}, {}
    for s, k in keys.items():
        m = None
        for p in parts:
            m = merge_frames(m, p['minutes'].get(k))
        m = merge_frames(m, late['minutes'].get(k))
        mins[s] = m if m is not None else candles_to_df([])
        dm = None
        for p in parts:
            dm = merge_frames(dm, p['daily'].get(s))
        daily[s] = dm if dm is not None else candles_to_df([])
    nifty = None
    for p in parts:
        nifty = merge_frames(nifty, p['nifty'])
    return mins, daily, nifty, late.get('lot', {})


# Pricing a NEW signal the same way the scanner does: scanner.equity.scan.price_fut(s, minutes, tick, lot, cfg)
#   with s = {'side', 'time', 'entry_ref', 'snapshot': {...}} - see v2/patched/scanner/equity/scan.py. Simpler route:
#   scanner.equity.fills.simulate / run_policies on the minutes after the signal minute, then size with
#   scanner.equity.scan.lots_for and cost with scanner.equity.costs.round_trip + costs.slippage (0.02 %), cfg = EqConfig().


if __name__ == '__main__':
    D = load_all(cache=False)
    for k, d in D.items():
        print(k, len(d), 'signals', d.day.nunique(), 'sessions', d.day.min(), d.day.max())
    show(evaluate(D, {}))

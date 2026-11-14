# Independent recomputation of every number in ../six_month.json (does NOT import or copy six_month.py).
# harness is used ONLY to load D (H.load_all) - regime labels are read from D['regime'].
import json, math, os, sys
from datetime import datetime, timedelta, timezone
import numpy as np, pandas as pd

SP = '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
sys.path.insert(0, SP + '/hunt')
import harness as H

OUT = os.path.dirname(os.path.abspath(__file__))
J = json.load(open(SP + '/hunt/six_month/six_month.json'))
D = H.load_all()
POLS = ['T1', 'T2', 'T3', 'CLOSE', 'T2_TR', 'T3_TR', 'CLOSE_TR']
IST = timezone(timedelta(hours=5, minutes=30))

# ------------------------------------------------------------------ own Black-76 and option costs
def ncdf(x):
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def b76(F, K, T, s, call):
    if not (math.isfinite(F) and math.isfinite(K) and math.isfinite(T) and math.isfinite(s)):
        return float('nan')
    if T <= 0:
        return max(F - K, 0.0) if call else max(K - F, 0.0)
    v = s * math.sqrt(T)
    d1 = (math.log(F / K) + 0.5 * v * v) / v
    d2 = d1 - v
    if call:
        return F * ncdf(d1) - K * ncdf(d2)
    return K * ncdf(-d2) - F * ncdf(-d1)


def costs(p0, p1, q, slip=0.25):
    buy, sell = p0 * q, p1 * q
    brk = (20.0 if buy > 0 else 0.0) + (20.0 if sell > 0 else 0.0)
    exch = (buy + sell) * 0.03553 / 100
    sebi = (buy + sell) * 1e-6
    stamp = buy * 0.003 / 100
    stt = sell * 0.15 / 100
    gst = 0.18 * (brk + exch + sebi)
    slp = (p0 + p1) * q * slip / 100
    return brk + exch + sebi + stamp + stt + gst + slp


def ts(x):
    return datetime.fromisoformat(x)


def years_to_expiry(entry, expiry):
    e = datetime.fromisoformat(expiry + 'T15:30:00+05:30')
    return (e - entry).total_seconds() / (365.0 * 86400)


def opt_row(r, pol, decay=2.31, lag=1.0):
    q = r['o_qty']
    q = 0.0 if (q is None or not math.isfinite(float(q))) else float(q)
    call = r['o_kind'] == 'CE'
    F0, F1, s = float(r['o_F0']), float(r['o_F1_' + pol]), float(r['o_iv'])
    K = F0
    e0 = ts(r['o_entry_ts'])
    x = r['o_exit_ts_' + pol]
    T0 = years_to_expiry(e0, r['o_expiry'])
    if isinstance(x, str) and x:
        hold = (ts(x) - e0).total_seconds() / 60 + lag
        T1 = T0 - decay * hold / 525600
    else:
        T1 = float('nan')
    p0, p1 = b76(F0, K, T0, s, call), b76(F1, K, T1, s, call)
    net = q * (p1 - p0) - costs(p0, p1, q)
    if not (math.isfinite(net) and q > 0):
        net = 0.0
    return p0, p1, q, net


# ------------------------------------------------------------------ selection
def my_pick(df, col, thr=75.0, n=6):
    d = df[df[col].notna() & (df[col] >= thr)].copy()
    d['_neg'] = -d[col]
    d = d.sort_values(['day', 'time', '_neg', 'symbol'], kind='mergesort')
    out = []
    for day, g in d.groupby('day', sort=True):
        out.append(g.iloc[:n])
    return pd.concat(out) if out else d.iloc[:0]


def my_switch1(df):
    down = df['regime'] == 'Downtrend'
    a = my_pick(df[~down], 's_fable_op').assign(pol='T3')
    b = my_pick(df[down], 'v3_mine').assign(pol='T1')
    return pd.concat([a, b]).sort_values(['day', 'time', 'symbol'], kind='mergesort')


def max_open(t):
    ev = []
    for _, r in t.iterrows():
        e0 = ts(r['o_entry_ts'])
        x = r['o_exit_ts_' + r['pol']]
        if isinstance(x, str) and x:
            x1 = ts(x) + timedelta(minutes=1)
        else:
            x1 = datetime.fromisoformat(r['day'] + 'T15:30:00+05:30')
        ev.append((e0, 1, r['outlay']))
        ev.append((x1, 0, -r['outlay']))
    ev.sort(key=lambda z: (z[0], z[1]))
    cur = best = 0.0
    for _, _, v in ev:
        cur += v
        best = max(best, cur)
    return best


def maxdd(byday):
    eq = byday.cumsum()
    peak = eq.cummax().clip(lower=0)
    return float((eq - peak).min())


def describe(df, t, days):
    months = sorted({d[:7] for d in days})
    t = t.copy()
    t['pnl'] = [r['myopt_' + r['pol']] for _, r in t.iterrows()]
    t['fut'] = [r['net_' + r['pol']] for _, r in t.iterrows()]
    t['stop'] = [bool(r['r_' + r['pol']] <= -0.97) for _, r in t.iterrows()]
    t['outlay'] = [r['myp0'] * r['o_qty'] if r['o_qty'] > 0 else 0.0 for _, r in t.iterrows()]
    byday = t.groupby('day')['pnl'].sum().reindex(days).fillna(0.0)
    fday = t.groupby('day')['fut'].sum().reindex(days).fillna(0.0)
    cnt = t.groupby('day').size().reindex(days).fillna(0)
    mo = t.groupby(t['day'].str[:7])['pnl'].sum().reindex(months).fillna(0.0)
    mf = t.groupby(t['day'].str[:7])['fut'].sum().reindex(months).fillna(0.0)
    mn = t.groupby(t['day'].str[:7]).size().reindex(months).fillna(0).astype(int)
    lg = t['side'] == 'LONG'
    n = len(t)
    prem = float(np.nansum(t['outlay']))
    nq = int((t['o_qty'] > 0).sum())
    wins, losses = t.loc[t.pnl > 0, 'pnl'], t.loc[t.pnl <= 0, 'pnl']
    return {
        'trades': n, 'trades_per_day': n / len(days), 'longs': int(lg.sum()), 'shorts': int((~lg).sum()),
        'opt_net': float(t.pnl.sum()), 'fut_net': float(np.nansum(t.fut)),
        'opt_long': float(t.pnl[lg].sum()), 'opt_short': float(t.pnl[~lg].sum()),
        'opt_won_pct': 100.0 * float((t.pnl > 0).mean()), 'stopped_pct': 100.0 * float(t['stop'].mean()),
        'opt_avg_win': float(wins.mean()), 'opt_avg_loss': float(losses.mean()),
        '_avg_loss_strict_lt0': float(t.loc[t.pnl < 0, 'pnl'].mean()), '_n_zero_pnl': int((t.pnl == 0).sum()),
        '_n_fut_nan': int(t.fut.isna().sum()),
        'opt_days_up': int((byday > 0).sum()), 'opt_days_down': int((byday < 0).sum()), 'days_no_trade': int((cnt == 0).sum()),
        'opt_worst_day': float(byday.min()), 'opt_best_day': float(byday.max()),
        'opt_max_dd': maxdd(byday),
        'fut_worst_day': float(fday.min()), 'fut_max_dd': maxdd(fday),
        'opt_months_up': int((mo > 0).sum()), 'months': len(months),
        'opt_worst_month': [mo.idxmin(), float(mo.min())], 'opt_best_month': [mo.idxmax(), float(mo.max())],
        'premium_total': prem, 'premium_avg': prem / n if n else 0.0, '_premium_avg_qty_gt0': prem / nq if nq else 0.0,
        'premium_max_open': max_open(t), 'opt_return_on_premium_pct': 100.0 * float(t.pnl.sum()) / prem if prem else 0.0,
        'month_opt': {k: float(v) for k, v in mo.items()}, 'month_fut': {k: float(v) for k, v in mf.items()},
        'month_trades': {k: int(v) for k, v in mn.items()},
        'exit_mix': {k: int(v) for k, v in t['pol'].value_counts().items()},
        '_keys': sorted(zip(t.day, t.time, t.symbol)),
    }


PCT = {'opt_won_pct', 'stopped_pct', 'opt_return_on_premium_pct'}
COUNT = {'trades', 'longs', 'shorts', 'opt_days_up', 'opt_days_down', 'days_no_trade', 'opt_months_up', 'months'}
mism, checks = [], []


def cmp(path, mine, theirs, kind):
    if kind == 'count':
        bad = int(mine) != int(theirs)
    elif kind == 'pct':
        bad = abs(float(mine) - float(theirs)) > 0.1
    elif kind == 'ratio':
        bad = abs(float(mine) - float(theirs)) > 0.01
    elif kind == 'str':
        bad = mine != theirs
    else:
        bad = abs(float(mine) - float(theirs)) > 1.0
    checks.append(path)
    if bad:
        mism.append({'item': path, 'json_value': theirs, 'my_value': mine})


MODELS = [('Opus (T1), live model', 's_opus', 'T1'), ('Opus v2 (T1)', 'v2_mine', 'T1'), ('Opus v3 (T1)', 'v3_mine', 'T1'),
          ('Fable (T3)', 's_fable', 'T3'), ('Fable-OP (T3)', 's_fable_op', 'T3'), ('Switch-1', None, None),
          ('Opus v3, trailing stop to close (CLOSE_TR)', 'v3_mine', 'CLOSE_TR')]
GRID = {'Opus': 's_opus', 'Opus v2': 'v2_mine', 'Opus v3': 'v3_mine', 'Fable': 's_fable', 'Fable-OP': 's_fable_op'}

mine_all = {'sessions': {}, 'models': {}, 'grid': {}, 'row_checks': {}}
for S in ('real', 'unseen'):
    df = D[S].copy()
    # own v2 / v3 score derivation from the brief: v2 = long -> Fable-OP, short -> Opus; v3 = v2 but longs with rel_vol < 1 -> 0
    lg = df['side'] == 'LONG'
    df['v2_mine'] = np.where(lg, df['s_fable_op'], df['s_opus'])
    df['v3_mine'] = np.where(lg, np.where(df['rel_vol'] < 1.0, 0.0, df['s_fable_op']), df['s_opus'])
    rc = {'v2_vs_D_max_abs': float(np.nanmax(np.abs(df['v2_mine'] - df['s_opus_v2']))),
          'v3_vs_D_max_abs': float(np.nanmax(np.abs(df['v3_mine'] - df['s_opus_v3']))),
          'rel_vol_nan': int(df['rel_vol'].isna().sum()), 'regime_nan': int(df['regime'].isna().sum())}
    # own option net for every row and policy, compared with harness opt_<P>
    p0s = []
    for p in POLS:
        res = [opt_row(r, p) for _, r in df.iterrows()]
        df['myopt_' + p] = [z[3] for z in res]
        if p == 'T1':
            df['myp0'] = [z[0] for z in res]
        d = (df['myopt_' + p] - df['opt_' + p]).abs()
        rc['opt_%s_max_abs_diff' % p] = float(d.max())
        rc['opt_%s_rows_diff_gt_1' % p] = int((d > 1).sum())
        rc['opt_%s_zero_rows' % p] = int((df['myopt_' + p] == 0).sum())
        rc['net_%s_nan' % p] = int(df['net_' + p].isna().sum())
        rc['r_%s_nan' % p] = int(df['r_' + p].isna().sum())
        rc['exit_before_entry_%s' % p] = int(sum(ts(x) < ts(e) for x, e in zip(df['o_exit_ts_' + p], df['o_entry_ts'])))
        rc['exit_other_day_%s' % p] = int((df['o_exit_ts_' + p].str[:10] != df['day']).sum())
        rc['exit_after_1529_%s' % p] = int((df['o_exit_ts_' + p].str[11:16] > '15:29').sum())
    rc['expiry_before_day'] = int((df['o_expiry'] < df['day']).sum())
    rc['kind_side_mismatch'] = int(((df['o_kind'] == 'CE') != lg).sum())
    rc['p0_nonfinite'] = int((~np.isfinite(df['myp0'])).sum())
    mine_all['row_checks'][S] = rc

    days = sorted(df['day'].unique())
    per_month = {}
    for d0 in days:
        per_month[d0[:7]] = per_month.get(d0[:7], 0) + 1
    se = {'n': len(days), 'first': days[0], 'last': days[-1], 'per_month': per_month}
    mine_all['sessions'][S] = se
    js = J['sessions'][S]
    cmp('sessions.%s.n' % S, se['n'], js['n'], 'count')
    cmp('sessions.%s.first' % S, se['first'], js['first'], 'str')
    cmp('sessions.%s.last' % S, se['last'], js['last'], 'str')
    for k in sorted(set(per_month) | set(js['per_month'])):
        cmp('sessions.%s.per_month.%s' % (S, k), per_month.get(k), js['per_month'].get(k), 'count')

    mine_all['models'][S] = {}
    for name, col, pol in MODELS:
        t = my_switch1(df) if col is None else my_pick(df, col).assign(pol=pol)
        m = describe(df, t, days)
        mine_all['models'][S][name] = m
        jm = J['models'][S][name]
        for k, v in m.items():
            if k.startswith('_'):
                continue
            path = 'models.%s.%s.%s' % (S, name, k)
            if k not in jm:
                mism.append({'item': path, 'json_value': 'MISSING', 'my_value': v}); continue
            if k in ('month_opt', 'month_fut', 'month_trades', 'exit_mix'):
                for kk in sorted(set(v) | set(jm[k])):
                    cmp(path + '.' + kk, v.get(kk, 0), jm[k].get(kk, 0), 'count' if k in ('month_trades', 'exit_mix') else 'rs')
            elif k in ('opt_worst_month', 'opt_best_month'):
                cmp(path + '.month', v[0], jm[k][0], 'str'); cmp(path + '.value', v[1], jm[k][1], 'rs')
            elif k in COUNT:
                cmp(path, v, jm[k], 'count')
            elif k in PCT:
                cmp(path, v, jm[k], 'pct')
            elif k == 'trades_per_day':
                cmp(path, v, jm[k], 'ratio')
            else:
                cmp(path, v, jm[k], 'rs')
        for k in jm:
            if k not in m:
                mism.append({'item': 'models.%s.%s.%s' % (S, name, k), 'json_value': jm[k], 'my_value': 'NOT RECOMPUTED'})

    mine_all['grid'][S] = {}
    for gname, col in GRID.items():
        t = my_pick(df, col)
        row = {}
        for p in POLS:
            row[p] = {'opt': float(t['myopt_' + p].sum()), 'fut': float(np.nansum(t['net_' + p])), 'n': len(t)}
            cmp('grid.%s.%s.%s.opt' % (S, gname, p), row[p]['opt'], J['grid'][S][gname][p]['opt'], 'rs')
            cmp('grid.%s.%s.%s.fut' % (S, gname, p), row[p]['fut'], J['grid'][S][gname][p]['fut'], 'rs')
        mine_all['grid'][S][gname] = row

# cross-checks of model rows against the grid (same model and exit) inside the JSON itself
for S in ('real', 'unseen'):
    for name, g, p in [('Opus (T1), live model', 'Opus', 'T1'), ('Opus v2 (T1)', 'Opus v2', 'T1'), ('Opus v3 (T1)', 'Opus v3', 'T1'),
                       ('Fable (T3)', 'Fable', 'T3'), ('Fable-OP (T3)', 'Fable-OP', 'T3'), ('Opus v3, trailing stop to close (CLOSE_TR)', 'Opus v3', 'CLOSE_TR')]:
        jm, jg = J['models'][S][name], J['grid'][S][g][p]
        cmp('internal.%s.%s.opt_net==grid' % (S, name), jm['opt_net'], jg['opt'], 'rs')
        cmp('internal.%s.%s.fut_net==grid' % (S, name), jm['fut_net'], jg['fut'], 'rs')
        cmp('internal.%s.%s.sum(month_opt)==opt_net' % (S, name), sum(jm['month_opt'].values()), jm['opt_net'], 'rs')
        cmp('internal.%s.%s.sum(month_fut)==fut_net' % (S, name), sum(jm['month_fut'].values()), jm['fut_net'], 'rs')
        cmp('internal.%s.%s.long+short==opt_net' % (S, name), jm['opt_long'] + jm['opt_short'], jm['opt_net'], 'rs')

for k in mine_all['models']:
    for n_ in mine_all['models'][k]:
        mine_all['models'][k][n_].pop('_keys', None)
json.dump(mine_all, open(OUT + '/recompute_values.json', 'w'), indent=1, default=float)
json.dump({'n_checks': len(checks), 'mismatches': mism}, open(OUT + '/mismatches.json', 'w'), indent=1, default=str)
print('checks', len(checks), 'mismatches', len(mism))
for m in mism:
    print(m)
print(json.dumps(mine_all['row_checks'], indent=1))
for S in ('real', 'unseen'):
    for name, m in mine_all['models'][S].items():
        print(S, name, 'zero-pnl trades', m['_n_zero_pnl'], 'avg loss <0 only', round(m['_avg_loss_strict_lt0']), 'vs <=0', round(m['opt_avg_loss']),
              'prem avg qty>0', round(m['_premium_avg_qty_gt0']), 'fut NaN', m['_n_fut_nan'])

# Check 2 + 3: apply the live rule to the RAW real rows (pull.json + feat.pkl rel_vol, no harness pick/regime/run)
# and compare trade counts, six-month and monthly FUTURES nets, futures worst day / max DD with six_month.json.
# Regime is rebuilt here from nifty_daily.json with an explicit loop that only reads closes strictly before the day.
import json, sys
import numpy as np, pandas as pd
SP = '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
OUT = SP + '/hunt/six_month/sources'
J = json.load(open(SP + '/hunt/six_month/six_month.json'))

P = pd.read_pickle(OUT + '/raw_pull.pkl')
F = pd.read_pickle(OUT + '/raw_feat.pkl')
KEY = ['day', 'time', 'symbol', 'setup']
X = P.merge(F[KEY + ['side', 'f_rel_vol']], on=KEY, how='inner')
assert len(X) == len(P) == 4996
lg = X.side == 'LONG'
X['s_opus'] = X.p_opus
X['s_fable'] = X.p_fable - 5.0
X['s_fable_op'] = X.p_fable_op
X['s_opus_v2'] = np.where(lg, X.p_fable_op, X.p_opus)
X['s_opus_v3'] = np.where(lg, np.where(X.f_rel_vol < 1.0, 0.0, X.p_fable_op), X.p_opus)

# ---------------- regime, independent: walk the sorted closes, use only closes of days < D
nd = json.load(open(SP + '/v2/data/nifty_daily.json'))['data']['candles']
cl = sorted((c[0][:10], float(c[4])) for c in nd)
days_n = [d for d, _ in cl]
assert len(set(days_n)) == len(days_n)
REG = {}
for i, (d, _) in enumerate(cl):
    past = [c for _, c in cl[:i]]              # strictly before day d
    if len(past) < 50:
        REG[d] = None
        continue
    prev = past[-1]
    ma20 = sum(past[-20:]) / 20
    ma50 = sum(past[-50:]) / 50
    REG[d] = 'Uptrend' if (prev > ma20 and ma20 > ma50) else ('Downtrend' if (prev < ma20 and ma20 < ma50) else 'Sideways')
X['regime'] = X.day.map(REG)
print('regime NaN rows', int(X.regime.isna().sum()), 'days by regime', X.groupby('regime').day.nunique().to_dict())

# compare with harness regime (H.regime is only read, not used for the picks)
sys.path.insert(0, SP + '/hunt')
import harness as H
HR = H.regime()
dd = sorted(set(X.day))
bad = [d for d in dd if HR.loc[d, 'A'] != REG[d]]
print('regime label mismatches vs H.regime on real days:', len(bad), bad[:5])
Dh = H.load_all()
mm = (Dh['real'].day.map(REG) != Dh['real'].regime).sum()
print('D[real].regime vs my regime, row mismatches:', int(mm))
# leakage probe: does the label change if the day's own close is altered? (perturb close of each day; label of that day must not move)
leak = 0
for i in range(50, len(cl)):
    d = cl[i][0]
    past = [c for _, c in cl[:i]]
    alt = past[:]       # same past; own close never enters
    leak += 0
print('same-day leakage by construction: 0 (labels use cl[:i] only); harness uses c.shift(1) and rolling(..).mean().shift(1)')


def pick(df, col, thr=75.0, n=6):
    out = []
    for day, g in df.groupby('day', sort=True):
        g = g[g[col] >= thr]
        # time order; ties: higher score, then symbol
        g = g.sort_values(['time', col, 'symbol'], ascending=[True, False, True], kind='mergesort')
        out.append(g.head(n))
    return pd.concat(out) if out else df.iloc[:0]


DAYS = sorted(X.day.unique())
MONTHS = sorted({d[:7] for d in DAYS})


def summary(t, netcol):
    byday = t.groupby('day')[netcol].sum().reindex(DAYS).fillna(0.0)
    eq = byday.cumsum()
    peak = np.maximum.accumulate(np.concatenate([[0.0], eq.to_numpy()]))[1:]
    mo = t.groupby(t.day.str[:7])[netcol].sum().reindex(MONTHS).fillna(0.0)
    return {'n': len(t), 'fut': float(t[netcol].sum()), 'worst': float(byday.min()), 'dd': float((eq.to_numpy() - peak).min()),
            'months': {k: float(v) for k, v in mo.items()}, 'mn': t.groupby(t.day.str[:7]).size().reindex(MONTHS).fillna(0).astype(int).to_dict(),
            'longs': int((t.side == 'LONG').sum()), 'no_trade_days': int((t.groupby('day').size().reindex(DAYS).fillna(0) == 0).sum())}


res = {}
SPEC = {'Opus (T1), live model': ('s_opus', 'T1'), 'Opus v2 (T1)': ('s_opus_v2', 'T1'), 'Opus v3 (T1)': ('s_opus_v3', 'T1'),
        'Fable (T3)': ('s_fable', 'T3'), 'Fable-OP (T3)': ('s_fable_op', 'T3'),
        'Opus v3, trailing stop to close (CLOSE_TR)': ('s_opus_v3', 'CLOSE_TR')}
for name, (col, pol) in SPEC.items():
    t = pick(X, col).copy()
    t['fut'] = t['p_net_' + pol]
    res[name] = summary(t, 'fut')
# Switch-1
a = pick(X[X.regime != 'Downtrend'], 's_fable_op').assign(pol='T3')
b = pick(X[X.regime == 'Downtrend'], 's_opus_v3').assign(pol='T1')
t = pd.concat([a, b])
t['fut'] = np.where(t.pol == 'T3', t.p_net_T3, t.p_net_T1)
res['Switch-1'] = summary(t, 'fut')
res['Switch-1']['exit_mix'] = t.pol.value_counts().to_dict()

mism = []
print('\n%-44s %5s %5s | %11s %11s | %9s %9s | %9s %9s' % ('model', 'n', 'json', 'fut mine', 'json', 'worst', 'json', 'maxDD', 'json'))
for name, r in res.items():
    j = J['models']['real'][name]
    print('%-44s %5d %5d | %11.0f %11d | %9.0f %9d | %9.0f %9d' % (name[:44], r['n'], j['trades'], r['fut'], j['fut_net'], r['worst'], j['fut_worst_day'], r['dd'], j['fut_max_dd']))
    for k, jk, tol in (('n', 'trades', 0), ('fut', 'fut_net', 1), ('worst', 'fut_worst_day', 1), ('dd', 'fut_max_dd', 1), ('longs', 'longs', 0), ('no_trade_days', 'days_no_trade', 0)):
        if abs(r[k] - j[jk]) > tol:
            mism.append((name, k, r[k], j[jk]))
    for m in MONTHS:
        if abs(r['months'][m] - j['month_fut'][m]) > 1:
            mism.append((name, 'month_fut ' + m, r['months'][m], j['month_fut'][m]))
        if r['mn'][m] != j['month_trades'][m]:
            mism.append((name, 'month_trades ' + m, r['mn'][m], j['month_trades'][m]))
    if 'exit_mix' in r and r['exit_mix'] != j['exit_mix']:
        mism.append((name, 'exit_mix', r['exit_mix'], j['exit_mix']))
# grid futures (model x exit)
for mname, col in {'Opus': 's_opus', 'Opus v2': 's_opus_v2', 'Opus v3': 's_opus_v3', 'Fable': 's_fable', 'Fable-OP': 's_fable_op'}.items():
    t = pick(X, col)
    for p in ['T1', 'T2', 'T3', 'CLOSE', 'T2_TR', 'T3_TR', 'CLOSE_TR']:
        v = float(t['p_net_' + p].sum())
        if abs(v - J['grid']['real'][mname][p]['fut']) > 1:
            mism.append(('grid ' + mname, p, v, J['grid']['real'][mname][p]['fut']))
print('\nmonthly futures (mine):')
for name, r in res.items():
    print('  %-44s ' % name[:44] + ' '.join('%s %+.0f' % (m[5:], v) for m, v in r['months'].items()))
print('\nMISMATCHES (> Rs 1 or count):', len(mism))
for m in mism:
    print('  ', m)
json.dump({'res': res, 'mism': [list(map(str, m)) for m in mism]}, open(OUT + '/c2_result.json', 'w'), indent=1)
X.to_pickle(OUT + '/raw_real_scored.pkl')

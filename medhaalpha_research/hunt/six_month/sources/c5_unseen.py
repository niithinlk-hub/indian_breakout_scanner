# Check 5: unseen set vs raw proxy_unseen/proxy_*.json.
#  (a) full rebuild of every A/B signal straight from the JSON, compare all score and futures-net columns with D['unseen']
#  (b) 30 random picked rows (union of the picks of all models) printed side by side
#  (c) live rule applied to the raw rows -> counts and futures nets vs six_month.json
#  (d) scanner's own opus_v2 / opus_v3 scores in the proxy vs the harness derivation
import json, sys, glob
import numpy as np, pandas as pd
SP = '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
OUT = SP + '/hunt/six_month/sources'
sys.path.insert(0, SP + '/hunt')
import harness as H
J = json.load(open(SP + '/hunt/six_month/six_month.json'))
POLS = ['T1', 'T2', 'T3', 'CLOSE', 'T2_TR', 'T3_TR', 'CLOSE_TR']

recs, dropped, nofut = [], 0, 0
for p in sorted(glob.glob(SP + '/v2/proxy_unseen/proxy_*.json')):
    doc = json.load(open(p))
    for s in doc['signals']:
        if s['setup'] not in ('A', 'B'):
            continue
        if s['fut']['T1']['status'] == 'no_data':
            dropped += 1
            continue
        d = {'day': doc['day'], 'time': s['time'], 'symbol': s['symbol'], 'setup': s['setup'], 'side': s['side'],
             'x_opus': s['scores']['opus'], 'x_fable': s['scores']['fable'], 'x_fable_op': s['scores']['fable_op'],
             'x_opus_v2_scanner': s['scores'].get('opus_v2'), 'x_opus_v3_scanner': s['scores'].get('opus_v3'),
             'x_rel_vol': s['snapshot'].get('rel_vol'), 'x_rel_vol_top': s.get('rel_vol'), 'x_lot': s['lot'], 'x_lots': s['lots'],
             'x_status': s['fut']['T1']['status']}
        for q in POLS:
            o = s['fut'].get(q)
            if not o or o.get('net_rs') is None:
                nofut += 1
            d['x_net_' + q] = (o or {}).get('net_rs', np.nan)
        recs.append(d)
X = pd.DataFrame(recs)
print('proxy A/B usable signals', len(X), 'dropped no_data', dropped, 'missing policy nets', nofut, 'days', X.day.nunique())
KEY = ['day', 'time', 'symbol', 'setup']
print('duplicate keys in proxy', int(X.duplicated(KEY, keep=False).sum()))
lg = X.side == 'LONG'
X['s_opus'], X['s_fable'], X['s_fable_op'] = X.x_opus, X.x_fable - 5.0, X.x_fable_op
X['s_opus_v2'] = np.where(lg, X.x_fable_op, X.x_opus)
X['s_opus_v3'] = np.where(lg, np.where(X.x_rel_vol < 1.0, 0.0, X.x_fable_op), X.x_opus)
for q in POLS:
    X['net_' + q] = X['x_net_' + q]

D = H.load_all()
U = D['unseen']
M = X.merge(U, on=KEY, how='outer', indicator=True, suffixes=('_raw', ''))
print('raw vs D[unseen] join', M._merge.value_counts().to_dict())
B = M[M._merge == 'both']
for c in ['s_opus', 's_fable', 's_fable_op', 's_opus_v2', 's_opus_v3'] + ['net_' + q for q in POLS]:
    a, b = B[c + '_raw'].astype(float), B[c].astype(float)
    dif = (a - b).abs()
    nanm = int((a.isna() != b.isna()).sum())
    print('  %-13s max |diff| %.6f  rows over tol %d  NaN mismatch %d  NaN in D %d' % (c, dif.max(), int((dif > (0.05 if c[0] == 's' else 1)).sum()), nanm, int(b.isna().sum())))

# (d) scanner's own v2/v3 vs harness derivation
for c in ('opus_v2', 'opus_v3'):
    a = B['x_' + c + '_scanner'].astype(float)
    b = B['s_' + c].astype(float)
    dif = (a - b).abs()
    bad = B[dif > 0.05]
    print('  scanner %s vs harness s_%s: rows differ %d (of %d), NaN scanner %d' % (c, c, len(bad), len(B), int(a.isna().sum())))
    if len(bad):
        print(bad[['day', 'time', 'symbol', 'side', 'x_rel_vol', 'x_opus', 'x_fable_op', 'x_' + c + '_scanner', 's_' + c]].head(8).to_string())
print('  snapshot rel_vol vs top-level rel_vol max diff', float((B.x_rel_vol - B.x_rel_vol_top).abs().max()))

# (c) live rule on raw rows
def pick(df, col, thr=75.0, n=6):
    out = []
    for day, g in df.groupby('day', sort=True):
        g = g[g[col] >= thr].sort_values(['time', col, 'symbol'], ascending=[True, False, True], kind='mergesort')
        out.append(g.head(n))
    return pd.concat(out)

REG = D['unseen'].groupby('day').regime.first()
X['regime'] = X.day.map(REG)
DAYS = sorted(X.day.unique())
MONTHS = sorted({d[:7] for d in DAYS})
SPEC = {'Opus (T1), live model': ('s_opus', 'T1'), 'Opus v2 (T1)': ('s_opus_v2', 'T1'), 'Opus v3 (T1)': ('s_opus_v3', 'T1'),
        'Fable (T3)': ('s_fable', 'T3'), 'Fable-OP (T3)': ('s_fable_op', 'T3'), 'Opus v3, trailing stop to close (CLOSE_TR)': ('s_opus_v3', 'CLOSE_TR')}
mism, picked = [], []
def cmp(name, t):
    j = J['models']['unseen'][name]
    bd = t.groupby('day').fut.sum().reindex(DAYS).fillna(0.0); eq = bd.cumsum()
    dd = float((eq - eq.cummax().clip(lower=0)).min())
    mo = t.groupby(t.day.str[:7]).fut.sum().reindex(MONTHS).fillna(0.0)
    print('  %-44s n %d/%d fut %.0f/%d worst %.0f/%d dd %.0f/%d' % (name[:44], len(t), j['trades'], t.fut.sum(), j['fut_net'], bd.min(), j['fut_worst_day'], dd, j['fut_max_dd']))
    for k, mine, js in (('n', len(t), j['trades']), ('fut', t.fut.sum(), j['fut_net']), ('worst', bd.min(), j['fut_worst_day']), ('dd', dd, j['fut_max_dd'])):
        if abs(mine - js) > (0 if k == 'n' else 1):
            mism.append((name, k, mine, js))
    for m in MONTHS:
        if abs(mo[m] - j['month_fut'][m]) > 1:
            mism.append((name, 'month_fut ' + m, mo[m], j['month_fut'][m]))
print('\nlive rule on raw unseen rows vs six_month.json (mine/json):')
for name, (col, pol) in SPEC.items():
    t = pick(X, col).copy(); t['fut'] = t['net_' + pol]
    picked.append(t[KEY]); cmp(name, t)
a = pick(X[X.regime != 'Downtrend'], 's_fable_op').assign(pol='T3')
b = pick(X[X.regime == 'Downtrend'], 's_opus_v3').assign(pol='T1')
t = pd.concat([a, b]); t['fut'] = np.where(t.pol == 'T3', t.net_T3, t.net_T1)
picked.append(t[KEY]); cmp('Switch-1', t)
for mname, col in {'Opus': 's_opus', 'Opus v2': 's_opus_v2', 'Opus v3': 's_opus_v3', 'Fable': 's_fable', 'Fable-OP': 's_fable_op'}.items():
    t = pick(X, col)
    for p in POLS:
        v = float(t['net_' + p].sum())
        if abs(v - J['grid']['unseen'][mname][p]['fut']) > 1:
            mism.append(('grid ' + mname, p, v, J['grid']['unseen'][mname][p]['fut']))
print('unseen mismatches:', len(mism)); [print('  ', m) for m in mism]

# what if the scanner's own opus_v2/opus_v3 scores were used instead of the harness derivation
for c in ('opus_v2', 'opus_v3'):
    t = pick(X.assign(_s=X['x_' + c + '_scanner']), '_s').copy()
    print('  using scanner %s score: n %d, T1 fut %.0f (json harness-derived: n %d, fut %d)' % (c, len(t), t.net_T1.sum(),
          J['models']['unseen']['Opus v2 (T1)' if c == 'opus_v2' else 'Opus v3 (T1)']['trades'], J['models']['unseen']['Opus v2 (T1)' if c == 'opus_v2' else 'Opus v3 (T1)']['fut_net']))

# (b) 30 random picked rows side by side with the proxy JSON
P = pd.concat(picked).drop_duplicates()
S = P.sample(30, random_state=20261114).merge(X, on=KEY).merge(U, on=KEY, suffixes=('_raw', '_D'))
cols = []
bad = 0
for _, r in S.iterrows():
    diffs = []
    for c in ['s_opus', 's_fable', 's_fable_op', 's_opus_v2', 's_opus_v3'] + ['net_' + q for q in POLS]:
        if not (abs(float(r[c + '_raw']) - float(r[c + '_D'])) <= (0.05 if c[0] == 's' else 1)):
            diffs.append(c)
    bad += bool(diffs)
    print('  %s %s %-11s %s  opus %5.1f/%5.1f fable-5 %5.1f/%5.1f fop %5.1f/%5.1f v3 %5.1f/%5.1f  T1 %9.2f/%9.2f T3 %9.2f/%9.2f CLTR %9.2f/%9.2f %s' % (
        r.day, r.time, r.symbol, r.setup, r.s_opus_raw, r.s_opus_D, r.s_fable_raw, r.s_fable_D, r.s_fable_op_raw, r.s_fable_op_D, r.s_opus_v3_raw, r.s_opus_v3_D,
        r.net_T1_raw, r.net_T1_D, r.net_T3_raw, r.net_T3_D, r.net_CLOSE_TR_raw, r.net_CLOSE_TR_D, ','.join(diffs) or 'ok'))
print('random-30 rows with any mismatch:', bad)
X.to_pickle(OUT + '/raw_unseen.pkl')

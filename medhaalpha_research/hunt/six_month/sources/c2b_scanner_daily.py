# Check 2b: per-day comparison of my live-rule picks (raw rows) with the scanner's own per-day 'live' summary in pull.json six.summary.
import json, numpy as np, pandas as pd
SP = '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
X = pd.read_pickle(SP + '/hunt/six_month/sources/raw_real_scored.pkl')
six = json.load(open(SP + '/six/pull.json'))['six']
def pick(df, col, thr=75.0, n=6):
    out = []
    for day, g in df.groupby('day', sort=True):
        out.append(g[g[col] >= thr].sort_values(['time', col, 'symbol'], ascending=[True, False, True], kind='mergesort').head(n))
    return pd.concat(out)
for m, col in (('opus', 's_opus'), ('fable', 's_fable'), ('fable_op', 's_fable_op')):
    t = pick(X, col)
    bad_n, bad_v, tot_s, tot_m = [], [], {}, {}
    for d in six['summary']:
        L = d['models'][m]['live']
        g = t[t.day == d['day']]
        if L['n'] != len(g):
            bad_n.append((d['day'], L['n'], len(g)))
        for p in ('T1', 'T3', 'CLOSE_TR'):
            v = float(g['p_net_' + p].sum())
            tot_s[p] = tot_s.get(p, 0) + L[p]; tot_m[p] = tot_m.get(p, 0) + v
            if abs(v - L[p]) > 1.0:
                bad_v.append((d['day'], p, L[p], round(v, 2)))
    print(m, 'days', len(six['summary']), '| day count mismatches', len(bad_n), bad_n[:5], '| day net mismatches > Rs 1:', len(bad_v), bad_v[:5])
    print('   sum of scanner daily (rupee-rounded) vs my unrounded totals:', {p: (tot_s[p], round(tot_m[p], 2)) for p in tot_s})

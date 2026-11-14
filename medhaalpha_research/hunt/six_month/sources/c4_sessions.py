# Check 4: sessions per month vs Nifty trading days (nifty_daily.json) in each window; sessions with no signal at all;
# effect of including those flat sessions on worst day / max drawdown (futures and option) for every model.
# Also probes for check 3: regime NaN rows in unseen, and an explicit no-leak test (alter day-D close -> label of D unchanged).
import json, sys, glob, os
import numpy as np, pandas as pd
SP = '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
sys.path.insert(0, SP + '/hunt')
import harness as H
J = json.load(open(SP + '/hunt/six_month/six_month.json'))
D = H.load_all()

nd = json.load(open(SP + '/v2/data/nifty_daily.json'))['data']['candles']
ndays = sorted(c[0][:10] for c in nd)
WIN = {'real': ('2026-05-12', '2026-11-11'), 'unseen': ('2025-11-03', '2026-05-11')}
pull_days = [d['day'] for d in json.load(open(SP + '/six/pull.json'))['sig']['days']]
proxy_days = sorted(os.path.basename(p)[6:16] for p in glob.glob(SP + '/v2/proxy_unseen/proxy_*.json'))
src_days = {'real': pull_days, 'unseen': proxy_days}
missing = {}
for s, (lo, hi) in WIN.items():
    nt = [d for d in ndays if lo <= d <= hi]
    have = sorted(D[s].day.unique())
    src = sorted(set(src_days[s]))
    pm_n = pd.Series(nt).str[:7].value_counts().sort_index().to_dict()
    pm_h = pd.Series(have).str[:7].value_counts().sort_index().to_dict()
    print('\n%s window %s..%s: nifty trading days %d, source files/days %d, sessions in D %d, json n %d' % (s, lo, hi, len(nt), len(src), len(have), J['sessions'][s]['n']))
    print('  per month nifty :', pm_n)
    print('  per month D     :', pm_h)
    print('  per month json  :', J['sessions'][s]['per_month'])
    miss_src = sorted(set(nt) - set(src))
    miss_sig = sorted(set(src) - set(have))
    extra = sorted(set(have) - set(nt))
    print('  nifty days with no source day/file:', miss_src)
    print('  source days with no A/B signal kept (no signal at all):', miss_sig)
    print('  D days that are not nifty trading days:', extra)
    missing[s] = sorted(set(nt) - set(have))
    print('  => sessions with no signal in D (counted as absent, not flat):', missing[s])
    # weekday sanity of nifty days
    wd = pd.to_datetime(pd.Series(nt)).dt.dayofweek
    print('  nifty days on weekends:', list(pd.Series(nt)[wd >= 5]))

# unseen proxy: days with a file but zero A/B signals or all no_data
for p in sorted(glob.glob(SP + '/v2/proxy_unseen/proxy_*.json')):
    doc = json.load(open(p))
    sig = [x for x in doc['signals'] if x['setup'] in ('A', 'B')]
    ok = [x for x in sig if x['fut']['T1']['status'] != 'no_data']
    if not ok:
        print('  proxy file with no usable A/B signal:', doc['day'], len(doc['signals']), len(sig))

# effect of flat sessions on worst day / max DD (futures and option) per model
MODELS = {'Opus (T1), live model': ('s_opus', 75, 'T1', 6), 'Opus v2 (T1)': ('s_opus_v2', 75, 'T1', 6), 'Opus v3 (T1)': ('s_opus_v3', 75, 'T1', 6),
          'Fable (T3)': ('s_fable', 75, 'T3', 6), 'Fable-OP (T3)': ('s_fable_op', 75, 'T3', 6), 'Switch-1': H.switch1,
          'Opus v3, trailing stop to close (CLOSE_TR)': ('s_opus_v3', 75, 'CLOSE_TR', 6)}
for s, (lo, hi) in WIN.items():
    nt = [d for d in ndays if lo <= d <= hi]
    have = sorted(D[s].day.unique())
    print('\n%s: effect of using all %d nifty days instead of %d sessions' % (s, len(nt), len(have)))
    for name, spec in MODELS.items():
        t = H.run(D[s], spec)
        out = []
        for col in ('fut', 'pnl'):
            for days in (have, nt):
                bd = t[col].groupby(t.day).sum().reindex(days).fillna(0.0)
                eq = bd.cumsum()
                out.append((round(bd.min()), round((eq - eq.cummax().clip(lower=0)).min()), int((bd > 0).sum()), int((bd < 0).sum())))
        j = J['models'][s][name]
        flag = '' if (out[0][:2] == out[1][:2] and out[2][:2] == out[3][:2]) else '  <-- changes'
        print('  %-44s fut worst/DD %s -> %s | opt worst/DD %s -> %s | json fut %d/%d opt %d/%d | tpd %.2f -> %.2f%s' % (
            name[:44], out[0][:2], out[1][:2], out[2][:2], out[3][:2], j['fut_worst_day'], j['fut_max_dd'], j['opt_worst_day'], j['opt_max_dd'],
            len(t) / len(have), len(t) / len(nt), flag))

# ---- check 3 probes
R = H.regime()
for s in ('real', 'unseen', 'known'):
    print('regime NaN rows in', s, int(D[s].regime.isna().sum()))
# no-leak test: perturb day-D close by +-20 %, recompute label for D with harness formula; must be unchanged
import copy
base = R['A']
c = pd.Series({x[0][:10]: float(x[4]) for x in nd}).sort_index()
chg = 0
for d in [x for x in c.index if '2025-11-03' <= x <= '2026-11-11']:
    for f in (0.8, 1.2):
        c2 = c.copy(); c2[d] *= f
        prev, ma20, ma50 = c2.shift(1)[d], c2.rolling(20).mean().shift(1)[d], c2.rolling(50).mean().shift(1)[d]
        lab = 'Uptrend' if (prev > ma20 and ma20 > ma50) else ('Downtrend' if (prev < ma20 and ma20 < ma50) else 'Sideways')
        chg += lab != base[d]
print('no-leak probe: labels changed by perturbing the same-day close:', chg)
# missing nifty days would make shift(1) skip a session: list business days absent from nifty (holidays expected)
bd = pd.bdate_range('2025-10-01', '2026-11-12').strftime('%Y-%m-%d')
print('weekdays absent from nifty_daily (should be NSE holidays only):', sorted(set(bd) - set(c.index)))

# Side split over 1 Sep - 13 Nov (50 sessions): multi-day holds and the Rs 3 lakh futures-margin simulation, next to Opus and Fable-OP.
import io, contextlib, json, os, sys
import pandas as pd
sp = sys.argv[1]
sys.argv = [sys.argv[0], sp]
src = open(os.path.join(sp, 'tools', 'cap_sim.py')).read()
head = src.split('out = {"sessions"')[0]
simsrc = 'def sim' + src.split('def sim')[1].split('for m in MS:')[0]
with contextlib.redirect_stdout(io.StringIO()):
    exec(head)
exec(simsrc)
picks = {tuple(k) for k in json.load(open(sp + '/v2/split_picks.json'))}
rows += json.load(open(sp + '/v2/hold_extra_cash.json'))['rows'] + json.load(open(sp + '/v2/hold_extra_fut.json'))['rows']
n = 0
for r in rows:
    if (r['day'], r['symbol'], r['setup'], r['time']) in picks and 'split' not in r['models']:
        r['models'] = list(r['models']) + ['split']
    n += 'split' in r['models']
print('split trades with hold results:', n, 'of', len(picks), '| sessions', NS)
res = {}
for m in ('opus', 'fable_op', 'split'):
    tr = [r for r in rows if m in r['models']]
    for pol in ('T1', 'T2', 'T3'):
        s = summ(tr, pol)
        res['hold|%s|%s' % (m, pol)] = s
        print('%-8s held %s: n=%3d hit=%3d (%.0f%%) stop=%3d open=%d net %+9d per trade %+6d | days to target %s' % (
            m, pol, s['n'], s['hit'], 100 * s['hit'] / s['n'], s['stopped'], s['open'], s['net'], s['net'] / s['n'], s['days_hist']))
    for pol in ('T1', 'T3'):
        for cap in (None, 300000.0):
            s = sim(tr, pol, cap, 0.20)
            res['cap|%s|%s|%s' % (m, pol, 'all' if cap is None else '3L')] = s
            print('   %-8s %s %-9s: taken %3d skipped %3d | hit %3d stop %3d | net %+9d | x250/50 %+10d | max fall %+8d | peak margin %9d (%d open) | %s' % (
                m, pol, 'no limit' if cap is None else 'Rs 3 lakh', s['taken'], s['skipped'], s['hit'], s['stopped'], s['net'], s['year'], s['max_dd'], s['peak_margin'], s['peak_open'], s['by_month']))
    print()
json.dump(res, open(sp + '/v2/e9.json', 'w'))

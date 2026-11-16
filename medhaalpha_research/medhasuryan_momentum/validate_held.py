# Checks heldsim.py against the research's stored held results (medhasuryan/bt4.json, made with the scanner's own code):
# every trade of the four models on both periods, status and net Rs per exit (T1, T2, T3).
import json, os, sys
import numpy as np, pandas as pd
RP = sys.argv[1]
os.environ['MEDHA_SP'] = RP
sys.path.insert(0, RP + '/hunt'); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as H, heldsim as HS
D = H.load_all()
DT = HS.Data(RP)
B = json.load(open(RP + '/medhasuryan/bt4.json'))
ST = {'H': 'target', 'S': 'stopped', 'E': 'expiry'}
for per in B['periods']:
    s = per['key']
    df = D[s].set_index(['day', 'time', 'symbol'], drop=False)
    cols = per['cols']
    tot = {}
    mism = {p: 0 for p in ('T1', 'T2', 'T3')}
    n = 0
    seen = set()
    for model, trades in per['trades'].items() if isinstance(per['trades'], dict) else [('all', per['trades'])]:
        for t in trades:
            rec = dict(zip(cols, t))
            key = (rec['day'], rec['time'], rec['symbol'])
            if key in seen:
                continue
            seen.add(key)
            r = df.loc[key]
            r = r.iloc[0] if isinstance(r, pd.DataFrame) else r
            got = HS.held_trade(DT, r, s)
            n += 1
            for p in ('T1', 'T2', 'T3'):
                want = rec[p]
                g = got[p] if got else None
                tot.setdefault(p, [0.0, 0.0])
                tot[p][0] += want[4] or 0
                tot[p][1] += (g['net'] if g else 0)
                if g is None or ST.get(want[0], want[0]) != g['status'] or abs((want[4] or 0) - g['net']) > max(50, 0.01 * abs(want[4] or 0)):
                    mism[p] += 1
    print('%s: %d distinct trades' % (s, n))
    for p in ('T1', 'T2', 'T3'):
        print('   %s  stored total %+11.0f  rebuilt %+11.0f  (diff %.2f%%)  trades differing %d' % (p, tot[p][0], tot[p][1], 100 * (tot[p][1] - tot[p][0]) / abs(tot[p][0]), mism[p]))

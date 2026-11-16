# Same-day backtest (every trade closed by 15:29) of MedhaSuryan-M against MedhaSuryan and the other baselines, using the
# research's own test bench (hunt/harness.py, read-only). Arg 1 = the medhaalpha_research folder; arg 2 = output json.
import json, os, sys
import numpy as np, pandas as pd
RP, OUT = sys.argv[1], sys.argv[2]
os.environ['MEDHA_SP'] = RP
sys.path.insert(0, RP + '/hunt'); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as H
import momscore as M

D = H.load_all()
from sameday_defs import SETTINGS, make

cands = {k: make(*v) for k, v in SETTINGS.items()}
DES = ('2026-05-12', '2026-08-31')
design = {}
d = D['real'][(D['real'].day >= DES[0]) & (D['real'].day <= DES[1])]
days = sorted(d.day.unique())
for name, spec in dict(H.BASE, **cands).items():
    design[name] = H.stats(H.run(d, spec), days)
print('== DESIGN WINDOW 12 May-31 Aug 2026 (choose here only), option net')
for k, v in design.items():
    print('  %-22s n %4d  opt %+9d  fut %+9d  /trade %+6d  worst day %+8d  max DD %+8d' % (k, v['n'], v['net'], v['fut'], v['per_trade'], v['worst_day'], v['maxdd']))
lim = 1.25 * design['Switch-1']['maxdd']
ok = {k: v for k, v in design.items() if k in SETTINGS and v['maxdd'] >= lim}
chosen = max(ok, key=lambda k: ok[k]['net'])
print('max DD limit %.0f -> chosen: %s' % (lim, chosen))
res = H.evaluate(D, cands)
H.show(res)
json.dump({'settings': SETTINGS, 'design': design, 'chosen': chosen, 'eval': res}, open(OUT, 'w'), indent=1)

# The live-session table's columns, for six months: trades, stopped, futures, options (same day, modelled), losing days, worst day.
import sys, json
import numpy as np, pandas as pd
SP = sys.argv[1]
sys.path.insert(0, SP + '/hunt'); import harness as H
D = H.load_all()
M = {'Switch-1': H.switch1, 'Fable (T3)': ('s_fable', 75, 'T3', 6), 'Fable-OP (T3)': ('s_fable_op', 75, 'T3', 6), 'Opus (T1), live': ('s_opus', 75, 'T1', 6)}
out = {}
for s in ('real', 'unseen'):
    df = D[s]; days = sorted(df.day.unique()); out[s] = {}
    for name, spec in M.items():
        t = H.run(df, spec)
        fd = t.fut.groupby(t.day).sum().reindex(days).fillna(0.0)
        od = t.pnl.groupby(t.day).sum().reindex(days).fillna(0.0)
        r = {'trades': len(t), 'stopped_pct': round(100 * t.stopped.mean()), 'fut': round(t.fut.sum()), 'opt': round(t.pnl.sum()),
             'fut_days_down': int((fd < 0).sum()), 'fut_days_up': int((fd > 0).sum()), 'fut_worst_day': round(fd.min()),
             'opt_days_down': int((od < 0).sum()), 'opt_worst_day': round(od.min()), 'sessions': len(days),
             'fut_maxdd': round(float((fd.cumsum() - fd.cumsum().cummax().clip(lower=0)).min())),
             'opt_maxdd': round(float((od.cumsum() - od.cumsum().cummax().clip(lower=0)).min()))}
        out[s][name] = r
        print(s, name, r)
json.dump(out, open(SP + '/hunt/live17/six_table.json', 'w'), indent=1)

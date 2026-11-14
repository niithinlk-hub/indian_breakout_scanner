# Exploratory check of the post-hoc lead: Opus v3 picks, exit CLOSE_TR, on OPTION net.
# Day-bootstrap of the daily difference against Fable-OP T3, Opus v3 T1 and Switch-1; month-by-month wins.
import sys, numpy as np, pandas as pd
sys.path.insert(0, sys.argv[1] + '/hunt'); import harness as H
D = H.load_all()
rng = np.random.default_rng(7)
def daily(df, spec):
    t = H.run(df, spec)
    return t.groupby('day').pnl.sum().reindex(sorted(df.day.unique()), fill_value=0.0)
cands = {'v3 CLOSE_TR': ('s_opus_v3', 75, 'CLOSE_TR', 6), 'v3 T3': ('s_opus_v3', 75, 'T3', 6), 'v3 CLOSE': ('s_opus_v3', 75, 'CLOSE', 6)}
bases = {'Fable-OP T3': ('s_fable_op', 75, 'T3', 6), 'Opus v3 T1': ('s_opus_v3', 75, 'T1', 6), 'Switch-1': H.switch1}
for s, cut in [('unseen', None), ('real', 'h2'), ('real', 'h1'), ('known', None)]:
    df = D[s]
    if cut == 'h2': df = df[df.day >= '2026-09-01']
    if cut == 'h1': df = df[df.day <= '2026-08-31']
    lab = s + ('' if cut is None else ' ' + cut)
    B = {k: daily(df, v) for k, v in bases.items()}
    for cn, cs in cands.items():
        c = daily(df, cs)
        out = []
        for bn, b in B.items():
            d = (c - b).values
            bs = np.array([rng.choice(d, len(d)).sum() for _ in range(5000)])
            m = (c - b).groupby(pd.to_datetime(c.index).to_period('M')).sum()
            out.append('%s %+9.0f P(>0)=%.2f months won %d/%d' % (bn, d.sum(), (bs > 0).mean(), (m > 0).sum(), len(m)))
        print('%-12s %-12s net %+9.0f | ' % (lab, cn, c.sum()) + ' | '.join(out))

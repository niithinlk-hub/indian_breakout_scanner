# First v3 candidates on six months: v2 plus (G1) longs need relative volume >= 1, (G2) no new short once Nifty is down 1 % or more,
# (S) a short may also qualify on Fable-OP >= 75. Each alone and together.
import sys, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, sys.argv[1] + '/v2')
import numpy as np, pandas as pd
from frame import load
from lab import *
df = load()
A = df[df.design | df.unseen].copy()
print('missing rel_vol: %d of %d | missing nifty_dir: %d' % (A.rel_vol.isna().sum(), len(A), A.nifty_dir.isna().sum()))
lg = A.long == 1
g1 = ~(A.rel_vol < 1.0)          # missing passes


def build(G1=False, G2=None, S=False, rv=1.0):
    ls = np.where(~(A.rel_vol < rv) if G1 else True, A.t_fable_op, 0.0)
    ss = np.maximum(A.t_opus, A.t_fable_op) if S else A.t_opus
    if G2 is not None:
        ss = np.where(A.nifty_dir >= G2, 0.0, ss)
    return np.where(lg, ls, ss)


A['opus'], A['v2'] = A.t_opus, build()
CANDS = [('Opus', 'opus'), ('v2', 'v2')]
for name, kw in (('v2 + G1 (longs rel vol >= 1)', dict(G1=True)), ('v2 + G2 (no short, Nifty -1%)', dict(G2=1.0)), ('v2 + G2 at -0.75%', dict(G2=0.75)), ('v2 + S (FOP shorts too)', dict(S=True)),
                 ('v2 + G1 + G2', dict(G1=True, G2=1.0)), ('v3a: G1 + G2 + S', dict(G1=True, G2=1.0, S=True)), ('v3b: G1 + G2(0.75) + S', dict(G1=True, G2=0.75, S=True)),
                 ('v3c: G1(1.5) + G2 + S', dict(G1=True, G2=1.0, S=True, rv=1.5))):
    col = 'c%d' % len(CANDS)
    A[col] = build(**kw)
    CANDS.append((name, col))
for per, mask in (('ALL 126', A.day > ''), ('H1 12 May-31 Aug', A.design), ('H2 1 Sep-11 Nov', A.unseen)):
    P = A[mask]
    print('==', per)
    for name, col in CANDS:
        print(line(name, stat(P, live_df(P, col, 75)))[:165])
print('\n== by month: trades:hit%:stop%/net k')
for name, col in CANDS:
    if name in ('Opus', 'v2', 'v3a: G1 + G2 + S', 'v2 + G1 + G2'):
        t = A.loc[live_df(A, col, 75)]
        print('%-22s' % name[:22], ' | '.join('%s %2d:%2.0f:%2.0f/%+4.0f' % (mo[5:], len(g), 100 * g.hit.mean(), 100 * g['stop'].mean(), g.net1.sum() / 1000) for mo, g in t.groupby('month')))

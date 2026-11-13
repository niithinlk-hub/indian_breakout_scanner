# Side split with no new numbers: longs must score >= 75 on Fable-OP, shorts >= 75 on Opus (both cuts as live today).
# Chosen AFTER the unseen check of the blended candidates, so the unseen figures below are not a clean test of it.
import sys, warnings, json
warnings.filterwarnings('ignore')
sys.path.insert(0, sys.argv[1] + '/v2')
import numpy as np, pandas as pd
from frame import load
from lab import *
df = load()
df['opus'], df['fable_op'] = df.t_opus, df.t_fable_op
df['split'] = np.where(df.long == 1, df.t_fable_op, df.t_opus)
df['split_u'] = np.where(df.long == 1, df.t_fable_op, np.maximum(df.t_opus, df.t_fable_op))     # shorts: either model
df['anti'] = np.where(df.long == 1, df.t_opus, df.t_fable_op)                                   # the opposite pairing, as a sanity check
CANDS = (('Opus >= 75 (now)', 'opus'), ('Fable-OP >= 75 (now)', 'fable_op'), ('SPLIT: FOP longs + Opus shorts', 'split'), ('  shorts from either model', 'split_u'), ('  opposite pairing', 'anti'))
res = {}
for name, mask in (('DESIGN 12 May - 31 Aug (78 sessions)', df.design), ('UNSEEN 1 Sep - 11 Nov (48 sessions)', df.unseen), ('ALL 12 May - 11 Nov (126 sessions)', df.design | df.unseen)):
    P = df[mask]
    print('==', name)
    for lab, col in CANDS:
        s = stat(P, live_df(P, col, 75))
        res[name[:6].strip() + '|' + col] = s
        print(line(lab, s))
    print()
A = df[df.design | df.unseen]
print('== by month: trades : hit% : stop% / T1 net')
for lab, col in CANDS[:3]:
    t = A.loc[live_df(A, col, 75)]
    print('%-30s' % lab, ' | '.join('%s %2d:%2.0f:%2.0f/%+4.0fk' % (mo[5:], len(g), 100 * g.hit.mean(), 100 * g['stop'].mean(), g.net1.sum() / 1000) for mo, g in t.groupby('month')))
print('\n== by side, all 126 sessions')
for lab, col in CANDS[:3]:
    t = A.loc[live_df(A, col, 75)]
    for per, m in (('design', A.design), ('unseen', A.unseen)):
        print('%-30s %s' % (lab, per), ' | '.join('%s n=%3d hit %4.1f%% stop %4.1f%% T1 %+7.0f' % (s, len(g), 100 * g.hit.mean(), 100 * g['stop'].mean(), g.net1.sum()) for s, g in t[m.loc[t.index]].groupby('side')))
# paired day-level comparison, split vs Opus
days = sorted(A.day.unique())
o, s = A.loc[live_df(A, 'opus', 75)], A.loc[live_df(A, 'split', 75)]
do = o.groupby('day').net1.sum().reindex(days).fillna(0).to_numpy()
ds = s.groupby('day').net1.sum().reindex(days).fillna(0).to_numpy()
ho, no = o.groupby('day').hit.sum().reindex(days).fillna(0).to_numpy(), o.groupby('day').size().reindex(days).fillna(0).to_numpy()
hs, ns = s.groupby('day').hit.sum().reindex(days).fillna(0).to_numpy(), s.groupby('day').size().reindex(days).fillna(0).to_numpy()
rng = np.random.default_rng(11)
B = 20000
ix = rng.integers(0, len(days), size=(B, len(days)))
dnet = (ds - do)[ix].sum(axis=1)
dhit = hs[ix].sum(axis=1) / ns[ix].sum(axis=1) - ho[ix].sum(axis=1) / no[ix].sum(axis=1)
print('\npaired by day over 126 sessions (resampled %d times): T1 net difference split - Opus = %+.0f, 5th-95th pct %+.0f to %+.0f, positive in %.0f%% of resamples' % (
    B, (ds - do).sum(), np.percentile(dnet, 5), np.percentile(dnet, 95), 100 * (dnet > 0).mean()))
print('hit-rate difference = %+.1f pts, 5th-95th pct %+.1f to %+.1f, positive in %.1f%% of resamples' % (
    100 * (hs.sum() / ns.sum() - ho.sum() / no.sum()), 100 * np.percentile(dhit, 5), 100 * np.percentile(dhit, 95), 100 * (dhit > 0).mean()))
print('split trades also taken by Opus: %d of %d | no-trade days: Opus %d, split %d of %d' % (len(set(o.index) & set(s.index)), len(s), int((no == 0).sum()), int((ns == 0).sum()), len(days)))
json.dump({k: v for k, v in res.items()}, open(sys.argv[1] + '/v2/e7.json', 'w'))

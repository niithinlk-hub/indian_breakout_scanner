# Second check: the full cash-share replays (signals found on cash, results on cash) for 1 Sep - 19 Oct against the real result
# for the same 33 sessions, model by model and side by side.
import glob, json, os, sys, warnings
warnings.filterwarnings('ignore')
os.environ["DATABASE_URL"] = "sqlite:////tmp/claude-0/v2_unused.db"
os.environ["ENGINE_URL"] = "http://127.0.0.1:9"; os.environ["SCANNER_TOKEN"] = ""
sys.path.insert(0, sys.argv[1] + '/v2')
import numpy as np, pandas as pd
import scanner
assert "/v2/patched/" in scanner.__file__
from scanner.equity.config import EqConfig
from scanner.equity.backtest import with_all_models
from scanner.equity.score import MODELS
cfg = EqConfig()
SP = sys.argv[1]
rows = []
days = []
for p in sorted(glob.glob(SP + '/replay_sep/replay_*.json')):
    d = with_all_models(json.load(open(p)), cfg)
    days.append(d['day'])
    for s in d['signals']:
        for m in MODELS:
            if 'live' in s['in'][m]:
                rows.append({'day': d['day'], 'model': m, 'side': s['side'], 'hit': s['fut']['T1']['status'] == 'target', 'stop': s['fut']['T1']['status'] == 'stopped', 'net': s['fut']['T1']['net_rs']})
P = pd.DataFrame(rows)
from frame import load
from lab import *
df = load()
A = df[(df.day >= days[0]) & (df.day <= days[-1])].copy()
lg = A.long == 1
A['opus'], A['fable'], A['fable_op'] = A.t_opus, A.t_fable - 5, A.t_fable_op
A['opus_v2'] = np.where(lg, A.t_fable_op, A.t_opus)
A['opus_v3'] = np.where(lg, np.where(A.rel_vol < 1.0, 0.0, A.t_fable_op), A.t_opus)
print('33 sessions', days[0], '->', days[-1])
for m in MODELS:
    t = A.loc[live_df(A, m, 75)]
    g = P[P.model == m]
    line1 = '%-8s real: n=%3d hit %4.1f%% stop %4.1f%% net %+8.0f | cash replay: n=%3d hit %4.1f%% stop %4.1f%% net %+8.0f' % (
        m, len(t), 100 * t.hit.mean(), 100 * t['stop'].mean(), t.net1.sum(), len(g), 100 * g.hit.mean(), 100 * g['stop'].mean(), g.net.sum())
    bys = ' | '.join('%s real n=%2d %+7.0f / cash n=%2d %+7.0f' % (s, (t.side == s).sum(), t[t.side == s].net1.sum(), (g.side == s).sum(), g[g.side == s].net.sum()) for s in ('LONG', 'SHORT'))
    dr = t.groupby('day').net1.sum().reindex(days).fillna(0); dc = g.groupby('day').net.sum().reindex(days).fillna(0)
    print(line1, '||', bys, '|| daily corr %.2f' % np.corrcoef(dr, dc)[0, 1])

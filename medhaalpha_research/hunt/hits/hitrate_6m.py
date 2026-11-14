# Same-day hit rates for T1 / T2 / T3, six-month backtests (every trade squared off at 15:29 on its entry day).
# T1 = the stored T1 outcome. T2 / T3: the record's R is after costs, so a target counts as reached when that policy's R
# is at least the T1 policy's R plus the extra distance (T2 +0.9 R, T3 +1.6 R), less 0.03 R for the slightly higher charges.
# Checked against the stored per-policy outcomes of the cash stand-in period, which has them.
import glob, json, sys
import numpy as np
sys.path.insert(0, sys.argv[1] + '/hunt'); import harness as H
D = H.load_all()
M = {'Opus v3 (T1)': ('s_opus_v3', 75, 'T1', 6), 'Fable-OP (T3)': ('s_fable_op', 75, 'T3', 6), 'Switch-1': H.switch1}


def hits(t):
    t1 = (t.status_T1 == 'target').to_numpy()
    t2 = t1 & (t.r_T2 >= t.r_T1 + 0.9 - 0.03).to_numpy()
    t3 = t2 & (t.r_T3 >= t.r_T1 + 1.6 - 0.03).to_numpy()
    st = (t.r_T1 <= -0.97).to_numpy() | (t.status_T1 == 'stopped').to_numpy()
    return t1, t2, t3, st


# check on the stand-in period against stored statuses
st = {}
for p in sorted(glob.glob(sys.argv[1] + '/v2/proxy_unseen/proxy_*.json')):
    d = json.load(open(p))
    for s in d['signals']:
        st[(d['day'], s['time'], s['symbol'], s['setup'])] = {q: s['fut'][q]['status'] for q in ('T1', 'T2', 'T3')}
U = D['unseen']
t1, t2, t3, _ = hits(U)
true = {q: np.array([st[(r.day, r.time, r.symbol, r.setup)][q] == 'target' for r in U.itertuples()]) for q in ('T1', 'T2', 'T3')}
print('rule check on %d stand-in signals: T1 agrees %.1f%%, T2 %.1f%%, T3 %.1f%%' % (len(U), 100 * (t1 == true['T1']).mean(),
      100 * (t2 == true['T2']).mean(), 100 * (t3 == true['T3']).mean()))
out = {}
for s, lab in (('real', '12 May-11 Nov 2026 (real futures)'), ('unseen', '3 Nov 2025-11 May 2026 (cash prices)')):
    print('==', lab)
    out[s] = {}
    for name, spec in M.items():
        t = H.run(D[s], spec)
        a, b, c, d = hits(t)
        n = len(t)
        out[s][name] = {'n': n, 'T1': int(a.sum()), 'T2': int(b.sum()), 'T3': int(c.sum()), 'stopped_before_T1': int(d.sum())}
        print('  %-14s n=%3d | T1 %3d (%4.1f%%) | T2 %3d (%4.1f%%) | T3 %3d (%4.1f%%) | stopped before T1 %3d (%4.1f%%) | of T1 hits: T2 %4.1f%% T3 %4.1f%%' % (
            name, n, a.sum(), 100 * a.mean(), b.sum(), 100 * b.mean(), c.sum(), 100 * c.mean(), d.sum(), 100 * d.mean(),
            100 * b.sum() / a.sum(), 100 * c.sum() / a.sum()))
json.dump(out, open(sys.argv[1] + '/hunt/hits/hitrate_6m.json', 'w'), indent=1)

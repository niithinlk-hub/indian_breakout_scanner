# Part 1b: exact re-pricing only on rows where the replay's futures trade IS the six-month record's trade
# (futures net equal within Rs 1 on all 7 exits), so the futures lots, entry, exit price and exit minute are the real ones.
import sys, json
import numpy as np, pandas as pd
SP = sys.argv[1]
sys.path.insert(0, SP + '/hunt'); import harness as H
D = H.load_all(); R = D['real']
X = pd.read_pickle(SP + '/hunt/six_month/lots_fix/h2_replay_inputs.pkl')
h2 = R[R.day >= '2026-09-01']
h2x = h2.join(X)
same = h2x.found.astype(bool).copy()
for p in H.POL:
    same &= (h2x['f_net_' + p].astype(float) - h2x['net_' + p]).abs().le(1.0) & h2x['f_F1_' + p].notna()
same &= h2x.f_lots.fillna(0) > 0
E = h2x[same].copy()
E['o_F0'] = E.f_F0.astype(float); E['o_qty'] = (E.f_lots * E.f_lot).astype(float)
for p in H.POL:
    E['o_F1_' + p] = E['f_F1_' + p].astype(float); E['o_exit_ts_' + p] = E['f_exit_ts_' + p]
    E['opt_' + p] = H.option_net(E, p)
print('rows that are the same futures trade in the replay and the six-month record: %d of %d' % (len(E), len(h2)))
MODELS = {'Opus (T1)': ('s_opus', 75, 'T1', 6), 'Opus v2 (T1)': ('s_opus_v2', 75, 'T1', 6), 'Opus v3 (T1)': ('s_opus_v3', 75, 'T1', 6),
          'Fable (T3)': ('s_fable', 75, 'T3', 6), 'Fable-OP (T3)': ('s_fable_op', 75, 'T3', 6), 'Switch-1': H.switch1,
          'Opus v3 CLOSE_TR': ('s_opus_v3', 75, 'CLOSE_TR', 6)}
out = {}
print('  %-18s %5s %6s %12s %12s %8s %10s %10s' % ('model', 'n', 'exact', 'current', 'exact', 'diff %', 'lots eq %', 'exit min eq %'))
for name, spec in MODELS.items():
    t = H.run(h2, spec)
    inx = t.index.isin(E.index)
    sub = E.loc[t.index[inx]]
    pol = t.pol[inx].to_numpy()
    cur = t.pnl[inx].to_numpy()
    ex = np.array([sub.iloc[k]['opt_' + p] for k, p in enumerate(pol)])
    lots_eq = (sub.o_qty.to_numpy() == t.o_qty[inx].to_numpy()).mean()
    ts_eq = np.mean([pd.Timestamp(sub.iloc[k]['f_exit_ts_' + p]) == pd.Timestamp(t[inx].iloc[k]['o_exit_ts_' + p]) for k, p in enumerate(pol)])
    out[name] = {'n': len(t), 'n_exact': int(inx.sum()), 'current': round(float(cur.sum())), 'exact': round(float(ex.sum())),
                 'corr': round(float(np.corrcoef(cur, ex)[0, 1]), 3), 'lots_equal_pct': round(100 * lots_eq, 1), 'exit_minute_equal_pct': round(100 * ts_eq, 1)}
    o = out[name]
    print('  %-18s %5d %6d %+12.0f %+12.0f %+7.1f%% %9.1f%% %9.1f%%  corr %.3f' % (name, o['n'], o['n_exact'], o['current'], o['exact'],
          100 * (o['exact'] - o['current']) / abs(o['current']), o['lots_equal_pct'], o['exit_minute_equal_pct'], o['corr']))
allc = E.index.isin(h2.index)
cur_all = np.concatenate([h2.loc[E.index, 'opt_' + p].to_numpy() for p in H.POL]); ex_all = np.concatenate([E['opt_' + p].to_numpy() for p in H.POL])
print('all exact rows x 7 exits: current %+.0f, exact %+.0f (%+.1f%%), corr %.3f' % (cur_all.sum(), ex_all.sum(), 100 * (ex_all.sum() - cur_all.sum()) / abs(cur_all.sum()), np.corrcoef(cur_all, ex_all)[0, 1]))
json.dump(out, open(SP + '/hunt/six_month/lots_fix/part1b.json', 'w'), indent=1)

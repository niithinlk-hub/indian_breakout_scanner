# How much do the six-month OPTION figures on the real set move if each option uses the scanner's actual FUTURES
# lots and the actual futures move, instead of lots and move sized from the cash-share stop?
#  Part 1, 1 Sep - 11 Nov: the scanner's day-by-day replays on real futures (replay_sep, replay7, replay_oct, replay_nov2,
#          replay) give the exact futures entry, stop, lots, exit price and exit minute per policy. Re-price exactly.
#  Part 2, all real rows where the futures lots can be inferred from pull.json (>= 2 distinct R across policies):
#          qty = inferred futures lots, move = R x (Rs per R / qty). Compare with the current pricing on the same rows.
import glob, json, os, sys
import numpy as np, pandas as pd
SP = sys.argv[1]
sys.path.insert(0, SP + '/hunt'); import harness as H
OUT = SP + '/hunt/six_month/lots_fix'
D = H.load_all(); R = D['real']
MODELS = {'Opus (T1)': ('s_opus', 75, 'T1', 6), 'Opus v2 (T1)': ('s_opus_v2', 75, 'T1', 6), 'Opus v3 (T1)': ('s_opus_v3', 75, 'T1', 6),
          'Fable (T3)': ('s_fable', 75, 'T3', 6), 'Fable-OP (T3)': ('s_fable_op', 75, 'T3', 6), 'Switch-1': H.switch1,
          'Opus v3 CLOSE_TR': ('s_opus_v3', 75, 'CLOSE_TR', 6)}

# ---------------------------------------------------------------- part 1: exact futures inputs from the replays
rec, files = {}, {}
order = ['replay_sep', 'replay7', 'replay_oct', 'replay_nov2', 'replay']           # later folders override earlier ones
for d in order:
    for f in sorted(glob.glob('%s/%s/replay_*.json' % (SP, d))):
        x = json.load(open(f))
        files[x['day']] = d
        for s in x['signals']:
            if s.get('setup') not in ('A', 'B') or not s.get('fut'):
                continue
            rec[(x['day'], s['time'], s['symbol'], s['setup'])] = s
h2 = R[(R.day >= '2026-09-01')].copy()
print('real 1 Sep-11 Nov: %d rows, %d sessions; replay sessions available: %d (%s .. %s)' % (len(h2), h2.day.nunique(), len(files), min(files), max(files)))
miss_days = sorted(set(h2.day) - set(files))
print('sessions with no replay file:', miss_days)
X = []
ok = mism = 0
for i, r in h2.iterrows():
    s = rec.get((r.day, r.time, r.symbol, r.setup))
    row = {'idx': i, 'found': s is not None}
    if s is not None:
        row['f_lots'], row['f_lot'] = s.get('lots'), s.get('lot')
        row['f_F0'] = s['fut']['T1'].get('entry') if s['fut'].get('T1') else np.nan
        for p in H.POL:
            o = s['fut'].get(p) or {}
            row['f_F1_' + p], row['f_exit_ts_' + p], row['f_net_' + p], row['f_status_' + p] = o.get('exit'), o.get('exit_ts'), o.get('net_rs'), o.get('status')
        nets = np.array([row['f_net_' + p] if row['f_net_' + p] is not None else np.nan for p in H.POL], float)
        real = np.array([r['net_' + p] for p in H.POL], float)
        if np.all(np.abs(nets - real) <= 1.0):
            ok += 1
        else:
            mism += 1
    X.append(row)
X = pd.DataFrame(X).set_index('idx')
print('rows found in replays: %d of %d; futures net equal to the six-month record on all 7 exits: %d; differ: %d' % (X.found.sum(), len(X), ok, mism))
X.to_pickle(OUT + '/h2_replay_inputs.pkl')

# exact option re-pricing on rows that are found and agree
h2x = h2.join(X)
good = h2x.found & h2x.f_lots.notna() & (h2x.f_lots > 0)
for p in H.POL:
    good &= h2x['f_status_' + p].ne('no_data') & h2x['f_F1_' + p].notna()
print('rows usable for exact re-pricing: %d' % good.sum())
E = h2x[good].copy()
E['o_F0'] = E.f_F0.astype(float)
E['o_qty'] = (E.f_lots * E.f_lot).astype(float)
for p in H.POL:
    E['o_F1_' + p] = E['f_F1_' + p].astype(float)
    E['o_exit_ts_' + p] = E['f_exit_ts_' + p]
    E['opt_' + p] = H.option_net(E, p)
    E['net_' + p] = E['f_net_' + p].astype(float)
# entry minute check: replay entry ts = o_entry_ts?  (keep the harness entry ts)
res1 = {}
days = sorted(h2.day.unique())
print('\nPART 1. 1 Sep - 11 Nov, OPTION net: current pricing vs exact futures lots/prices from the replays')
print('  %-18s %5s %5s %12s %12s %8s | %12s %12s' % ('model', 'n', 'exact', 'current', 'exact', 'diff %', 'cur (same rows)', 'fut net'))
for name, spec in MODELS.items():
    t = H.run(h2, spec)
    inx = t.index.isin(E.index)
    cur_all = float(t.pnl.sum())
    # exact: replace the rows that can be priced exactly, keep current for the rest
    ex = t.copy()
    sub = E.loc[t.index[inx]]
    ex.loc[inx, 'pnl'] = [sub.loc[i, 'opt_' + p] for i, p in zip(t.index[inx], t.pol[inx])]
    res1[name] = {'n': len(t), 'n_exact': int(inx.sum()), 'current': round(cur_all), 'exact': round(float(ex.pnl.sum())),
                  'current_same_rows': round(float(t.pnl[inx].sum())), 'exact_same_rows': round(float(ex.pnl[inx].sum())), 'fut': round(float(t.fut.sum())),
                  'months_current': {k: round(float(v)) for k, v in t.groupby(t.day.str[:7]).pnl.sum().items()},
                  'months_exact': {k: round(float(v)) for k, v in ex.groupby(ex.day.str[:7]).pnl.sum().items()},
                  'lots_equal_pct': round(100 * float((sub.o_qty.values == t.o_qty[inx].values).mean()), 1)}
    r = res1[name]
    print('  %-18s %5d %5d %+12.0f %+12.0f %+7.1f%% | %+12.0f %+12.0f | lots equal on %.1f%% of exact rows' % (
        name, r['n'], r['n_exact'], r['current'], r['exact'], 100 * (r['exact'] - r['current']) / abs(r['current']), r['current_same_rows'], r['fut'], r['lots_equal_pct']))

# ---------------------------------------------------------------- part 2: inferred futures lots, whole six months
F = pd.read_pickle(SP + '/hunt/six_month/sources/real_fut_lots.pkl')
assert (F.day.values == R.day.values).all() and (F.symbol.values == R.symbol.values).all()
F.index = R.index
clean = F.fut_lots_est.notna() & (F.cres.abs() < 0.35)
print('\nPART 2. rows with inferred futures lots: %d of %d' % (clean.sum(), len(R)))
C = R[clean].copy()
C['o_qty'] = (F.fut_lots_est[clean] * F.L[clean]).astype(float)
ru = F.A[clean] / C.o_qty                                   # futures Rs per R per unit
sgn = np.where(C.side == 'LONG', 1.0, -1.0)
ratio = ru / C.o_risk_abs
print('  futures risk per unit / cash-stop risk per unit: quantiles %s' % np.round(np.quantile(ratio, [0.05, 0.25, 0.5, 0.75, 0.95]), 3).tolist())
for p in H.POL:
    C['o_F1_' + p] = C.o_F0 + sgn * C['r_' + p] * ru
    C['opt_' + p] = H.option_net(C, p)
res2 = {}
print('  %-18s %5s %5s %12s %12s %12s' % ('model', 'n', 'rows', 'current', 'fut lots+move', 'lots only'))
for name, spec in MODELS.items():
    t = H.run(R, spec)
    inx = t.index.isin(C.index)
    sub = C.loc[t.index[inx]]
    corr = np.array([sub.loc[i, 'opt_' + p] for i, p in zip(t.index[inx], t.pol[inx])])
    lots_only = 0.0
    for p in t.pol[inx].unique():
        m = inx & (t.pol == p).to_numpy()
        lots_only += float(H.option_net(t[m], p, qty=C.loc[t.index[m], 'o_qty'].to_numpy()).sum())
    res2[name] = {'rows': int(inx.sum()), 'current': round(float(t.pnl[inx].sum())), 'fut_lots_and_move': round(float(corr.sum())), 'lots_only': round(lots_only),
                  'total_current': round(float(t.pnl.sum())), 'total_with_fix': round(float(t.pnl[~inx].sum() + corr.sum()))}
    r = res2[name]
    print('  %-18s %5d %5d %+12.0f %+12.0f %+12.0f | six-month total %+.0f -> %+.0f (%+.1f%%)' % (
        name, len(t), r['rows'], r['current'], r['fut_lots_and_move'], r['lots_only'], r['total_current'], r['total_with_fix'],
        100 * (r['total_with_fix'] - r['total_current']) / r['total_current']))
json.dump({'part1_sep_nov_exact': res1, 'part2_inferred': res2}, open(OUT + '/lots_fix.json', 'w'), indent=1)

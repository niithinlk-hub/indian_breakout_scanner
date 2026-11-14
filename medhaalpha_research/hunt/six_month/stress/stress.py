# Robustness of the OPTION ranking of the seven rows in ../six_month.json (task id: stress).
#  1. re-price every picked trade under alternative option-model assumptions (one at a time)
#  2. day bootstrap of six-month option net (same resampled days for all models), pairwise P(first > second)
#  3. month by month on real: leader per month, months beating Opus (T1)
#  4. concentration: share of six-month option net from best 5 days / best month
#  5. capital: most premium open at once (entry .. futures exit + 1 min) vs Rs 3 lakh
# Also cross-checks the base figures against six_month.json.
import json, os, sys, itertools
import numpy as np, pandas as pd

SP = '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
sys.path.insert(0, SP + '/hunt')
import harness as H

OUT = os.path.dirname(os.path.abspath(__file__))
J = json.load(open(SP + '/hunt/six_month/six_month.json'))
D = H.load_all()

MODELS = {
    'Opus (T1), live model': ('s_opus', 75, 'T1', 6),
    'Opus v2 (T1)': ('s_opus_v2', 75, 'T1', 6),
    'Opus v3 (T1)': ('s_opus_v3', 75, 'T1', 6),
    'Fable (T3)': ('s_fable', 75, 'T3', 6),
    'Fable-OP (T3)': ('s_fable_op', 75, 'T3', 6),
    'Switch-1': H.switch1,
    'Opus v3, trailing stop to close (CLOSE_TR)': ('s_opus_v3', 75, 'CLOSE_TR', 6),
}
SHORT = {'Opus (T1), live model': 'Opus', 'Opus v2 (T1)': 'v2', 'Opus v3 (T1)': 'v3', 'Fable (T3)': 'Fable',
         'Fable-OP (T3)': 'FOP', 'Switch-1': 'Sw1', 'Opus v3, trailing stop to close (CLOSE_TR)': 'v3CTR'}
BOOT = ['Fable-OP (T3)', 'Switch-1', 'Fable (T3)', 'Opus v3 (T1)', 'Opus v3, trailing stop to close (CLOSE_TR)', 'Opus (T1), live model']
SCEN = {
    'base': {},
    'decay1.5': {'decay': 1.5},
    'decay3.5': {'decay': 3.5},
    'iv0.8': {'iv_mult': 0.8},
    'iv1.2': {'iv_mult': 1.2},
    'slip0.5': {'slip_pct': 0.5},
    'slip1.0': {'slip_pct': 1.0},
    'lag3': {'exit_lag_min': 3.0},
    'worst(decay3.5+slip1.0+lag3)': {'decay': 3.5, 'slip_pct': 1.0, 'exit_lag_min': 3.0},
}
CAP = 300000.0


def reprice(t, **kw):
    """option net and detail per row of picked trades t (with 'pol'), under kwargs for H.option_net."""
    parts = [H.option_net(g, p, detail=True, **kw) for p, g in t.groupby('pol')]
    return pd.concat(parts).reindex(t.index)


def max_open(t, outlay):
    """independent max-open premium: events at entry (+outlay) and futures exit + 1 min (-outlay); releases first on ties."""
    e0 = pd.to_datetime(t['o_entry_ts'], utc=True).to_numpy()
    x = np.array([r['o_exit_ts_' + r['pol']] for _, r in t.iterrows()])
    x = (pd.to_datetime(pd.Series(x), utc=True) + pd.Timedelta(minutes=1)).to_numpy()
    ts = np.concatenate([e0, x])
    fl = np.concatenate([np.ones(len(t)), np.zeros(len(t))])
    v = np.concatenate([outlay, -outlay])
    o = np.lexsort((fl, ts))
    cur = np.cumsum(v[o])
    i = int(np.argmax(cur))
    return float(cur[i]), pd.Timestamp(ts[o][i]).tz_convert('Asia/Kolkata')


res = {'scenarios': {}, 'order': {}, 'boot': {}, 'months': {}, 'conc': {}, 'capital': {}, 'json_check': []}
rng = np.random.default_rng(20261114)
for s in ('real', 'unseen'):
    df = D[s]
    days = sorted(df.day.unique())
    T = {m: H.run(df, spec) for m, spec in MODELS.items()}
    # ---- 1. scenarios
    sc = {}
    for sn, kw in SCEN.items():
        sc[sn] = {}
        for m, t in T.items():
            det = reprice(t, **kw)
            sc[sn][m] = float(det['net'].sum())
            if sn == 'base':
                assert np.allclose(det['net'].to_numpy(), t['pnl'].to_numpy(), atol=1e-6), m
                t['outlay'] = det['outlay'].where(det['qty'] > 0, 0.0).to_numpy()
                assert np.isfinite(t['outlay']).all()
            if sn == 'iv1.2':
                t['outlay_iv12'] = det['outlay'].where(det['qty'] > 0, 0.0).to_numpy()
    res['scenarios'][s] = {sn: {m: round(v) for m, v in d.items()} for sn, d in sc.items()}
    base_order = sorted(MODELS, key=lambda m: -sc['base'][m])
    res['order'][s] = {}
    for sn in SCEN:
        o = sorted(MODELS, key=lambda m: -sc[sn][m])
        swaps = [(SHORT[a], SHORT[b]) for a, b in itertools.combinations(base_order, 2) if sc[sn][a] < sc[sn][b]]
        res['order'][s][sn] = {'order': ' > '.join(SHORT[m] for m in o), 'changed': o != base_order, 'swapped_pairs': swaps}
    # ---- json cross-check (base)
    for m, t in T.items():
        jm = J['models'][s][m]
        byday = t.pnl.groupby(t.day).sum().reindex(days).fillna(0.0)
        mo = t.pnl.groupby(t.day.str[:7]).sum()
        mx, when = max_open(t, t['outlay'].to_numpy())
        chk = {'opt_net': float(t.pnl.sum()), 'opt_best_day': float(byday.max()), 'opt_worst_day': float(byday.min()),
               'premium_total': float(t.outlay.sum()), 'premium_max_open': mx, 'trades': len(t)}
        for k, v in chk.items():
            if abs(v - jm[k]) > 1:
                res['json_check'].append({'set': s, 'model': m, 'item': k, 'json': jm[k], 'mine': round(v, 1)})
        for k, v in mo.items():
            if abs(v - jm['month_opt'][k]) > 1:
                res['json_check'].append({'set': s, 'model': m, 'item': 'month_opt ' + k, 'json': jm['month_opt'][k], 'mine': round(v, 1)})
        if jm['opt_best_month'][0] != mo.idxmax() or abs(jm['opt_best_month'][1] - mo.max()) > 1:
            res['json_check'].append({'set': s, 'model': m, 'item': 'opt_best_month', 'json': jm['opt_best_month'], 'mine': [mo.idxmax(), round(mo.max())]})
    # ---- 2. bootstrap
    M = np.column_stack([T[m].pnl.groupby(T[m].day).sum().reindex(days).fillna(0.0).to_numpy() for m in BOOT])
    nB, nd = 10000, len(days)
    idx = rng.integers(0, nd, size=(nB, nd))
    tot = M[idx].sum(axis=1)           # nB x models
    bo = {}
    for i, j in itertools.permutations(range(len(BOOT)), 2):
        if i < j:
            bo['%s > %s' % (SHORT[BOOT[i]], SHORT[BOOT[j]])] = {'p': round(float((tot[:, i] > tot[:, j]).mean()), 4),
                                                                 'ties': int((tot[:, i] == tot[:, j]).sum()),
                                                                 'diff_obs': round(float(M[:, i].sum() - M[:, j].sum()))}
    q = {SHORT[m]: [round(float(np.percentile(tot[:, k], 5))), round(float(np.percentile(tot[:, k], 95))), round(float((tot[:, k] > 0).mean()), 4)] for k, m in enumerate(BOOT)}
    best = np.bincount(tot.argmax(axis=1), minlength=len(BOOT)) / nB
    res['boot'][s] = {'pairs': bo, 'p5_p95_Ppos': q, 'P_best_of_6': {SHORT[m]: round(float(best[k]), 4) for k, m in enumerate(BOOT)}}
    # ---- 3. months
    months = sorted({d[:7] for d in days})
    MO = pd.DataFrame({SHORT[m]: T[m].pnl.groupby(T[m].day.str[:7]).sum().reindex(months).fillna(0.0) for m in MODELS})
    res['months'][s] = {'table': {mo: {k: round(v) for k, v in MO.loc[mo].items()} for mo in months},
                        'leader': {mo: MO.loc[mo].idxmax() for mo in months},
                        'beats_Opus': {c: int((MO[c] > MO['Opus']).sum()) for c in MO.columns if c != 'Opus'},
                        'beats_Opus_excl_partial': {c: int((MO[c].iloc[1:-1] > MO['Opus'].iloc[1:-1]).sum()) for c in MO.columns if c != 'Opus'}}
    # ---- 4. concentration
    co = {}
    for m, t in T.items():
        byday = t.pnl.groupby(t.day).sum().reindex(days).fillna(0.0)
        tot6 = float(byday.sum())
        b5 = float(byday.nlargest(5).sum())
        mo = byday.groupby(byday.index.str[:7]).sum()
        co[SHORT[m]] = {'net': round(tot6), 'best5': round(b5), 'best5_share%': round(100 * b5 / tot6, 1),
                        'best5_days': list(byday.nlargest(5).index), 'best_month': mo.idxmax(), 'best_month_net': round(float(mo.max())),
                        'best_month_share%': round(100 * float(mo.max()) / tot6, 1), 'net_ex_best5': round(tot6 - b5),
                        'net_ex_best_month': round(tot6 - float(mo.max()))}
    res['conc'][s] = co
    # ---- 5. capital
    ca = {}
    for m, t in T.items():
        mx, when = max_open(t, t['outlay'].to_numpy())
        mx12, w12 = max_open(t, t['outlay_iv12'].to_numpy())
        # per-day peak, to count days above Rs 3 lakh and days above 2.5 lakh
        peaks = []
        for d, g in t.groupby('day'):
            peaks.append(max_open(g, g['outlay'].to_numpy())[0])
        peaks = np.array(peaks)
        ca[SHORT[m]] = {'max_open': round(mx), 'at': str(when), 'max_open_iv1.2': round(mx12), 'at_iv1.2': str(w12),
                        'days_over_3L': int((peaks > CAP).sum()), 'days_over_2.5L': int((peaks > 250000).sum()),
                        'max_single_outlay': round(float(t.outlay.max())), 'median_day_peak': round(float(np.median(peaks)))}
    res['capital'][s] = ca

json.dump(res, open(OUT + '/stress.json', 'w'), indent=1, default=str)

# ------------------------------------------------------------------ printout
for s in ('real', 'unseen'):
    print('\n======== %s' % s.upper())
    print('-- 1. six-month option net by scenario (Rs)')
    hdr = ['%-30s' % 'scenario'] + ['%9s' % SHORT[m] for m in MODELS]
    print(' '.join(hdr))
    for sn in SCEN:
        print('%-30s ' % sn + ' '.join('%9d' % res['scenarios'][s][sn][m] for m in MODELS) + '   ' + res['order'][s][sn]['order']
              + ('   CHANGED ' + str(res['order'][s][sn]['swapped_pairs']) if res['order'][s][sn]['changed'] else ''))
    print('-- 2. bootstrap P(first > second), 10,000 day resamples')
    for k, v in res['boot'][s]['pairs'].items():
        print('   %-14s %.3f  (observed diff %+d, ties %d)' % (k, v['p'], v['diff_obs'], v['ties']))
    print('   5th/95th pct, P(>0):', res['boot'][s]['p5_p95_Ppos'])
    print('   P(best of the 6):', res['boot'][s]['P_best_of_6'])
    print('-- 3. months')
    for mo, row in res['months'][s]['table'].items():
        print('   %s ' % mo + ' '.join('%s %+d' % (k, v) for k, v in row.items()) + '  leader ' + res['months'][s]['leader'][mo])
    print('   months beating Opus:', res['months'][s]['beats_Opus'], ' excl. partial first/last month:', res['months'][s]['beats_Opus_excl_partial'])
    print('-- 4. concentration')
    for k, v in res['conc'][s].items():
        print('   %-6s net %+9d best5 %+8d (%.1f%%) best month %s %+8d (%.1f%%) ex-best5 %+9d ex-best-month %+9d' % (
            k, v['net'], v['best5'], v['best5_share%'], v['best_month'], v['best_month_net'], v['best_month_share%'], v['net_ex_best5'], v['net_ex_best_month']))
    print('-- 5. capital')
    for k, v in res['capital'][s].items():
        print('   %-6s max open %8d at %s | iv x1.2: %8d | days >3L %d, >2.5L %d | largest single outlay %d | median day peak %d' % (
            k, v['max_open'], v['at'], v['max_open_iv1.2'], v['days_over_3L'], v['days_over_2.5L'], v['max_single_outlay'], v['median_day_peak']))
print('\n-- json cross-check mismatches (> Rs 1):', res['json_check'] or 'none')

# Cross-check of the INPUTS in D (harness.load_all) against the raw sources: six/pull.json (real) and
# v2/proxy_unseen/proxy_*.json (unseen), plus the scanner's own live picks / totals. Reads only; writes into this folder.
import glob, json, math, os, sys
import numpy as np, pandas as pd

SP = '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
sys.path.insert(0, SP + '/hunt')
import harness as H
OUT = os.path.dirname(os.path.abspath(__file__))
D = H.load_all()
J = json.load(open(SP + '/hunt/six_month/six_month.json'))
POLS = ['T1', 'T2', 'T3', 'CLOSE', 'T2_TR', 'T3_TR', 'CLOSE_TR']
rep = {}


def my_pick(df, col, thr=75.0, n=6):
    d = df[df[col].notna() & (df[col] >= thr)].copy()
    d['_neg'] = -d[col]
    d = d.sort_values(['day', 'time', '_neg', 'symbol'], kind='mergesort')
    return d.groupby('day', sort=True).head(n)


# ---------------------------------------------------------------- REAL vs pull.json
P = json.load(open(SP + '/six/pull.json'))
recs = []
for dd in P['sig']['days']:
    for s in dd['signals']:
        t, sym, setup, sc, net, r = s
        if setup not in ('A', 'B'):
            continue
        recs.append({'day': dd['day'], 'time': t, 'symbol': sym, 'setup': setup, 'p_opus': sc[0], 'p_fable': sc[1], 'p_fable_op': sc[2],
                     **{'pn_' + p: net[i] for i, p in enumerate(POLS)}, **{'pr_' + p: r[i] for i, p in enumerate(POLS)}})
PR = pd.DataFrame(recs)
R = D['real']
M = R.merge(PR, on=['day', 'time', 'symbol', 'setup'], how='outer', indicator=True)
rr = {'rows_D': len(R), 'rows_pull_AB': len(PR), 'merge': M['_merge'].value_counts().to_dict()}
B = M[M._merge == 'both']
rr['score_opus_maxdiff'] = float((B.s_opus - B.p_opus).abs().max())
rr['score_fable_maxdiff(s_fable+5)'] = float((B.s_fable + 5 - B.p_fable).abs().max())
rr['score_fable_op_maxdiff'] = float((B.s_fable_op - B.p_fable_op).abs().max())
rr['rows_score_differs'] = int(((B.s_opus - B.p_opus).abs() > 1e-9).sum() + ((B.s_fable + 5 - B.p_fable).abs() > 1e-9).sum() + ((B.s_fable_op - B.p_fable_op).abs() > 1e-9).sum())
for p in POLS:
    rr['net_%s_maxdiff' % p] = float((B['net_' + p] - B['pn_' + p]).abs().max())
    rr['r_%s_maxdiff' % p] = float((B['r_' + p] - B['pr_' + p]).abs().max())
# scanner's own live totals (pull.json six.totals.<m>.live) vs grid futures in six_month.json
gmap = {'opus': 'Opus', 'fable': 'Fable', 'fable_op': 'Fable-OP'}
tot = {}
for m, g in gmap.items():
    lv = P['six']['totals'][m]['live']
    tot[m] = {'n_scanner': lv['n'], 'n_json_model': None}
    for p in POLS:
        tot[m][p] = {'scanner': lv[p], 'json_grid_fut': J['grid']['real'][g][p]['fut'], 'diff': J['grid']['real'][g][p]['fut'] - lv[p]}
rr['scanner_live_totals_vs_grid'] = tot
# per-day live picks: scanner summary vs my live-rule pick
per_day = {}
cols = {'opus': 's_opus', 'fable': 's_fable', 'fable_op': 's_fable_op'}
for m, col in cols.items():
    t = my_pick(R, col)
    g = t.groupby('day')
    bad = []
    for s in P['six']['summary']:
        lv = s['models'][m]['live']
        n_m = int(g.size().get(s['day'], 0))
        sums = {p: float(t.loc[t.day == s['day'], 'net_' + p].sum()) for p in POLS}
        dif = max(abs(sums[p] - lv[p]) for p in POLS)
        if n_m != lv['n'] or dif > 1.0:
            bad.append((s['day'], n_m, lv['n'], round(dif, 2)))
    per_day[m] = {'days_checked': len(P['six']['summary']), 'days_mismatch(n or any policy sum > Rs1)': bad[:20], 'n_bad': len(bad)}
    # worst day / max dd for the model's main exit
    pol = 'T1' if m == 'opus' else 'T3'
    days = sorted(R.day.unique())
    byd = t.groupby('day')['net_' + pol].sum().reindex(days).fillna(0)
    eq = byd.cumsum()
    per_day[m]['mine_worst_day_%s' % pol] = float(byd.min())
    per_day[m]['scanner_worst_day_%s' % pol] = P['six']['totals'][m]['live']['worst_day'][pol]
    per_day[m]['mine_maxdd_%s' % pol] = float((eq - eq.cummax().clip(lower=0)).min())
    per_day[m]['scanner_maxdd_%s' % pol] = P['six']['totals'][m]['live']['max_drawdown'][pol]
    per_day[m]['mine_days_pos_%s' % pol] = int((byd > 0).sum())
    per_day[m]['scanner_days_pos_%s' % pol] = P['six']['totals'][m]['live']['days_positive'][pol]
rr['per_day_live_vs_scanner'] = per_day
# monthly
mon = {}
for mo in P['six']['months']:
    for m, col in cols.items():
        pol = 'T1' if m == 'opus' else 'T3'
        t = my_pick(R, col)
        tm = t[t.day.str[:7] == mo['month']]
        mon['%s.%s' % (mo['month'], m)] = {'n_mine': len(tm), 'n_scanner': mo['totals'][m]['live']['n'],
                                           pol + '_mine': round(float(tm['net_' + pol].sum()), 2), pol + '_scanner': mo['totals'][m]['live'][pol]}
rr['monthly_vs_scanner'] = mon
rep['real'] = rr

# ---------------------------------------------------------------- UNSEEN vs proxy files
recs = []
for f in sorted(glob.glob(SP + '/v2/proxy_unseen/proxy_*.json')):
    doc = json.load(open(f))
    for s in doc['signals']:
        if s['setup'] not in ('A', 'B'):
            continue
        d = {'day': doc['day'], 'time': s['time'], 'symbol': s['symbol'], 'setup': s['setup'], 'nodata': s['fut']['T1']['status'] == 'no_data',
             'lot': s['lot'], 'lots': s['lots'], 'entry_ref': s['entry_ref']}
        for m in ('opus', 'fable', 'fable_op', 'opus_v2', 'opus_v3'):
            d['p_' + m] = s['scores'].get(m)
            d['in_' + m] = 'live' in (s.get('in', {}).get(m) or [])
        for p in POLS:
            o = s['fut'].get(p) or {}
            d['pn_' + p], d['pr_' + p], d['px_' + p], d['pts_' + p], d['pe_' + p] = o.get('net_rs'), o.get('r'), o.get('exit'), o.get('exit_ts'), o.get('entry')
        recs.append(d)
U0 = pd.DataFrame(recs)
U = D['unseen']
ur = {'proxy_AB_rows': len(U0), 'proxy_nodata_rows': int(U0.nodata.sum()), 'rows_D': len(U)}
M = U.merge(U0, on=['day', 'time', 'symbol', 'setup'], how='outer', indicator=True)
ur['merge'] = M['_merge'].value_counts().to_dict()
B = M[M._merge == 'both']
ur['score_opus_maxdiff'] = float((B.s_opus - B.p_opus).abs().max())
ur['score_fable_maxdiff(s_fable+5)'] = float((B.s_fable + 5 - B.p_fable).abs().max())
ur['score_fable_op_maxdiff'] = float((B.s_fable_op - B.p_fable_op).abs().max())
dv2 = (B.s_opus_v2 - B.p_opus_v2).abs()
dv3 = (B.s_opus_v3 - B.p_opus_v3).abs()
ur['score_opus_v2_rows_differ(harness vs scanner)'] = int((dv2 > 1e-9).sum())
ur['score_opus_v3_rows_differ(harness vs scanner)'] = int((dv3 > 1e-9).sum())
ur['score_v2_examples'] = B.loc[dv2 > 1e-9, ['day', 'time', 'symbol', 'side', 'rel_vol', 's_opus', 's_fable_op', 's_opus_v2', 'p_opus_v2']].head(8).to_dict('records')
ur['score_v3_examples'] = B.loc[dv3 > 1e-9, ['day', 'time', 'symbol', 'side', 'rel_vol', 's_opus', 's_fable_op', 's_opus_v3', 'p_opus_v3']].head(8).to_dict('records')
# do differences cross the 75 cut?
ur['v2_cut_flips'] = int(((B.s_opus_v2 >= 75) != (B.p_opus_v2 >= 75)).sum())
ur['v3_cut_flips'] = int(((B.s_opus_v3 >= 75) != (B.p_opus_v3 >= 75)).sum())
for p in POLS:
    ur['net_%s_maxdiff' % p] = float((B['net_' + p] - B['pn_' + p].astype(float)).abs().max())
    ur['o_exit_ts_%s_differs' % p] = int((B['o_exit_ts_' + p] != B['pts_' + p]).sum())
    ur['o_F1_%s_vs_exit_maxdiff' % p] = float((B['o_F1_' + p] - B['px_' + p].astype(float)).abs().max())
ur['o_F0_vs_fut_entry_maxdiff'] = float((B['o_F0'] - B['pe_T1'].astype(float)).abs().max())
ur['o_qty_vs_lot*lots_differs'] = int((B['o_qty'] != B['lot_y'] * B['lots_y']).sum()) if 'lot_y' in B else int((B['o_qty'] != B['lot'] * B['lots']).sum())
# scanner's own 'live' picks per model vs my live-rule pick on D
lp = {}
for m, col in [('opus', 's_opus'), ('fable', 's_fable'), ('fable_op', 's_fable_op'), ('opus_v2', 's_opus_v2'), ('opus_v3', 's_opus_v3')]:
    mine = set(map(tuple, my_pick(U, col)[['day', 'time', 'symbol']].values))
    scan = set(map(tuple, U0.loc[U0['in_' + m], ['day', 'time', 'symbol']].values))
    scan_ok = set(map(tuple, U0.loc[U0['in_' + m] & ~U0.nodata, ['day', 'time', 'symbol']].values))
    lp[m] = {'mine': len(mine), 'scanner_live_AB': len(scan), 'scanner_live_AB_with_data': len(scan_ok),
             'mine_not_scanner': sorted(mine - scan)[:10], 'n_mine_not_scanner': len(mine - scan),
             'scanner_not_mine': sorted(scan - mine)[:10], 'n_scanner_not_mine': len(scan - mine)}
ur['live_pick_vs_scanner'] = lp
rep['unseen'] = ur

# ---------------------------------------------------------------- IV formula check (both sets)
for S in ('real', 'unseen'):
    d = D[S]
    rv = d['atr_pct'] * math.sqrt(252) / 125
    iv = np.exp(-0.414 + 0.757 * np.log(rv) + 0.034 * (d['o_kind'] == 'PE'))
    rep.setdefault('iv', {})[S] = {'max_abs_diff': float((iv - d['o_iv']).abs().max()), 'rows_diff_gt_1e-6': int(((iv - d['o_iv']).abs() > 1e-6).sum())}

json.dump(rep, open(OUT + '/crosscheck_sources.json', 'w'), indent=1, default=str)
print(json.dumps(rep, indent=1, default=str))

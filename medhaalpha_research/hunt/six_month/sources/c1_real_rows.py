# Check 1: rebuild the real-set signal list straight from six/pull.json and v2/data/feat.pkl (no harness code)
# and compare row by row with D['real'] (harness cache sets_opt.pkl).
import json, pickle, sys, collections
import numpy as np, pandas as pd
SP = '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
OUT = SP + '/hunt/six_month/sources'
sys.path.insert(0, SP + '/hunt')

pull = json.load(open(SP + '/six/pull.json'))['sig']
POLS = pull['policies']
assert pull['models'] == ['opus', 'fable', 'fable_op'], pull['models']
P = []
for day in pull['days']:
    for t, sym, setup, sc, net, r in day['signals']:
        if setup not in ('A', 'B'):
            continue
        d = {'day': day['day'], 'time': t, 'symbol': sym, 'setup': setup,
             'p_opus': sc[0], 'p_fable': sc[1], 'p_fable_op': sc[2]}
        for i, p in enumerate(POLS):
            d['p_net_' + p] = net[i] if net is not None else None
            d['p_r_' + p] = r[i] if r is not None else None
        P.append(d)
P = pd.DataFrame(P)
print('pull.json A/B signals', len(P), 'days', P.day.nunique(), 'null T1 net', P['p_net_T1'].isna().sum())

rows = pickle.load(open(SP + '/v2/data/feat.pkl', 'rb'))
F = []
for r in rows:
    f = dict(r['f'])
    d = {'day': r['day'], 'time': r['time'], 'symbol': r['symbol'], 'setup': r['setup'], 'side': r['side'],
         'f_opus': r['true']['opus'], 'f_fable': r['true']['fable'], 'f_fable_op': r['true']['fable_op'],
         'f_rel_vol': f.get('rel_vol'), 'f_out': r['out']}
    for i, p in enumerate(POLS):
        d['f_net_' + p] = r['net'][i]
    F.append(d)
F = pd.DataFrame(F)
F = F[F.setup.isin(['A', 'B'])]
print('feat.pkl A/B rows', len(F), 'null T1 net', F['f_net_T1'].isna().sum())

KEY = ['day', 'time', 'symbol', 'setup']
for nm, X in (('pull', P), ('feat', F)):
    dup = X.duplicated(KEY, keep=False).sum()
    print(nm, 'duplicate keys', dup)

M = P.merge(F, on=KEY, how='outer', indicator=True)
print('pull vs feat join:', M['_merge'].value_counts().to_dict())
both = M[M._merge == 'both']
for a, b in (('p_opus', 'f_opus'), ('p_fable', 'f_fable'), ('p_fable_op', 'f_fable_op')) + tuple(('p_net_' + p, 'f_net_' + p) for p in POLS):
    dif = (both[a].astype(float) - both[b].astype(float)).abs()
    print('  pull %-14s vs feat: max |diff| %.4f, rows > tol %d' % (a[2:], dif.max(), (dif > 0.01).sum()))

# ---- compare with harness D['real']
import harness as H
D = H.load_all()
R = D['real'].copy()
print('D[real] rows', len(R), 'days', R.day.nunique())
R['_k'] = 1
J = F.merge(P, on=KEY, how='left').merge(R, on=KEY, how='outer', indicator=True)
print('raw vs D[real] join:', J['_merge'].value_counts().to_dict())
J = J[J._merge == 'both']
checks = {
    's_opus': J['p_opus'],
    's_fable': J['p_fable'] - 5.0,
    's_fable_op': J['p_fable_op'],
    'net_T1': J['p_net_T1'], 'net_T3': J['p_net_T3'], 'net_CLOSE_TR': J['p_net_CLOSE_TR'],
    'net_T2': J['p_net_T2'], 'net_CLOSE': J['p_net_CLOSE'], 'net_T2_TR': J['p_net_T2_TR'], 'net_T3_TR': J['p_net_T3_TR'],
}
mism = {}
for c, src in checks.items():
    dif = (J[c].astype(float) - src.astype(float)).abs()
    nbad = int((dif > (0.05 if c.startswith('s_') else 1.0)).sum()) + int(J[c].isna().ne(src.isna()).sum())
    print('  D[real].%-13s vs raw: max |diff| %.6f, rows over tol %d' % (c, dif.max(), nbad))
    mism[c] = nbad
# derived scores from raw
lg = J['side_x'] == 'LONG' if 'side_x' in J else J['side'] == 'LONG'
side = J['side_x'] if 'side_x' in J else J['side']
assert (side == np.where(J.setup == 'A', 'LONG', 'SHORT')).all(), 'setup/side mismatch'
v2 = np.where(lg, J['p_fable_op'], J['p_opus'])
v3 = np.where(lg, np.where(J['f_rel_vol'].astype(float) < 1.0, 0.0, J['p_fable_op']), J['p_opus'])
for c, src in (('s_opus_v2', v2), ('s_opus_v3', v3)):
    dif = np.abs(J[c].to_numpy(float) - src.astype(float))
    print('  D[real].%-13s vs derivation: max |diff| %.6f, rows over 0.05 %d' % (c, np.nanmax(dif), int((dif > 0.05).sum())))
# rel_vol NaN on longs?
print('  longs with rel_vol NaN in feat:', int((lg & J['f_rel_vol'].isna()).sum()), '(NaN < 1 is False -> keeps fable_op score)')
print('  D[real].rel_vol vs feat rel_vol max diff', float((J['rel_vol'] - J['f_rel_vol'].astype(float)).abs().max()))
# status_T1 vs out
st = J['f_out'].map({'hit': 'target', 'stop': 'stopped'}).fillna('close')
print('  status_T1 mismatches', int((st != J['status_T1']).sum()), 'feat out values', J['f_out'].value_counts().to_dict())
# T1 status consistency with r_T1
print('  r_T1 of target rows min', float(J.loc[J.status_T1 == 'target', 'r_T1'].min()), ' stopped rows max', float(J.loc[J.status_T1 == 'stopped', 'r_T1'].max()))

# score ranges
for c in ('p_opus', 'p_fable', 'p_fable_op'):
    print('  %s range %.1f..%.1f, NaN %d' % (c, J[c].min(), J[c].max(), J[c].isna().sum()))
# Fable live cut check: number of rows with true fable >= 80 vs s_fable >= 75
print('  true fable>=80:', int((J.p_fable >= 80).sum()), ' s_fable>=75:', int((J.s_fable >= 75).sum()))
# setup C excluded check (pull has C signals; harness drops them)
nC = sum(1 for day in pull['days'] for x in day['signals'] if x[2] == 'C')
print('  setup C signals excluded from real:', nC)
P.to_pickle(OUT + '/raw_pull.pkl'); F.to_pickle(OUT + '/raw_feat.pkl')
json.dump(mism, open(OUT + '/c1_result.json', 'w'), indent=1)

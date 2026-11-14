"""EXPLORATORY diagnostics (not pre-registered, not used for the choice). Does the Nifty RV state separate where the
longer exit pays for a bought option? Controls for S3: Opus v3 with CLOSE_TR on every row, and the inverted switch."""
import sys, numpy as np, pandas as pd
SP='/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
sys.path.insert(0, SP+'/hunt'); import harness as H
R = pd.read_pickle('ratios.pkl'); RATIO, PD = R['RATIO'], R['PD']
HM = {h:i for i,h in enumerate(RATIO.columns)}; DI = {d:i for i,d in enumerate(RATIO.index)}
D = H.load_all()
for s in H.SETS:
    d = D[s]; d['rv_ratio'] = RATIO.to_numpy()[d.day.map(DI).astype(int), d.time.map(HM)]; d['pd_ratio'] = d.day.map(PD)
def part(s):
    d = D[s]
    if s == 'real':
        return {'real_h1(design)': d[d.day<='2026-08-31'], 'real_h2': d[d.day>='2026-09-01']}
    return {s: d}
print('Mean option net per trade (Rs), by rv_ratio state at the signal bar; n in brackets')
for base, a, b in (('s_fable_op','T3','T1'), ('s_opus_v3','CLOSE_TR','T1')):
    print('\n%s picks: %s vs %s' % (base, a, b))
    for s in H.SETS:
        for nm, d in part(s).items():
            t = H.pick(d, base, 75, 6)
            hi = t.rv_ratio >= 1.0
            line = '  %-16s' % nm
            for lab, m in (('rv>=1', hi), ('rv<1', ~hi)):
                line += ' | %s n=%3d %s %+6.0f %s %+6.0f diff %+6.0f' % (lab, m.sum(), a, t.loc[m,'opt_'+a].mean(), b, t.loc[m,'opt_'+b].mean(), (t.loc[m,'opt_'+a]-t.loc[m,'opt_'+b]).mean())
            print(line)
def v3_all_ctr(df):
    t = H.pick(df, 's_opus_v3', 75, 6); t['pol'] = 'CLOSE_TR'; return t
def v3_inv(df):
    t = H.pick(df, 's_opus_v3', 75, 6); t['pol'] = np.where(t.rv_ratio >= 1.0, 'T1', 'CLOSE_TR'); return t
def fop_all_t1(df):
    t = H.pick(df, 's_fable_op', 75, 6); t['pol'] = 'T1'; return t
def S3(df):
    t = H.pick(df, 's_opus_v3', 75, 6); t['pol'] = np.where(t.rv_ratio >= 1.0, 'CLOSE_TR', 'T1'); return t
res = H.evaluate(D, {'[ref] S3 v3 CLOSE_TR|T1 by rv': S3, '[ctl] v3 CLOSE_TR all rows': v3_all_ctr, '[ctl] v3 inverted switch': v3_inv, '[ctl] FOP T1 all rows': fop_all_t1})
H.show(res)
print('\nreal 2nd half / unseen risk detail (worst day, max DD) for the reference rows:')
for m in ('Opus v3 (T1)','Fable-OP (T3)','[ref] S3 v3 CLOSE_TR|T1 by rv','[ctl] v3 CLOSE_TR all rows'):
    print('  %-32s real_h2 net %+d wd %+d dd %+d | unseen net %+d wd %+d dd %+d' % (m, res['real'][m]['h2']['net'], res['real'][m]['h2']['worst_day'], res['real'][m]['h2']['maxdd'], res['unseen'][m]['all']['net'], res['unseen'][m]['all']['worst_day'], res['unseen'][m]['all']['maxdd']))

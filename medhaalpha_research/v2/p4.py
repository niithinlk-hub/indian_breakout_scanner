# The unseen-dates test, exactly as fixed in opus_v3_unseen_test_protocol.md.
import json, sys, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, sys.argv[1] + '/v2')
import numpy as np, pandas as pd
from lab import live_df
from p3 import proxy_rows, add_models
SP, PDIR = sys.argv[1], sys.argv[2]
X = add_models(proxy_rows(PDIR))
days = sorted(X.day.unique())
print('sessions', len(days), days[0], '->', days[-1], '| stand-in signals', len(X))
P = {}
out = {'sessions': len(days), 'from': days[0], 'to': days[-1], 'models': {}}
for m, name in (('m_opus', 'Opus'), ('m_fable_op', 'Fable-OP'), ('m_v2', 'Opus v2'), ('m_v3', 'Opus v3')):
    t = X.loc[live_df(X, m, 75)]
    P[m] = t
    byday = t.groupby('day').net1.sum().reindex(days).fillna(0)
    eq = byday.cumsum()
    o = {'n': len(t), 'hit': round(100 * t.hit.mean(), 1), 'stop': round(100 * t['stop'].mean(), 1), 'won': round(100 * (t.net1 > 0).mean(), 1), 'net': round(t.net1.sum()), 'net3': round(t.net3.sum()),
         'days_up': int((byday > 0).sum()), 'days_dn': int((byday < 0).sum()), 'maxdd': round(float((eq - eq.cummax().clip(lower=0)).min())),
         'side': {s: [int(len(g)), round(100 * g.hit.mean(), 1), round(100 * g['stop'].mean(), 1), round(g.net1.sum())] for s, g in t.groupby('side')},
         'bym': {mo: [int(len(g)), round(100 * g.hit.mean(), 1), round(100 * g['stop'].mean(), 1), round(g.net1.sum())] for mo, g in t.groupby(t.day.str[:7])}}
    out['models'][m] = o
    print('%-9s n=%3d hit %4.1f%% stop %4.1f%% won %4.1f%% net T1 %+8d (T3 %+8d) | days +%d/-%d maxDD %+7d | %s' % (name, o['n'], o['hit'], o['stop'], o['won'], o['net'], o['net3'], o['days_up'], o['days_dn'], o['maxdd'],
          ' | '.join('%s n=%3d hit %4.1f stop %4.1f net %+8d' % (s, *v) for s, v in o['side'].items())))
rng = np.random.default_rng(2026)
ix = rng.integers(0, len(days), size=(20000, len(days)))


def daily(t):
    f = lambda s: s.reindex(days).fillna(0).to_numpy()
    return f(t.groupby('day').net1.sum()), f(t.groupby('day').hit.sum()), f(t.groupby('day')['stop'].sum()), f(t.groupby('day').size())


out['tests'] = {}
for a, b in (('m_v3', 'm_opus'), ('m_v3', 'm_v2'), ('m_v2', 'm_opus'), ('m_v3', 'm_fable_op')):
    na, ha, sa, ca = daily(P[a]); nb, hb, sb, cb = daily(P[b])
    dn = (na - nb)[ix].sum(axis=1)
    dh = ha[ix].sum(axis=1) / ca[ix].sum(axis=1) - hb[ix].sum(axis=1) / cb[ix].sum(axis=1)
    ds = sa[ix].sum(axis=1) / ca[ix].sum(axis=1) - sb[ix].sum(axis=1) / cb[ix].sum(axis=1)
    o = {'hit_diff': round(100 * (ha.sum() / ca.sum() - hb.sum() / cb.sum()), 1), 'hit_p5': round(100 * np.percentile(dh, 5), 1), 'hit_p95': round(100 * np.percentile(dh, 95), 1), 'hit_ahead': round(100 * (dh > 0).mean(), 1),
         'net_diff': round(float((na - nb).sum())), 'net_p5': round(float(np.percentile(dn, 5))), 'net_p95': round(float(np.percentile(dn, 95))), 'net_ahead': round(100 * (dn > 0).mean(), 1),
         'stop_diff': round(100 * (sa.sum() / ca.sum() - sb.sum() / cb.sum()), 1), 'stop_lower': round(100 * (ds < 0).mean(), 1), 'trades_ratio': round(100 * ca.sum() / cb.sum(), 1)}
    out['tests']['%s-%s' % (a, b)] = o
    print('%s minus %s: reach-T1 %+5.1f pts (5-95%%: %+5.1f to %+5.1f; ahead in %5.1f%%) | net %+8d (%+8d to %+8d; ahead in %5.1f%%) | stop-outs %+5.1f pts (lower in %5.1f%%) | trades %.0f%%' % (
        a[2:], b[2:], o['hit_diff'], o['hit_p5'], o['hit_p95'], o['hit_ahead'], o['net_diff'], o['net_p5'], o['net_p95'], o['net_ahead'], o['stop_diff'], o['stop_lower'], o['trades_ratio']))
print('MAIN TEST (v3 reaches T1 more often than Opus in at least 95%% of resamples):', 'PASS' if out['tests']['m_v3-m_opus']['hit_ahead'] >= 95 else 'FAIL')
L = X[(X.side == 'LONG') & (X.fable_op >= 75)]
g = {'low_n': int((L.rel_vol < 1).sum()), 'low_hit': round(100 * L[L.rel_vol < 1].hit.mean(), 1), 'low_stop': round(100 * L[L.rel_vol < 1]['stop'].mean(), 1), 'low_per': round(L[L.rel_vol < 1].net1.mean()),
     'ok_n': int((L.rel_vol >= 1).sum()), 'ok_hit': round(100 * L[L.rel_vol >= 1].hit.mean(), 1), 'ok_stop': round(100 * L[L.rel_vol >= 1]['stop'].mean(), 1), 'ok_per': round(L[L.rel_vol >= 1].net1.mean())}
out['gate'] = g
print('volume condition, stand-in longs with Fable-OP >= 75: rel_vol < 1: n=%d hit %.1f%% stop %.1f%% net/trade %+d | rel_vol >= 1: n=%d hit %.1f%% stop %.1f%% net/trade %+d' % tuple(g.values()))
print('\nby month: trades:hit%:stop%/net k')
for m, name in (('m_opus', 'Opus'), ('m_v2', 'Opus v2'), ('m_v3', 'Opus v3'), ('m_fable_op', 'Fable-OP')):
    print('%-9s' % name, ' | '.join('%s %2d:%2.0f:%2.0f/%+4.0f' % (mo[2:], v[0], v[1], v[2], v[3] / 1000) for mo, v in out['models'][m]['bym'].items()))
json.dump(out, open(SP + '/v2/p4.json', 'w'))

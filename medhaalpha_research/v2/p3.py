# How well does the cash stand-in track the real result? Known months only (12 May - 19 Oct, 111 sessions).
import glob, json, os, sys, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, sys.argv[1] + '/v2')
import numpy as np, pandas as pd
from frame import load
from lab import live_df
SP, PDIR = sys.argv[1], sys.argv[2]
LCUT = float(sys.argv[3]) if len(sys.argv) > 3 else 75.0
SCUT = float(sys.argv[4]) if len(sys.argv) > 4 else 75.0


def proxy_rows(pdir):
    rows = []
    for p in sorted(glob.glob(pdir + '/proxy_*.json')):
        d = json.load(open(p))
        for s in d['signals']:
            if s['setup'] in ('A', 'B') and s['fut']['T1']['status'] != 'no_data':
                rv = s['snapshot'].get('rel_vol')
                rows.append({'day': d['day'], 'time': s['time'], 'symbol': s['symbol'], 'side': s['side'], 'opus': s['scores']['opus'], 'fable_op': s['scores']['fable_op'],
                             'rel_vol': rv, 'hit': int(s['fut']['T1']['status'] == 'target'), 'stop': int(s['fut']['T1']['status'] == 'stopped'), 'net1': s['fut']['T1']['net_rs'],
                             'net3': s['fut']['T3']['net_rs']})
    return pd.DataFrame(rows)


def add_models(P, lcut=75.0, scut=75.0):
    lg = P.side == 'LONG'
    P = P.copy()
    P['m_opus'] = P.opus
    P['m_fable_op'] = P.fable_op
    P['m_v2'] = np.where(lg, P.fable_op + (75 - lcut), P.opus + (75 - scut))
    P['m_v3'] = np.where(lg, np.where(P.rel_vol < 1.0, 0.0, P.fable_op + (75 - lcut)), P.opus + (75 - scut))
    return P


def summ(P, col):
    t = P.loc[live_df(P, col, 75)]
    return t


if __name__ == '__main__':
    X = add_models(proxy_rows(PDIR), LCUT, SCUT)
    days = sorted(X.day.unique())
    df = load()
    T = df[(df.day >= days[0]) & (df.day <= days[-1])].copy()
    T = T.rename(columns={'t_opus': 'opus', 't_fable_op': 'fable_op'})
    T = add_models(T)
    print('sessions', len(days), days[0], '->', days[-1], '| proxy signals', len(X), '| real signals', len(T), '| proxy cuts: long %.0f short %.0f' % (LCUT, SCUT))
    res = {}
    for m, name in (('m_opus', 'Opus'), ('m_fable_op', 'Fable-OP'), ('m_v2', 'Opus v2'), ('m_v3', 'Opus v3')):
        a, b = summ(T, m), summ(X, m)
        res[m] = (a, b)
        da, db = a.groupby('day').net1.sum().reindex(days).fillna(0), b.groupby('day').net1.sum().reindex(days).fillna(0)
        print('%-9s real n=%3d hit %4.1f%% stop %4.1f%% net %+8.0f | stand-in n=%3d hit %4.1f%% stop %4.1f%% net %+8.0f | daily corr %.2f | longs real %3d %+8.0f / stand-in %3d %+8.0f | shorts real %3d %+8.0f / stand-in %3d %+8.0f' % (
            name, len(a), 100 * a.hit.mean(), 100 * a['stop'].mean(), a.net1.sum(), len(b), 100 * b.hit.mean(), 100 * b['stop'].mean(), b.net1.sum(), np.corrcoef(da, db)[0, 1],
            (a.side == 'LONG').sum(), a[a.side == 'LONG'].net1.sum(), (b.side == 'LONG').sum(), b[b.side == 'LONG'].net1.sum(),
            (a.side == 'SHORT').sum(), a[a.side == 'SHORT'].net1.sum(), (b.side == 'SHORT').sum(), b[b.side == 'SHORT'].net1.sum()))
    print('\nv3 minus Opus by month: reach-T1 points and net (real | stand-in)')
    for mo in sorted({d[:7] for d in days}):
        out = []
        for k in (0, 1):
            v, o = res['m_v3'][k], res['m_opus'][k]
            v, o = v[v.day.str[:7] == mo], o[o.day.str[:7] == mo]
            out.append('%+5.1f pts %+8.0f (v3 %2d trades, Opus %2d)' % (100 * (v.hit.mean() - o.hit.mean()), v.net1.sum() - o.net1.sum(), len(v), len(o)))
        print('  %s  real %s | stand-in %s' % (mo, out[0], out[1]))
    for k, lab in ((0, 'real'), (1, 'stand-in')):
        v, o = res['m_v3'][k], res['m_opus'][k]
        print('%-8s v3 minus Opus: reach-T1 %+5.1f pts | stop-outs %+5.1f pts | net %+8.0f | trades %d vs %d' % (lab, 100 * (v.hit.mean() - o.hit.mean()), 100 * (v['stop'].mean() - o['stop'].mean()), v.net1.sum() - o.net1.sum(), len(v), len(o)))
    L = X[(X.side == 'LONG') & (X.fable_op >= 75)]
    print('stand-in longs with Fable-OP >= 75: rel_vol < 1: n=%d hit %.0f%% net/trade %+.0f | rel_vol >= 1: n=%d hit %.0f%% net/trade %+.0f' % (
        (L.rel_vol < 1).sum(), 100 * L[L.rel_vol < 1].hit.mean(), L[L.rel_vol < 1].net1.mean(), (L.rel_vol >= 1).sum(), 100 * L[L.rel_vol >= 1].hit.mean(), L[L.rel_vol >= 1].net1.mean()))

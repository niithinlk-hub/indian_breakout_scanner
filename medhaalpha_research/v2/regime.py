# Which model suits which market. Each session is labelled from Nifty's daily closes up to the day BEFORE it (so the label
# is known before the open): uptrend = last close above its 20-day average and that above the 50-day average;
# downtrend = the reverse; sideways = anything else. A second labelling (20-day change of +/-2 %) is the cross-check.
import glob, json, os, sys, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, sys.argv[1] + '/v2')
import numpy as np, pandas as pd
from base import SP, PI
from frame import load
from lab import live_df
import pickle

nd = json.load(open(SP + '/v2/data/nifty_daily.json'))['data']['candles']
N = pd.DataFrame(nd, columns=['ts', 'o', 'h', 'l', 'c', 'v', 'oi']).assign(day=lambda x: x.ts.str[:10]).sort_values('day').set_index('day')
c = N.c
prev = c.shift(1); ma20 = c.rolling(20).mean().shift(1); ma50 = c.rolling(50).mean().shift(1); r20 = (c.shift(1) / c.shift(21) - 1) * 100
REG = pd.DataFrame({'prev': prev, 'ma20': ma20, 'ma50': ma50, 'r20': r20, 'chg': (c / prev - 1) * 100})
REG['A'] = np.where((prev > ma20) & (ma20 > ma50), 'Uptrend', np.where((prev < ma20) & (ma20 < ma50), 'Downtrend', 'Sideways'))
REG['B'] = np.where(r20 >= 2, 'Uptrend', np.where(r20 <= -2, 'Downtrend', 'Sideways'))
REG['D'] = np.where(REG.chg >= 0.4, 'Up day', np.where(REG.chg <= -0.4, 'Down day', 'Flat day'))
MODELS = (('opus', 'Opus', 'T1'), ('opus_v2', 'Opus v2', 'T1'), ('opus_v3', 'Opus v3', 'T1'), ('fable', 'Fable', 'T3'), ('fable_op', 'Fable-OP', 'T3'))
RAT = json.load(open(SP + '/v2/opt_est.json'))['ratios']


def real_trades():
    df = load()
    rows = pickle.load(open(SP + '/v2/data/feat.pkl', 'rb'))
    A = df[df.design | df.unseen].copy()
    A['r3'] = [rows[df.index.get_loc(i)]['r'][PI['T3']] for i in A.index]
    lg = A.long == 1
    A['s_opus'], A['s_fable'], A['s_fable_op'] = A.t_opus, A.t_fable - 5.0, A.t_fable_op
    A['s_opus_v2'] = np.where(lg, A.t_fable_op, A.t_opus)
    A['s_opus_v3'] = np.where(lg, np.where(A.rel_vol < 1.0, 0.0, A.t_fable_op), A.t_opus)
    c1 = np.where(A.out == 'hit', 'target', np.where(A.out == 'stop', 'stopped', np.where(A.net1 > 0, 'close_up', 'close_dn')))
    c3 = np.where(A.r3 >= 2.3, 'target', np.where(A.r3 <= -0.97, 'stopped', np.where(A.net3 > 0, 'close_up', 'close_dn')))
    A['opt1'] = [RAT['T1'][k] for k in c1] * A.net1
    A['opt3'] = [RAT['T3'][k] for k in c3] * A.net3
    out = []
    for m, name, ex in MODELS:
        t = A.loc[live_df(A, 's_' + m, 75), ['day', 'side', 'hit', 'stop', 'net1', 'net3', 'opt1', 'opt3']].copy()
        t['model'] = m
        out.append(t)
    return pd.concat(out), sorted(A.day.unique())


def standin_trades(pdir):
    rows = []
    for p in sorted(glob.glob(pdir + '/proxy_*.json')):
        d = json.load(open(p))
        for s in d['signals']:
            if s['setup'] in ('A', 'B') and s['fut']['T1']['status'] != 'no_data':
                rows.append({'day': d['day'], 'time': s['time'], 'symbol': s['symbol'], 'side': s['side'], 'hit': int(s['fut']['T1']['status'] == 'target'), 'stop': int(s['fut']['T1']['status'] == 'stopped'),
                             'net1': s['fut']['T1']['net_rs'], 'net3': s['fut']['T3']['net_rs'], 's_opus': s['scores']['opus'], 's_fable': s['scores']['fable'] - 5.0, 's_fable_op': s['scores']['fable_op'],
                             's_opus_v2': s['scores']['opus_v2'], 's_opus_v3': s['scores']['opus_v3']})
    X = pd.DataFrame(rows)
    out = []
    for m, name, ex in MODELS:
        t = X.loc[live_df(X, 's_' + m, 75), ['day', 'side', 'hit', 'stop', 'net1', 'net3']].copy()
        t['model'] = m
        out.append(t)
    return pd.concat(out), sorted(X.day.unique())


def table(T, days, lab, col='A', money=('net', 'Futures net/session'), opt=False):
    reg = REG.loc[days, col]
    res = {}
    print('\n== %s | sessions by label: %s' % (lab, reg.value_counts().to_dict()))
    order = ['Uptrend', 'Sideways', 'Downtrend'] if col != 'D' else ['Up day', 'Flat day', 'Down day']
    for g in order:
        dd = [d for d in days if reg[d] == g]
        if not dd:
            continue
        res[g] = {'sessions': len(dd)}
        print('  %s (%d sessions; Nifty over those days %+.1f%% in total)' % (g, len(dd), REG.loc[dd, 'chg'].sum()))
        for m, name, ex in MODELS:
            t = T[(T.model == m) & (T.day.isin(dd))]
            net = t['net1' if ex == 'T1' else 'net3'].sum()
            o = t['opt1' if ex == 'T1' else 'opt3'].sum() if opt else float('nan')
            lo, sh = t[t.side == 'LONG'], t[t.side == 'SHORT']
            byday = t.groupby('day')['net1' if ex == 'T1' else 'net3'].sum().reindex(dd).fillna(0)
            res[g][m] = {'n': len(t), 'per_session': len(t) / len(dd), 'hit': 100 * t.hit.mean() if len(t) else 0, 'stop': 100 * t['stop'].mean() if len(t) else 0, 'net': net, 'net_ps': net / len(dd),
                         'opt': o, 'opt_ps': o / len(dd) if opt else float('nan'), 'net_t1': t.net1.sum(), 'net_t3': t.net3.sum(), 'longs': len(lo), 'shorts': len(sh),
                         'long_net': lo['net1' if ex == 'T1' else 'net3'].sum(), 'short_net': sh['net1' if ex == 'T1' else 'net3'].sum(), 'days_up': int((byday > 0).sum()), 'days_dn': int((byday < 0).sum())}
            r = res[g][m]
            print('    %-9s exit %s: trades %3d (%.1f/day) reach-T1 %4.1f%% stop %4.1f%% | net %+8.0f (%+6.0f/session)%s | at T1 %+8.0f at T3 %+8.0f | longs %3d %+8.0f shorts %3d %+8.0f | days +%d/-%d' % (
                name, ex, r['n'], r['per_session'], r['hit'], r['stop'], r['net'], r['net_ps'], (' options est %+8.0f (%+6.0f/session)' % (r['opt'], r['opt_ps'])) if opt else '', r['net_t1'], r['net_t3'],
                r['longs'], r['long_net'], r['shorts'], r['short_net'], r['days_up'], r['days_dn']))
    return res


if __name__ == '__main__':
    R, rdays = real_trades()
    K, kdays = standin_trades(SP + '/v2/proxy_known')
    U, udays = standin_trades(SP + '/v2/proxy_unseen')
    last = REG.dropna().iloc[-1]
    print('latest label (for the session after %s): A=%s B=%s | prev close %.0f, 20-day avg %.0f, 50-day avg %.0f, 20-day change %+.1f%%' % (REG.dropna().index[-1], last.A, last.B, last.prev, last.ma20, last.ma50, last.r20))
    out = {}
    out['real_A'] = table(R, rdays, 'REAL futures, 12 May - 11 Nov 2026 (trend label A: moving averages)', 'A', opt=True)
    out['real_B'] = table(R, rdays, 'REAL futures, same period (trend label B: 20-day change +/-2%)', 'B', opt=True)
    out['real_D'] = table(R, rdays, 'REAL futures, same period, by what Nifty did ON the day (hindsight)', 'D', opt=True)
    out['unseen_A'] = table(U, udays, 'STAND-IN (cash), 3 Nov 2025 - 11 May 2026 (label A)', 'A')
    out['unseen_B'] = table(U, udays, 'STAND-IN (cash), same period (label B)', 'B')
    out['unseen_D'] = table(U, udays, 'STAND-IN (cash), same period, by what Nifty did on the day', 'D')
    out['known_A'] = table(K, kdays, 'STAND-IN (cash), 12 May - 19 Oct 2026 (label A)', 'A')
    json.dump(out, open(SP + '/v2/regime.json', 'w'), default=float)
    pickle.dump({'R': R, 'rdays': rdays, 'K': K, 'kdays': kdays, 'U': U, 'udays': udays, 'REG': REG}, open(SP + '/v2/regime_trades.pkl', 'wb'))

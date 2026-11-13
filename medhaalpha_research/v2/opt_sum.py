import json, sys
import numpy as np, pandas as pd
sp = sys.argv[1]
D = json.load(open(sp + '/v2/opt5.json'))
rows, days = D['rows'], D['days']
SC = (('opus', 'T1', 'Opus, exit T1'), ('opus_v2', 'T1', 'Opus v2, exit T1'), ('opus_v3', 'T1', 'Opus v3, exit T1'), ('fable', 'T3', 'Fable, exit T3'), ('fable_op', 'T3', 'Fable-OP, exit T3'))
out = {}
for m, pol, name in SC:
    tr = [r for r in rows if m in r['models']]
    o = {'n': len(tr)}
    for mode, fk in (('same', 'fut_same'), ('held', 'fut_held')):
        x = [r for r in tr if pol in r[mode]]
        nets = [r[mode][pol]['net_rs'] for r in x]
        outl = [r[mode][pol]['outlay'] for r in x]
        byday = {d: 0.0 for d in days}
        for r in x:
            byday[r['day']] += r[mode][pol]['net_rs']
        v = [byday[d] for d in days]
        eq = pk = dd = 0.0
        for a in v:
            eq += a; pk = max(pk, eq); dd = min(dd, eq - pk)
        ev = []
        for r in x:
            ev.append((pd.Timestamp(r['entry_ts']), 1, r[mode][pol]['outlay'])); ev.append((pd.Timestamp(r[mode][pol]['exit_ts']), 0, -r[mode][pol]['outlay']))
        cur = peak = 0.0; cnt = pc = 0
        for t, _, a in sorted(ev, key=lambda e: (e[0], e[1])):
            cur += a; cnt += 1 if a > 0 else -1
            if cur > peak:
                peak, pc = cur, cnt
        o[mode] = {'priced': len(x), 'net': round(sum(nets)), 'won': sum(a > 0 for a in nets), 'fut_net_same_trades': round(sum(r[fk][pol]['net_rs'] for r in x)), 'fut_net_all': round(sum(r[fk][pol]['net_rs'] for r in tr)),
                   'avg_outlay': round(np.mean(outl)), 'max_outlay': round(max(outl)), 'total_outlay': round(sum(outl)), 'best': round(max(nets)), 'worst': round(min(nets)),
                   'avg_win': round(np.mean([a for a in nets if a > 0])), 'avg_loss': round(np.mean([a for a in nets if a <= 0])), 'days_up': sum(a > 0 for a in v), 'days_dn': sum(a < 0 for a in v),
                   'worst_day': round(min(v)), 'maxdd': round(dd), 'peak_outlay': round(peak), 'peak_open': pc,
                   'oct': round(sum(r[mode][pol]['net_rs'] for r in x if r['day'] < '2026-11-01')), 'nov': round(sum(r[mode][pol]['net_rs'] for r in x if r['day'] >= '2026-11-01')),
                   'target': sum(r[fk][pol]['status'] == 'target' for r in x), 'stopped': sum(r[fk][pol]['status'] == 'stopped' for r in x),
                   'ret_on_outlay': round(100 * sum(nets) / sum(outl), 1), 'byday': {d: [sum(1 for r in x if r['day'] == d), round(byday[d])] for d in days}}
        if mode == 'held':
            o[mode]['open'] = sum(r[fk][pol]['status'] == 'open' for r in x)
            o[mode]['avg_sessions'] = round(np.mean([r['fut_held'][pol]['sessions'] for r in x]), 2)
    out[m] = o
    for mode in ('same', 'held'):
        s = o[mode]
        print('%-18s %-5s trades %2d priced %2d | option net %+8d (futures same trades %+8d) | won %2d | hit %2d stop %2d | avg win %+6d avg loss %+6d worst %+6d | outlay avg %6d peak %7d (%d open) | return on premium %5.1f%% | Oct %+7d Nov %+7d | days +%d/-%d maxDD %+7d' % (
            name, mode, o['n'], s['priced'], s['net'], s['fut_net_same_trades'], s['won'], s['target'], s['stopped'], s['avg_win'], s['avg_loss'], s['worst'], s['avg_outlay'], s['peak_outlay'], s['peak_open'], s['ret_on_outlay'],
            s['oct'], s['nov'], s['days_up'], s['days_dn'], s['maxdd']))
json.dump(out, open(sp + '/v2/opt_sum.json', 'w'))
# calibration set: every trade, same day, option net against futures net by futures outcome
print('\ncalibration (all 146 trades, same day): option net as a share of futures net, by how the futures leg ended')
for pol in ('T1', 'T3'):
    x = [(r['fut_same'][pol]['status'], r['fut_same'][pol]['net_rs'], r['same'][pol]['net_rs']) for r in rows if pol in r['same']]
    for cls, f in (('target', lambda s, a: s == 'target'), ('stopped', lambda s, a: s == 'stopped'), ('close, futures up', lambda s, a: s == 'close' and a > 0), ('close, futures down', lambda s, a: s == 'close' and a <= 0)):
        g = [(a, b) for s, a, b in x if f(s, a)]
        if g:
            print('  %s %-20s n=%3d futures %+9.0f options %+9.0f ratio %.2f | per trade futures %+7.0f options %+7.0f' % (pol, cls, len(g), sum(a for a, _ in g), sum(b for _, b in g), sum(b for _, b in g) / sum(a for a, _ in g),
                  np.mean([a for a, _ in g]), np.mean([b for _, b in g])))

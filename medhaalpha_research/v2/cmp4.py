import json, os, sys
import pandas as pd
sp = sys.argv[1]
H = json.load(open(sp + '/v2/hold4.json'))
rows, days = H['rows'], H['days']
NS = len(days)
src = open(os.path.join(sp, 'tools', 'cap_sim.py')).read()
exec('import pandas as pd\n' + 'def sim' + src.split('def sim')[1].split('for m in MS:')[0])
MS = (('opus', 'Opus'), ('fable', 'Fable'), ('fable_op', 'Fable-OP'), ('opus_v2', 'Opus v2'))
out = {'days': days, 'models': {}}
for m, name in MS:
    tr = [r for r in rows if m in r['models']]
    o = {'n': len(tr), 'longs': sum(r['side'] == 'LONG' for r in tr)}
    for p in ('T1', 'T2', 'T3', 'CLOSE'):
        x = [r['same_day'][p] for r in tr]
        o['sd_' + p] = {'net': round(sum(a['net_rs'] for a in x)), 'target': sum(a['status'] == 'target' for a in x), 'stopped': sum(a['status'] == 'stopped' for a in x),
                        'won': sum(a['net_rs'] > 0 for a in x), 'r': round(sum(a['r'] for a in x), 1)}
    for p in ('T1', 'T2', 'T3'):
        x = [r['res'][p] for r in tr]
        hit = [a for a in x if a['status'] == 'target']
        o['hold_' + p] = {'net': round(sum(a['net_rs'] for a in x)), 'target': len(hit), 'stopped': sum(a['status'] == 'stopped' for a in x), 'open': sum(a['status'] == 'open' for a in x),
                          'days_hist': [sum(1 for a in hit if a['sessions'] == k) for k in range(5)] + [sum(1 for a in hit if a['sessions'] >= 5)]}
        xo = [r['option'][p] for r in tr if p in r['option']]
        o['opt_' + p] = {'priced': len(xo), 'net': round(sum(a['net_rs'] for a in xo)), 'fut_same': round(sum(r['same_day'][p]['net_rs'] for r in tr if p in r['option']))}
    byday = {d: [0, 0, 0, 0.0] for d in days}
    for r in tr:
        b = byday[r['day']]
        b[0] += 1; b[1] += r['same_day']['T1']['status'] == 'target'; b[2] += r['same_day']['T1']['status'] == 'stopped'; b[3] += r['same_day']['T1']['net_rs']
    o['byday'] = byday
    v = [byday[d][3] for d in days]
    eq = pk = dd = 0.0
    for a in v:
        eq += a; pk = max(pk, eq); dd = min(dd, eq - pk)
    o['days_up'], o['days_dn'], o['days_none'] = sum(a > 0 for a in v), sum(a < 0 for a in v), sum(byday[d][0] == 0 for d in days)
    o['worst_day'], o['best_day'], o['maxdd'] = round(min(v)), round(max(v)), round(dd)
    for per, lo, hi in (('oct', '2026-10-21', '2026-10-31'), ('nov', '2026-11-01', '2026-11-30')):
        t2 = [r for r in tr if lo <= r['day'] <= hi]
        o[per] = {'n': len(t2), 'hit': sum(r['same_day']['T1']['status'] == 'target' for r in t2), 'stop': sum(r['same_day']['T1']['status'] == 'stopped' for r in t2),
                  'T1': round(sum(r['same_day']['T1']['net_rs'] for r in t2)), 'T3': round(sum(r['same_day']['T3']['net_rs'] for r in t2)),
                  'hT1': round(sum(r['res']['T1']['net_rs'] for r in t2)), 'hT3': round(sum(r['res']['T3']['net_rs'] for r in t2))}
    for side in ('LONG', 'SHORT'):
        t2 = [r for r in tr if r['side'] == side]
        o[side] = {'n': len(t2), 'hit': sum(r['same_day']['T1']['status'] == 'target' for r in t2), 'stop': sum(r['same_day']['T1']['status'] == 'stopped' for r in t2),
                   'T1': round(sum(r['same_day']['T1']['net_rs'] for r in t2))}
    for pol in ('T1', 'T3'):
        for cap, lab in ((None, 'all'), (300000.0, '3L')):
            s = sim(tr, pol, cap, 0.20)
            o['cap_%s_%s' % (pol, lab)] = {k: s[k] for k in ('taken', 'skipped', 'net', 'hit', 'stopped', 'open', 'max_dd', 'peak_margin', 'peak_open')}
    out['models'][m] = o
    print('%-8s n=%2d (longs %2d) | same day T1: hit %2d stop %2d won %2d net %+8d | T2 %+8d T3 %+8d CLOSE %+8d | days +%d/-%d/none %d worst %+d maxDD %+d' % (
        name, o['n'], o['longs'], o['sd_T1']['target'], o['sd_T1']['stopped'], o['sd_T1']['won'], o['sd_T1']['net'], o['sd_T2']['net'], o['sd_T3']['net'], o['sd_CLOSE']['net'],
        o['days_up'], o['days_dn'], o['days_none'], o['worst_day'], o['maxdd']))
    print('         held: T1 %d/%d/%d %+8d | T2 %d/%d/%d %+8d | T3 %d/%d/%d %+8d | days to T3 %s' % (
        o['hold_T1']['target'], o['hold_T1']['stopped'], o['hold_T1']['open'], o['hold_T1']['net'], o['hold_T2']['target'], o['hold_T2']['stopped'], o['hold_T2']['open'], o['hold_T2']['net'],
        o['hold_T3']['target'], o['hold_T3']['stopped'], o['hold_T3']['open'], o['hold_T3']['net'], o['hold_T3']['days_hist']))
    print('         options same day: T1 priced %d of %d net %+8d (futures on those %+8d) | T3 priced %d net %+8d' % (
        o['opt_T1']['priced'], o['n'], o['opt_T1']['net'], o['opt_T1']['fut_same'], o['opt_T3']['priced'], o['opt_T3']['net']))
    print('         Oct 21-30: %s | Nov 2-13: %s' % (o['oct'], o['nov']))
    print('         by side: %s | %s' % (o['LONG'], o['SHORT']))
    print('         Rs 3 lakh: T1 %s | T3 %s' % (o['cap_T1_3L'], o['cap_T3_3L']))
json.dump(out, open(sp + '/v2/cmp4.json', 'w'))
sets = {m: {(r['day'], r['symbol'], r['setup']) for r in rows if m in r['models']} for m, _ in MS}
print('overlap: opus&fable_op %d | opus&fable %d | fable&fable_op %d | v2&opus %d | v2&fable_op %d | all four %d' % (
    len(sets['opus'] & sets['fable_op']), len(sets['opus'] & sets['fable']), len(sets['fable'] & sets['fable_op']), len(sets['opus_v2'] & sets['opus']),
    len(sets['opus_v2'] & sets['fable_op']), len(sets['opus'] & sets['fable'] & sets['fable_op'] & sets['opus_v2'])))

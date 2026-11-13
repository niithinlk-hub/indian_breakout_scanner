import json, sys
sp = sys.argv[1]
C = json.load(open(sp + '/v2/cmp4.json'))
H = json.load(open(sp + '/v2/hold4.json'))
M = C['models']
MS = (('opus', 'Opus'), ('fable', 'Fable'), ('fable_op', 'Fable-OP'), ('opus_v2', 'Opus v2'))


def inr(x, sign=True):
    x = int(round(x))
    s = str(abs(x))
    if len(s) > 3:
        head, tail, parts = s[:-3], s[-3:], []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ','.join(parts + [tail])
    return ('-' if x < 0 else '+' if sign else '') + s


def row(label, f):
    return '| %s | %s |' % (label, ' | '.join(f(M[m]) for m, _ in MS))


hdr = ['| | ' + ' | '.join(n for _, n in MS) + ' |', '|---|---|---|---|---|']
L = ['# Opus, Fable, Fable-OP and Opus v2: 21 Oct to 13 Nov 2026 (17 sessions)', '',
     '20 Oct was a market holiday, so the period starts on 21 Oct. Each model takes the first 6 signals a day that reach its own cut-off (Opus 75, Fable 80, Fable-OP 75, Opus v2 75), setups A and B. '
     'Trades come from my replays of each session on the November futures, the same replays used earlier; Opus v2 picks come from the patched copy of the scanner code. '
     'Lots sized to Rs 15,000 risk; charges and 0.02 % slippage a side included. Opus v2 exists only on paper; nothing on the VPS was changed.', '',
     '## Same-day results (anything open is squared off at the close)', ''] + hdr
L.append(row('Trades', lambda o: '%d' % o['n']))
L.append(row('Longs / shorts', lambda o: '%d / %d' % (o['LONG']['n'], o['SHORT']['n'])))
L.append(row('Reached T1', lambda o: '%d (%.0f %%)' % (o['sd_T1']['target'], 100 * o['sd_T1']['target'] / o['n'])))
L.append(row('Stopped out', lambda o: '%d (%.0f %%)' % (o['sd_T1']['stopped'], 100 * o['sd_T1']['stopped'] / o['n'])))
L.append(row('Ended in profit at T1', lambda o: '%d (%.0f %%)' % (o['sd_T1']['won'], 100 * o['sd_T1']['won'] / o['n'])))
L.append(row('Net, exit at T1 (Rs)', lambda o: inr(o['sd_T1']['net'])))
L.append(row('Net, hold for T2 (Rs)', lambda o: inr(o['sd_T2']['net'])))
L.append(row('Net, hold for T3 (Rs)', lambda o: inr(o['sd_T3']['net'])))
L.append(row('Net, stop only, exit at the close (Rs)', lambda o: inr(o['sd_CLOSE']['net'])))
L.append(row('Net per trade at T1 (Rs)', lambda o: inr(o['sd_T1']['net'] / o['n'])))
L.append(row('Days up / down / no trade (T1)', lambda o: '%d / %d / %d' % (o['days_up'], o['days_dn'], o['days_none'])))
L.append(row('Worst day at T1 (Rs)', lambda o: inr(o['worst_day'])))
L.append(row('Largest fall from a peak at T1 (Rs)', lambda o: inr(o['maxdd'])))
L += ['', '## Held across days (original stop, no square-off; open trades marked to the 13 Nov close)', ''] + hdr
for p in ('T1', 'T2', 'T3'):
    L.append(row('Exit %s: hit / stopped / open' % p, lambda o, p=p: '%d / %d / %d' % (o['hold_' + p]['target'], o['hold_' + p]['stopped'], o['hold_' + p]['open'])))
    L.append(row('Exit %s: net (Rs)' % p, lambda o, p=p: inr(o['hold_' + p]['net'])))
L += ['', 'Trading days taken to reach T3 (after the entry day):', ''] + hdr
for i, lab in enumerate(('Same session', '1', '2', '3', '4', '5 or more')):
    L.append(row(lab, lambda o, i=i: '%d' % o['hold_T3']['days_hist'][i]))
L += ['', '## The two halves, exit at T1 same day', ''] + hdr
L.append(row('21-30 Oct (8 sessions): trades', lambda o: '%d' % o['oct']['n']))
L.append(row('21-30 Oct: reached T1 / stopped', lambda o: '%d / %d' % (o['oct']['hit'], o['oct']['stop'])))
L.append(row('21-30 Oct: net (Rs)', lambda o: inr(o['oct']['T1'])))
L.append(row('2-13 Nov (9 sessions): trades', lambda o: '%d' % o['nov']['n']))
L.append(row('2-13 Nov: reached T1 / stopped', lambda o: '%d / %d' % (o['nov']['hit'], o['nov']['stop'])))
L.append(row('2-13 Nov: net (Rs)', lambda o: inr(o['nov']['T1'])))
L += ['', '## Longs and shorts, exit at T1 same day', ''] + hdr
for side, lab in (('LONG', 'Longs'), ('SHORT', 'Shorts')):
    L.append(row('%s: trades' % lab, lambda o, side=side: '%d' % o[side]['n']))
    L.append(row('%s: reached T1 / stopped' % lab, lambda o, side=side: '%d / %d' % (o[side]['hit'], o[side]['stop'])))
    L.append(row('%s: net (Rs)' % lab, lambda o, side=side: inr(o[side]['T1'])))
L += ['', '## Options, same day (the trades whose option leg was priced in the replay)', ''] + hdr
L.append(row('Trades with an option price', lambda o: '%d of %d' % (o['opt_T1']['priced'], o['n'])))
L.append(row('Option net, exit when futures reach T1 (Rs)', lambda o: inr(o['opt_T1']['net'])))
L.append(row('Futures net on the same trades (Rs)', lambda o: inr(o['opt_T1']['fut_same'])))
L.append(row('Option net, exit when futures reach T3 (Rs)', lambda o: inr(o['opt_T3']['net'])))
L += ['', 'Opus v2 has fewer priced option legs because a few of its picks were not picked by any model when the replays were stored.', '',
      '## With Rs 3 lakh of futures margin (about two positions at a time, margin taken as 20 % of contract value), held across days', ''] + hdr
for p in ('T1', 'T3'):
    L.append(row('Exit %s: trades carried / skipped' % p, lambda o, p=p: '%d / %d' % (o['cap_%s_3L' % p]['taken'], o['cap_%s_3L' % p]['skipped'])))
    L.append(row('Exit %s: net (Rs)' % p, lambda o, p=p: inr(o['cap_%s_3L' % p]['net'])))
    L.append(row('Exit %s: largest fall (Rs)' % p, lambda o, p=p: inr(o['cap_%s_3L' % p]['max_dd'])))
L += ['', 'Seventeen sessions with two slots is a small sample; which signals fire first decides most of it.', '',
      '## Day by day, exit at T1 same day: trades and net (Rs)', '',
      '| Date | ' + ' | '.join(n for _, n in MS) + ' |', '|---|---|---|---|---|']
for d in C['days']:
    L.append('| %s | %s |' % (d[5:], ' | '.join(('%d: %s' % (M[m]['byday'][d][0], inr(M[m]['byday'][d][3]))) if M[m]['byday'][d][0] else 'no trade' for m, _ in MS)))
L.append('| **Total** | %s |' % ' | '.join('**%d: %s**' % (M[m]['n'], inr(M[m]['sd_T1']['net'])) for m, _ in MS))
for m, name in MS:
    L += ['', '## %s: every trade' % name, '',
          '| Date | Time | Symbol | Side | Score | Same day T1 | Same day T1 net (Rs) | Same day T3 net (Rs) | Held T1 | Held T3 | Held T3 net (Rs) |', '|---|---|---|---|---|---|---|---|---|---|---|']
    lab = {'target': 'hit', 'stopped': 'stopped', 'open': 'open', 'close': 'closed'}
    for r in H['rows']:
        if m in r['models']:
            sc = r['scores'].get(m, r['scores']['fable_op'] if r['side'] == 'LONG' else r['scores']['opus'])
            L.append('| %s | %s | %s | %s | %.1f | %s | %s | %s | %s | %s | %s |' % (r['day'][5:], r['time'], r['symbol'], r['side'], sc, lab[r['same_day']['T1']['status']],
                     inr(r['same_day']['T1']['net_rs']), inr(r['same_day']['T3']['net_rs']), lab[r['res']['T1']['status']], lab[r['res']['T3']['status']], inr(r['res']['T3']['net_rs'])))
L += ['', '## Notes', '',
      '- Opus\'s score weights were tuned on 21 Oct to 9 Nov, which is most of this period.',
      '- These are replays, not live fills. On 13 Nov the live paper ledger showed Opus at Rs -18,241 where the replay shows Rs -2,928.',
      '- Three trades were priced on the cash share because the futures were too thin at the signal minute.', '']
open(sp + '/four_models_21Oct-13Nov.md', 'w').write('\n'.join(L))
print('\n'.join(L[:62]))
print('...')
print('\n'.join(L[62:98]))

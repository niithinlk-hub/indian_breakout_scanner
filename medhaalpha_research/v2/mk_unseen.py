import json, sys
sp = sys.argv[1]
R = json.load(open(sp + '/v2/p4.json')); C = json.load(open(sp + '/v2/p5.json'))
M = R['models']; T = R['tests']; G = R['gate']


def inr(x, sign=True):
    x = int(round(x)); s = str(abs(x))
    if len(s) > 3:
        head, tail, parts = s[:-3], s[-3:], []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ','.join(parts + [tail])
    return ('-' if x < 0 else '+' if sign else '') + s


MS = (('m_opus', 'Opus'), ('m_fable_op', 'Fable-OP'), ('m_v2', 'Opus v2'), ('m_v3', 'Opus v3'))
t = T['m_v3-m_opus']
L = ['# Opus v3 on unseen dates: result', '',
     'Test rules were fixed beforehand in `opus_v3_unseen_test_protocol.md`; the code fingerprints at run time match that file. Nothing on the VPS was changed.', '',
     '**Dates:** 3 Nov 2025 to 11 May 2026, %d sessions. No model was fitted on any of them. Nifty fell 7.4 %% over the period (including an 11 %% fall in March 2026); over the scanner\'s six-month backtest period it rose 6 %%.' % R['sessions'],
     '', '**Data:** cash-share stand-in, because real futures candles before mid-May 2026 no longer exist at the data source. On known months the stand-in showed a little over half of the real reach-T1 gap between v3 and Opus and could not judge profit.', '',
     '## Verdict', '',
     '- **Main test: passed.** v3 reached T1 %.1f %% of the time against Opus\'s %.1f %%, a gap of %+.1f points (5th to 95th percentile %+.1f to %+.1f), ahead in %.0f %% of 20,000 resamples.' % (
         M['m_v3']['hit'], M['m_opus']['hit'], t['hit_diff'], t['hit_p5'], t['hit_p95'], t['hit_ahead']),
     '- **Profit: not confirmed.** On the stand-in v3 lost Rs %s and Opus lost Rs %s. v3 was ahead in only %.0f %% of resamples.' % (inr(M['m_v3']['net'], False).lstrip('-'), inr(M['m_opus']['net'], False).lstrip('-'), t['net_ahead']),
     '- **Stop-outs: worse than Opus** (%.1f %% against %.1f %%).' % (M['m_v3']['stop'], M['m_opus']['stop']),
     '- **The short side did not hold up.** Shorts picked by the Opus score lost money in this period.',
     '- **Fable-OP did best of the four** on both accuracy and net.', '',
     '## Results, same-day exit at T1 (stand-in)', '', '| | ' + ' | '.join(n for _, n in MS) + ' |', '|---|---|---|---|---|']
row = lambda lab, f: '| %s | %s |' % (lab, ' | '.join(f(M[m]) for m, _ in MS))
L.append(row('Trades', lambda o: '%d' % o['n']))
L.append(row('Reached T1', lambda o: '%.1f %%' % o['hit']))
L.append(row('Stopped out', lambda o: '%.1f %%' % o['stop']))
L.append(row('Ended in profit', lambda o: '%.1f %%' % o['won']))
L.append(row('Net at T1 (Rs)', lambda o: inr(o['net'])))
L.append(row('Net, hold for T3 (Rs)', lambda o: inr(o['net3'])))
L.append(row('Days up / down', lambda o: '%d / %d' % (o['days_up'], o['days_dn'])))
L.append(row('Longs: trades, reached T1, net', lambda o: '%d, %.1f %%, %s' % (o['side']['LONG'][0], o['side']['LONG'][1], inr(o['side']['LONG'][3]))))
L.append(row('Shorts: trades, reached T1, net', lambda o: '%d, %.1f %%, %s' % (o['side']['SHORT'][0], o['side']['SHORT'][1], inr(o['side']['SHORT'][3]))))
L += ['', '## The items the protocol said would be reported', '',
      '| Comparison | Reached T1 | Ahead in | Net (Rs) | Ahead in | Stop-outs | Trades |', '|---|---|---|---|---|---|---|']
for k, n in (('m_v3-m_opus', 'v3 against Opus'), ('m_v3-m_v2', 'v3 against v2 (the volume condition)'), ('m_v2-m_opus', 'v2 against Opus'), ('m_v3-m_fable_op', 'v3 against Fable-OP')):
    o = T[k]
    L.append('| %s | %+.1f pts | %.0f %% | %s | %.0f %% | %+.1f pts | %.0f %% |' % (n, o['hit_diff'], o['hit_ahead'], inr(o['net_diff']), o['net_ahead'], o['stop_diff'], o['trades_ratio']))
L += ['', '- **Trade count:** v3 took %.0f %% as many trades as Opus (rule: at least 85 %%). Met.' % t['trades_ratio'],
      '- **Volume condition:** among longs scoring 75 or more on Fable-OP, the %d with relative volume under 1 reached T1 %.1f %% of the time and lost Rs %s a trade; the other %d reached T1 %.1f %% and made Rs %s a trade. Same direction as in the known months.' % (
          G['low_n'], G['low_hit'], inr(G['low_per'], False).lstrip('-'), G['ok_n'], G['ok_hit'], inr(G['ok_per'], False)),
      '- **Side structure:** Fable-OP\'s longs reached T1 far more often than Opus\'s longs (%.1f %% against %.1f %%), as expected. Opus\'s shorts did not beat its longs: both lost (shorts Rs %s, longs Rs %s).' % (
          M['m_fable_op']['side']['LONG'][1], M['m_opus']['side']['LONG'][1], inr(M['m_opus']['side']['SHORT'][3]), inr(M['m_opus']['side']['LONG'][3])), '',
      '## Month by month: trades, reached T1, stopped, net (Rs)', '', '| Month | Opus | Opus v3 | Fable-OP |', '|---|---|---|---|']
for mo in sorted(M['m_opus']['bym']):
    L.append('| %s | %s |' % (mo, ' | '.join('%d, %.0f %%, %.0f %%, %s' % (*M[m]['bym'][mo][:3], inr(M[m]['bym'][mo][3])) for m in ('m_opus', 'm_v3', 'm_fable_op'))))
hb = sum(M['m_v3']['bym'][mo][1] > M['m_opus']['bym'][mo][1] for mo in M['m_opus']['bym'])
nb = sum(M['m_v3']['bym'][mo][3] > M['m_opus']['bym'][mo][3] for mo in M['m_opus']['bym'])
L += ['', 'v3 reached T1 more often than Opus in %d of 7 months and had the better net in %d of 7.' % (hb, nb), '',
      '## The same stand-in on both periods', '',
      'This puts the unseen period next to the known one on the same measuring stick. Net per session, stand-in:', '',
      '| | Known months (12 May - 19 Oct 2026) | Unseen (3 Nov 2025 - 11 May 2026) |', '|---|---|---|']
for m, n in MS:
    L.append('| %s | %s | %s |' % (n, inr(C['known'][m]['per_session']), inr(C['unseen'][m]['per_session'])))
L.append('| v3 longs: reached T1, net | %.1f %%, %s | %.1f %%, %s |' % (C['known']['m_v3']['long'][1], inr(C['known']['m_v3']['long'][3]), C['unseen']['m_v3']['long'][1], inr(C['unseen']['m_v3']['long'][3])))
L.append('| v3 shorts: reached T1, net | %.1f %%, %s | %.1f %%, %s |' % (C['known']['m_v3']['short'][1], inr(C['known']['m_v3']['short'][3]), C['unseen']['m_v3']['short'][1], inr(C['unseen']['m_v3']['short'][3])))
L += ['', 'The long side behaved the same in both periods. The short side made money in the known months and lost in the unseen ones, with the same reach-T1 rate but more stop-outs. Every model did worse in the unseen period than in the known one.', '',
      '## What this does and does not show', '',
      '- **Shown:** v3 is more accurate than Opus on dates nothing was fitted to, by about the margin the stand-in gave on known months. The volume condition points the same way again.',
      '- **Not shown:** that v3 makes more money than Opus, or that it is profitable in a period like this one. The stand-in understates profit heavily (on known months it showed v3 at Rs 1.5 lakh where the real figure was Rs 5.0 lakh, and showed Fable-OP at a small loss where the real figure was a Rs 3.1 lakh profit), so these losses are not a measure of what real futures would have done. But they are no evidence of profit either.',
      '- **New:** the scanner\'s six-month backtest period was kinder to every model than the six months before it. Its profit figures should not be read as typical.',
      '- **Limits of the stand-in:** signals are found on cash prices rather than futures, so about a third of the trades differ from what the live scanner would pick; the stock list is today\'s F&O list, not the list as it stood then; lot sizes are today\'s.', '',
      '## What would settle the profit question', '',
      'Only results on real futures, which means forward trades: the data source keeps no real futures history older than six months. A daily after-close replay on live contracts (the method that matched the scanner exactly on 21 Oct - 13 Nov) would build that record for all five models.', '']
open(sp + '/opus_v3_unseen_test_result.md', 'w').write('\n'.join(L))
print('\n'.join(L))

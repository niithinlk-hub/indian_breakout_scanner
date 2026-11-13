import json, sys
import numpy as np
sp = sys.argv[1]
D = json.load(open(sp + '/v2/opt5.json')); S = json.load(open(sp + '/v2/opt_sum.json')); E = json.load(open(sp + '/v2/opt_est.json'))
SC = (('opus', 'opus', 'T1', 'Opus, exit T1'), ('opus_v2', 'v2', 'T1', 'Opus v2, exit T1'), ('opus_v3', 'v3', 'T1', 'Opus v3, exit T1'), ('fable', 'fable', 'T3', 'Fable, exit T3'), ('fable_op', 'fable_op', 'T3', 'Fable-OP, exit T3'))


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


slip = {}
for m, e, pol, name in SC:
    slip[m] = {}
    for mode in ('same', 'held'):
        x = [r for r in D['rows'] if m in r['models'] and pol in r[mode]]
        turn = sum((r[mode][pol]['entry'] + r[mode][pol]['exit']) * r['qty'] for r in x)
        slip[m][mode] = {p: S[m][mode]['net'] - (p - 0.25) / 100 * turn for p in (0.25, 0.5, 1.0)}
        slip[m][mode]['turn_per_trade'] = turn / len(x)
    slip[m]['six'] = {p: E[e]['est'] - (p - 0.25) / 100 * slip[m]['same']['turn_per_trade'] * E[e]['n'] for p in (0.25, 0.5, 1.0)}
hdr = ['| | ' + ' | '.join(n for *_, n in SC) + ' |', '|---|---|---|---|---|---|']
row = lambda lab, f: '| %s | %s |' % (lab, ' | '.join(f(m, e) for m, e, _, _ in SC))
L = ['# Options: Opus, Opus v2 and Opus v3 at T1; Fable and Fable-OP at T3', '',
     'The option for each trade is the one the scanner picks: monthly expiry, strike nearest the signal price, a call for a long and a put for a short, same number of lots as the futures trade would have had. '
     'It is bought at the open of the entry minute and sold at the open of the first option candle after the futures leg reaches its exit (T1 or T3), its stop, or the end of the holding period. '
     'Option charges and 0.25 % slippage a side are included, as the scanner costs them. Nothing on the VPS was changed.', '',
     '## 1. Real option prices: 21 Oct to 13 Nov 2026 (17 sessions)', '',
     'Only the November option contracts can still be read, so this is the only period with real option prices. Every same-day figure reproduces the replay\'s own stored option result (274 legs checked, none different).', '',
     '**Squared off at the close of the entry day**', ''] + hdr
L.append(row('Trades', lambda m, e: '%d' % S[m]['n']))
L.append(row('Trades with an option price', lambda m, e: '%d' % S[m]['same']['priced']))
L.append(row('Option profit (Rs)', lambda m, e: inr(S[m]['same']['net'])))
L.append(row('Trades in profit', lambda m, e: '%d' % S[m]['same']['won']))
L.append(row('Average winner / loser (Rs)', lambda m, e: '%s / %s' % (inr(S[m]['same']['avg_win']), inr(S[m]['same']['avg_loss']))))
L.append(row('Worst trade (Rs)', lambda m, e: inr(S[m]['same']['worst'])))
L.append(row('21-30 Oct / 2-13 Nov (Rs)', lambda m, e: '%s / %s' % (inr(S[m]['same']['oct']), inr(S[m]['same']['nov']))))
L.append(row('Days up / down', lambda m, e: '%d / %d' % (S[m]['same']['days_up'], S[m]['same']['days_dn'])))
L.append(row('Largest fall from a peak (Rs)', lambda m, e: inr(S[m]['same']['maxdd'])))
L.append(row('Average premium paid a trade (Rs)', lambda m, e: inr(S[m]['same']['avg_outlay'], False)))
L.append(row('Most premium in use at once (Rs)', lambda m, e: inr(S[m]['same']['peak_outlay'], False)))
L.append(row('Profit as % of premium paid', lambda m, e: '%.1f %%' % S[m]['same']['ret_on_outlay']))
L.append(row('Futures profit on the same trades (Rs)', lambda m, e: inr(S[m]['same']['fut_net_same_trades'])))
L += ['', '**Held across days until the target or the stop (open trades marked to the 13 Nov close)**', ''] + hdr
L.append(row('Trades with an option price', lambda m, e: '%d' % S[m]['held']['priced']))
L.append(row('Option profit (Rs)', lambda m, e: inr(S[m]['held']['net'])))
L.append(row('Trades in profit', lambda m, e: '%d' % S[m]['held']['won']))
L.append(row('Average winner / loser (Rs)', lambda m, e: '%s / %s' % (inr(S[m]['held']['avg_win']), inr(S[m]['held']['avg_loss']))))
L.append(row('Worst trade (Rs)', lambda m, e: inr(S[m]['held']['worst'])))
L.append(row('21-30 Oct / 2-13 Nov (Rs)', lambda m, e: '%s / %s' % (inr(S[m]['held']['oct']), inr(S[m]['held']['nov']))))
L.append(row('Days up / down', lambda m, e: '%d / %d' % (S[m]['held']['days_up'], S[m]['held']['days_dn'])))
L.append(row('Largest fall from a peak (Rs)', lambda m, e: inr(S[m]['held']['maxdd'])))
L.append(row('Most premium in use at once (Rs)', lambda m, e: '%s (%d open)' % (inr(S[m]['held']['peak_outlay'], False), S[m]['held']['peak_open'])))
L.append(row('Average trading days held', lambda m, e: '%.1f' % S[m]['held']['avg_sessions']))
L.append(row('Futures profit on the same trades (Rs)', lambda m, e: inr(S[m]['held']['fut_net_same_trades'])))
R = E['ratios']
L += ['', '## 2. Why options change the ranking', '',
      'In this period, by how the futures leg ended (all 146 trades, same day):', '', '| Futures leg ended | Futures result a trade (Rs) | Option result a trade (Rs) | Share kept by the option |', '|---|---|---|---|',
      '| Reached T1 | +9,198 | +5,528 | %.0f %% |' % (100 * R['T1']['target']), '| Stopped out (exit-T1 plan) | -11,514 | -4,343 | %.0f %% |' % (100 * R['T1']['stopped']),
      '| Reached T3 | +23,286 | +14,545 | %.0f %% |' % (100 * R['T3']['target']), '| Stopped out (exit-T3 plan) | -11,473 | -4,472 | %.0f %% |' % (100 * R['T3']['stopped']), '',
      'A stop-out costs well under half as much in the option as in the future, while a target keeps about 60 %. So models with many stop-outs (Fable above all) look much better in options than in futures, and the gap between the models narrows.', '',
      '## 3. Six months, estimated: 12 May to 11 Nov 2026 (126 sessions)', '',
      'The May to October option contracts have expired and cannot be read. These figures convert each six-month futures result with the shares in section 2 (plus the two for trades squared off at the close). '
      'They are estimates, same-day exit, every signal taken. Applied back to 21 Oct - 13 Nov, the conversion gives Opus +74,574 (real +75,984), v2 +64,755 (+67,670), v3 +81,362 (+80,078), Fable +1,54,058 (+1,52,097), Fable-OP +1,20,936 (+1,02,661).', ''] + hdr
L.append(row('Trades', lambda m, e: '%d' % E[e]['n']))
L.append(row('Futures profit, real (Rs)', lambda m, e: inr(E[e]['fut'])))
L.append(row('Option profit, estimated (Rs)', lambda m, e: inr(E[e]['est'])))
L.append(row('Range from the conversion alone (Rs)', lambda m, e: '%s to %s' % (inr(E[e]['p5']), inr(E[e]['p95']))))
L.append(row('12 May - 31 Aug / 1 Sep - 11 Nov (Rs)', lambda m, e: '%s / %s' % (inr(E[e]['h1']), inr(E[e]['h2']))))
L.append(row('Months in profit', lambda m, e: '%d of 7' % E[e]['months_up']))
L.append(row('Largest fall from a peak (Rs)', lambda m, e: inr(E[e]['maxdd'])))
months = sorted(E['opus']['bym'])
L += ['', 'Estimated option profit by month (Rs):', '', '| Month | ' + ' | '.join(n for *_, n in SC) + ' |', '|---|---|---|---|---|---|']
for mo in months:
    L.append('| %s | %s |' % (mo, ' | '.join(inr(E[e]['bym'][mo]) for _, e, _, _ in SC)))
L += ['', 'The range covers only the uncertainty in the conversion shares. It does not cover months whose option pricing differed from 21 Oct - 13 Nov (for example the September fall).', '',
      '## 4. If option fills are worse than assumed', '',
      'Stock options often trade with wide gaps between bid and offer. The figures above assume 0.25 % a side. Same trades at 0.5 % and 1 % a side:', '',
      '| | ' + ' | '.join(n for *_, n in SC) + ' |', '|---|---|---|---|---|---|']
for mode, lab in (('same', '17 sessions, same day'), ('held', '17 sessions, held'), ('six', 'Six months, estimated')):
    for p in (0.25, 0.5, 1.0):
        L.append('| %s, %.2g %% a side (Rs) | %s |' % (lab, p, ' | '.join(inr(slip[m][mode][p]) for m, *_ in SC)))
L += ['', '## 5. Capital', '',
      'Average premium is about Rs 21,000 to 25,000 a trade. The most premium in use at once in the 17 sessions was Rs %s to %s when squared off daily and Rs %s to %s when held across days. '
      'So Rs 3 lakh a method covers every signal in options; the futures-margin limit of about two positions does not apply.' % (
          inr(min(S[m]['same']['peak_outlay'] for m, *_ in SC), False), inr(max(S[m]['same']['peak_outlay'] for m, *_ in SC), False),
          inr(min(S[m]['held']['peak_outlay'] for m, *_ in SC), False), inr(max(S[m]['held']['peak_outlay'] for m, *_ in SC), False)), '',
      '## 6. Limits', '',
      '- Real option prices cover 17 sessions, and almost all the profit in them came in 2 - 13 Nov, a sharply rising market.',
      '- The six-month figures are conversions, not prices, and are same-day only; held-across-days option results cannot be built for May to October.',
      '- A few trades had no option candle to price (5 of Opus\'s 65 same-day, for example); they are left out of the option totals.',
      '- Opus v2 and v3 exist only on paper. Opus\'s weights were tuned on 21 Oct - 9 Nov. These are replays, not live fills.', '',
      '## 7. Every trade, 21 Oct to 13 Nov', '',
      '| Date | Time | Symbol | Option | Qty | Models | Premium paid (Rs) | Same day: exit T1 (Rs) | Same day: exit T3 (Rs) | Held: exit T1 (Rs) | Held: exit T3 (Rs) |', '|---|---|---|---|---|---|---|---|---|---|---|']
short = {'opus': 'O', 'fable': 'F', 'fable_op': 'FOP', 'opus_v2': 'v2', 'opus_v3': 'v3'}
for r in D['rows']:
    g = lambda mode, pol: inr(r[mode][pol]['net_rs']) if pol in r[mode] else 'no price'
    prem = r['held'].get('T1', r['same'].get('T1', {})).get('outlay')
    L.append('| %s | %s | %s | %s | %d | %s | %s | %s | %s | %s | %s |' % (r['day'][5:], r['time'], r['symbol'], r['option'].replace(r['symbol'] + ' ', ''), r['qty'], ' '.join(short[m] for m in r['models']),
             inr(prem, False) if prem else '-', g('same', 'T1'), g('same', 'T3'), g('held', 'T1'), g('held', 'T3')))
L += ['', 'Models: O = Opus, F = Fable, FOP = Fable-OP, v2 = Opus v2, v3 = Opus v3.', '']
open(sp + '/options_five_scenarios.md', 'w').write('\n'.join(L))
json.dump(slip, open(sp + '/v2/opt_slip.json', 'w'))
print('\n'.join(L[:52]))
print('...')
print('\n'.join(L[52:92]))

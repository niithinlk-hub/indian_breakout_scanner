import json, sys
sp = sys.argv[1]
F7 = json.load(open(sp + '/v2/f7.json')); F5 = json.load(open(sp + '/v2/f5.json')); F6 = json.load(open(sp + '/v2/f6.json')); HV = json.load(open(sp + '/v2/hold_v3.json'))
E9 = json.load(open(sp + '/v2/e9.json'))


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


MS = (('opus', 'Opus'), ('fable', 'Fable'), ('fable_op', 'Fable-OP'), ('v2', 'Opus v2'), ('v3', 'Opus v3'))


def table(per, cols):
    L = ['| | ' + ' | '.join(n for _, n in cols) + ' |', '|---|' + '---|' * len(cols)]
    g = lambda c: F7['%s|%s' % (per, c)]
    L.append('| Trades | ' + ' | '.join('%d' % g(c)['n'] for c, _ in cols) + ' |')
    L.append('| Reached T1 | ' + ' | '.join('%.1f %%' % g(c)['hit%'] for c, _ in cols) + ' |')
    L.append('| Stopped out | ' + ' | '.join('%.1f %%' % g(c)['stop%'] for c, _ in cols) + ' |')
    L.append('| Ended in profit | ' + ' | '.join('%.1f %%' % g(c)['won%'] for c, _ in cols) + ' |')
    L.append('| Net, exit at T1 (Rs) | ' + ' | '.join(inr(g(c)['T1']) for c, _ in cols) + ' |')
    L.append('| Net per trade (Rs) | ' + ' | '.join(inr(g(c)['per']) for c, _ in cols) + ' |')
    L.append('| Net, hold for T2 (Rs) | ' + ' | '.join(inr(g(c)['T2']) for c, _ in cols) + ' |')
    L.append('| Net, hold for T3 (Rs) | ' + ' | '.join(inr(g(c)['T3']) for c, _ in cols) + ' |')
    L.append('| Days up / down | ' + ' | '.join('%d / %d' % (g(c)['days_up'], g(c)['days_dn']) for c, _ in cols) + ' |')
    L.append('| Largest fall from a peak (Rs) | ' + ' | '.join(inr(g(c)['maxdd']) for c, _ in cols) + ' |')
    return L


b = F7['boot']
L = ['# Opus v2 six-month check, and Opus v3', '',
     'Built and tested in isolation. Nothing on the VPS was changed and the patch has not been applied anywhere.', '',
     'All figures: the scanner\'s own six-month backtest file, 12 May to 11 Nov 2026 (126 sessions, real contract months), live rule (first 6 signals a day at or above each model\'s cut-off), '
     'same-day exit at T1, lots sized to Rs 15,000 risk, charges and 0.02 % slippage a side.', '',
     '## 1. Six-month check', ''] + table('all', MS) + ['',
     'Opus v2 against Opus: reaches T1 far more often and makes about twice the net, but is stopped out slightly more often (26.3 % against 24.1 %). So it meets two of the three aims, not the third.', '',
     '## 2. Opus v3', '',
     'Opus v2 with one extra condition: **a long must have relative volume of 1 or more** (the stock\'s volume so far today at least equal to its normal volume by that time of day). Shorts are unchanged.', '',
     '- The 22 longs this removes reached T1 32 % of the time, were stopped 36 % of the time and lost Rs 31,091 between them. Four later signals take freed places.',
     '- Looking wider, at all 559 longs scoring 65 or more on Fable-OP: the 103 on below-normal volume lost about Rs 1,000 a trade in each half of the six months.',
     '- The value 1 is the one the scanner\'s settings already name as "preferred" volume. Cuts from 0.6 to 1.2 all beat v2, so it is not a lone peak.', '',
     '**By half**', '',
     '| | v2, 12 May - 31 Aug | v3, 12 May - 31 Aug | v2, 1 Sep - 11 Nov | v3, 1 Sep - 11 Nov |', '|---|---|---|---|---|']
g = lambda k: F7[k]
for lab, key, fmt in (('Trades', 'n', '%d'), ('Reached T1', 'hit%', '%.1f %%'), ('Stopped out', 'stop%', '%.1f %%')):
    L.append('| %s | %s | %s | %s | %s |' % (lab, fmt % g('h1|v2')[key], fmt % g('h1|v3')[key], fmt % g('h2|v2')[key], fmt % g('h2|v3')[key]))
L.append('| Net at T1 (Rs) | %s | %s | %s | %s |' % (inr(g('h1|v2')['T1']), inr(g('h1|v3')['T1']), inr(g('h2|v2')['T1']), inr(g('h2|v3')['T1'])))
L += ['', '**Month by month: trades, reached T1, stopped, net (Rs)**', '', '| Month | Opus | Opus v2 | Opus v3 |', '|---|---|---|---|']
bm = F7['bym']
for mo in sorted(bm['opus']):
    L.append('| %s | %s |' % (mo, ' | '.join('%d, %.0f %%, %.0f %%, %s' % (bm[c][mo][0], bm[c][mo][1], bm[c][mo][2], inr(bm[c][mo][3])) for c in ('opus', 'v2', 'v3'))))
better = sum(bm['v3'][mo][3] > bm['v2'][mo][3] for mo in bm['v3'])
L += ['', 'v3 made more than v2 in %d of 7 months.' % better, '',
      '**Longs and shorts, six months**', '', '| | Longs: trades | Longs: reached T1 | Longs: stopped | Longs: net (Rs) | Shorts: trades | Shorts: reached T1 | Shorts: stopped | Shorts: net (Rs) |', '|---|---|---|---|---|---|---|---|---|']
sd = F7['side']
for c, n in MS:
    lo, sh = sd[c]['LONG'], sd[c]['SHORT']
    L.append('| %s | %d | %.1f %% | %.1f %% | %s | %d | %.1f %% | %.1f %% | %s |' % (n, lo[0], lo[1], lo[2], inr(lo[3]), sh[0], sh[1], sh[2], inr(sh[3])))
L += ['', '**How sure (126 days resampled 20,000 times)**', '',
      '| v3 compared with | Net at T1 (Rs) | 5th to 95th percentile | Net higher in | Reach-T1 | Higher in | Stop-outs | Lower in |', '|---|---|---|---|---|---|---|---|']
for k, n in (('v3-v2', 'Opus v2'), ('v3-opus', 'Opus'), ('v3-fable_op', 'Fable-OP')):
    o = b[k]
    L.append('| %s | %s | %s to %s | %.0f %% | %+.1f pts | %.0f %% | %+.1f pts | %.0f %% |' % (n, inr(o['net']), inr(o['net_p5']), inr(o['net_p95']), o['net_pos'], o['hit'], o['hit_pos'], o['stop'], o['stop_neg']))
L += ['', 'Against v2 the step is small and each part of it is likely rather than certain. Against Opus, reach-T1 and net are clearly better; stop-outs are not.', '',
      '## 3. Why stop-outs do not come down further', '',
      'On shorts, v3 and Opus use the same score and are stopped equally often (about 20 %%). The gap is on longs: v3\'s longs are stopped %.0f %% of the time and reach T1 %.0f %%; Opus\'s longs are stopped %.0f %%, reach T1 only %.0f %% and lose money.' % (
          sd['v3']['LONG'][2], sd['v3']['LONG'][1], sd['opus']['LONG'][2], sd['opus']['LONG'][1]), '',
      'Three ways of cutting stop-outs were tested. Each cut them, and each cost more in T1 hits and net than it saved.', '',
      '**a. Where the stop sits.** Run on v3\'s trades plus the shorts that qualify on Fable-OP (355 trades). Same entries, levels rebuilt with the scanner\'s level code, day replayed on cash 1-minute candles (the expired futures cannot be read). '
      'The cash replay of today\'s rule matches the real outcome on 310 of 355 trades.', '',
      '| Stop rule | Trades taken | Skipped (one lot over Rs 15,000 risk) | Reached T1 | Stopped | Net (Rs) |', '|---|---|---|---|---|---|']
for k, o in F5.items():
    L.append('| %s | %d | %d | %.1f %% | %.1f %% | %s |' % (k, o['taken'], o['skipped'], o['hit'], o['stop'], inr(o['net'])))
L += ['', '**b. Moving the stop to the entry price part-way to T1** (same trades, same replay).', '', '| Rule | Reached T1 | Full stop-outs | Scratched at entry | Net (Rs) | Months better than today\'s rule |', '|---|---|---|---|---|---|']
for k, o in F6.items():
    L.append('| %s | %.1f %% | %.1f %% | %.1f %% | %s | %s |' % (k, o['hit'], o['stop'], o['be'], inr(o['net']), '-' if k == 'as now' else '%d of 7' % o['months_better']))
L += ['', '**c. Extra filters chosen from the data.** For each month in turn, the best filter per side was chosen from 22 features using the other six months, then applied to the month left out. '
      'The filters chosen changed from month to month. On the left-out months, in the two versions of the search I ran, stop-outs were 26.3 % and 27.1 % (v2: 26.3 %) and the net was Rs +4,71,432 and Rs +5,59,409 (v2: Rs +5,28,284): no gain on stop-outs, and no reliable gain on net. '
      'A rule to skip shorts once Nifty is down 1 % helped in May to August and hurt in September to November.', '',
      'About a quarter of these trades being stopped looks like the cost of trading breakouts with a stop of about half a day\'s range: tighter selection does not remove it, and a looser stop or an early move to entry gives back more than it saves.', '',
      '## 4. Other checks', '',
      '- **Latest 17 sessions, 21 Oct to 13 Nov (real November futures):** Opus 65 trades, 40 % reached T1, 22 % stopped, Rs +69,390. v2: 54, 41 %, 22 %, Rs +62,552. v3: 52, 44 %, 21 %, Rs +96,393. Fable-OP: 33, 48 %, 21 %, Rs +63,709.',
      '- **Volume figures are exact:** my rebuilt relative volume equals the scanner\'s own stored value on all 872 signals where both exist.',
      '- **Patched code:** applied to an offline copy and run on the 17 stored replay days. The three existing scores are reproduced exactly, existing models\' picks are untouched, and the v2 and v3 picks equal the ones tested here.',
      '- **Held across days, 1 Sep to 13 Nov, every signal taken:** exit T1: Opus Rs %s, v2 Rs %s, v3 Rs %s. Exit T3: Opus Rs %s, v2 Rs %s, v3 Rs %s. (One v3 trade has no multi-day result and is left out.)' % (
          inr(E9['hold|opus|T1']['net']), inr(HV['v2']['hold_T1']['net']), inr(HV['v3']['hold_T1']['net']), inr(E9['hold|opus|T3']['net']), inr(HV['v2']['hold_T3']['net']), inr(HV['v3']['hold_T3']['net'])),
      '- **With Rs 3 lakh of futures margin (about two positions at a time), same 50 sessions:** exit T1: Opus Rs %s, v2 Rs %s, v3 Rs %s. Exit T3: Opus Rs %s, v2 Rs %s, v3 Rs %s. At T1 Opus is still ahead here.' % (
          inr(E9['cap|opus|T1|3L']['net']), inr(HV['v2']['cap_T1']['net']), inr(HV['v3']['cap_T1']['net']), inr(E9['cap|opus|T3|3L']['net']), inr(HV['v2']['cap_T3']['net']), inr(HV['v3']['cap_T3']['net'])), '',
      '## 5. Limits', '',
      '- The volume condition was found by comparing 27 features on these same six months, so the size of its gain is not proven. Its direction is supported in both halves and in the wider pool of longs.',
      '- There is no untouched period left to test v3 on. Only forward paper trades can settle it.',
      '- About 6 in 10 trades enter in the first 15 minutes, where real fills are likely worse than assumed.',
      '- Backtest, not live. No option results for May to October (those contracts have expired).', '',
      '## 6. Files', '',
      '- `opus_v2_v3_integration.patch`: adds `opus_v2` and `opus_v3` as logged score models (score.py, config.py, backtest.py). Replaces the earlier v2-only patch. Not applied. `backtest.py` in the image has Windows line endings; use `git apply --ignore-whitespace` if the repository copy differs.',
      '- `opus_v3_check.py`: lists Opus, v2 and v3 picks from any stored scanner day (replay or backtest JSON).', '']
open(sp + '/opus_v3_backtest_report.md', 'w').write('\n'.join(L))
print('\n'.join(L))

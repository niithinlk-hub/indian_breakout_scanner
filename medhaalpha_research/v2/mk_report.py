import sys, json, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, sys.argv[1] + '/v2')
import numpy as np, pandas as pd
from frame import load
from lab import *
sp = sys.argv[1]
df = load()
df['opus'], df['fable_op'] = df.t_opus, df.t_fable_op
df['v2'] = np.where(df.long == 1, df.t_fable_op, df.t_opus)
df['anti'] = np.where(df.long == 1, df.t_opus, df.t_fable_op)
df['blend'] = np.where(df.long == 1, 0.5 * df.t_opus + 0.5 * df.t_fable_op + 5.0, df.t_opus)
A = df[df.design | df.unseen]
e9 = json.load(open(sp + '/v2/e9.json'))
e10 = json.load(open(sp + '/v2/e10.json'))


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


def S(P, col):
    return stat(P, live_df(P, col, 75))


L = ['# Opus v2: backtest report', '',
     'Built and tested in isolation. Nothing on the VPS was changed, and the patch in this folder has not been applied anywhere.', '',
     '## What Opus v2 is', '',
     'A side split, with no new weights or cut-offs:', '',
     '- a **long** (setup A) is scored by Fable-OP and needs 75 or more;',
     '- a **short** (setup B) is scored by Opus and needs 75 or more, exactly as today;',
     '- everything else is unchanged: same signals, same stops and targets, first 6 qualifying signals a day.', '',
     'Reason: Opus\'s picks made money on shorts and not on longs, in May to August (months its weights never saw) and again in September to November. Fable-OP is the reverse.', '',
     '## Result, same-day exit at T1', '',
     'Source: the scanner\'s own six-month backtest (12 May to 11 Nov 2026, 126 sessions, real contract months, lots sized to Rs 15,000 risk, charges and 0.02 % slippage a side). '
     '"Reached T1" is the accuracy measure; anything not at T1 or the stop is squared off at the close.', '']
for title, mask, ns in (('All 126 sessions, 12 May to 11 Nov', df.design | df.unseen, 126), ('12 May to 31 Aug, 78 sessions', df.design, 78), ('1 Sep to 11 Nov, 48 sessions', df.unseen, 48)):
    P = df[mask]
    o, v, f = S(P, 'opus'), S(P, 'v2'), S(P, 'fable_op')
    L += ['**%s**' % title, '', '| | Opus now | Opus v2 | Fable-OP |', '|---|---|---|---|']
    L.append('| Trades | %d | %d | %d |' % (o['n'], v['n'], f['n']))
    L.append('| Trades a session | %.1f | %.1f | %.1f |' % (o['n'] / ns, v['n'] / ns, f['n'] / ns))
    L.append('| Reached T1 | %.1f %% | %.1f %% | %.1f %% |' % (o['hit%'], v['hit%'], f['hit%']))
    L.append('| Stopped out | %.1f %% | %.1f %% | %.1f %% |' % (o['stop%'], v['stop%'], f['stop%']))
    L.append('| Ended in profit | %.1f %% | %.1f %% | %.1f %% |' % (o['won%'], v['won%'], f['won%']))
    L.append('| Net, exit at T1 (Rs) | %s | %s | %s |' % (inr(o['T1']), inr(v['T1']), inr(f['T1'])))
    L.append('| Net per trade (Rs) | %s | %s | %s |' % (inr(o['per']), inr(v['per']), inr(f['per'])))
    L.append('| Net, hold for T2 (Rs) | %s | %s | %s |' % (inr(o['T2']), inr(v['T2']), inr(f['T2'])))
    L.append('| Net, hold for T3 (Rs) | %s | %s | %s |' % (inr(o['T3']), inr(v['T3']), inr(f['T3'])))
    L.append('| Days up / down | %d / %d | %d / %d | %d / %d |' % (o['days_up'], o['days_dn'], v['days_up'], v['days_dn'], f['days_up'], f['days_dn']))
    L.append('| Largest fall from a peak (Rs) | %s | %s | %s |' % (inr(o['maxdd']), inr(v['maxdd']), inr(f['maxdd'])))
    L.append('')
L += ['## Month by month', '', '| Month | Nifty | Opus trades | Opus reached T1 | Opus net (Rs) | v2 trades | v2 reached T1 | v2 net (Rs) |', '|---|---|---|---|---|---|---|---|']
six = json.load(open(sp + '/six/pull.json'))['six']
nifty = {m['month']: m['nifty_pct'] for m in six['months']}
to, tv = A.loc[live_df(A, 'opus', 75)], A.loc[live_df(A, 'v2', 75)]
better_hit = better_net = 0
for mo in sorted(A.month.unique()):
    a, b = to[to.month == mo], tv[tv.month == mo]
    better_hit += b.hit.mean() > a.hit.mean(); better_net += b.net1.sum() > a.net1.sum()
    L.append('| %s | %+.1f %% | %d | %.0f %% | %s | %d | %.0f %% | %s |' % (mo, nifty[mo], len(a), 100 * a.hit.mean(), inr(a.net1.sum()), len(b), 100 * b.hit.mean(), inr(b.net1.sum())))
L += ['', 'Opus v2 reached T1 more often in %d of 7 months and made more money in %d of 7.' % (better_hit, better_net), '',
      '## By side', '', '| Period | Model | Longs: trades | Longs: reached T1 | Longs: net (Rs) | Shorts: trades | Shorts: reached T1 | Shorts: net (Rs) |', '|---|---|---|---|---|---|---|---|']
for per, mask in (('12 May - 31 Aug', df.design), ('1 Sep - 11 Nov', df.unseen)):
    P = df[mask]
    for lab, col in (('Opus now', 'opus'), ('Fable-OP', 'fable_op'), ('Opus v2', 'v2'), ('Opposite pairing', 'anti')):
        t = P.loc[live_df(P, col, 75)]
        lg, sh = t[t.long == 1], t[t.long == 0]
        L.append('| %s | %s | %d | %.0f %% | %s | %d | %.0f %% | %s |' % (per, lab, len(lg), 100 * lg.hit.mean(), inr(lg.net1.sum()), len(sh), 100 * sh.hit.mean(), inr(sh.net1.sum())))
L += ['', '"Opposite pairing" is Opus for longs and Fable-OP for shorts. It is the worst of the four in both periods, which is what the split predicts.', '']
# paired resampling
days = sorted(A.day.unique())
do = to.groupby('day').net1.sum().reindex(days).fillna(0).to_numpy(); dv = tv.groupby('day').net1.sum().reindex(days).fillna(0).to_numpy()
ho, no = to.groupby('day').hit.sum().reindex(days).fillna(0).to_numpy(), to.groupby('day').size().reindex(days).fillna(0).to_numpy()
hv, nv = tv.groupby('day').hit.sum().reindex(days).fillna(0).to_numpy(), tv.groupby('day').size().reindex(days).fillna(0).to_numpy()
rng = np.random.default_rng(11)
ix = rng.integers(0, len(days), size=(20000, len(days)))
dnet = (dv - do)[ix].sum(axis=1)
dhit = hv[ix].sum(axis=1) / nv[ix].sum(axis=1) - ho[ix].sum(axis=1) / no[ix].sum(axis=1)
L += ['## How sure is the difference', '', 'The 126 days resampled 20,000 times, Opus v2 minus Opus on the same days:', '',
      '- reached-T1 rate: %+.1f points, 5th to 95th percentile %+.1f to %+.1f; higher in every resample.' % (100 * (hv.sum() / nv.sum() - ho.sum() / no.sum()), 100 * np.percentile(dhit, 5), 100 * np.percentile(dhit, 95)),
      '- net at T1: Rs %s, 5th to 95th percentile %s to %s; higher in %.0f %% of resamples.' % (inr((dv - do).sum()), inr(np.percentile(dnet, 5)), inr(np.percentile(dnet, 95)), 100 * (dnet > 0).mean()), '',
      'So the accuracy gain is firm. The profit gain is likely, not certain.', '',
      '## Checks', '']
g = e10['grid']
cells = [g[k] for k in g]
L += ['- **Other cut-offs.** Long cut 70 to 80 and short cut 72 to 80 (20 combinations): reached-T1 rate %.0f to %.0f %%, net Rs %s to %s. Opus now: %.0f %%, Rs %s. The 75 / 75 pair is not a lone peak.' % (
          min(c['hit%'] for c in cells), max(c['hit%'] for c in cells), inr(min(c['T1'] for c in cells)), inr(max(c['T1'] for c in cells)), S(A, 'opus')['hit%'], inr(S(A, 'opus')['T1'])),
      '- **Costlier early entries.** %d of v2\'s %d trades enter in the first 15 minutes (Opus: %d of %d), where fills are likely worse than the 0.02 %% a side assumed. At 0.05 %% a side on those entries v2 nets about Rs %s and Opus Rs %s; at 0.10 %%, Rs %s and Rs %s (turnover taken as Rs 13 lakh a trade).' % (
          e10['slip|split']['early'], e10['slip|split']['n'], e10['slip|opus']['early'], e10['slip|opus']['n'], inr(e10['slip|split']['slip_0.05']), inr(e10['slip|opus']['slip_0.05']),
          inr(e10['slip|split']['slip_0.1']), inr(e10['slip|opus']['slip_0.1'])),
      '- **Patched code.** The patch was applied to a copy of the scanner code and run offline on the 17 stored replay days (21 Oct to 13 Nov, 1,169 signals): the existing three scores are reproduced exactly, the existing models\' picks are untouched, and opus_v2\'s picks equal the picks tested here on every day.',
      '- **Latest 17 sessions (21 Oct to 13 Nov).** Opus: 65 trades, 26 reached T1, Rs +69,390. Opus v2: 54 trades, 22 reached T1, Rs +62,552. No gain in this stretch, which includes the weeks Opus was tuned on. On 12 and 13 Nov, two rising days, Opus took 12 longs and v2 took 1.',
      '- **Held across days, 1 Sep to 13 Nov (50 sessions), every signal taken.** Exit T1: Opus Rs %s on %d trades, v2 Rs %s on %d. Exit T3: Opus Rs %s, v2 Rs %s. (1 Sep to 19 Oct followed on the cash share, as in the earlier September work.)' % (
          inr(e9['hold|opus|T1']['net']), e9['hold|opus|T1']['n'], inr(e9['hold|split|T1']['net']), e9['hold|split|T1']['n'], inr(e9['hold|opus|T3']['net']), inr(e9['hold|split|T3']['net'])),
      '- **Rs 3 lakh of futures margin (about two positions at a time), same 50 sessions.** Exit T1: Opus Rs %s (%d trades carried), v2 Rs %s (%d). Exit T3: Opus Rs %s (%d), v2 Rs %s (%d). With so few slots the result depends on which signals happen to fire first, and v2 is not ahead at T1.' % (
          inr(e9['cap|opus|T1|3L']['net']), e9['cap|opus|T1|3L']['taken'], inr(e9['cap|split|T1|3L']['net']), e9['cap|split|T1|3L']['taken'],
          inr(e9['cap|opus|T3|3L']['net']), e9['cap|opus|T3|3L']['taken'], inr(e9['cap|split|T3|3L']['net']), e9['cap|split|T3|3L']['taken']), '']
U = df[df.unseen]
o, b = S(U, 'opus'), S(U, 'blend')
L += ['## What was tried and dropped', '',
      '1. **A new score fitted from the raw features** (move in ATRs, distance from VWAP, gap, time, relative volume and 12 more; separate fits for longs and shorts). '
      'Fitted on three of the four months May to August and tested on the fourth, in turn: at Opus\'s trade count most variants reached T1 more often (32 to 48 %), but all were stopped far more often and every one lost money (as much as Rs 3.6 lakh, against Opus\'s gain of 1.4 lakh). Dropped.',
      '2. **Blending the Opus and Fable-OP scores.** Fixed on May to August, then checked once on 1 Sep to 11 Nov: longs on an equal blend, shorts on Opus gave %d trades, %.1f %% reached T1, Rs %s, against Opus\'s %d trades, %.1f %%, Rs %s. More accurate, no more profitable. '
      'The side tables showed why: any weight on Opus made the long picks worse. That is what led to the plain split.' % (b['n'], b['hit%'], inr(b['T1']), o['n'], o['hit%'], inr(o['T1'])),
      '3. **Skipping shorts on broadly weak days** (Nifty already well down, or many shorts already fired). Strong on May to August, weak or reversed on 1 Sep to 11 Nov. Not included.', '',
      '## Limits', '',
      '- **The split was chosen after seeing 1 Sep to 11 Nov** (step 2 above), so that period is not a clean test of it. In its favour: it has no fitted number, Opus\'s short-only strength shows in May to August (months Opus never saw), and Fable-OP\'s long strength shows in September to November (months Fable-OP never saw).',
      '- **Profit is uneven.** The six-month gain comes mostly from May, July and September. v2 was behind Opus in August, October and November.',
      '- **Stops are slightly more frequent** (26 % against 24 %) and the largest fall from a peak is a little deeper.',
      '- **In strongly rising markets v2 trades less than Opus**, because Fable-OP passes fewer longs than Opus does.',
      '- **Backtest, not live.** On 13 Nov the live paper ledger showed Opus at Rs -18,241 where the replay shows Rs -2,928.',
      '- No option results: the option contracts for May to October have expired.', '',
      '## How it was built', '',
      '- Signals, the three scores and outcomes: the scanner\'s own six-month per-signal file (4,996 setup A and B signals).',
      '- Features for step 1: rebuilt for every signal with the scanner\'s own feature code from 6.9 million cash 1-minute candles (20 Apr to 12 Nov). The rebuilt scores match the scanner\'s own with correlation 0.84 to 0.95, which is too loose for threshold decisions, so the final candidate uses only the scanner\'s own stored scores.',
      '- Fitting was confined to 12 May to 31 Aug. 1 Sep to 11 Nov was opened once, for the blended candidates.', '',
      '## Files', '',
      '- `opus_v2_integration.patch`: adds `opus_v2` as a fourth score model (score.py, config.py, backtest.py). Not applied. `backtest.py` in the image has Windows line endings; apply with `git apply --ignore-whitespace` if the repository copy differs. The dashboard lives in the engine service, which I have not seen; its model selector may need the new name added.',
      '- `opus_v2_check.py`: lists Opus v2\'s picks from any stored scanner day (replay or backtest JSON), so it can be paper-tracked without changing anything.', '']
open(sp + '/opus_v2_backtest_report.md', 'w').write('\n'.join(L))
print('\n'.join(L))

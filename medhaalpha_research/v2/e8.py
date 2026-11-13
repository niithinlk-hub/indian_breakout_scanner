# Split picks for 1 Sep - 13 Nov: (a) exact check on my futures-basis replays, 21 Oct - 13 Nov; (b) coverage by the hold rows already computed.
import sys, json, glob, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, sys.argv[1] + '/v2')
import numpy as np, pandas as pd
from base import SP
from frame import load
from lab import *
df = load()
df['split'] = np.where(df.long == 1, df.t_fable_op, df.t_opus)
picks = {}                                     # (day, symbol, setup, time) -> source
U = df[df.day >= '2026-09-01']
for i in live_df(U, 'split', 75):
    r = U.loc[i]
    picks[(r.day, r.symbol, r.setup, r.time)] = 'report'
# replays: every day 21 Oct - 13 Nov
rep = {}
tot = {}
for d in ('replay_oct', 'replay_nov2', 'replay7'):
    for p in sorted(glob.glob(SP + '/' + d + '/replay_*.json')):
        j = json.load(open(p))
        pool = [s for s in j['signals'] if s['setup'] in ('A', 'B') and s['fut']['T1']['status'] != 'no_data']
        for m, key in (('opus', lambda s: s['scores']['opus']), ('fable_op', lambda s: s['scores']['fable_op']),
                       ('split', lambda s: s['scores']['fable_op'] if s['side'] == 'LONG' else s['scores']['opus'])):
            sel = []
            for s in sorted(pool, key=lambda s: (s['time'], -key(s), s['symbol'])):
                if key(s) >= 75 and len(sel) < 6:
                    sel.append(s)
            rep[(j['day'], m)] = sel
            if m != 'split':
                assert {(s['symbol'], s['setup']) for s in sel} == {(s['symbol'], s['setup']) for s in j['signals'] if 'live' in s['in'][m]}, (j['day'], m)
print('replay selection code reproduces the replays\' own Opus and Fable-OP live picks on all', len({k[0] for k in rep}), 'replay days')
mis = 0
for (day, m), sel in rep.items():
    if m == 'split' and day <= '2026-11-11':
        a = {(s['symbol'], s['setup'], s['time']) for s in sel}
        b = {(k[1], k[2], k[3]) for k in picks if k[0] == day}
        mis += a != b
print('split picks from replays vs from the six-month report, 21 Oct - 11 Nov: days that differ =', mis)
for day in ('2026-11-12', '2026-11-13'):
    for m in ('opus', 'fable_op', 'split'):
        sel = rep[(day, m)]
        print('  %s %-8s n=%d hit %d stop %d T1 %+8.0f T3 %+8.0f | %s' % (day, m, len(sel), sum(s['fut']['T1']['status'] == 'target' for s in sel), sum(s['fut']['T1']['status'] == 'stopped' for s in sel),
              sum(s['fut']['T1']['net_rs'] for s in sel), sum(s['fut']['T3']['net_rs'] for s in sel), ' '.join('%s(%s)' % (s['symbol'], s['side'][0]) for s in sel)))
    for s in rep[(day, 'split')]:
        picks[(day, s['symbol'], s['setup'], s['time'])] = 'replay'
hold = {}
for r in json.load(open(SP + '/hold_sep.json'))['rows']:
    hold[(r['day'], r['symbol'], r['setup'], r['time'])] = r
for r in json.load(open(SP + '/t3_hold.json'))['rows']:
    hold[(r['day'], r['symbol'], r['setup'], r['time'])] = r
missing = [k for k in sorted(picks) if k not in hold]
print('split picks 1 Sep - 13 Nov:', len(picks), '| with a multi-day hold row already:', len(picks) - len(missing), '| missing:', missing)
json.dump([list(k) for k in sorted(picks)], open(SP + '/v2/split_picks.json', 'w'))

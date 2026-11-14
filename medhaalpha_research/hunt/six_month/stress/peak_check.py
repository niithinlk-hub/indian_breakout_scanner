# list the trades open at the reported premium peaks (sanity check of item 5)
import sys
SP = '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
sys.path.insert(0, SP + '/hunt'); import harness as H
import pandas as pd
D = H.load_all()
for s, spec, day in (('unseen', ('s_opus', 75, 'T1', 6), '2026-01-21'), ('unseen', H.switch1, '2026-01-21'), ('real', ('s_fable', 75, 'T3', 6), '2026-08-20')):
    t = H.run(D[s], spec); t = t[t.day == day].copy()
    det = pd.concat([H.option_net(g, p, detail=True) for p, g in t.groupby('pol')]).reindex(t.index)
    t['outlay'] = det.outlay
    t['exit'] = [r['o_exit_ts_' + r['pol']][11:16] for _, r in t.iterrows()]
    print(s, day, t.regime.iloc[0]); print(t[['time', 'symbol', 'side', 'pol', 'o_entry_ts', 'exit', 'o_qty', 'outlay', 'pnl']].to_string()); print()

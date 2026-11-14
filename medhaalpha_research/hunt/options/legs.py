# Collect the real option legs (21 Oct - 13 Nov 2026) the scanner recorded, one row per signal x policy.
import json, glob, sys
import pandas as pd
SP = sys.argv[1]
POL = ['T1', 'T2', 'T3', 'CLOSE', 'T2_TR', 'T3_TR', 'CLOSE_TR']
MON = {m: i + 1 for i, m in enumerate('JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC'.split())}
seen, rows = set(), []
for d in ['replay_oct', 'replay_nov2', 'replay7', 'replay']:
    for f in sorted(glob.glob(f'{SP}/{d}/replay_*.json')):
        x = json.load(open(f))
        for s in x['signals']:
            o = s.get('option')
            if s.get('setup') not in ('A', 'B') or not o:
                continue
            key = (x['day'], s['time'], s['symbol'], s['setup'])
            if key in seen:
                continue
            seen.add(key)
            p = o['symbol'].split()
            exp = '20%s-%02d-%02d' % (p[-1], MON[p[-2]], int(p[-3]))
            for pol in POL:
                L, Fu = o['legs'].get(pol), s['fut'].get(pol)
                if not L or not Fu or L.get('entry') is None or L.get('exit') is None or Fu.get('status') == 'no_data':
                    continue
                rows.append({'day': x['day'], 'time': s['time'], 'symbol': s['symbol'], 'setup': s['setup'], 'side': s['side'], 'pol': pol,
                             'atr_pct': s['snapshot'].get('atr_pct'), 'price': s['snapshot'].get('price'), 'lot': s['lot'], 'lots': s['lots'],
                             'strike': o['strike'], 'kind': p[-4], 'expiry': exp, 'o_entry_ts': L['entry_ts'], 'o_entry': L['entry'], 'o_exit_ts': L['exit_ts'],
                             'o_exit': L['exit'], 'o_net': L['net_rs'], 'o_costs': L['costs'], 'o_slip': L['slip_rs'], 'o_status': L['status'], 'stale': L.get('stale_entry_min'),
                             'f_entry': Fu['entry'], 'f_exit': Fu['exit'], 'f_exit_ts': Fu['exit_ts'], 'f_net': Fu['net_rs'], 'f_r': Fu['r'], 'f_status': Fu['status']})
df = pd.DataFrame(rows)
df.to_pickle('legs.pkl')
print(len(df), 'legs from', df.drop_duplicates(['day', 'time', 'symbol']).shape[0], 'signals', df.day.min(), df.day.max())
print(df[df.pol == 'T1'][['symbol', 'kind', 'strike', 'price', 'f_entry', 'expiry', 'o_entry', 'o_exit', 'o_net', 'f_net', 'stale']].head(8).to_string())
print(df.expiry.value_counts().to_dict(), df.lots.describe().to_dict())

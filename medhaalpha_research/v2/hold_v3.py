# Held-across-days and Rs 3 lakh view for Opus v3 over 1 Sep - 13 Nov, from hold rows already computed.
import io, contextlib, json, os, sys
import pandas as pd
sp = sys.argv[1]
src = open(os.path.join(sp, 'tools', 'cap_sim.py')).read()
exec('def sim' + src.split('def sim')[1].split('for m in MS:')[0])
rows = {}
for f in ('hold_sep.json', 'v2/hold_extra_cash.json', 'v2/hold_extra_fut.json', 'v2/hold4.json'):
    for r in json.load(open(os.path.join(sp, f)))['rows']:
        r = dict(r)
        r.setdefault('entry_ts', (pd.Timestamp('%sT%s:00+05:30' % (r['day'], r['time'])) + pd.Timedelta(minutes=1)).isoformat())
        rows[(r['day'], r['symbol'], r['setup'], r['time'])] = r
days = sorted(set(json.load(open(sp + '/hold_sep.json'))['days']) | set(json.load(open(sp + '/v2/hold4.json'))['days']))
NS = len(days)
six = {tuple(k) for k in json.load(open(sp + '/v2/v3_picks.json')) if k[0] >= '2026-09-01' and k[0] <= '2026-10-20'}
rep = {tuple(k) for k in json.load(open(sp + '/v2/v3_picks_replays.json'))}
v3 = six | rep
v2 = {tuple(k) for k in json.load(open(sp + '/v2/split_picks.json'))}
out = {'sessions': NS}
for name, pk in (('v2', v2), ('v3', v3)):
    miss = [k for k in sorted(pk) if k not in rows]
    tr = [rows[k] for k in sorted(pk) if k in rows]
    o = {'n': len(pk), 'missing': len(miss)}
    for pol in ('T1', 'T3'):
        x = [r['res'][pol] for r in tr]
        o['hold_' + pol] = {'net': round(sum(a['net_rs'] for a in x)), 'hit': sum(a['status'] == 'target' for a in x), 'stopped': sum(a['status'] == 'stopped' for a in x), 'open': sum(a['status'] == 'open' for a in x)}
        s = sim(tr, pol, 300000.0, 0.20)
        o['cap_' + pol] = {k: s[k] for k in ('taken', 'skipped', 'net', 'max_dd')}
    out[name] = o
    print(name, 'picks', len(pk), 'missing hold rows', miss, '|', {k: v for k, v in o.items() if k not in ('n', 'missing')})
json.dump(out, open(sp + '/v2/hold_v3.json', 'w'))

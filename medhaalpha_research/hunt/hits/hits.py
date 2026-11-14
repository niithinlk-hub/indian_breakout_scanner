# When each held trade reached T1, T2 and T3 (or the stop), 21 Oct - 13 Nov 2026, from v2/hold4.json: every live-rule pick
# of the five models held across days on its November future (no square-off) until its target or its fixed stop.
# "days" = trading sessions after the entry day (0 = the entry day itself). Open = neither by the 13 Nov close.
import json, sys, statistics as st
import pandas as pd
R = sys.argv[1]                                   # medhaalpha_research folder
H = json.load(open(R + '/v2/hold4.json'))
DOWN = {'2026-10-23', '2026-10-26'}               # Nifty downtrend before the open (prev close < 20-day avg < 50-day avg)
rows = []
for t in H['rows']:
    sw = ('opus_v3' in t['models']) if t['day'] in DOWN else ('fable_op' in t['models'])
    rec = {'day': t['day'], 'time': t['time'], 'symbol': t['symbol'], 'side': t['side'], 'models': t['models'], 'switch1': sw,
           'switch1_exit': ('T1' if t['day'] in DOWN else 'T3') if sw else None}
    for p in ('T1', 'T2', 'T3'):
        o = t['res'][p]
        rec[p] = {'status': o['status'], 'at': o['exit_ts'], 'days': o['sessions'], 'net_rs': o['net_rs']}
    rows.append(rec)
json.dump(rows, open(R + '/hunt/hits/hits.json', 'w'), indent=1)


def stage(r):
    """What the trade reached: T3 / T2 / T1 / stopped before T1 / open."""
    for p in ('T3', 'T2', 'T1'):
        if r[p]['status'] == 'target':
            return p
    return 'stopped before T1' if r['T1']['status'] == 'stopped' else 'still open'


def when(o):
    ts = pd.Timestamp(o['at'])
    d = o['days']
    return '%s, %s %s' % ('same day' if d == 0 else '+%d day%s' % (d, '' if d == 1 else 's'), ts.strftime('%d %b'), ts.strftime('%H:%M'))


print('== Summary per model (picks held until target or stop)')
for m in ('opus', 'opus_v2', 'opus_v3', 'fable', 'fable_op', 'switch1'):
    sel = [r for r in rows if (r['switch1'] if m == 'switch1' else m in r['models'])]
    line = '%-9s n=%3d' % (m, len(sel))
    for p in ('T1', 'T2', 'T3'):
        hit = [r[p]['days'] for r in sel if r[p]['status'] == 'target']
        same = sum(1 for d in hit if d == 0)
        line += ' | %s hit %3d (%2.0f%%) same day %3d, median %.0f days, max %d' % (p, len(hit), 100 * len(hit) / len(sel), same,
                                                                                   st.median(hit) if hit else 0, max(hit) if hit else 0)
    line += ' | stopped before T1 %d, open %d' % (sum(r['T1']['status'] == 'stopped' for r in sel), sum(stage(r) == 'still open' for r in sel))
    print(line)

print('\n== Switch-1 (MedhaSuryan) trades, one per line')
for r in [r for r in rows if r['switch1']]:
    cells = []
    for p in ('T1', 'T2', 'T3'):
        o = r[p]
        cells.append('%s %s' % (p, when(o) if o['status'] == 'target' else ('stop ' + when(o) if o['status'] == 'stopped' else 'open')))
    print('%s %s %-11s %-5s exit %s | reached %-18s | %s' % (r['day'], r['time'], r['symbol'], r['side'], r['switch1_exit'], stage(r), ' | '.join(cells)))

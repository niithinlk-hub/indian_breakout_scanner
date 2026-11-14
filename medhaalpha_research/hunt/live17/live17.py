# The live scanner's 17 sessions, 21 Oct - 13 Nov 2026, replayed at real futures and REAL option prices (v2/opt5.json):
# the five-model table rebuilt, plus Switch-1 (Fable-OP exit T3, except on Downtrend days: Opus v3 exit T1).
import json, sys
import numpy as np, pandas as pd
SP = sys.argv[1]
sys.path.insert(0, SP + '/hunt'); import harness as H
O = json.load(open(SP + '/v2/opt5.json'))
days = O['days']
rg = H.regime()
lab = {d: (rg.loc[d, 'A'] if d in rg.index else None) for d in days}
print('regime per session:', lab)
nd = json.load(open(SP + '/v2/data/nifty_daily.json'))['data']['candles']
print('nifty daily candles up to', max(c[0][:10] for c in nd))


def trades(model):
    out = []
    for r in O['rows']:
        if model == 'switch1':
            m, pol = ('opus_v3', 'T1') if lab[r['day']] == 'Downtrend' else ('fable_op', 'T3')
        else:
            m, pol = model, {'opus': 'T1', 'opus_v2': 'T1', 'opus_v3': 'T1', 'fable': 'T3', 'fable_op': 'T3'}[model]
        if m not in r['models']:
            continue
        out.append({'day': r['day'], 'time': r['time'], 'symbol': r['symbol'], 'side': r['side'], 'pol': pol, 'from': m,
                    'fut': r['fut_same'][pol]['net_rs'], 'fut_status': r['fut_same'][pol]['status'],
                    'opt_same': (r['same'].get(pol) or {}).get('net_rs'), 'opt_held': (r['held'].get(pol) or {}).get('net_rs'),
                    'fut_held': r['fut_held'][pol]['net_rs'], 'outlay': (r['same'].get(pol) or {}).get('outlay')})
    return pd.DataFrame(out)


res = {}
for m in ('opus', 'opus_v2', 'opus_v3', 'fable', 'fable_op', 'switch1'):
    t = trades(m)
    fd = t.groupby('day').fut.sum().reindex(days).fillna(0.0)
    od = t.groupby('day').opt_same.sum(min_count=1).reindex(days).fillna(0.0)
    oh = t.groupby('day').opt_held.sum(min_count=1).reindex(days).fillna(0.0)
    r = {'trades': len(t), 'stopped': int((t.fut_status == 'stopped').sum()), 'stopped_pct': round(100 * (t.fut_status == 'stopped').mean()),
         'fut': round(t.fut.sum()), 'opt_same': round(t.opt_same.fillna(0).sum()), 'opt_held': round(t.opt_held.fillna(0).sum()),
         'unpriced_same': int(t.opt_same.isna().sum()), 'unpriced_held': int(t.opt_held.isna().sum()),
         'fut_held': round(t.fut_held.sum()),
         'fut_days_up': int((fd > 0).sum()), 'fut_days_down': int((fd < 0).sum()), 'fut_worst_day': round(fd.min()),
         'opt_days_down': int((od < 0).sum()), 'opt_worst_day': round(od.min()), 'opt_held_worst_day': round(oh.min()),
         'fut_maxdd': round(float((fd.cumsum() - fd.cumsum().cummax().clip(lower=0)).min())),
         'opt_maxdd': round(float((od.cumsum() - od.cumsum().cummax().clip(lower=0)).min())),
         'longs': int((t.side == 'LONG').sum()), 'from': t['from'].value_counts().to_dict(),
         'by_day_fut': {d: round(v) for d, v in fd.items()}, 'by_day_opt': {d: round(v) for d, v in od.items()},
         'oct': {'fut': round(t[t.day <= '2026-10-31'].fut.sum()), 'opt': round(t[t.day <= '2026-10-31'].opt_same.fillna(0).sum())},
         'nov': {'fut': round(t[t.day > '2026-10-31'].fut.sum()), 'opt': round(t[t.day > '2026-10-31'].opt_same.fillna(0).sum())},
         'nov13': t[t.day == '2026-11-13'][['time', 'symbol', 'side', 'pol', 'fut_status', 'fut', 'opt_same']].round(0).to_dict('records')}
    res[m] = r
    print('%-9s n=%d stop=%d (%d%%) fut=%d opt_same=%d opt_held=%d unpriced=%d/%d fut up/dn=%d/%d worst=%d maxdd=%d | opt dn=%d worst=%d maxdd=%d | from %s' % (
        m, r['trades'], r['stopped'], r['stopped_pct'], r['fut'], r['opt_same'], r['opt_held'], r['unpriced_same'], r['unpriced_held'],
        r['fut_days_up'], r['fut_days_down'], r['fut_worst_day'], r['fut_maxdd'], r['opt_days_down'], r['opt_worst_day'], r['opt_maxdd'], r['from']))
    print('   21-31 Oct fut %+d opt %+d | 2-13 Nov fut %+d opt %+d | 13 Nov %s' % (r['oct']['fut'], r['oct']['opt'], r['nov']['fut'], r['nov']['opt'], r['nov13']))
json.dump({'regime': lab, 'models': res}, open(SP + '/hunt/live17/live17.json', 'w'), indent=1)
print('\nper day (futures / options same day):')
for d in days:
    print('  %s %-10s ' % (d, lab[d]) + ' '.join('%s %+7d/%+7d' % (m[:6], res[m]['by_day_fut'][d], res[m]['by_day_opt'][d]) for m in ('fable', 'fable_op', 'opus_v3', 'switch1')))

# Six-month comparison of the score models on OPTION profit (modelled) and futures profit, month by month.
#   Main period: real, 12 May - 11 Nov 2026, the scanner's own six-month backtest on real futures prices.
#   Check period: unseen, 3 Nov 2025 - 11 May 2026, cash-share stand-in prices.
# Live rule for every model: per day, in time order, the first 6 signals scoring >= 75 (Fable: its score - 5 >= 75, i.e. live cut 80).
import json, os, sys
import numpy as np, pandas as pd
HUNT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HUNT)
import harness as H

OUT = os.path.dirname(os.path.abspath(__file__))
D = H.load_all()
MODELS = {
    'Opus (T1), live model': ('s_opus', 75, 'T1', 6),
    'Opus v2 (T1)': ('s_opus_v2', 75, 'T1', 6),
    'Opus v3 (T1)': ('s_opus_v3', 75, 'T1', 6),
    'Fable (T3)': ('s_fable', 75, 'T3', 6),
    'Fable-OP (T3)': ('s_fable_op', 75, 'T3', 6),
    'Switch-1': H.switch1,
    'Opus v3, trailing stop to close (CLOSE_TR)': ('s_opus_v3', 75, 'CLOSE_TR', 6),
}
SCORES = {'Opus': 's_opus', 'Opus v2': 's_opus_v2', 'Opus v3': 's_opus_v3', 'Fable': 's_fable', 'Fable-OP': 's_fable_op'}


def max_open_premium(t):
    """Most premium tied up at one moment: each option is held from entry to one minute after the futures exit."""
    ev = []
    for r in t.itertuples():
        e0 = pd.Timestamp(r.o_entry_ts)
        x = getattr(r, 'o_exit_ts_' + r.pol) if hasattr(r, 'o_exit_ts_' + r.pol) else None
        x = pd.Timestamp(x) if isinstance(x, str) and x else e0.normalize() + pd.Timedelta(hours=15, minutes=30)
        if x.tzinfo is None:
            x = x.tz_localize(e0.tzinfo)
        x = x + pd.Timedelta(minutes=1)
        ev += [(e0, 1, r.outlay), (x, 0, -r.outlay)]       # exits sort before entries at the same minute
    cur = best = 0.0
    for _, _, v in sorted(ev, key=lambda z: (z[0], z[1])):
        cur += v
        best = max(best, cur)
    return best


def describe(df, spec):
    days = sorted(df.day.unique())
    t = H.run(df, spec)
    # premium outlay per trade, same pricing as the option net
    det = pd.concat([H.option_net(g, p, detail=True) for p, g in t.groupby('pol')]).reindex(t.index)
    assert np.allclose(det['net'].to_numpy(), t['pnl'].to_numpy(), atol=1e-6)
    t['outlay'] = det['outlay'].where(det['qty'] > 0, 0.0)
    byday = t.pnl.groupby(t.day).sum().reindex(days).fillna(0.0)
    fday = t.fut.groupby(t.day).sum().reindex(days).fillna(0.0)
    eq, feq = byday.cumsum(), fday.cumsum()
    months = sorted({d[:7] for d in days})
    mo = t.groupby(t.day.str[:7]).pnl.sum().reindex(months).fillna(0.0)
    mf = t.groupby(t.day.str[:7]).fut.sum().reindex(months).fillna(0.0)
    mn = t.groupby(t.day.str[:7]).size().reindex(months).fillna(0).astype(int)
    lg = t.side == 'LONG'
    prem = float(t.outlay.sum())
    return {
        'trades': len(t), 'trades_per_day': round(len(t) / len(days), 2), 'longs': int(lg.sum()), 'shorts': int((~lg).sum()),
        'opt_net': round(float(t.pnl.sum())), 'fut_net': round(float(t.fut.sum())),
        'opt_long': round(float(t.pnl[lg].sum())), 'opt_short': round(float(t.pnl[~lg].sum())),
        'opt_won_pct': round(100 * float((t.pnl > 0).mean()), 1), 'stopped_pct': round(100 * float(t.stopped.mean()), 1),
        'opt_avg_win': round(float(t.pnl[t.pnl > 0].mean())), 'opt_avg_loss': round(float(t.pnl[t.pnl <= 0].mean())),
        'opt_days_up': int((byday > 0).sum()), 'opt_days_down': int((byday < 0).sum()), 'days_no_trade': int((t.groupby('day').size().reindex(days).fillna(0) == 0).sum()),
        'opt_worst_day': round(float(byday.min())), 'opt_best_day': round(float(byday.max())),
        'opt_max_dd': round(float((eq - eq.cummax().clip(lower=0)).min())),
        'fut_worst_day': round(float(fday.min())), 'fut_max_dd': round(float((feq - feq.cummax().clip(lower=0)).min())),
        'opt_months_up': int((mo > 0).sum()), 'months': len(months),
        'opt_worst_month': [mo.idxmin(), round(float(mo.min()))], 'opt_best_month': [mo.idxmax(), round(float(mo.max()))],
        'premium_total': round(prem), 'premium_avg': round(prem / len(t)) if len(t) else 0,
        'premium_max_open': round(max_open_premium(t)), 'opt_return_on_premium_pct': round(100 * float(t.pnl.sum()) / prem, 1) if prem else 0.0,
        'month_opt': {k: round(float(v)) for k, v in mo.items()}, 'month_fut': {k: round(float(v)) for k, v in mf.items()},
        'month_trades': {k: int(v) for k, v in mn.items()},
        'exit_mix': t.pol.value_counts().to_dict(),
    }


res = {'sessions': {}, 'models': {}, 'grid': {}}
for s in ('real', 'unseen'):
    df = D[s]
    res['sessions'][s] = {'n': int(df.day.nunique()), 'first': df.day.min(), 'last': df.day.max(),
                          'per_month': {k: int(v) for k, v in df.groupby(df.day.str[:7]).day.nunique().items()}}
    res['models'][s] = {name: describe(df, spec) for name, spec in MODELS.items()}
    # model x exit grid, six-month totals
    g = {}
    for mname, col in SCORES.items():
        t = H.pick(df, col, 75, 6)
        g[mname] = {p: {'opt': round(float(t['opt_' + p].sum())), 'fut': round(float(t['net_' + p].sum()))} for p in H.POL}
    res['grid'][s] = g

json.dump(res, open(OUT + '/six_month.json', 'w'), indent=1)

# ---------------------------------------------------------------------------- printout
def L(x):
    """Indian digit grouping with sign."""
    s = '%d' % abs(int(round(x)))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ','.join(parts) + ',' + tail
    return ('-' if x < 0 else '+') + s

for s in ('real', 'unseen'):
    se = res['sessions'][s]
    print('\n==== %s  %s to %s, %d sessions %s' % (s.upper(), se['first'], se['last'], se['n'], se['per_month']))
    for name, r in res['models'][s].items():
        print('\n-- %s' % name)
        print('   trades %d (%.2f/day, %d long, %d short)  OPTION net %s  futures net %s  won %.1f%%  stopped %.1f%%' % (
            r['trades'], r['trades_per_day'], r['longs'], r['shorts'], L(r['opt_net']), L(r['fut_net']), r['opt_won_pct'], r['stopped_pct']))
        print('   option: long %s short %s | avg win %s loss %s | days up/down %d/%d | worst day %s best %s | max DD %s | months up %d/%d' % (
            L(r['opt_long']), L(r['opt_short']), L(r['opt_avg_win']), L(r['opt_avg_loss']), r['opt_days_up'], r['opt_days_down'],
            L(r['opt_worst_day']), L(r['opt_best_day']), L(r['opt_max_dd']), r['opt_months_up'], r['months']))
        print('   premium: avg %s/trade, total %s, most open at once %s, return on premium %.1f%% | futures worst day %s max DD %s' % (
            L(r['premium_avg']), L(r['premium_total']), L(r['premium_max_open']), r['opt_return_on_premium_pct'], L(r['fut_worst_day']), L(r['fut_max_dd'])))
        print('   month option: ' + '  '.join('%s %s (%d)' % (k, L(v), r['month_trades'][k]) for k, v in r['month_opt'].items()))
        print('   month futures: ' + '  '.join('%s %s' % (k, L(v)) for k, v in r['month_fut'].items()))
    print('\n   model x exit, six-month OPTION net (futures in brackets):')
    for m, row in res['grid'][s].items():
        print('   %-9s ' % m + ' '.join('%s %s (%s)' % (p, L(v['opt']), L(v['fut'])) for p, v in row.items()))

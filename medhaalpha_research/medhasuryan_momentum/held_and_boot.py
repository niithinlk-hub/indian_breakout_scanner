# Held-across-days backtest (heldsim.py) of MedhaSuryan, Fable-OP, Opus v3 and the four MedhaSuryan-M settings, plus a
# day-resampled bootstrap of "MedhaSuryan-M beats MedhaSuryan" on same-day options, same-day futures and held futures.
# Arg 1 = medhaalpha_research folder; arg 2 = output json.
import json, os, sys
import numpy as np, pandas as pd
RP, OUT = sys.argv[1], sys.argv[2]
os.environ['MEDHA_SP'] = RP
sys.path.insert(0, RP + '/hunt'); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as H, heldsim as HS, momscore as M
from sameday_defs import SETTINGS, make

D = H.load_all()
DT = HS.Data(RP)
MODELS = {'Opus v3 (T1)': lambda df: H.pick(df, 's_opus_v3', 75).assign(pol='T1'),
          'Fable-OP (T3)': lambda df: H.pick(df, 's_fable_op', 75).assign(pol='T3'),
          'MedhaSuryan': H.switch1}
MODELS.update({k: make(*v) for k, v in SETTINGS.items()})
SLICES = {'design 12 May-31 Aug 2026': ('real', '2026-05-12', '2026-08-31'),
          'test 1 Sep-11 Nov 2026': ('real', '2026-09-01', '2026-11-11'),
          'test 3 Nov 2025-11 May 2026': ('unseen', '2025-11-03', '2026-05-11'),
          'all 12 May-11 Nov 2026': ('real', '2026-05-12', '2026-11-11')}
cache = {}


def held(s, df, t):
    out = []
    for i, pol in zip(t.index, t.pol):
        if (s, i) not in cache:
            cache[(s, i)] = HS.held_trade(DT, df.loc[i], s)
        g = cache[(s, i)]
        out.append(None if g is None else dict(g[pol], hit={p: g[p]['status'] == 'target' for p in ('T1', 'T2', 'T3')}))
    return out


res = {}
rng = np.random.default_rng(20261116)
for name, (s, lo, hi) in SLICES.items():
    df = D[s]
    d = df[(df.day >= lo) & (df.day <= hi)]
    days = sorted(d.day.unique())
    res[name] = {'sessions': len(days), 'models': {}}
    byday = {}
    for mname, f in MODELS.items():
        t = H.run(d, f)
        hh = held(s, d, t)
        ok = [x for x in hh if x]
        hnet = np.array([x['net'] if x else 0.0 for x in hh])
        r = H.stats(t, days)
        r.update({'held': round(float(hnet.sum())), 'priced': len(ok),
                  'held_T1%': round(100 * np.mean([x['hit']['T1'] for x in ok]), 1) if ok else 0,
                  'held_T2%': round(100 * np.mean([x['hit']['T2'] for x in ok]), 1) if ok else 0,
                  'held_T3%': round(100 * np.mean([x['hit']['T3'] for x in ok]), 1) if ok else 0,
                  'held_stopped%': round(100 * np.mean([x['status'] == 'stopped' for x in ok]), 1) if ok else 0,
                  'held_median_days': float(np.median([x['days'] for x in ok])) if ok else None})
        hb = pd.Series(hnet, index=t.day.values).groupby(level=0).sum().reindex(days).fillna(0.0)
        eq = hb.cumsum()
        r['held_maxdd_by_entry_day'] = round(float((eq - eq.cummax().clip(lower=0)).min()))
        res[name]['models'][mname] = r
        byday[mname] = {'opt': t.pnl.groupby(t.day).sum().reindex(days).fillna(0.0).to_numpy(),
                        'fut': t.fut.groupby(t.day).sum().reindex(days).fillna(0.0).to_numpy(), 'held': hb.to_numpy()}
    # bootstrap: resample the sessions with replacement, 5,000 times
    idx = rng.integers(0, len(days), size=(5000, len(days)))
    boot = {}
    for k in SETTINGS:
        boot[k] = {m: round(100 * float(np.mean(byday[k][m][idx].sum(1) > byday['MedhaSuryan'][m][idx].sum(1))), 1) for m in ('opt', 'fut', 'held')}
    res[name]['boot_beats_medhasuryan_pct'] = boot
    print('\n== %s (%d sessions)' % (name, len(days)))
    print('  %-20s %5s %10s %10s %10s %9s %9s | %6s %6s %6s %6s | P(beat MS) opt/fut/held' % ('model', 'n', 'options', 'futures', 'held', 'worst day', 'max DD', 'T1%', 'T2%', 'T3%', 'stop%'))
    for mname, r in res[name]['models'].items():
        b = boot.get(mname)
        print('  %-20s %5d %+10d %+10d %+10d %+9d %+9d | %6.1f %6.1f %6.1f %6.1f | %s' % (mname[:20], r['n'], r['net'], r['fut'], r['held'], r['worst_day'], r['maxdd'],
              r['held_T1%'], r['held_T2%'], r['held_T3%'], r['held_stopped%'], ('%5.1f %5.1f %5.1f' % (b['opt'], b['fut'], b['held'])) if b else ''))
json.dump(res, open(OUT, 'w'), indent=1)

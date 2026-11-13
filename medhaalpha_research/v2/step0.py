import sys
sys.path.insert(0, sys.argv[1] + '/v2')
from base import *
# 1. does classify() reproduce the report's own hit / stopped counts?
bad = 0
allr = rows()
by = {}
for r in allr:
    by.setdefault(r['day'], []).append(r)
for s in SIX['summary']:
    a = s['models']['opus']['all']
    mine = by.get(s['day'], [])
    if (len(mine), sum(x['out'] == 'hit' for x in mine), sum(x['out'] == 'stop' for x in mine)) != (a['n'], a['t1_hit'], a['t1_stopped']):
        bad += 1
print('days where my hit/stop classification differs from the report:', bad, 'of', len(SIX['summary']), '| signals A+B', len(allr))
for name, (lo, hi) in (('DESIGN 12 May-31 Aug', DESIGN), ('UNSEEN 1 Sep-11 Nov', UNSEEN)):
    rs = rows(lo, hi)
    nd = len({r['day'] for r in rs})
    print('\n==', name, '| sessions', nd, '| signals', len(rs), '| all-signal hit%% %.1f stop%% %.1f' % (100 * sum(r['out'] == 'hit' for r in rs) / len(rs), 100 * sum(r['out'] == 'stop' for r in rs) / len(rs)))
    for m, thr in (('opus', 75), ('fable', 80), ('fable_op', 75)):
        print(fmt('%s >= %d (as live)' % (m, thr), stats(live(rs, lambda r, m=m: r[m], thr))))
    if name.startswith('DESIGN'):
        for m in ('opus', 'fable_op'):
            for thr in (60, 65, 68, 70, 72, 75, 78, 80, 85):
                print(fmt('   %s >= %d' % (m, thr), stats(live(rs, lambda r, m=m: r[m], thr))))

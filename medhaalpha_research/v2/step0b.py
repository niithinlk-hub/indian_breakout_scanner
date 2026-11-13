import sys
sys.path.insert(0, sys.argv[1] + '/v2')
from base import *
rs = rows(*DESIGN)
target = len(live(rs, lambda r: r['opus'], 75))


def thr_for(score, target):
    """Lowest threshold (0.5 steps) whose live selection has at most `target` trades."""
    best = None
    for t10 in range(400, 1000, 5):
        t = t10 / 10
        n = len(live(rs, score, t))
        if n <= target:
            return t, n
    return None, 0


res = []
for a in range(0, 11, 2):
    for b in range(0, 11 - a, 2):
        c = 10 - a - b
        sc = lambda r, a=a, b=b, c=c: (a * r['opus'] + b * r['fable'] + c * r['fable_op']) / 10
        t, n = thr_for(sc, target)
        tr = live(rs, sc, t)
        s = stats(tr)
        months = []
        for mo in ('2026-05', '2026-06', '2026-07', '2026-08'):
            mt = [x for x in tr if x['day'].startswith(mo)]
            months.append('%d%%/%+dk' % (100 * sum(x['out'] == 'hit' for x in mt) / max(1, len(mt)), sum(x['net'][PI['T1']] for x in mt) / 1000))
        res.append((s['T1'], 'opus %.1f fable %.1f fop %.1f thr %.1f' % (a / 10, b / 10, c / 10, t), s, months))
for _, name, s, months in sorted(res, key=lambda x: -x[2]['hit%']):
    print(fmt(name, s)[:118], '| by month', ' '.join(months))

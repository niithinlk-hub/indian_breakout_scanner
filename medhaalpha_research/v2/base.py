# Shared loader for the Opus-v2 work: the scanner's own six-month per-signal file (real contract months).
import json, os
# Root of the research folder: the parent of this v2/ directory, unless MEDHA_RESEARCH points elsewhere.
SP = os.environ.get('MEDHA_RESEARCH', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_d = json.load(open(SP + '/six/pull.json'))
SIX, SIG = _d['six'], _d['sig']
MI = {m: i for i, m in enumerate(SIG['models'])}
PI = {p: i for i, p in enumerate(SIG['policies'])}
DESIGN = ('2026-05-12', '2026-08-31')      # where anything may be fitted
UNSEEN = ('2026-09-01', '2026-11-11')      # looked at only to check a finished candidate
DAYS = [x['day'] for x in SIG['days']]


def classify(r):
    """T1 outcome from the per-policy R values: 'hit', 'stop' or 'close' (squared off at the close)."""
    r1, r2, r3, rc = r[PI['T1']], r[PI['T2']], r[PI['T3']], r[PI['CLOSE']]
    if r1 == r2 == r3 == rc:
        return 'stop' if r1 <= -0.999 else 'hit' if r1 >= 0.97 else 'close'
    return 'hit'


def rows(lo=None, hi=None, setups=('A', 'B')):
    out = []
    for x in SIG['days']:
        if (lo and x['day'] < lo) or (hi and x['day'] > hi):
            continue
        for s in x['signals']:
            if s[2] in setups and s[4][PI['T1']] is not None:
                out.append({'day': x['day'], 'time': s[0], 'symbol': s[1], 'setup': s[2], 'opus': s[3][MI['opus']], 'fable': s[3][MI['fable']],
                            'fable_op': s[3][MI['fable_op']], 'net': s[4], 'r': s[5], 'out': classify(s[5])})
    return out


def live(rs, score, thr, n=6):
    """The live rule: per day, in time order (ties: higher score, then symbol), the first n scoring >= thr."""
    out, byday = [], {}
    for r in rs:
        byday.setdefault(r['day'], []).append(r)
    for day in sorted(byday):
        k = 0
        for r in sorted(byday[day], key=lambda r: (r['time'], -score(r), r['symbol'])):
            if score(r) >= thr and k < n:
                out.append(r)
                k += 1
    return out


def stats(tr, ndays=None):
    n = len(tr)
    hit, stop = sum(t['out'] == 'hit' for t in tr), sum(t['out'] == 'stop' for t in tr)
    byday = {}
    for t in tr:
        byday[t['day']] = byday.get(t['day'], 0.0) + t['net'][PI['T1']]
    eq = pk = dd = 0.0
    for d in sorted(byday):
        eq += byday[d]; pk = max(pk, eq); dd = min(dd, eq - pk)
    return {'n': n, 'hit': hit, 'stop': stop, 'hit%': round(100 * hit / n, 1) if n else 0, 'stop%': round(100 * stop / n, 1) if n else 0,
            'won%': round(100 * sum(t['net'][PI['T1']] > 0 for t in tr) / n, 1) if n else 0,
            'T1': round(sum(t['net'][PI['T1']] for t in tr)), 'T2': round(sum(t['net'][PI['T2']] for t in tr)), 'T3': round(sum(t['net'][PI['T3']] for t in tr)),
            'per': round(sum(t['net'][PI['T1']] for t in tr) / n) if n else 0, 'R': round(sum(t['r'][PI['T1']] for t in tr), 1),
            'days_up': sum(v > 0 for v in byday.values()), 'days_dn': sum(v < 0 for v in byday.values()), 'maxdd': round(dd), 'longs': sum(t['setup'] == 'A' for t in tr)}


def fmt(name, s):
    return '%-34s n=%3d hit %5.1f%% stop %5.1f%% won %5.1f%% | T1 %+8d (%+5d/trade, R %+6.1f) T2 %+8d T3 %+8d | days +%d/-%d maxDD %+7d longs %d' % (
        name, s['n'], s['hit%'], s['stop%'], s['won%'], s['T1'], s['per'], s['R'], s['T2'], s['T3'], s['days_up'], s['days_dn'], s['maxdd'], s['longs'])

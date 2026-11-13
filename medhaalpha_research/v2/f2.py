# Do the two effects hold in the wider pool (not just v2's picks)? Longs with Fable-OP >= 65, shorts with Opus >= 65, six months.
import sys, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, sys.argv[1] + '/v2')
import numpy as np, pandas as pd
from frame import load
df = load()
A = df[df.design | df.unseen].copy()
A['half'] = np.where(A.design, 'H1', 'H2')


def tab(g, col, bins, labels):
    g = g.assign(_b=pd.cut(g[col], bins, labels=labels))
    out = []
    for b, x in g.groupby('_b', observed=True):
        out.append('%s n%d hit %.0f stop %.0f net/trade %+.0f' % (b, len(x), 100 * x.hit.mean(), 100 * x['stop'].mean(), x.net1.mean()))
    return ' | '.join(out)


L = A[(A.long == 1) & (A.t_fable_op >= 65)]
print('LONGS with Fable-OP >= 65: n=%d' % len(L))
for lab, g in (('all', L), ('H1', L[L.half == 'H1']), ('H2', L[L.half == 'H2']), ('FOP 65-75', L[L.t_fable_op < 75]), ('FOP >= 75', L[L.t_fable_op >= 75])):
    print('  rel_vol   %-9s %s' % (lab, tab(g, 'rel_vol', [-1, 1, 1.5, 2.5, 4, 1e9], ['<1', '1-1.5', '1.5-2.5', '2.5-4', '4+'])))
for mo, g in L.groupby('month'):
    print('  rel_vol   %-9s %s' % (mo, tab(g, 'rel_vol', [-1, 2, 1e9], ['<2', '2+'])))
for lab, g in (('all', L), ('H1', L[L.half == 'H1']), ('H2', L[L.half == 'H2'])):
    print('  ext52     %-9s %s' % (lab, tab(g, 'ext52', [-1e9, -20, -10, -5, 1e9], ['>20% off', '10-20', '5-10', '<5% off'])))
for lab, g in (('all', L), ('H1', L[L.half == 'H1']), ('H2', L[L.half == 'H2'])):
    print('  atr_pct   %-9s %s' % (lab, tab(g, 'atr_pct', [0, 2.0, 2.5, 3.0, 1e9], ['<2', '2-2.5', '2.5-3', '3+'])))
S = A[(A.long == 0) & (A.t_opus >= 65)]
print('\nSHORTS with Opus >= 65: n=%d' % len(S))
for lab, g in (('all', S), ('H1', S[S.half == 'H1']), ('H2', S[S.half == 'H2']), ('Opus 65-75', S[S.t_opus < 75]), ('Opus >= 75', S[S.t_opus >= 75])):
    print('  nifty down %-10s %s' % (lab, tab(g, 'nifty_dir', [-9, 0.35, 0.5, 0.75, 1.0, 9], ['<0.35', '0.35-0.5', '0.5-0.75', '0.75-1', '1+'])))
for mo, g in S.groupby('month'):
    print('  nifty down %-10s %s' % (mo, tab(g, 'nifty_dir', [-9, 0.5, 9], ['<0.5', '0.5+'])))
for lab, g in (('all', S), ('H1', S[S.half == 'H1']), ('H2', S[S.half == 'H2'])):
    print('  rel_vol    %-10s %s' % (lab, tab(g, 'rel_vol', [-1, 1, 1.5, 2.5, 1e9], ['<1', '1-1.5', '1.5-2.5', '2.5+'])))
for lab, g in (('all', S), ('H1', S[S.half == 'H1']), ('H2', S[S.half == 'H2'])):
    print('  time       %-10s %s' % (lab, tab(g, 'minutes_since_open', [0, 15, 45, 105, 165, 400], ['-09:30', '-10:00', '-11:00', '-12:00', '12:00+'])))
print('\nnifty_dir check for shorts: min %.2f (setup B needs Nifty down at least 0.25)' % S.nifty_dir.min(), '| share below 0.25: %.1f%%' % (100 * (S.nifty_dir < 0.25).mean()))

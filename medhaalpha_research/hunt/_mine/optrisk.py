import harness as H
D = H.load_all()
C = {}
for pol in ('T1', 'T3', 'T3_TR', 'CLOSE', 'CLOSE_TR'):
    C['v3 ATM ' + pol] = ('s_opus_v3', 75, pol, 6)
for pol in ('T3', 'T3_TR', 'CLOSE', 'CLOSE_TR'):
    C['FOP ATM ' + pol] = ('s_fable_op', 75, pol, 6)
H.show(H.evaluate(D, C))

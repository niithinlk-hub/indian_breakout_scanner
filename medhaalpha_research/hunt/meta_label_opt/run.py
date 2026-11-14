"""meta_label_opt: meta-labelling for option profit (pre-registered test).

Primary model = every A/B signal (high recall). Secondary model predicts whether the OPTION trade pays
(y = 1[opt_T3 > 0], or 1[opt_T1 > 0] for setting b) from the 20 COMMON features (minus price), side, both scores,
the day's Nifty regime (one-hot) and r20, crowd counts so far today, and days to expiry. Trained on the real design
window only (12 May - 31 Aug 2026). OOF p from GroupKFold(5) by day, Platt calibration on OOF, final refit on all
design rows applied to every other row. Gate = design OOF quantile at the baseline's design selection rate.
Trades = H.pick(df, p, thr, 6).

Grid (choose on design OOF by option net, risk-constrained):
  a GBDT y=opt_T3>0 gate 5.97 % exit T3     b GBDT y=opt_T1>0 gate 8.23 % exit T1
  c per-side logistic on [s_opus, s_fable_op, product] y=opt_T3>0 gate 5.97 % exit T3     d as a, gate 9.0 %
"""
import json, os, sys
import numpy as np
import pandas as pd

SP = '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
OUT = SP + '/hunt/meta_label_opt'
sys.path.insert(0, SP + '/hunt')
import harness as H  # noqa: E402

import lightgbm as lgb  # noqa: E402
from sklearn.calibration import _SigmoidCalibration  # noqa: E402  (Platt, as CalibratedClassifierCV(method='sigmoid'))
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402
from sklearn.model_selection import GroupKFold  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

D_LO, D_HI = '2026-05-12', '2026-08-31'
REGS = ['Uptrend', 'Downtrend', 'Sideways']
BASE_FEATS = [c for c in H.COMMON if c != 'price']
assert len(BASE_FEATS) == 20
FEATS = BASE_FEATS + ['side_long', 's_opus', 's_fable_op'] + ['reg_' + r for r in REGS] + ['r20', 'n_same_so_far', 'n_opp_so_far',
                                                                                         'n_same_minute', 'dte']
MONO = [1 if f in ('s_opus', 's_fable_op') else 0 for f in FEATS]


def add_features(d):
    R = H.regime()
    d['side_long'] = (d['side'] == 'LONG').astype(float)
    reg = d['day'].map(R['A'])
    for r in REGS:
        d['reg_' + r] = (reg == r).astype(float)
    d['r20'] = d['day'].map(R['r20']).astype(float)
    # crowd so far today: rows of the same day with strictly earlier time (all rows are A/B signals)
    t = d['time']
    n_same, n_opp = np.zeros(len(d)), np.zeros(len(d))
    for (day, side), g in d.groupby(['day', 'side']):
        # count same-side rows that day with time < this row's time
        tt = np.sort(g['time'].to_numpy())
        n_same[d.index.get_indexer(g.index)] = np.searchsorted(tt, g['time'].to_numpy(), side='left')
    for day, g in d.groupby('day'):
        for side in ('LONG', 'SHORT'):
            mine = g[g.side == side]
            other = np.sort(g[g.side != side]['time'].to_numpy())
            n_opp[d.index.get_indexer(mine.index)] = np.searchsorted(other, mine['time'].to_numpy(), side='left')
    d['n_same_so_far'] = n_same
    d['n_opp_so_far'] = n_opp
    d['n_same_minute'] = d.groupby(['day', 'time'])['symbol'].transform('size').astype(float) - 1.0
    d['dte'] = (pd.to_datetime(d['o_expiry']) - pd.to_datetime(d['day'])).dt.days.astype(float)
    return d


def gbdt():
    return lgb.LGBMClassifier(num_leaves=7, max_depth=3, min_child_samples=80, learning_rate=0.03, n_estimators=300, subsample=0.7,
                              subsample_freq=1, colsample_bytree=0.7, reg_lambda=10, path_smooth=20, monotone_constraints=MONO,
                              random_state=0, n_jobs=2, verbose=-1, deterministic=True, force_row_wise=True)


LR_FEATS = ['s_opus', 's_fable_op', 'sxs']


def lr_X(d):
    return np.column_stack([d['s_opus'].to_numpy(float), d['s_fable_op'].to_numpy(float), (d['s_opus'] * d['s_fable_op']).to_numpy(float)])


def lr():
    return make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))


def fit_gbdt_model(des, y, folds, others):
    """Returns OOF calibrated p on design rows, calibrated p on each frame in `others`, OOF raw, and the final model."""
    X = des[FEATS]
    raw = np.full(len(des), np.nan)
    for tr, te in folds:
        m = gbdt().fit(X.iloc[tr], y[tr])
        raw[te] = m.predict_proba(X.iloc[te])[:, 1]       # LGBM has no decision_function -> predict_proba (as CalibratedClassifierCV)
    cal = _SigmoidCalibration().fit(raw, y)
    p_oof = cal.predict(raw)
    final = gbdt().fit(X, y)
    raw_oth = {k: pd.Series(final.predict_proba(o[FEATS])[:, 1], index=o.index) for k, o in others.items()}
    p_oth = {k: pd.Series(cal.predict(v.to_numpy()), index=v.index) for k, v in raw_oth.items()}
    return pd.Series(p_oof, index=des.index), p_oth, raw, final, cal, raw_oth


def fit_lr_model(des, y, folds, others):
    """Per side logistic stacker; Platt calibration per side on that side's OOF decision function."""
    y = pd.Series(y, index=des.index)
    raw = pd.Series(np.nan, index=des.index)
    for tr, te in folds:
        dtr, dte_ = des.iloc[tr], des.iloc[te]
        for side in ('LONG', 'SHORT'):
            a, b = dtr[dtr.side == side], dte_[dte_.side == side]
            m = lr().fit(lr_X(a), y.loc[a.index])
            raw.loc[b.index] = m.decision_function(lr_X(b))
    p_oof = pd.Series(np.nan, index=des.index)
    p_oth = {k: pd.Series(np.nan, index=o.index) for k, o in others.items()}
    coefs, cals = {}, {}
    for side in ('LONG', 'SHORT'):
        ms = des.side == side
        cal = _SigmoidCalibration().fit(raw[ms].to_numpy(), y[ms].to_numpy())
        cals[side] = cal
        p_oof[ms] = cal.predict(raw[ms].to_numpy())
        final = lr().fit(lr_X(des[ms]), y[ms])
        coefs[side] = [round(float(c), 4) for c in final[-1].coef_[0]] + [round(float(final[-1].intercept_[0]), 4)]
        for k, o in others.items():
            mo = o.side == side
            if mo.any():
                p_oth[k][mo] = cal.predict(final.decision_function(lr_X(o[mo])))
    return p_oof, p_oth, raw.to_numpy(), coefs, cals


def gate(p_oof, rate):
    """thr such that the share of design rows with p >= thr equals `rate` (k = round(rate * N) highest)."""
    k = int(round(rate * len(p_oof)))
    s = np.sort(np.asarray(p_oof))[::-1]
    return float(s[k - 1]), k


def main():
    pd.set_option('display.width', 200)
    D = H.load_all()
    for s in H.SETS:
        D[s] = add_features(D[s])
    real = D['real']
    is_des = (real.day >= D_LO) & (real.day <= D_HI)
    des = real[is_des].copy()
    print('design rows %d, days %d (expected 2,746 / 78)' % (len(des), des.day.nunique()))
    print('features (%d): %s' % (len(FEATS), FEATS))
    print('design corr(s_opus, s_fable_op) = %.3f' % des[['s_opus', 's_fable_op']].corr().iloc[0, 1])
    base_rate_fop = float((des.s_fable_op >= 75).mean())
    base_rate_v3 = float((des.s_opus_v3 >= 75).mean())
    print('baseline design selection rates (pre-cap): s_fable_op>=75 %.4f, s_opus_v3>=75 %.4f' % (base_rate_fop, base_rate_v3))

    folds = list(GroupKFold(n_splits=5).split(des, groups=des['day']))
    others = {'real_h2': real[~is_des], 'unseen': D['unseen'], 'known': D['known']}
    y3 = (des['opt_T3'] > 0).astype(int).to_numpy()
    y1 = (des['opt_T1'] > 0).astype(int).to_numpy()
    print('label base rates on design: opt_T3>0 %.3f, opt_T1>0 %.3f' % (y3.mean(), y1.mean()))

    models = {}
    pa_oof, pa_oth, ra, fa, cala, rawa_oth = fit_gbdt_model(des, y3, folds, others)
    models['gbdt_T3'] = (pa_oof, pa_oth, y3)
    pb_oof, pb_oth, rb, fb, calb, rawb_oth = fit_gbdt_model(des, y1, folds, others)
    models['gbdt_T1'] = (pb_oof, pb_oth, y1)
    pc_oof, pc_oth, rc, coefs, calc = fit_lr_model(des, y3, folds, others)
    models['lr_T3'] = (pc_oof, pc_oth, y3)

    # Platt maps: p = expit(-(a*f + b)); a < 0 = increasing in the raw output, a > 0 = DECREASING (ranking inverted)
    print('\nPlatt calibration fitted on OOF raw output (p = expit(-(a*f+b)); a<0 keeps the ranking, a>0 INVERTS it):')
    lgm = (des.side == 'LONG').to_numpy()
    platt = {}
    for k, cal, rr, yy in [('gbdt_T3', cala, ra, y3), ('gbdt_T1', calb, rb, y1)]:
        platt[k] = {'a': float(cal.a_), 'b': float(cal.b_), 'raw_oof_auc': float(roc_auc_score(yy, rr))}
        print('  %-8s a %+.4f b %+.4f | raw OOF AUC %.4f | per fold raw AUC %s | %s' % (k, cal.a_, cal.b_, roc_auc_score(yy, rr),
              ' '.join('%.3f' % roc_auc_score(yy[te], rr[te]) for _, te in folds), 'INVERTED' if cal.a_ > 0 else 'kept'))
    for side, cal in calc.items():
        m = lgm if side == 'LONG' else ~lgm
        platt['lr_T3_' + side] = {'a': float(cal.a_), 'b': float(cal.b_), 'raw_oof_auc': float(roc_auc_score(y3[m], rc[m]))}
        print('  lr_T3 %-5s a %+.4f b %+.4f | raw OOF AUC %.4f | %s' % (side, cal.a_, cal.b_, roc_auc_score(y3[m], rc[m]), 'INVERTED' if cal.a_ > 0 else 'kept'))

    print('\nOOF design AUC (calibrated p; label of the model):')
    auc = {}
    for k, (po, _, yy) in models.items():
        auc[k] = float(roc_auc_score(yy, po))
        lg = (des.side == 'LONG').to_numpy()
        print('  %-8s all %.4f | longs %.4f | shorts %.4f' % (k, auc[k], roc_auc_score(yy[lg], po[lg]), roc_auc_score(yy[~lg], po[~lg])))
    # reference AUCs of the raw scores against the same labels
    for sc in ('s_opus', 's_fable_op', 's_opus_v3'):
        print('  ref %-10s vs opt_T3>0 %.4f | vs opt_T1>0 %.4f' % (sc, roc_auc_score(y3, des[sc]), roc_auc_score(y1, des[sc])))
    print('  logistic stacker final coefs [s_opus, s_fable_op, product, intercept] (standardised):', coefs)
    imp = pd.Series(fa.booster_.feature_importance('gain'), index=FEATS).sort_values(ascending=False)
    print('  gbdt_T3 final-model gain importance (top 12):', ', '.join('%s %.0f' % (i, v) for i, v in imp.head(12).items()))
    imp_b = pd.Series(fb.booster_.feature_importance('gain'), index=FEATS).sort_values(ascending=False)
    print('  gbdt_T1 final-model gain importance (top 12):', ', '.join('%s %.0f' % (i, v) for i, v in imp_b.head(12).items()))

    # write p columns: design rows = OOF p (never in-sample), every other row = final model
    col = {'gbdt_T3': 'p_meta_T3', 'gbdt_T1': 'p_meta_T1', 'lr_T3': 'p_lr_T3'}
    for k, (po, poth, _) in models.items():
        c = col[k]
        real[c] = np.nan
        real.loc[po.index, c] = po.values
        real.loc[poth['real_h2'].index, c] = poth['real_h2'].values
        D['unseen'][c] = poth['unseen'].values
        D['known'][c] = poth['known'].values
    assert real[list(col.values())].notna().all().all()

    RATE = {'a': 0.0597, 'b': 0.0823, 'c': 0.0597, 'd': 0.090}
    SETTING = {'a': ('gbdt_T3', 'T3'), 'b': ('gbdt_T1', 'T1'), 'c': ('lr_T3', 'T3'), 'd': ('gbdt_T3', 'T3')}
    NAME = {'a': 'meta a GBDT T3 g5.97', 'b': 'meta b GBDT T1 g8.23', 'c': 'meta c LR T3 g5.97', 'd': 'meta d GBDT T3 g9.0'}
    specs, thr = {}, {}
    for s, (m, pol) in SETTING.items():
        thr[s], k = gate(models[m][0].to_numpy(), RATE[s])
        specs[s] = (col[m], thr[s], pol, 6)
        print('setting %s: model %s exit %s gate %.2f %% -> top %d design rows, thr p >= %.5f' % (s, m, pol, 100 * RATE[s], k, thr[s]))

    # ---------------------------------------------------------------- design-window choice (OOF p only)
    ddays = sorted(des.day.unique())
    dD = real[is_des]
    print('\n== DESIGN WINDOW (real %s to %s, %d days), OOF p | OPTION net (modelled)' % (D_LO, D_HI, len(ddays)))
    hdr = '  %-24s %5s %10s %8s %7s %10s %10s | %10s' % ('model', 'n', 'opt net', '/trade', 'd+/d-', 'worst day', 'max DD', 'futures')
    print(hdr)
    design = {}
    for name, spec in list(H.BASE.items()) + [(NAME[s], specs[s]) for s in 'abcd']:
        st = H.stats(H.run(dD, spec), ddays)
        design[name] = st
        print('  %-24s %5d %+10d %+8d %3d/%-3d %+10d %+10d | %+10d' % (name, st['n'], st['net'], st['per_trade'], st['days_up'], st['days_dn'],
                                                                       st['worst_day'], st['maxdd'], st['fut']))
    b1, b2 = design['Opus v3 (T1)'], design['Fable-OP (T3)']
    wd_lim = 1.25 * max(b1['worst_day'], b2['worst_day'])      # better (less negative) baseline, per metric
    dd_lim = 1.25 * max(b1['maxdd'], b2['maxdd'])
    print('  risk limits (1.25x the better design baseline, per metric): worst day >= %+d, max DD >= %+d' % (wd_lim, dd_lim))
    ok = {s: design[NAME[s]]['worst_day'] >= wd_lim and design[NAME[s]]['maxdd'] >= dd_lim for s in 'abcd'}
    for s in 'abcd':
        print('  setting %s: design opt net %+d, risk ok %s' % (s, design[NAME[s]]['net'], ok[s]))
    pool = [s for s in 'abcd' if ok[s]]
    flagged = not pool
    if flagged:
        pool = list('abcd')
    choice = max(pool, key=lambda s: design[NAME[s]]['net'])
    print('  CHOICE: setting %s (%s)%s' % (choice, NAME[choice], '  [FLAGGED: no setting met the design risk limits; highest net taken]' if flagged else ''))

    # ---------------------------------------------------------------- held-out comparison
    cand_name = 'META %s (chosen)' % choice
    print('\n######## Candidate vs baselines on every set (real h1 = design window scored with OOF p; known shares design dates = contaminated)')
    res = H.compare(D, {cand_name: specs[choice]})

    print('\n######## All four grid settings on every set (for transparency; the choice above used the design window only)')
    res_all = H.evaluate(D, {NAME[s]: specs[s] for s in 'abcd'}, with_base=False)
    H.show(res_all)

    # realised selection rates
    print('\nRealised selection rate per set (rows with p >= thr / all rows; trades after 6/day cap / all rows):')
    rates = {}
    for s in 'abcd':
        c, t = specs[s][0], specs[s][1]
        rates[s] = {}
        for k, d in [('design', dD), ('real_h2', real[~is_des]), ('unseen', D['unseen']), ('known', D['known'])]:
            gate_rate = float((d[c] >= t).mean())
            tr = len(H.pick(d, c, t, 6)) / len(d)
            rates[s][k] = {'gate': round(gate_rate, 4), 'traded': round(tr, 4)}
        print('  %s: ' % s + ' | '.join('%s %.2f%% / %.2f%%' % (k, 100 * v['gate'], 100 * v['traded']) for k, v in rates[s].items()))
    brates = {}
    for nm, sc in [('Fable-OP>=75', 's_fable_op'), ('Opus v3>=75', 's_opus_v3')]:
        brates[nm] = {k: round(float((d[sc] >= 75).mean()), 4) for k, d in [('design', dD), ('real_h2', real[~is_des]), ('unseen', D['unseen']), ('known', D['known'])]}
        print('  baseline %s gate rate: ' % nm + ' | '.join('%s %.2f%%' % (k, 100 * v) for k, v in brates[nm].items()))

    # calibration shift check: mean p and label rate by set
    print('\nCalibration check (mean calibrated p vs realised label rate; label = the model\'s own):')
    for k, (po, poth, yy) in models.items():
        lab = 'opt_T1' if k == 'gbdt_T1' else 'opt_T3'
        parts = ['design OOF p %.3f / y %.3f' % (po.mean(), yy.mean())]
        for sk in ('real_h2', 'unseen', 'known'):
            o = others[sk]
            parts.append('%s p %.3f / y %.3f' % (sk, poth[sk].mean(), (o[lab] > 0).mean()))
        print('  %-8s ' % k + ' | '.join(parts))
    # AUC on held-out sets (diagnostic only)
    print('Held-out AUC (diagnostic): ' + ' | '.join('%s %s' % (k, ' '.join('%s %.3f' % (sk, roc_auc_score((others[sk]['opt_T1' if k == 'gbdt_T1' else 'opt_T3'] > 0).astype(int), poth[sk]))
                                                                             for sk in ('real_h2', 'unseen', 'known'))) for k, (po, poth, yy) in models.items()))

    # verdict vs the bar
    def g(set_, name, part='all'):
        return res[set_][name][part]
    cu, ch = g('unseen', cand_name), g('real', cand_name, 'h2')
    beats_u = cu['net'] > g('unseen', 'Opus v3 (T1)')['net'] and cu['net'] > g('unseen', 'Fable-OP (T3)')['net']
    beats_h2 = ch['net'] > g('real', 'Opus v3 (T1)', 'h2')['net'] and ch['net'] > g('real', 'Fable-OP (T3)', 'h2')['net']
    beats_s1 = cu['net'] > g('unseen', 'Switch-1')['net'] and ch['net'] > g('real', 'Switch-1', 'h2')['net']

    def risk_ok(set_, part):
        c = g(set_, cand_name, part)
        b = [g(set_, 'Opus v3 (T1)', part), g(set_, 'Fable-OP (T3)', part)]
        return c['worst_day'] >= 1.25 * max(x['worst_day'] for x in b) and c['maxdd'] >= 1.25 * max(x['maxdd'] for x in b)
    rok = risk_ok('unseen', 'all') and risk_ok('real', 'h2')
    print('\nVERDICT (option net): beats both on unseen %s | beats both on real 2nd half %s | beats Switch-1 on both %s | risk ok (unseen & real h2) %s'
          % (beats_u, beats_h2, beats_s1, rok))

    # ---------------------------------------------------------------- EXPLORATORY (not pre-registered)
    # The pre-registered Platt step inverts the GBDT ranking (raw OOF AUC < 0.5 -> fitted slope of the wrong sign). This variant
    # ranks by the RAW GBDT probability instead (any increasing calibration gives the same ranking), gate = same design rates on
    # the raw OOF quantile. Shown only to show the inversion is not hiding a working model. Not used for any choice.
    print('\n######## EXPLORATORY, NOT PRE-REGISTERED: GBDT ranked by RAW probability (no Platt inversion); design rows = raw OOF')
    for c, ro, roth in [('raw_meta_T3', ra, rawa_oth), ('raw_meta_T1', rb, rawb_oth)]:
        real[c] = np.nan
        real.loc[des.index, c] = ro
        real.loc[roth['real_h2'].index, c] = roth['real_h2'].values
        D['unseen'][c] = roth['unseen'].values
        D['known'][c] = roth['known'].values
    dD = real[is_des]
    xs = {}
    for s_,(c, ro, pol, rate) in {'a': ('raw_meta_T3', ra, 'T3', 0.0597), 'b': ('raw_meta_T1', rb, 'T1', 0.0823), 'd': ('raw_meta_T3', ra, 'T3', 0.090)}.items():
        t_, k_ = gate(ro, rate)
        xs['EXPL raw %s %s g%.2f' % (s_, pol, 100 * rate)] = (c, t_, pol, 6)
    for nm, spec in xs.items():
        st = H.stats(H.run(dD, spec), ddays)
        print('  design %-24s n %3d opt net %+9d worst day %+8d max DD %+9d futures %+9d' % (nm, st['n'], st['net'], st['worst_day'], st['maxdd'], st['fut']))
    res_x = H.evaluate(D, xs, with_base=False)
    H.show(res_x)

    out = {'id': 'meta_label_opt', 'platt': platt, 'exploratory_raw_rank': res_x, 'choice': choice, 'choice_name': cand_name, 'flagged': flagged, 'thresholds': thr, 'rates_target': RATE,
           'design': design, 'design_risk_limits': {'worst_day': wd_lim, 'maxdd': dd_lim}, 'design_risk_ok': ok,
           'oof_auc': auc, 'selection_rates': rates, 'baseline_gate_rates': brates, 'lr_coefs': coefs,
           'verdict': {'beats_both_unseen': beats_u, 'beats_both_real_h2': beats_h2, 'beats_switch1_both': beats_s1, 'risk_ok': rok},
           'evaluate': res, 'evaluate_all_settings': res_all}
    json.dump(out, open(OUT + '/results.json', 'w'), indent=1, default=float)
    print('\nwrote', OUT + '/results.json')


if __name__ == '__main__':
    main()

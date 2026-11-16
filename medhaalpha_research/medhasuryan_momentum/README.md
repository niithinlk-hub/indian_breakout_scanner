# MedhaSuryan-M: MedhaSuryan with more weight on momentum (16 Nov 2026)

Research only. **Nothing live was changed:** not the VPS, not the scanner or engine, not `medhasuryan_integration.patch`, not the app in `app/`. The live score is still Opus v3, and MedhaSuryan is still as written in `medhasuryan.md`.

## Verdict

**Adding more momentum does not reliably improve MedhaSuryan.**
- A light tilt (20% momentum) is roughly a draw. It does better on Sep–Nov 2026 and worse on Nov 2025–May 2026, and the same-day and held results point in opposite directions on each period.
- Heavier tilts (30% and 40%) are worse than MedhaSuryan on almost every measure.
- Recommendation: keep MedhaSuryan as it is. If you still want the 20% tilt (S1 below), paper-trade it next to MedhaSuryan before it goes anywhere near the VPS.

## 1. The change

```
MedhaSuryan-M = (1 − w) × MedhaSuryan + w × Momentum
```

MedhaSuryan itself is unchanged: the Fable-OP score, or Opus v3 on Nifty downtrend days. Fable-OP already carries some momentum: 30 points for today's move in ATRs and 20 for a fresh day's extreme.

**Momentum (0 to 100)** adds four standard momentum ingredients that Fable-OP does not use. Each one is known at the signal minute, and each is a straight-line ramp between round values fixed before any backtest:

| Part | Points | Full | Nothing |
|---|---|---|---|
| Relative strength today: stock's day move minus Nifty's, both in the trade's direction | 35 | 2.5% | 0% or worse |
| 20-day trend in the trade's direction (20-day return) | 25 | +10% | 0% or against |
| Breakout breadth: prior bars broken (log scale) | 20 | 60 bars | 2 bars |
| Volume so far vs normal for the time of day | 20 | 2.0× | 0.8× or less |

Everything else is the same as MedhaSuryan:
- first 6 signals a day that pass the cutoff;
- the ₹15,000 futures-risk sizing;
- exit at T3, or at T1 on Nifty downtrend days.

On downtrend days, Opus v3 still gives 0 to a long with below-normal volume. At most 30% of such a score can come back from Momentum, so those longs still never pass.

## 2. How it was tested (the research's fair-test rules)

- **Four settings were declared before any result was seen.** The cutoffs for S1–S3 were set from the scores alone, so that each takes as many trades as MedhaSuryan does in the design window (160).

  | Setting | Momentum weight | Cutoff |
  |---|---|---|
  | S1 | 20% | 72.5 |
  | S2 | 30% | 72 |
  | S3 | 40% | 71 |
  | S4 | 30% | 75 (unchanged) |

- **The choice was made on the design window only** (12 May–31 Aug 2026): the best option net whose largest fall is no worse than 1.25× MedhaSuryan's. That picked **S1**.
- **Two periods count as the test:** 1 Sep–11 Nov 2026 (real futures) and 3 Nov 2025–11 May 2026 (cash prices standing in for futures; no model was built on it).
- **Same-day results** come from the research's own test bench, `hunt/harness.py`, unchanged. Options are modelled with Black-76, good to about ±10%.
- **Held results** (carried across days until target or stop, sold 15:15 the session before expiry) come from `heldsim.py`. That file is a rebuild of `medhasuryan/held4.py` that does not need the scanner's private source. Checked against the stored held results in `medhasuryan/bt4.json`:
  - all 1,192 stored trades over the four models and both periods match on status and on net within ₹50 or 1%;
  - totals agree within 0.1–0.5% (`validate_held.log`).

## 3. Results (₹)

"Options" and "Futures" are same-day results. "Held" is futures-equivalent, carried until target or stop. "Largest fall" is the deepest drop from a peak in option profit, day by day.

### Design window, 12 May–31 Aug 2026 (78 sessions): the choice was made here

| Model | Trades | Options | Futures | Held | Worst day | Largest fall |
|---|---|---|---|---|---|---|
| **MedhaSuryan** | 160 | **+3,39,868** | +4,20,965 | **+7,26,477** | −23,143 | −27,877 |
| **S1 (20%, chosen)** | 156 | +3,38,876 | **+4,39,906** | +6,54,718 | −17,808 | −31,458 |
| S2 (30%) | 157 | +2,68,828 | +2,91,627 | +4,70,313 | −17,808 | −36,288 |
| S3 (40%) | 161 | +2,53,774 | +2,80,244 | +3,79,726 | −19,077 | −44,428 |
| S4 (30%, cutoff 75) | 103 | +2,64,995 | +3,36,345 | +4,70,599 | −17,808 | −22,689 |

### Test 1: 1 Sep–11 Nov 2026 (48 sessions, real futures)

| Model | Trades | Options | Futures | Held | Worst day | Largest fall | T1 / T2 / T3 hit (held) |
|---|---|---|---|---|---|---|---|
| **MedhaSuryan** | 112 | +2,43,042 | +3,90,428 | **+6,13,860** | −15,030 | −28,584 | 70% / 54% / 44% |
| **S1 (20%)** | 112 | **+2,77,454** | **+4,37,938** | +5,64,368 | −13,410 | −23,485 | 69% / 51% / 41% |
| S2 (30%) | 109 | +2,60,539 | +4,07,843 | +5,06,809 | −13,410 | −25,785 | 67% / 51% / 39% |
| S3 (40%) | 121 | +2,26,896 | +3,39,923 | +4,78,255 | −25,578 | −44,130 | 65% / 50% / 40% |
| S4 (30%, cutoff 75) | 88 | +2,42,253 | +3,95,614 | +4,85,058 | −13,410 | −17,250 | 68% / 52% / 42% |

### Test 2: 3 Nov 2025–11 May 2026 (127 sessions, cash prices for futures): the fairest test

| Model | Trades | Options | Futures | Held | Worst day | Largest fall | T1 / T2 / T3 hit (held) |
|---|---|---|---|---|---|---|---|
| **MedhaSuryan** | 298 | **+2,67,606** | **+1,78,272** | +3,84,737 | −25,651 | −48,875 | 57% / 40% / 31% |
| **S1 (20%)** | 296 | +2,41,266 | +1,19,181 | **+4,29,982** | −25,267 | −43,781 | 55% / 40% / 32% |
| S2 (30%) | 277 | +2,33,542 | +1,13,209 | +4,00,709 | −27,411 | −59,693 | 55% / 40% / 32% |
| S3 (40%) | 291 | +2,16,983 | +74,975 | +3,66,056 | −28,904 | −1,01,132 | 54% / 39% / 32% |
| S4 (30%, cutoff 75) | 230 | +2,17,697 | +1,31,851 | +4,47,511 | −27,411 | −78,633 | 56% / 41% / 33% |

### Whole period, 12 May–11 Nov 2026 (126 sessions, real futures)

| Model | Trades | Options | Futures | Held |
|---|---|---|---|---|
| MedhaSuryan | 272 | +5,82,910 | +8,11,393 | **+13,40,337** |
| S1 (20%) | 268 | **+6,16,330** | **+8,77,844** | +12,19,087 |

### How sure: chance S1 beats MedhaSuryan

Trading days were re-sampled 5,000 times.

| Period | Options | Futures | Held |
|---|---|---|---|
| 1 Sep–11 Nov 2026 | 81% | 76% | 27% |
| 3 Nov 2025–11 May 2026 | 36% | 33% | 55% |

No measure clears 85% on both periods, so neither model can be called the better one.

The research's formal bar asks a new model to beat both Opus v3 (T1) and Fable-OP (T3) on option net in both test periods, with a worst day and largest fall no worse than 1.25× the better of the two.
- S1 beats both on option net in both periods.
- Like MedhaSuryan, S1 misses the worst-day limit in Nov 2025–May 2026: −25,267 against a limit of −20,576 (1.25 × Fable-OP's −16,461).
- Measured against MedhaSuryan itself, S1 is not better.

## 4. Which momentum ingredient helps (diagnostic)

This test was run after the results above were seen, so it is not a selection.

Each row is MedhaSuryan plus 20% of one part alone. Its cutoff gives 160 design-window trades.

| Variant | Sep–Nov 2026: options / futures / held | Nov 2025–May 2026: options / futures / held |
|---|---|---|
| MedhaSuryan as is | +2,43,042 / +3,90,428 / +6,13,860 | +2,67,606 / +1,78,272 / +3,84,737 |
| + all four (S1) | +2,77,454 / +4,37,938 / +5,64,368 | +2,41,266 / +1,19,181 / +4,29,982 |
| + relative strength only | +2,26,325 / +3,72,464 / +2,94,225 | +2,88,965 / +2,40,148 / +4,24,513 |
| + 20-day trend only | +1,29,550 / +1,36,503 / +3,09,966 | +1,68,751 / −46,125 / +96,590 |
| + breakout breadth only | +2,35,520 / +3,01,544 / +6,17,895 | +2,38,435 / +1,02,008 / +5,40,124 |
| + volume only | +2,12,352 / +2,84,357 / +4,25,216 | +2,60,529 / +1,22,507 / +6,51,840 |

What it shows:
- **The 20-day trend hurts clearly on both periods.** Favouring stocks already far along a 20-day run made results worse everywhere. This is the main reason heavier momentum weights lose.
- **The other three parts are mixed.** Each one helps on some measures and periods and hurts on others. Chasing any of them now would be fitting to noise.
- **This is likely why extra momentum adds little.** The scanner's setups only fire on momentum already: above the previous day's high and VWAP, at the top of the day's range, breaking prior bars. Fable-OP then scores today's move again. Momentum's correlation with the MedhaSuryan score is 0.40.

## 5. Limits

- Option figures are modelled (Black-76, fitted on 1,960 real option exits), good to about ±10%.
- The Nov 2025–May 2026 period and every held result use cash prices in place of futures.
- The rebuilt held simulator comes out about ₹2 a trade more favourable than the stored results. This applies to every model equally.
- The 4 settings and the anchor values were chosen by judgement. A different momentum definition could do differently, but the per-part check above gives no strong lead to follow.

## 6. Files and how to re-run

The scripts run against the research folder `medhaalpha_research/` on branch `claude/cool-cannon-2qua2u`. They need its raw data restored (see that folder's README) and Python with numpy, pandas and scipy. Pass the research folder as the first argument:

```
python sameday.py      <research folder> sameday.json     # same-day backtest, the 4 settings, the design-window choice
python validate_held.py <research folder>                 # rebuilt held simulator vs the stored bt4.json results
python held_and_boot.py <research folder> held.json       # held backtest + day re-sampling, all models
python parts_diag.py   <research folder> parts_diag.json  # one-part-at-a-time diagnostic
```

| File | What |
|---|---|
| `momscore.py` | The Momentum score and MedhaSuryan-M |
| `sameday_defs.py` | The 4 declared settings and the shared trade rule |
| `heldsim.py` | Held-across-days simulator (fills, sizing, futures charges) rebuilt from `held4.py`'s rules |
| `*.log`, `*.json` | Outputs of the runs above |

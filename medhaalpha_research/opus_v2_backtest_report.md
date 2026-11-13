# Opus v2: backtest report

Built and tested in isolation. Nothing on the VPS was changed, and the patch in this folder has not been applied anywhere.

## What Opus v2 is

A side split, with no new weights or cut-offs:

- a **long** (setup A) is scored by Fable-OP and needs 75 or more;
- a **short** (setup B) is scored by Opus and needs 75 or more, exactly as today;
- everything else is unchanged: same signals, same stops and targets, first 6 qualifying signals a day.

Reason: Opus's picks made money on shorts and not on longs, in May to August (months its weights never saw) and again in September to November. Fable-OP is the reverse.

## Result, same-day exit at T1

Source: the scanner's own six-month backtest (12 May to 11 Nov 2026, 126 sessions, real contract months, lots sized to Rs 15,000 risk, charges and 0.02 % slippage a side). "Reached T1" is the accuracy measure; anything not at T1 or the stop is squared off at the close.

**All 126 sessions, 12 May to 11 Nov**

| | Opus now | Opus v2 | Fable-OP |
|---|---|---|---|
| Trades | 369 | 353 | 233 |
| Trades a session | 2.9 | 2.8 | 1.8 |
| Reached T1 | 36.0 % | 47.6 % | 54.9 % |
| Stopped out | 24.1 % | 26.3 % | 31.3 % |
| Ended in profit | 53.1 % | 59.2 % | 61.4 % |
| Net, exit at T1 (Rs) | +2,50,359 | +5,28,284 | +3,61,287 |
| Net per trade (Rs) | +678 | +1,497 | +1,551 |
| Net, hold for T2 (Rs) | +3,25,980 | +7,08,460 | +5,94,981 |
| Net, hold for T3 (Rs) | +3,43,411 | +7,59,703 | +7,02,290 |
| Days up / down | 56 / 51 | 68 / 42 | 59 / 39 |
| Largest fall from a peak (Rs) | -83,253 | -98,957 | -71,909 |

**12 May to 31 Aug, 78 sessions**

| | Opus now | Opus v2 | Fable-OP |
|---|---|---|---|
| Trades | 213 | 212 | 160 |
| Trades a session | 2.7 | 2.7 | 2.1 |
| Reached T1 | 35.7 % | 49.5 % | 56.9 % |
| Stopped out | 24.9 % | 29.7 % | 31.9 % |
| Ended in profit | 51.2 % | 59.9 % | 63.1 % |
| Net, exit at T1 (Rs) | +1,42,079 | +2,92,754 | +2,68,276 |
| Net per trade (Rs) | +667 | +1,381 | +1,677 |
| Net, hold for T2 (Rs) | +1,31,228 | +4,09,211 | +3,97,026 |
| Net, hold for T3 (Rs) | +1,33,627 | +4,19,243 | +4,33,707 |
| Days up / down | 37 / 28 | 41 / 28 | 38 / 27 |
| Largest fall from a peak (Rs) | -75,901 | -62,982 | -48,761 |

**1 Sep to 11 Nov, 48 sessions**

| | Opus now | Opus v2 | Fable-OP |
|---|---|---|---|
| Trades | 156 | 141 | 73 |
| Trades a session | 3.2 | 2.9 | 1.5 |
| Reached T1 | 36.5 % | 44.7 % | 50.7 % |
| Stopped out | 23.1 % | 21.3 % | 30.1 % |
| Ended in profit | 55.8 % | 58.2 % | 57.5 % |
| Net, exit at T1 (Rs) | +1,08,281 | +2,35,530 | +93,011 |
| Net per trade (Rs) | +694 | +1,670 | +1,274 |
| Net, hold for T2 (Rs) | +1,94,752 | +2,99,248 | +1,97,955 |
| Net, hold for T3 (Rs) | +2,09,784 | +3,40,459 | +2,68,584 |
| Days up / down | 19 / 23 | 27 / 14 | 21 / 12 |
| Largest fall from a peak (Rs) | -67,996 | -98,957 | -71,909 |

## Month by month

| Month | Nifty | Opus trades | Opus reached T1 | Opus net (Rs) | v2 trades | v2 reached T1 | v2 net (Rs) |
|---|---|---|---|---|---|---|---|
| 2026-05 | -1.9 % | 43 | 33 % | +14,731 | 34 | 44 % | +79,446 |
| 2026-06 | +1.1 % | 67 | 39 % | +91,531 | 63 | 51 % | +93,020 |
| 2026-07 | +2.0 % | 58 | 31 % | +727 | 57 | 51 % | +1,11,580 |
| 2026-08 | -2.0 % | 45 | 40 % | +35,089 | 58 | 50 % | +8,708 |
| 2026-09 | -6.0 % | 64 | 36 % | +37,963 | 54 | 54 % | +2,00,858 |
| 2026-10 | +2.3 % | 72 | 33 % | +4,489 | 69 | 35 % | -18,926 |
| 2026-11 | +7.8 % | 20 | 50 % | +65,829 | 18 | 56 % | +53,598 |

Opus v2 reached T1 more often in 7 of 7 months and made more money in 4 of 7.

## By side

| Period | Model | Longs: trades | Longs: reached T1 | Longs: net (Rs) | Shorts: trades | Shorts: reached T1 | Shorts: net (Rs) |
|---|---|---|---|---|---|---|---|
| 12 May - 31 Aug | Opus now | 140 | 34 % | +22,527 | 73 | 40 % | +1,19,552 |
| 12 May - 31 Aug | Fable-OP | 143 | 56 % | +2,17,616 | 17 | 65 % | +50,661 |
| 12 May - 31 Aug | Opus v2 | 143 | 56 % | +2,17,616 | 69 | 36 % | +75,138 |
| 12 May - 31 Aug | Opposite pairing | 144 | 33 % | +21,782 | 17 | 65 % | +50,661 |
| 1 Sep - 11 Nov | Opus now | 69 | 30 % | -54,507 | 87 | 41 % | +1,62,788 |
| 1 Sep - 11 Nov | Fable-OP | 55 | 51 % | +65,615 | 18 | 50 % | +27,396 |
| 1 Sep - 11 Nov | Opus v2 | 55 | 51 % | +65,615 | 86 | 41 % | +1,69,915 |
| 1 Sep - 11 Nov | Opposite pairing | 71 | 28 % | -77,927 | 19 | 47 % | +15,694 |

"Opposite pairing" is Opus for longs and Fable-OP for shorts. It is the worst of the four in both periods, which is what the split predicts.

## How sure is the difference

The 126 days resampled 20,000 times, Opus v2 minus Opus on the same days:

- reached-T1 rate: +11.5 points, 5th to 95th percentile +6.9 to +16.5; higher in every resample.
- net at T1: Rs +2,77,924, 5th to 95th percentile -49,591 to +5,97,352; higher in 92 % of resamples.

So the accuracy gain is firm. The profit gain is likely, not certain.

## Checks

- **Other cut-offs.** Long cut 70 to 80 and short cut 72 to 80 (20 combinations): reached-T1 rate 43 to 48 %, net Rs +2,15,557 to +5,61,053. Opus now: 36 %, Rs +2,50,359. The 75 / 75 pair is not a lone peak.
- **Costlier early entries.** 209 of v2's 353 trades enter in the first 15 minutes (Opus: 56 of 369), where fills are likely worse than the 0.02 % a side assumed. At 0.05 % a side on those entries v2 nets about Rs +4,46,774 and Opus Rs +2,28,519; at 0.10 %, Rs +3,10,924 and Rs +1,92,119 (turnover taken as Rs 13 lakh a trade).
- **Patched code.** The patch was applied to a copy of the scanner code and run offline on the 17 stored replay days (21 Oct to 13 Nov, 1,169 signals): the existing three scores are reproduced exactly, the existing models' picks are untouched, and opus_v2's picks equal the picks tested here on every day.
- **Latest 17 sessions (21 Oct to 13 Nov).** Opus: 65 trades, 26 reached T1, Rs +69,390. Opus v2: 54 trades, 22 reached T1, Rs +62,552. No gain in this stretch, which includes the weeks Opus was tuned on. On 12 and 13 Nov, two rising days, Opus took 12 longs and v2 took 1.
- **Held across days, 1 Sep to 13 Nov (50 sessions), every signal taken.** Exit T1: Opus Rs +3,14,025 on 168 trades, v2 Rs +3,85,148 on 142. Exit T3: Opus Rs +4,09,914, v2 Rs +8,05,584. (1 Sep to 19 Oct followed on the cash share, as in the earlier September work.)
- **Rs 3 lakh of futures margin (about two positions at a time), same 50 sessions.** Exit T1: Opus Rs +2,50,742 (89 trades carried), v2 Rs +1,09,130 (79). Exit T3: Opus Rs +1,06,385 (48), v2 Rs +2,49,491 (47). With so few slots the result depends on which signals happen to fire first, and v2 is not ahead at T1.

## What was tried and dropped

1. **A new score fitted from the raw features** (move in ATRs, distance from VWAP, gap, time, relative volume and 12 more; separate fits for longs and shorts). Fitted on three of the four months May to August and tested on the fourth, in turn: at Opus's trade count most variants reached T1 more often (32 to 48 %), but all were stopped far more often and every one lost money (as much as Rs 3.6 lakh, against Opus's gain of 1.4 lakh). Dropped.
2. **Blending the Opus and Fable-OP scores.** Fixed on May to August, then checked once on 1 Sep to 11 Nov: longs on an equal blend, shorts on Opus gave 136 trades, 40.4 % reached T1, Rs +99,296, against Opus's 156 trades, 36.5 %, Rs +1,08,281. More accurate, no more profitable. The side tables showed why: any weight on Opus made the long picks worse. That is what led to the plain split.
3. **Skipping shorts on broadly weak days** (Nifty already well down, or many shorts already fired). Strong on May to August, weak or reversed on 1 Sep to 11 Nov. Not included.

## Limits

- **The split was chosen after seeing 1 Sep to 11 Nov** (step 2 above), so that period is not a clean test of it. In its favour: it has no fitted number, Opus's short-only strength shows in May to August (months Opus never saw), and Fable-OP's long strength shows in September to November (months Fable-OP never saw).
- **Profit is uneven.** The six-month gain comes mostly from May, July and September. v2 was behind Opus in August, October and November.
- **Stops are slightly more frequent** (26 % against 24 %) and the largest fall from a peak is a little deeper.
- **In strongly rising markets v2 trades less than Opus**, because Fable-OP passes fewer longs than Opus does.
- **Backtest, not live.** On 13 Nov the live paper ledger showed Opus at Rs -18,241 where the replay shows Rs -2,928.
- No option results: the option contracts for May to October have expired.

## How it was built

- Signals, the three scores and outcomes: the scanner's own six-month per-signal file (4,996 setup A and B signals).
- Features for step 1: rebuilt for every signal with the scanner's own feature code from 6.9 million cash 1-minute candles (20 Apr to 12 Nov). The rebuilt scores match the scanner's own with correlation 0.84 to 0.95, which is too loose for threshold decisions, so the final candidate uses only the scanner's own stored scores.
- Fitting was confined to 12 May to 31 Aug. 1 Sep to 11 Nov was opened once, for the blended candidates.

## Files

- `opus_v2_integration.patch`: adds `opus_v2` as a fourth score model (score.py, config.py, backtest.py). Not applied. `backtest.py` in the image has Windows line endings; apply with `git apply --ignore-whitespace` if the repository copy differs. The dashboard lives in the engine service, which I have not seen; its model selector may need the new name added.
- `opus_v2_check.py`: lists Opus v2's picks from any stored scanner day (replay or backtest JSON), so it can be paper-tracked without changing anything.

# Opus v2 six-month check, and Opus v3

Built and tested in isolation. Nothing on the VPS was changed and the patch has not been applied anywhere.

All figures: the scanner's own six-month backtest file, 12 May to 11 Nov 2026 (126 sessions, real contract months), live rule (first 6 signals a day at or above each model's cut-off), same-day exit at T1, lots sized to Rs 15,000 risk, charges and 0.02 % slippage a side.

## 1. Six-month check

| | Opus | Fable | Fable-OP | Opus v2 | Opus v3 |
|---|---|---|---|---|---|
| Trades | 369 | 475 | 233 | 353 | 335 |
| Reached T1 | 36.0 % | 42.1 % | 54.9 % | 47.6 % | 49.0 % |
| Stopped out | 24.1 % | 36.8 % | 31.3 % | 26.3 % | 25.4 % |
| Ended in profit | 53.1 % | 51.6 % | 61.4 % | 59.2 % | 60.3 % |
| Net, exit at T1 (Rs) | +2,50,359 | -1,61,959 | +3,61,287 | +5,28,284 | +5,89,038 |
| Net per trade (Rs) | +678 | -341 | +1,551 | +1,497 | +1,758 |
| Net, hold for T2 (Rs) | +3,25,980 | +2,29,669 | +5,94,981 | +7,08,460 | +7,95,436 |
| Net, hold for T3 (Rs) | +3,43,411 | +4,73,539 | +7,02,290 | +7,59,703 | +8,32,435 |
| Days up / down | 56 / 51 | 53 / 66 | 59 / 39 | 68 / 42 | 69 / 39 |
| Largest fall from a peak (Rs) | -83,253 | -3,62,999 | -71,909 | -98,957 | -98,136 |

Opus v2 against Opus: reaches T1 far more often and makes about twice the net, but is stopped out slightly more often (26.3 % against 24.1 %). So it meets two of the three aims, not the third.

## 2. Opus v3

Opus v2 with one extra condition: **a long must have relative volume of 1 or more** (the stock's volume so far today at least equal to its normal volume by that time of day). Shorts are unchanged.

- The 22 longs this removes reached T1 32 % of the time, were stopped 36 % of the time and lost Rs 31,091 between them. Four later signals take freed places.
- Looking wider, at all 559 longs scoring 65 or more on Fable-OP: the 103 on below-normal volume lost about Rs 1,000 a trade in each half of the six months.
- The value 1 is the one the scanner's settings already name as "preferred" volume. Cuts from 0.6 to 1.2 all beat v2, so it is not a lone peak.

**By half**

| | v2, 12 May - 31 Aug | v3, 12 May - 31 Aug | v2, 1 Sep - 11 Nov | v3, 1 Sep - 11 Nov |
|---|---|---|---|---|
| Trades | 212 | 199 | 141 | 136 |
| Reached T1 | 49.5 % | 50.8 % | 44.7 % | 46.3 % |
| Stopped out | 29.7 % | 29.1 % | 21.3 % | 19.9 % |
| Net at T1 (Rs) | +2,92,754 | +3,08,996 | +2,35,530 | +2,80,042 |

**Month by month: trades, reached T1, stopped, net (Rs)**

| Month | Opus | Opus v2 | Opus v3 |
|---|---|---|---|
| 2026-05 | 43, 33 %, 23 %, +14,731 | 34, 44 %, 24 %, +79,446 | 33, 42 %, 24 %, +68,915 |
| 2026-06 | 67, 39 %, 28 %, +91,531 | 63, 51 %, 32 %, +93,020 | 60, 53 %, 30 %, +1,07,734 |
| 2026-07 | 58, 31 %, 24 %, +727 | 57, 51 %, 21 %, +1,11,580 | 52, 54 %, 21 %, +1,16,793 |
| 2026-08 | 45, 40 %, 22 %, +35,089 | 58, 50 %, 40 %, +8,708 | 54, 50 %, 39 %, +15,555 |
| 2026-09 | 64, 36 %, 23 %, +37,963 | 54, 54 %, 13 %, +2,00,858 | 51, 53 %, 12 %, +1,93,158 |
| 2026-10 | 72, 33 %, 25 %, +4,489 | 69, 35 %, 29 %, -18,926 | 68, 37 %, 28 %, +266 |
| 2026-11 | 20, 50 %, 15 %, +65,829 | 18, 56 %, 17 %, +53,598 | 17, 65 %, 12 %, +86,618 |

v3 made more than v2 in 5 of 7 months.

**Longs and shorts, six months**

| | Longs: trades | Longs: reached T1 | Longs: stopped | Longs: net (Rs) | Shorts: trades | Shorts: reached T1 | Shorts: stopped | Shorts: net (Rs) |
|---|---|---|---|---|---|---|---|---|
| Opus | 209 | 32.5 % | 27.3 % | -31,980 | 160 | 40.6 % | 20.0 % | +2,82,339 |
| Fable | 337 | 42.7 % | 36.8 % | -96,288 | 138 | 40.6 % | 37.0 % | -65,671 |
| Fable-OP | 198 | 54.5 % | 31.3 % | +2,83,231 | 35 | 57.1 % | 31.4 % | +78,056 |
| Opus v2 | 198 | 54.5 % | 31.3 % | +2,83,231 | 155 | 38.7 % | 20.0 % | +2,45,052 |
| Opus v3 | 177 | 57.6 % | 30.5 % | +3,24,983 | 158 | 39.2 % | 19.6 % | +2,64,055 |

**How sure (126 days resampled 20,000 times)**

| v3 compared with | Net at T1 (Rs) | 5th to 95th percentile | Net higher in | Reach-T1 | Higher in | Stop-outs | Lower in |
|---|---|---|---|---|---|---|---|
| Opus v2 | +60,755 | -20,338 to +1,47,691 | 88 % | +1.4 pts | 96 % | -1.0 pts | 91 % |
| Opus | +3,38,679 | +25,804 to +6,46,553 | 96 % | +12.9 pts | 100 % | +1.3 pts | 32 % |
| Fable-OP | +2,27,751 | -22,615 to +4,93,064 | 93 % | -6.0 pts | 2 % | -6.0 pts | 99 % |

Against v2 the step is small and each part of it is likely rather than certain. Against Opus, reach-T1 and net are clearly better; stop-outs are not.

## 3. Why stop-outs do not come down further

On shorts, v3 and Opus use the same score and are stopped equally often (about 20 %). The gap is on longs: v3's longs are stopped 30 % of the time and reach T1 58 %; Opus's longs are stopped 27 %, reach T1 only 32 % and lose money.

Three ways of cutting stop-outs were tested. Each cut them, and each cost more in T1 hits and net than it saved.

**a. Where the stop sits.** Run on v3's trades plus the shorts that qualify on Fable-OP (355 trades). Same entries, levels rebuilt with the scanner's level code, day replayed on cash 1-minute candles (the expired futures cannot be read). The cash replay of today's rule matches the real outcome on 310 of 355 trades.

| Stop rule | Trades taken | Skipped (one lot over Rs 15,000 risk) | Reached T1 | Stopped | Net (Rs) |
|---|---|---|---|---|---|
| as now (stop 0.3-0.9 ATR, aim 0.5) | 341 | 14 | 50.4 % | 26.4 % | +5,79,302 |
| floor 0.4 ATR | 325 | 30 | 46.8 % | 24.6 % | +5,15,661 |
| floor 0.5 ATR, aim 0.6 | 298 | 57 | 41.6 % | 21.5 % | +4,33,938 |
| floor 0.6 ATR, aim 0.7 | 264 | 91 | 37.1 % | 19.3 % | +3,48,315 |
| floor 0.7 ATR, aim 0.8, cap 1.1 | 207 | 148 | 30.0 % | 15.9 % | +2,55,785 |
| aim 0.7 (floor 0.3) | 280 | 75 | 40.4 % | 22.9 % | +3,50,883 |
| as now, T1 at 0.8R | 341 | 14 | 56.6 % | 25.5 % | +3,51,513 |
| floor 0.5 aim 0.6, T1 at 0.8R | 298 | 57 | 48.7 % | 21.1 % | +2,65,241 |
| floor 0.6 aim 0.7, T1 at 0.7R | 264 | 91 | 53.0 % | 15.9 % | +3,11,892 |

**b. Moving the stop to the entry price part-way to T1** (same trades, same replay).

| Rule | Reached T1 | Full stop-outs | Scratched at entry | Net (Rs) | Months better than today's rule |
|---|---|---|---|---|---|
| as now | 50.4 % | 26.4 % | 0.0 % | +5,85,438 | - |
| stop to entry after 0.4R | 34.9 % | 18.2 % | 33.1 % | +3,50,645 | 0 of 7 |
| after 0.5R | 38.7 % | 20.2 % | 25.8 % | +4,12,862 | 2 of 7 |
| after 0.6R | 43.1 % | 22.6 % | 16.4 % | +4,40,282 | 2 of 7 |
| after 0.7R | 45.7 % | 24.6 % | 10.6 % | +4,70,497 | 1 of 7 |
| after 0.8R | 47.5 % | 25.5 % | 6.5 % | +5,03,262 | 0 of 7 |

**c. Extra filters chosen from the data.** For each month in turn, the best filter per side was chosen from 22 features using the other six months, then applied to the month left out. The filters chosen changed from month to month. On the left-out months, in the two versions of the search I ran, stop-outs were 26.3 % and 27.1 % (v2: 26.3 %) and the net was Rs +4,71,432 and Rs +5,59,409 (v2: Rs +5,28,284): no gain on stop-outs, and no reliable gain on net. A rule to skip shorts once Nifty is down 1 % helped in May to August and hurt in September to November.

About a quarter of these trades being stopped looks like the cost of trading breakouts with a stop of about half a day's range: tighter selection does not remove it, and a looser stop or an early move to entry gives back more than it saves.

## 4. Other checks

- **Latest 17 sessions, 21 Oct to 13 Nov (real November futures):** Opus 65 trades, 40 % reached T1, 22 % stopped, Rs +69,390. v2: 54, 41 %, 22 %, Rs +62,552. v3: 52, 44 %, 21 %, Rs +96,393. Fable-OP: 33, 48 %, 21 %, Rs +63,709.
- **Volume figures are exact:** my rebuilt relative volume equals the scanner's own stored value on all 872 signals where both exist.
- **Patched code:** applied to an offline copy and run on the 17 stored replay days. The three existing scores are reproduced exactly, existing models' picks are untouched, and the v2 and v3 picks equal the ones tested here.
- **Held across days, 1 Sep to 13 Nov, every signal taken:** exit T1: Opus Rs +3,14,025, v2 Rs +3,85,148, v3 Rs +4,34,977. Exit T3: Opus Rs +4,09,914, v2 Rs +8,05,584, v3 Rs +9,14,853. (One v3 trade has no multi-day result and is left out.)
- **With Rs 3 lakh of futures margin (about two positions at a time), same 50 sessions:** exit T1: Opus Rs +2,50,742, v2 Rs +1,09,130, v3 Rs +1,43,009. Exit T3: Opus Rs +1,06,385, v2 Rs +2,49,491, v3 Rs +2,26,619. At T1 Opus is still ahead here.

## 5. Limits

- The volume condition was found by comparing 27 features on these same six months, so the size of its gain is not proven. Its direction is supported in both halves and in the wider pool of longs.
- There is no untouched period left to test v3 on. Only forward paper trades can settle it.
- About 6 in 10 trades enter in the first 15 minutes, where real fills are likely worse than assumed.
- Backtest, not live. No option results for May to October (those contracts have expired).

## 6. Files

- `opus_v2_v3_integration.patch`: adds `opus_v2` and `opus_v3` as logged score models (score.py, config.py, backtest.py). Replaces the earlier v2-only patch. Not applied. `backtest.py` in the image has Windows line endings; use `git apply --ignore-whitespace` if the repository copy differs.
- `opus_v3_check.py`: lists Opus, v2 and v3 picks from any stored scanner day (replay or backtest JSON).

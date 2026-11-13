# Which model for which market: uptrend, sideways, downtrend

Prepared 13 Nov 2026. All figures are after costs, risk budget Rs 15,000 a trade, live rule (setups A and B, first 6 signals a day at or above the cut). Opus, Opus v2 and Opus v3 exit at T1; Fable and Fable-OP exit at T3.

## Answer

| Market (Nifty) | Use | Why |
|---|---|---|
| Uptrend | **Fable-OP, exit T3** | Best or near-best in every check. Its longs carry the result. Plain Opus loses money on longs here. |
| Sideways | **Fable-OP, exit T3** | Best in every check, real and stand-in. |
| Downtrend | **Opus v3, exit T1** | Fable-OP takes mostly longs, which do little in a falling market. Opus v3's shorts do the work. |

Plain Opus is not the best choice in any market. Fable (the original) looked best in real downtrends but was the worst model on the earlier-dates check, so it is not dependable.

**The market on the next session (after 12 Nov 2026) is an uptrend** by both definitions (last close 25,255; 20-day average 23,501; 50-day average 23,304; 20-day change +11.1 %). That points to Fable-OP, exit T3.

## Does switching by market beat using one model?

Rule tested: use Fable-OP, exit T3, except when Nifty is in a downtrend, when use Opus v3, exit T1.

| Check | Fable-OP alone (Rs) | Opus v3 alone (Rs) | Switch rule (Rs) |
|---|---:|---:|---:|
| Real futures, 12 May to 11 Nov 2026, trend rule 1 | +7,02,290 | +5,89,038 | **+8,11,393** |
| Real futures, same period, trend rule 2 | +7,02,290 | +5,89,038 | **+9,25,453** |
| Options estimate, same period, trend rule 1 | +6,12,190 | +5,53,263 | **+6,57,085** |
| Options estimate, same period, trend rule 2 | +6,12,190 | +5,53,263 | **+7,43,747** |
| Stand-in, 3 Nov 2025 to 11 May 2026, trend rule 1 | +78,849 | -1,28,597 | **+1,78,272** |
| Stand-in, same period, trend rule 2 | +78,849 | -1,28,597 | **+1,29,889** |
| Stand-in, 12 May to 19 Oct 2026, trend rule 1 | +42,654 | +1,52,729 | +69,567 |
| Stand-in, same period, trend rule 2 | +42,654 | +1,52,729 | +1,27,286 |

The switch rule beat Fable-OP alone in all eight checks. It beat Opus v3 alone in six of eight.

What to keep in mind:

- The gain is concentrated. On real data it came from September and October 2026 (28 downtrend sessions); on the stand-in it came from March 2026 (19 downtrend sessions). In June 2026, February 2026 and April 2026 the switch cost a little. It pays in long, persistent declines and is roughly neutral otherwise.
- The rule was chosen after looking at these same results, so the size of the gain is flattering. The direction (longs in rising and flat markets, shorts in falling ones) is the dependable part.
- Stand-in figures use cash-share prices in place of futures. They show direction, not the true size of profit.

## How each session was labelled

The label uses Nifty daily closes up to the day before the session, so it is known before the open.

- Trend rule 1 (main): uptrend when the last close is above its 20-day average and that average is above the 50-day average. Downtrend when both are reversed. Anything else is sideways.
- Trend rule 2 (cross-check): uptrend when Nifty gained 2 % or more over the last 20 sessions, downtrend when it lost 2 % or more, otherwise sideways.

## Real futures, 12 May to 11 Nov 2026 (126 sessions), trend rule 1

**Uptrend: 24 sessions**

| Model | Trades | Reach T1 | Stopped | Net per session (Rs) | Total net (Rs) | Options est. per session (Rs) |
|---|---:|---:|---:|---:|---:|---:|
| Opus (exit T1) | 69 | 31.9 % | 27.5 % | -1,500 | -35,999 | +997 |
| Opus v2 (exit T1) | 74 | 51.4 % | 23.0 % | +6,074 | +145,784 | +5,439 |
| Opus v3 (exit T1) | 66 | 51.5 % | 22.7 % | +5,599 | +134,381 | +4,903 |
| Fable (exit T3) | 99 | 39.4 % | 40.4 % | +6,019 | +144,448 | +7,664 |
| **Fable-OP (exit T3)** | 59 | 57.6 % | 28.8 % | **+10,685** | +256,429 | +8,475 |

**Sideways: 69 sessions**

| Model | Trades | Reach T1 | Stopped | Net per session (Rs) | Total net (Rs) | Options est. per session (Rs) |
|---|---:|---:|---:|---:|---:|---:|
| Opus (exit T1) | 210 | 37.1 % | 24.8 % | +2,623 | +180,969 | +3,298 |
| Opus v2 (exit T1) | 195 | 46.2 % | 29.7 % | +3,209 | +221,453 | +3,951 |
| Opus v3 (exit T1) | 187 | 48.1 % | 28.9 % | +3,980 | +274,639 | +4,253 |
| Fable (exit T3) | 276 | 41.7 % | 35.9 % | +730 | +50,402 | +3,843 |
| **Fable-OP (exit T3)** | 131 | 55.7 % | 29.0 % | **+5,434** | +374,946 | +4,516 |

**Downtrend: 33 sessions**

| Model | Trades | Reach T1 | Stopped | Net per session (Rs) | Total net (Rs) | Options est. per session (Rs) |
|---|---:|---:|---:|---:|---:|---:|
| Opus (exit T1) | 90 | 36.7 % | 20.0 % | +3,194 | +105,389 | +2,982 |
| Opus v2 (exit T1) | 84 | 47.6 % | 21.4 % | +4,880 | +161,047 | +4,091 |
| Opus v3 (exit T1) | 82 | 48.8 % | 19.5 % | +5,455 | +180,018 | +4,306 |
| **Fable (exit T3)** | 100 | 46.0 % | 36.0 % | **+8,445** | +278,689 | +7,594 |
| Fable-OP (exit T3) | 43 | 48.8 % | 41.9 % | +2,149 | +70,915 | +2,946 |

## Same period, trend rule 2 (cross-check)

**Uptrend: 20 sessions**

| Model | Trades | Reach T1 | Stopped | Net per session (Rs) | Total net (Rs) | Options est. per session (Rs) |
|---|---:|---:|---:|---:|---:|---:|
| Opus (exit T1) | 54 | 40.7 % | 18.5 % | +5,608 | +112,158 | +4,417 |
| Opus v2 (exit T1) | 33 | 57.6 % | 12.1 % | +6,575 | +131,508 | +4,501 |
| Opus v3 (exit T1) | 31 | 64.5 % | 6.5 % | +8,898 | +177,956 | +5,563 |
| **Fable (exit T3)** | 75 | 50.7 % | 26.7 % | **+16,759** | +335,177 | +12,278 |
| Fable-OP (exit T3) | 29 | 62.1 % | 17.2 % | +15,153 | +303,055 | +9,911 |

**Sideways: 57 sessions**

| Model | Trades | Reach T1 | Stopped | Net per session (Rs) | Total net (Rs) | Options est. per session (Rs) |
|---|---:|---:|---:|---:|---:|---:|
| Opus (exit T1) | 160 | 30.0 % | 26.9 % | -968 | -55,159 | +1,160 |
| Opus v2 (exit T1) | 183 | 43.7 % | 31.7 % | +1,096 | +62,462 | +3,190 |
| Opus v3 (exit T1) | 171 | 43.9 % | 32.7 % | +720 | +41,058 | +2,853 |
| Fable (exit T3) | 239 | 39.3 % | 39.3 % | -1,178 | -67,154 | +3,226 |
| **Fable-OP (exit T3)** | 139 | 52.5 % | 33.1 % | **+4,428** | +252,373 | +4,669 |

**Downtrend: 49 sessions**

| Model | Trades | Reach T1 | Stopped | Net per session (Rs) | Total net (Rs) | Options est. per session (Rs) |
|---|---:|---:|---:|---:|---:|---:|
| Opus (exit T1) | 155 | 40.6 % | 23.2 % | +3,946 | +193,360 | +3,988 |
| Opus v2 (exit T1) | 137 | 50.4 % | 22.6 % | +6,823 | +334,314 | +5,434 |
| **Opus v3 (exit T1)** | 133 | 51.9 % | 20.3 % | **+7,552** | +370,024 | +5,702 |
| Fable (exit T3) | 161 | 42.2 % | 37.9 % | +4,194 | +205,516 | +5,516 |
| Fable-OP (exit T3) | 65 | 56.9 % | 33.8 % | +2,997 | +146,862 | +3,017 |

## Earlier dates, stand-in prices, 3 Nov 2025 to 11 May 2026 (127 sessions), trend rule 1

**Uptrend: 36 sessions**

| Model | Trades | Reach T1 | Stopped | Net per session (Rs) | Total net (Rs) |
|---|---:|---:|---:|---:|---:|
| Opus (exit T1) | 74 | 31.1 % | 23.0 % | -1,666 | -59,979 |
| Opus v2 (exit T1) | 105 | 40.0 % | 36.2 % | -4,138 | -148,952 |
| Opus v3 (exit T1) | 103 | 39.8 % | 35.9 % | -4,007 | -144,246 |
| Fable (exit T3) | 159 | 39.0 % | 42.1 % | -7,614 | -274,095 |
| **Fable-OP (exit T3)** | 81 | 43.2 % | 38.3 % | **-683** | -24,598 |

**Sideways: 53 sessions**

| Model | Trades | Reach T1 | Stopped | Net per session (Rs) | Total net (Rs) |
|---|---:|---:|---:|---:|---:|
| Opus (exit T1) | 174 | 24.1 % | 25.9 % | -1,926 | -102,096 |
| Opus v2 (exit T1) | 147 | 36.7 % | 34.7 % | -1,843 | -97,681 |
| Opus v3 (exit T1) | 140 | 38.6 % | 33.6 % | -667 | -35,337 |
| Fable (exit T3) | 221 | 42.1 % | 38.9 % | -1,465 | -77,639 |
| **Fable-OP (exit T3)** | 94 | 48.9 % | 35.1 % | **+2,866** | +151,884 |

**Downtrend: 38 sessions**

| Model | Trades | Reach T1 | Stopped | Net per session (Rs) | Total net (Rs) |
|---|---:|---:|---:|---:|---:|
| Opus (exit T1) | 140 | 33.6 % | 25.7 % | -470 | -17,842 |
| Opus v2 (exit T1) | 123 | 36.6 % | 26.0 % | +1,146 | +43,541 |
| **Opus v3 (exit T1)** | 123 | 36.6 % | 26.0 % | **+1,342** | +50,986 |
| Fable (exit T3) | 123 | 39.0 % | 38.2 % | -4,600 | -174,788 |
| Fable-OP (exit T3) | 57 | 47.4 % | 28.1 % | -1,275 | -48,437 |

## Same earlier dates, trend rule 2

**Uptrend: 27 sessions**

| Model | Trades | Reach T1 | Stopped | Net per session (Rs) | Total net (Rs) |
|---|---:|---:|---:|---:|---:|
| Opus (exit T1) | 89 | 23.6 % | 22.5 % | -1,098 | -29,638 |
| Opus v2 (exit T1) | 78 | 37.2 % | 28.2 % | -876 | -23,659 |
| Opus v3 (exit T1) | 75 | 36.0 % | 29.3 % | -1,533 | -41,382 |
| Fable (exit T3) | 116 | 37.1 % | 43.1 % | -9,573 | -258,466 |
| **Fable-OP (exit T3)** | 52 | 46.2 % | 30.8 % | **+1,236** | +33,364 |

**Sideways: 68 sessions**

| Model | Trades | Reach T1 | Stopped | Net per session (Rs) | Total net (Rs) |
|---|---:|---:|---:|---:|---:|
| Opus (exit T1) | 176 | 27.3 % | 25.0 % | -2,177 | -148,037 |
| Opus v2 (exit T1) | 190 | 37.9 % | 36.3 % | -3,025 | -205,669 |
| Opus v3 (exit T1) | 184 | 39.7 % | 34.8 % | -1,778 | -120,897 |
| Fable (exit T3) | 291 | 41.9 % | 38.5 % | -1,846 | -125,528 |
| **Fable-OP (exit T3)** | 136 | 47.1 % | 38.2 % | **+924** | +62,843 |

**Downtrend: 32 sessions**

| Model | Trades | Reach T1 | Stopped | Net per session (Rs) | Total net (Rs) |
|---|---:|---:|---:|---:|---:|
| Opus (exit T1) | 123 | 35.0 % | 27.6 % | -70 | -2,243 |
| Opus v2 (exit T1) | 107 | 37.4 % | 28.0 % | +820 | +26,236 |
| **Opus v3 (exit T1)** | 107 | 37.4 % | 28.0 % | **+1,053** | +33,682 |
| Fable (exit T3) | 96 | 39.6 % | 39.6 % | -4,454 | -142,527 |
| Fable-OP (exit T3) | 44 | 45.5 % | 27.3 % | -542 | -17,358 |

## Where the money came from: longs and shorts (real futures, trend rule 1)

| Market | Model | Longs | Long net (Rs) | Shorts | Short net (Rs) |
|---|---|---:|---:|---:|---:|
| Uptrend | Opus (exit T1) | 52 | -69,124 | 17 | +33,125 |
| Uptrend | Opus v2 (exit T1) | 54 | +125,340 | 20 | +20,443 |
| Uptrend | Opus v3 (exit T1) | 46 | +113,938 | 20 | +20,443 |
| Uptrend | Fable (exit T3) | 80 | +182,649 | 19 | -38,202 |
| Uptrend | Fable-OP (exit T3) | 54 | +300,163 | 5 | -43,733 |
| Sideways | Opus (exit T1) | 125 | +108,269 | 85 | +72,701 |
| Sideways | Opus v2 (exit T1) | 117 | +178,661 | 78 | +42,792 |
| Sideways | Opus v3 (exit T1) | 107 | +219,754 | 80 | +54,886 |
| Sideways | Fable (exit T3) | 208 | +220,488 | 68 | -170,086 |
| Sideways | Fable-OP (exit T3) | 117 | +297,979 | 14 | +76,967 |
| Downtrend | Opus (exit T1) | 32 | -71,125 | 58 | +176,514 |
| Downtrend | Opus v2 (exit T1) | 27 | -20,771 | 57 | +181,817 |
| Downtrend | Opus v3 (exit T1) | 24 | -8,708 | 58 | +188,726 |
| Downtrend | Fable (exit T3) | 49 | -73,116 | 51 | +351,805 |
| Downtrend | Fable-OP (exit T3) | 27 | -16,845 | 16 | +87,760 |

## By the day's own direction (known only afterwards)

This cannot be used to choose a model in the morning. It shows what kind of day each model likes. Up day: Nifty closed up 0.4 % or more. Down day: down 0.4 % or more.

**Up day: 36 sessions**

| Model | Trades | Reach T1 | Stopped | Net per session (Rs) | Total net (Rs) | Options est. per session (Rs) |
|---|---:|---:|---:|---:|---:|---:|
| Opus (exit T1) | 65 | 33.8 % | 21.5 % | +2,541 | +91,471 | +2,236 |
| Opus v2 (exit T1) | 57 | 56.1 % | 28.1 % | +3,097 | +111,479 | +3,060 |
| Opus v3 (exit T1) | 54 | 59.3 % | 25.9 % | +3,840 | +138,244 | +3,340 |
| **Fable (exit T3)** | 129 | 40.3 % | 31.0 % | **+7,043** | +253,551 | +6,806 |
| Fable-OP (exit T3) | 55 | 58.2 % | 29.1 % | +6,888 | +247,961 | +5,422 |

**Flat day: 57 sessions**

| Model | Trades | Reach T1 | Stopped | Net per session (Rs) | Total net (Rs) | Options est. per session (Rs) |
|---|---:|---:|---:|---:|---:|---:|
| Opus (exit T1) | 165 | 34.5 % | 23.6 % | +999 | +56,946 | +2,190 |
| Opus v2 (exit T1) | 166 | 47.0 % | 28.3 % | +3,950 | +225,161 | +4,272 |
| Opus v3 (exit T1) | 153 | 48.4 % | 28.1 % | +4,161 | +237,149 | +4,225 |
| Fable (exit T3) | 213 | 39.4 % | 42.7 % | -5,871 | -334,654 | +701 |
| **Fable-OP (exit T3)** | 120 | 53.3 % | 30.0 % | **+4,412** | +251,464 | +4,223 |

**Down day: 33 sessions**

| Model | Trades | Reach T1 | Stopped | Net per session (Rs) | Total net (Rs) | Options est. per session (Rs) |
|---|---:|---:|---:|---:|---:|---:|
| Opus (exit T1) | 139 | 38.8 % | 25.9 % | +3,089 | +101,942 | +4,380 |
| Opus v2 (exit T1) | 130 | 44.6 % | 23.1 % | +5,807 | +191,644 | +5,590 |
| Opus v3 (exit T1) | 128 | 45.3 % | 21.9 % | +6,474 | +213,646 | +5,825 |
| **Fable (exit T3)** | 133 | 48.1 % | 33.1 % | **+16,807** | +554,642 | +12,568 |
| Fable-OP (exit T3) | 58 | 55.2 % | 36.2 % | +6,147 | +202,865 | +5,341 |

## Files

- `v2/regime.py` builds everything above; `v2/regime.json` holds the numbers; `v2/switch.log` holds the switch-rule totals and the month-by-month split.

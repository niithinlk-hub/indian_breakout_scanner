# Fable-OP vs Opus: scanner replay, 21 to 30 Oct 2026

Scanner's own replay code and default rules (setups A + B, scan 09:17 to 14:15, at most 6 trades a day, risk budget Rs 15,000 a trade).
Live rule: first 6 signals of the day scoring at or above 75. Entry at the next minute's open, anything still open squared off at the close.
Net figures are futures rupees after charges and assumed slippage, exiting at T1 (1R). 20 Oct was a market holiday and 31 Oct a Saturday. All October days are priced on the November futures contract, because October contracts have expired; the live scanner would have used the October contract only on 21 Oct. Option legs are left out: several were not priced.

## By session

| Session | Signals | Opus trades | Opus T1 hit / stopped / closed at EOD | Opus futures net | Fable-OP trades | Fable-OP T1 hit / stopped / closed at EOD | Fable-OP futures net |
|---|---|---|---|---|---|---|---|
| 2026-10-21 | 118 | 6 | 1 / 0 / 5 | -3,787 | 1 | 0 / 0 / 1 | +528 |
| 2026-10-22 | 126 | 4 | 1 / 2 / 1 | -5,380 | 1 | 1 / 0 / 0 | +6,847 |
| 2026-10-23 | 142 | 6 | 2 / 1 / 3 | +3,497 | 3 | 0 / 2 / 1 | -20,112 |
| 2026-10-26 | 45 | 2 | 1 / 1 / 0 | -295 | 4 | 2 / 2 / 0 | -3,053 |
| 2026-10-27 | 26 | 3 | 0 / 1 / 2 | -9,325 | 2 | 1 / 0 / 1 | +13,380 |
| 2026-10-28 | 34 | 6 | 2 / 4 / 0 | -28,863 | 1 | 0 / 0 / 1 | -821 |
| 2026-10-29 | 24 | 2 | 1 / 1 / 0 | +2,145 | 1 | 1 / 0 / 0 | +11,466 |
| 2026-10-30 | 23 | 4 | 2 / 0 / 2 | +15,400 | 1 | 0 / 0 / 1 | -5,545 |
| **Total** | | **33** | **10 / 10 / 13** | **-26,608** | **14** | **5 / 4 / 5** | **+2,690** |

## Fable-OP trades

| Date | Time | Symbol | Setup | Side | Qty | Score | Entry | Stop | T1 | Result | Exit time | R | Futures net |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10-21 | 09:21 | INFY | A | LONG | 800 | 77.6 | 1169.85 | 1152.7 | 1187.3 | closed at EOD | 15:29 | +0.11 | +528 |
| 10-22 | 09:47 | INDHOTEL | A | LONG | 1000 | 92.1 | 776.85 | 767.6 | 784.5 | T1 hit | 10:14 | +0.83 | +6,847 |
| 10-23 | 09:17 | INFY | A | LONG | 400 | 82.6 | 1195.85 | 1177.6 | 1214.2 | stopped | 09:55 | -1.00 | -7,804 |
| 10-23 | 09:19 | COFORGE | A | LONG | 475 | 78.6 | 1996.8 | 1973.0 | 2018.6 | stopped | 09:22 | -1.00 | -12,260 |
| 10-23 | 09:59 | IDFCFIRSTB | B | SHORT | 9275 | 78.2 | 72.68 | 73.94 | 71.5 | closed at EOD | 15:29 | +0.06 | -49 |
| 10-26 | 09:17 | KOTAKBANK | A | LONG | 2000 | 95.0 | 447.0 | 441.1 | 452.8 | stopped | 09:24 | -1.00 | -12,702 |
| 10-26 | 09:18 | AUBANK | B | SHORT | 500 | 89.6 | 863.6 | 883.1 | 847.1 | stopped | 09:42 | -1.00 | -10,216 |
| 10-26 | 09:18 | CUB | B | SHORT | 4650 | 77.4 | 214.49 | 216.9 | 211.52 | T1 hit | 09:40 | +1.23 | +12,804 |
| 10-26 | 09:21 | DRREDDY | A | LONG | 625 | 79.6 | 1259.4 | 1245.0 | 1272.0 | T1 hit | 09:24 | +0.88 | +7,062 |
| 10-27 | 09:17 | ATHERENERG | A | LONG | 375 | 79.3 | 1633.6 | 1596.8 | 1670.4 | T1 hit | 10:00 | +1.00 | +13,151 |
| 10-27 | 09:25 | RECLTD | B | SHORT | 1575 | 77.5 | 284.6 | 289.7 | 279.5 | closed at EOD | 15:29 | +0.09 | +229 |
| 10-28 | 13:01 | HEROMOTOCO | A | LONG | 150 | 80.6 | 5343.0 | 5268.5 | 5416.5 | closed at EOD | 15:29 | +0.00 | -821 |
| 10-29 | 09:17 | ADANIPORTS | A | LONG | 475 | 92.1 | 1804.2 | 1777.0 | 1830.2 | T1 hit | 10:30 | +0.96 | +11,466 |
| 10-30 | 09:17 | TRENT | A | LONG | 225 | 94.8 | 3055.5 | 3014.0 | 3096.0 | closed at EOD | 15:29 | -0.52 | -5,545 |

## Opus trades

| Date | Time | Symbol | Setup | Side | Qty | Score | Entry | Stop | T1 | Result | Exit time | R | Futures net |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10-21 | 11:40 | ATHERENERG | B | SHORT | 375 | 97.7 | 1397.0 | 1425.6 | 1368.4 | closed at EOD | 15:29 | -0.45 | -5,392 |
| 10-21 | 11:40 | ETERNAL | B | SHORT | 2425 | 98.6 | 313.4 | 319.15 | 308.05 | T1 hit | 14:28 | +0.93 | +12,196 |
| 10-21 | 11:40 | IREDA | B | SHORT | 9050 | 95.7 | 99.25 | 100.48 | 97.74 | closed at EOD | 15:29 | +0.03 | -552 |
| 10-21 | 11:40 | PGEL | B | SHORT | 950 | 95.7 | 494.2 | 503.85 | 484.55 | closed at EOD | 15:29 | +0.07 | +165 |
| 10-21 | 11:40 | SONACOMS | B | SHORT | 1225 | 98.8 | 750.25 | 762.7 | 741.2 | closed at EOD | 15:29 | -0.38 | -6,755 |
| 10-21 | 11:40 | SUZLON | B | SHORT | 12700 | 97.3 | 39.15 | 39.84 | 38.52 | closed at EOD | 15:29 | -0.33 | -3,449 |
| 10-22 | 09:17 | PAGEIND | B | SHORT | 20 | 81.3 | 34370.0 | 34760.0 | 33970.0 | stopped | 10:23 | -1.00 | -8,513 |
| 10-22 | 09:20 | KEI | B | SHORT | 175 | 79.6 | 3895.0 | 3966.4 | 3824.0 | T1 hit | 10:16 | +1.39 | +16,606 |
| 10-22 | 09:21 | SONACOMS | B | SHORT | 1225 | 76.3 | 740.55 | 748.8 | 729.3 | stopped | 09:48 | -1.00 | -11,032 |
| 10-22 | 10:07 | VMM | B | SHORT | 4850 | 90.0 | 86.54 | 87.96 | 84.66 | closed at EOD | 15:29 | -0.29 | -2,441 |
| 10-23 | 09:19 | COFORGE | A | LONG | 475 | 83.5 | 1996.8 | 1973.0 | 2018.6 | stopped | 09:22 | -1.00 | -12,260 |
| 10-23 | 09:59 | COLPAL | B | SHORT | 275 | 93.0 | 1599.8 | 1649.1 | 1550.9 | closed at EOD | 15:29 | +0.10 | +876 |
| 10-23 | 09:59 | CUB | B | SHORT | 2325 | 91.2 | 220.85 | 224.74 | 216.98 | closed at EOD | 15:29 | -0.54 | -5,450 |
| 10-23 | 09:59 | KFINTECH | B | SHORT | 575 | 95.1 | 800.1 | 815.0 | 787.5 | T1 hit | 12:41 | +0.85 | +6,755 |
| 10-23 | 09:59 | PNBHOUSING | B | SHORT | 650 | 95.5 | 1102.4 | 1118.8 | 1085.4 | T1 hit | 12:51 | +1.04 | +10,314 |
| 10-23 | 09:59 | UJJIVANSFB | B | SHORT | 8000 | 92.1 | 58.5 | 60.16 | 56.84 | closed at EOD | 15:29 | +0.28 | +3,262 |
| 10-26 | 09:18 | AUBANK | B | SHORT | 500 | 76.0 | 863.6 | 883.1 | 847.1 | stopped | 09:42 | -1.00 | -10,216 |
| 10-26 | 09:18 | UJJIVANSFB | B | SHORT | 8000 | 82.1 | 56.17 | 57.09 | 54.87 | T1 hit | 09:27 | +1.41 | +9,921 |
| 10-27 | 09:25 | RECLTD | B | SHORT | 1575 | 90.4 | 284.6 | 289.7 | 279.5 | closed at EOD | 15:29 | +0.09 | +229 |
| 10-27 | 13:11 | WAAREEENER | B | SHORT | 175 | 84.0 | 2259.8 | 2302.4 | 2212.0 | closed at EOD | 15:29 | +0.42 | +2,687 |
| 10-27 | 14:09 | ICICILIFE | B | SHORT | 1850 | 81.1 | 403.2 | 409.4 | 397.0 | stopped | 15:09 | -1.00 | -12,240 |
| 10-28 | 09:17 | NAVINFLUOR | A | LONG | 75 | 86.2 | 8448.0 | 8335.0 | 8561.0 | T1 hit | 09:56 | +1.00 | +7,810 |
| 10-28 | 09:49 | SAGILITY | A | LONG | 12000 | 76.1 | 46.13 | 45.34 | 46.92 | stopped | 13:25 | -1.00 | -10,055 |
| 10-28 | 10:22 | MFSL | B | SHORT | 400 | 91.0 | 1199.2 | 1219.6 | 1177.0 | stopped | 11:54 | -1.00 | -8,672 |
| 10-28 | 10:56 | MANKIND | A | LONG | 250 | 78.9 | 2547.9 | 2508.8 | 2588.4 | stopped | 12:17 | -1.01 | -10,555 |
| 10-28 | 11:17 | UNITDSPR | B | SHORT | 800 | 92.5 | 1223.2 | 1239.0 | 1210.4 | stopped | 11:25 | -1.00 | -13,635 |
| 10-28 | 12:55 | KPITTECH | A | LONG | 775 | 99.4 | 544.8 | 534.55 | 553.45 | T1 hit | 13:18 | +0.84 | +6,244 |
| 10-29 | 09:28 | APLAPOLLO | A | LONG | 350 | 75.2 | 2240.0 | 2212.0 | 2265.0 | stopped | 14:28 | -1.00 | -10,597 |
| 10-29 | 11:19 | ETERNAL | A | LONG | 2425 | 79.1 | 333.3 | 327.9 | 338.9 | T1 hit | 13:35 | +1.04 | +12,743 |
| 10-30 | 09:25 | INOXWIND | B | SHORT | 6400 | 75.6 | 57.95 | 59.85 | 56.03 | T1 hit | 14:01 | +1.01 | +11,886 |
| 10-30 | 09:26 | SUZLON | B | SHORT | 12700 | 84.3 | 35.37 | 36.06 | 34.66 | T1 hit | 09:39 | +1.03 | +8,538 |
| 10-30 | 10:10 | MFSL | B | SHORT | 400 | 76.2 | 1193.0 | 1212.4 | 1173.6 | closed at EOD | 15:29 | -0.69 | -5,869 |
| 10-30 | 10:17 | COROMANDEL | B | SHORT | 300 | 77.7 | 1682.7 | 1710.5 | 1654.9 | closed at EOD | 15:29 | +0.17 | +846 |

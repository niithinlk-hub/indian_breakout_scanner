# Fable-OP vs Opus: scanner replay, 3 to 13 Nov 2026

Scanner's own replay code and default rules (setups A + B, scan 09:17 to 14:15, at most 6 trades a day, risk budget Rs 15,000 a trade).
Live rule: first 6 signals of the day scoring at or above 75. Entry at the next minute's open, anything still open squared off at the close.
Net figures are futures rupees after charges and assumed slippage, exiting at T1 (1R). 10 Nov was a market holiday.

## By session

| Session | Signals | Opus trades | Opus T1 hit / stopped / closed at EOD | Opus futures net | Opus options net | Fable-OP trades | Fable-OP T1 hit / stopped / closed at EOD | Fable-OP futures net | Fable-OP options net |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-03 | 40 | 0 | 0 / 0 / 0 | +0 | +0 | 2 | 1 / 0 / 1 | +7,216 | +418 |
| 2026-11-04 | 50 | 4 | 2 / 0 / 2 | +24,682 | +15,199 | 2 | 2 / 0 / 0 | +20,619 | +11,606 |
| 2026-11-05 | 76 | 2 | 2 / 0 / 0 | +21,077 | +13,836 | 6 | 3 / 1 / 2 | +26,617 | +18,183 |
| 2026-11-06 | 29 | 6 | 4 / 1 / 1 | +30,236 | +24,179 | 2 | 1 / 1 / 0 | -5,331 | +460 |
| 2026-11-09 | 43 | 4 | 2 / 0 / 2 | +21,929 | +11,763 | 4 | 2 / 1 / 1 | -7,357 | +2,665 |
| 2026-11-11 | 72 | 2 | 0 / 2 / 0 | -22,047 | -10,254 | 2 | 1 / 0 / 1 | +7,560 | +5,066 |
| 2026-11-12 | 37 | 6 | 3 / 0 / 3 | +33,098 | +19,632 | 1 | 1 / 0 / 0 | +11,695 | +7,814 |
| 2026-11-13 | 19 | 6 | 3 / 1 / 2 | -2,928 | -167 | 0 | 0 / 0 / 0 | +0 | +0 |

## Fable-OP trades

| Date | Time | Symbol | Setup | Side | Qty | Score | Entry | Stop | T1 | Result | Exit time | R | Futures net | Option net |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 11-03 | 09:17 | IOC | A | LONG | 4875 | 85.0 | 138.4 | 136.53 | 140.47 | closed at EOD | 15:29 | -0.29 | -3,329 | -1,764 |
| 11-03 | 09:18 | MARICO | A | LONG | 1200 | 80.0 | 845.2 | 835.65 | 854.85 | T1 hit | 09:56 | +1.01 | +10,545 | +2,182 |
| 11-04 | 09:17 | ITC | A | LONG | 3450 | 78.1 | 278.3 | 274.35 | 282.35 | T1 hit | 09:20 | +1.03 | +12,988 | +9,615 |
| 11-04 | 09:17 | UNOMINDA | A | LONG | 550 | 83.8 | 1168.8 | 1154.1 | 1183.9 | T1 hit | 10:27 | +1.03 | +7,631 | +1,991 |
| 11-05 | 09:17 | AMBUJACEM | A | LONG | 2400 | 81.5 | 389.45 | 383.95 | 395.25 | closed at EOD | 15:29 | +0.28 | +2,768 | +2,170 |
| 11-05 | 09:17 | ASHOKLEY | A | LONG | 5000 | 85.0 | 163.5 | 160.85 | 166.23 | T1 hit | 09:27 | +1.03 | +12,804 | +5,769 |
| 11-05 | 09:17 | BSE | A | LONG | 200 | 85.0 | 3708.9 | 3662.7 | 3755.3 | T1 hit | 09:27 | +1.00 | +8,510 | +4,126 |
| 11-05 | 09:17 | EICHERMOT | A | LONG | 100 | 85.0 | 7604.0 | 7515.0 | 7700.0 | T1 hit | 09:46 | +1.08 | +8,812 | +3,927 |
| 11-05 | 09:17 | HYUNDAI | A | LONG | 550 | 85.0 | 2109.9 | 2086.7 | 2134.9 | stopped | 09:21 | -1.00 | -13,918 | -1,322 |
| 11-05 | 09:17 | MARUTI | A | LONG | 50 | 85.0 | 12506.0 | 12275.0 | 12747.0 | closed at EOD | 15:29 | +0.72 | +7,643 | +3,514 |
| 11-06 | 09:17 | CGPOWER | B | SHORT | 850 | 85.4 | 772.0 | 784.55 | 761.25 | T1 hit | 09:25 | +0.86 | +8,459 | +6,079 |
| 11-06 | 09:17 | MPHASIS | A | LONG | 275 | 91.1 | 2699.6 | 2652.2 | 2746.8 | stopped | 09:19 | -1.00 | -13,790 | -5,620 |
| 11-09 | 09:17 | BIOCON | A | LONG | 2500 | 88.5 | 372.3 | 367.25 | 377.45 | closed at EOD | 15:29 | -0.59 | -8,440 | -4,081 |
| 11-09 | 09:17 | MANKIND | A | LONG | 250 | 79.0 | 2624.6 | 2589.9 | 2656.1 | T1 hit | 09:24 | +0.91 | +7,189 | +7,773 |
| 11-09 | 09:17 | SBIN | A | LONG | 750 | 78.3 | 1031.35 | 1020.95 | 1042.45 | T1 hit | 09:37 | +1.07 | +7,525 | +5,703 |
| 11-09 | 09:38 | SIEMENS | A | LONG | 175 | 89.0 | 3699.5 | 3625.4 | 3764.2 | stopped | 12:31 | -1.00 | -13,630 | -6,729 |
| 11-11 | 09:17 | WAAREEENER | A | LONG | 175 | 75.9 | 2503.0 | 2450.6 | 2552.8 | T1 hit | 09:26 | +0.95 | +8,239 | +7,461 |
| 11-11 | 09:24 | MAHABANK | A | LONG | 6500 | 78.3 | 90.3 | 89.1 | 91.78 | closed at EOD | 15:29 | -0.01 | -679 | -2,395 |
| 11-12 | 09:18 | ICICILIFE | A | LONG | 1850 | 79.3 | 464.2 | 457.0 | 471.0 | T1 hit | 09:25 | +0.94 | +11,695 | +7,814 |

## Opus trades

| Date | Time | Symbol | Setup | Side | Qty | Score | Entry | Stop | T1 | Result | Exit time | R | Futures net | Option net |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 11-04 | 09:27 | VOLTAS | A | LONG | 750 | 75.6 | 1058.5 | 1043.1 | 1073.9 | T1 hit | 09:38 | +1.00 | +10,728 | +8,072 |
| 11-04 | 10:15 | NBCC | A | LONG | 6500 | 84.0 | 77.09 | 74.82 | 79.26 | closed at EOD | 15:29 | +0.46 | +6,224 | +3,705 |
| 11-04 | 12:43 | FORCEMOT | A | LONG | 25 | 87.9 | 18190.0 | 17866.0 | 18516.0 | closed at EOD | 15:29 | +0.18 | +988 | -553 |
| 11-04 | 13:20 | HINDALCO | A | LONG | 700 | 79.3 | 925.0 | 914.8 | 935.6 | T1 hit | 15:10 | +1.04 | +6,742 | +3,975 |
| 11-05 | 09:17 | 360ONE | A | LONG | 1000 | 77.4 | 1128.0 | 1113.5 | 1140.6 | T1 hit | 10:38 | +0.87 | +11,455 | +9,073 |
| 11-05 | 09:17 | LODHA | A | LONG | 625 | 79.9 | 1156.6 | 1144.8 | 1173.2 | T1 hit | 13:31 | +1.41 | +9,622 | +4,763 |
| 11-06 | 09:17 | ASTRAL | B | SHORT | 425 | 85.2 | 1281.7 | 1308.8 | 1250.4 | T1 hit | 09:21 | +1.16 | +12,733 | +7,676 |
| 11-06 | 09:19 | KALYANKJIL | A | LONG | 1350 | 87.1 | 569.9 | 561.6 | 578.2 | stopped | 09:26 | -1.00 | -11,987 | +971 |
| 11-06 | 09:35 | MCX | A | LONG | 225 | 84.6 | 3426.0 | 3375.6 | 3475.6 | T1 hit | 12:18 | +0.98 | +10,360 | +6,257 |
| 11-06 | 11:11 | FORCEMOT | A | LONG | 25 | 93.1 | 18967.0 | 18563.0 | 19417.0 | closed at EOD | 15:29 | +0.18 | +1,344 | -372 |
| 11-06 | 13:18 | HAVELLS | A | LONG | 500 | 91.9 | 1093.9 | 1075.6 | 1110.6 | T1 hit | 14:54 | +0.91 | +7,769 | +4,362 |
| 11-06 | 13:32 | TATASTEEL | A | LONG | 5500 | 78.1 | 184.87 | 182.64 | 186.88 | T1 hit | 13:48 | +0.90 | +10,018 | +5,285 |
| 11-09 | 11:28 | IRFC | A | LONG | 10850 | 78.7 | 81.75 | 80.55 | 83.03 | T1 hit | 14:48 | +1.07 | +12,974 | +8,446 |
| 11-09 | 11:29 | INOXWIND | A | LONG | 6400 | 78.6 | 66.93 | 65.6 | 68.3 | closed at EOD | 15:29 | +0.13 | +626 | -817 |
| 11-09 | 11:44 | PAGEIND | A | LONG | 20 | 88.4 | 36115.0 | 35695.0 | 36455.0 | T1 hit | 12:04 | +0.81 | +6,050 | +3,447 |
| 11-09 | 13:38 | NESTLEIND | A | LONG | 500 | 77.7 | 1289.9 | 1273.6 | 1306.8 | closed at EOD | 15:29 | +0.36 | +2,278 | +686 |
| 11-11 | 10:19 | ADANIENT | A | LONG | 309 | 75.7 | 2780.0 | 2746.0 | 2814.4 | stopped | 11:42 | -1.00 | -11,375 | -4,652 |
| 11-11 | 11:43 | NATIONALUM | A | LONG | 1875 | 81.9 | 331.8 | 326.45 | 336.95 | stopped | 13:06 | -1.00 | -10,672 | -5,602 |
| 11-12 | 09:26 | ABCAPITAL | A | LONG | 1550 | 83.7 | 408.15 | 403.05 | 413.55 | T1 hit | 09:40 | +1.06 | +7,706 | +5,265 |
| 11-12 | 09:31 | SBILIFE | A | LONG | 750 | 78.2 | 1801.3 | 1782.2 | 1816.8 | T1 hit | 10:41 | +0.81 | +10,265 | +8,066 |
| 11-12 | 09:34 | AUBANK | A | LONG | 1000 | 89.1 | 974.4 | 962.5 | 987.1 | closed at EOD | 15:29 | +0.33 | +2,909 | -517 |
| 11-12 | 09:46 | CAMS | A | LONG | 825 | 86.9 | 745.5 | 737.5 | 754.9 | closed at EOD | 15:29 | -0.29 | -2,537 | -1,746 |
| 11-12 | 10:07 | OBEROIRLTY | A | LONG | 350 | 77.8 | 1799.0 | 1778.6 | 1821.0 | T1 hit | 10:38 | +1.08 | +7,039 | +4,052 |
| 11-12 | 10:08 | GODREJPROP | A | LONG | 325 | 88.2 | 1859.7 | 1828.4 | 1891.6 | closed at EOD | 15:29 | +0.82 | +7,716 | +4,512 |
| 11-13 | 09:47 | GVT&D | A | LONG | 125 | 88.4 | 4308.5 | 4249.2 | 4370.8 | T1 hit | 09:58 | +1.05 | +7,215 | +5,242 |
| 11-13 | 09:54 | BLUESTARCO | A | LONG | 325 | 78.7 | 1607.2 | 1582.6 | 1635.2 | T1 hit | 10:56 | +1.14 | +8,542 | +4,819 |
| 11-13 | 10:08 | INDUSTOWER | A | LONG | 1700 | 84.6 | 399.6 | 392.7 | 406.5 | closed at EOD | 15:29 | -0.51 | -6,649 | -4,035 |
| 11-13 | 10:16 | BHEL | A | LONG | 2625 | 81.4 | 438.2 | 432.8 | 443.3 | closed at EOD | 15:29 | -0.50 | -8,240 | -5,462 |
| 11-13 | 10:17 | VMM | A | LONG | 9700 | 84.4 | 96.65 | 95.52 | 97.78 | T1 hit | 10:41 | +1.00 | +10,001 | +5,504 |
| 11-13 | 10:37 | SIEMENS | A | LONG | 175 | 77.9 | 3748.1 | 3673.3 | 3820.1 | stopped | 12:18 | -1.00 | -13,796 | -6,235 |

## How far to trust this

- A replay checks every stock every minute. On 13 Nov it found the same 21 signals as the live scanner's own log, 16 of them at the same minute; the other 5 were 1 to 17 minutes apart.
- That timing gap changed one of Opus's six trades on 13 Nov: the replay shows Opus at -2,928 for the day, the live paper ledger recorded -18,241.
- Slippage is assumed at 0.02% a side on futures and 0.25% on options. Most Fable-OP entries are at 09:18, where real slippage is likely higher.

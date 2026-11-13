# Options: Opus, Opus v2 and Opus v3 at T1; Fable and Fable-OP at T3

The option for each trade is the one the scanner picks: monthly expiry, strike nearest the signal price, a call for a long and a put for a short, same number of lots as the futures trade would have had. It is bought at the open of the entry minute and sold at the open of the first option candle after the futures leg reaches its exit (T1 or T3), its stop, or the end of the holding period. Option charges and 0.25 % slippage a side are included, as the scanner costs them. Nothing on the VPS was changed.

## 1. Real option prices: 21 Oct to 13 Nov 2026 (17 sessions)

Only the November option contracts can still be read, so this is the only period with real option prices. Every same-day figure reproduces the replay's own stored option result (274 legs checked, none different).

**Squared off at the close of the entry day**

| | Opus, exit T1 | Opus v2, exit T1 | Opus v3, exit T1 | Fable, exit T3 | Fable-OP, exit T3 |
|---|---|---|---|---|---|
| Trades | 65 | 54 | 52 | 58 | 33 |
| Trades with an option price | 60 | 50 | 48 | 56 | 32 |
| Option profit (Rs) | +75,984 | +67,670 | +80,078 | +1,52,097 | +1,02,661 |
| Trades in profit | 34 | 29 | 29 | 27 | 18 |
| Average winner / loser (Rs) | +4,977 / -3,586 | +4,969 / -3,639 | +5,211 / -3,738 | +9,357 / -3,467 | +8,747 / -3,913 |
| Worst trade (Rs) | -8,055 | -8,055 | -8,055 | -8,129 | -8,055 |
| 21-30 Oct / 2-13 Nov (Rs) | +9,774 / +66,210 | +19,862 / +47,808 | +19,718 / +60,361 | +2,620 / +1,49,478 | +16,165 / +86,496 |
| Days up / down | 10 / 6 | 13 / 2 | 13 / 2 | 9 / 6 | 10 / 5 |
| Largest fall from a peak (Rs) | -23,770 | -10,836 | -10,981 | -18,247 | -11,281 |
| Average premium paid a trade (Rs) | 21,291 | 22,224 | 22,192 | 24,277 | 22,144 |
| Most premium in use at once (Rs) | 1,47,286 | 1,54,643 | 1,54,643 | 1,59,902 | 1,22,838 |
| Profit as % of premium paid | 5.9 % | 6.1 % | 7.5 % | 11.2 % | 14.5 % |
| Futures profit on the same trades (Rs) | +73,139 | +60,851 | +94,692 | +1,80,724 | +1,68,211 |

**Held across days until the target or the stop (open trades marked to the 13 Nov close)**

| | Opus, exit T1 | Opus v2, exit T1 | Opus v3, exit T1 | Fable, exit T3 | Fable-OP, exit T3 |
|---|---|---|---|---|---|
| Trades with an option price | 65 | 54 | 52 | 57 | 33 |
| Option profit (Rs) | +95,503 | +60,867 | +86,601 | +2,21,495 | +1,61,731 |
| Trades in profit | 40 | 30 | 31 | 27 | 16 |
| Average winner / loser (Rs) | +5,138 / -4,401 | +5,959 / -4,912 | +5,997 / -4,729 | +13,392 / -4,670 | +16,970 / -6,458 |
| Worst trade (Rs) | -8,322 | -9,094 | -9,094 | -16,066 | -15,135 |
| 21-30 Oct / 2-13 Nov (Rs) | +27,044 / +68,459 | +11,968 / +48,898 | +20,545 / +66,055 | -5,836 / +2,27,331 | -12,798 / +1,74,529 |
| Days up / down | 10 / 6 | 10 / 5 | 11 / 4 | 10 / 5 | 9 / 6 |
| Largest fall from a peak (Rs) | -24,341 | -25,979 | -17,403 | -38,033 | -28,182 |
| Most premium in use at once (Rs) | 2,59,963 (8 open) | 2,67,321 (8 open) | 2,67,321 (8 open) | 2,40,808 (12 open) | 1,40,088 (7 open) |
| Average trading days held | 0.5 | 0.5 | 0.5 | 0.8 | 1.0 |
| Futures profit on the same trades (Rs) | +1,59,593 | +67,992 | +1,18,121 | +2,80,959 | +2,95,079 |

## 2. Why options change the ranking

In this period, by how the futures leg ended (all 146 trades, same day):

| Futures leg ended | Futures result a trade (Rs) | Option result a trade (Rs) | Share kept by the option |
|---|---|---|---|
| Reached T1 | +9,198 | +5,528 | 60 % |
| Stopped out (exit-T1 plan) | -11,514 | -4,343 | 38 % |
| Reached T3 | +23,286 | +14,545 | 62 % |
| Stopped out (exit-T3 plan) | -11,473 | -4,472 | 39 % |

A stop-out costs well under half as much in the option as in the future, while a target keeps about 60 %. So models with many stop-outs (Fable above all) look much better in options than in futures, and the gap between the models narrows.

## 3. Six months, estimated: 12 May to 11 Nov 2026 (126 sessions)

The May to October option contracts have expired and cannot be read. These figures convert each six-month futures result with the shares in section 2 (plus the two for trades squared off at the close). They are estimates, same-day exit, every signal taken. Applied back to 21 Oct - 13 Nov, the conversion gives Opus +74,574 (real +75,984), v2 +64,755 (+67,670), v3 +81,362 (+80,078), Fable +1,54,058 (+1,52,097), Fable-OP +1,20,936 (+1,02,661).

| | Opus, exit T1 | Opus v2, exit T1 | Opus v3, exit T1 | Fable, exit T3 | Fable-OP, exit T3 |
|---|---|---|---|---|---|
| Trades | 369 | 353 | 335 | 475 | 233 |
| Futures profit, real (Rs) | +2,50,359 | +5,28,284 | +5,89,038 | +4,73,539 | +7,02,290 |
| Option profit, estimated (Rs) | +3,49,874 | +5,38,147 | +5,53,263 | +6,99,737 | +6,12,190 |
| Range from the conversion alone (Rs) | +2,59,632 to +4,35,540 | +4,49,893 to +6,21,950 | +4,69,973 to +6,32,327 | +5,48,556 to +8,46,488 | +5,34,163 to +6,87,242 |
| 12 May - 31 Aug / 1 Sep - 11 Nov (Rs) | +2,05,786 / +1,44,088 | +3,29,998 / +2,08,149 | +3,26,395 / +2,26,869 | +2,93,309 / +4,06,427 | +3,87,668 / +2,24,522 |
| Months in profit | 7 of 7 | 7 of 7 | 7 of 7 | 7 of 7 | 7 of 7 |
| Largest fall from a peak (Rs) | -21,714 | -29,444 | -29,444 | -61,153 | -31,743 |

Estimated option profit by month (Rs):

| Month | Opus, exit T1 | Opus v2, exit T1 | Opus v3, exit T1 | Fable, exit T3 | Fable-OP, exit T3 |
|---|---|---|---|---|---|
| 2026-05 | +31,687 | +63,749 | +57,419 | +26,273 | +37,404 |
| 2026-06 | +93,836 | +1,03,115 | +1,07,501 | +67,636 | +50,303 |
| 2026-07 | +32,676 | +99,525 | +99,909 | +1,05,519 | +1,73,211 |
| 2026-08 | +47,587 | +63,610 | +61,566 | +93,882 | +1,26,750 |
| 2026-09 | +54,975 | +1,32,242 | +1,25,877 | +1,58,633 | +78,062 |
| 2026-10 | +43,651 | +35,560 | +44,475 | +94,671 | +60,301 |
| 2026-11 | +45,461 | +40,347 | +56,516 | +1,53,124 | +86,159 |

The range covers only the uncertainty in the conversion shares. It does not cover months whose option pricing differed from 21 Oct - 13 Nov (for example the September fall).

## 4. If option fills are worse than assumed

Stock options often trade with wide gaps between bid and offer. The figures above assume 0.25 % a side. Same trades at 0.5 % and 1 % a side:

| | Opus, exit T1 | Opus v2, exit T1 | Opus v3, exit T1 | Fable, exit T3 | Fable-OP, exit T3 |
|---|---|---|---|---|---|
| 17 sessions, same day, 0.25 % a side (Rs) | +75,984 | +67,670 | +80,078 | +1,52,097 | +1,02,661 |
| 17 sessions, same day, 0.5 % a side (Rs) | +69,375 | +61,918 | +74,526 | +1,44,886 | +98,843 |
| 17 sessions, same day, 1 % a side (Rs) | +56,158 | +50,413 | +63,421 | +1,30,463 | +91,208 |
| 17 sessions, held, 0.25 % a side (Rs) | +95,503 | +60,867 | +86,601 | +2,21,495 | +1,61,731 |
| 17 sessions, held, 0.5 % a side (Rs) | +88,268 | +54,612 | +80,513 | +2,13,860 | +1,57,669 |
| 17 sessions, held, 1 % a side (Rs) | +73,797 | +42,103 | +68,337 | +1,98,591 | +1,49,546 |
| Six months, estimated, 0.25 % a side (Rs) | +3,49,874 | +5,38,147 | +5,53,263 | +6,99,737 | +6,12,190 |
| Six months, estimated, 0.5 % a side (Rs) | +3,09,230 | +4,97,535 | +5,14,512 | +6,38,569 | +5,84,393 |
| Six months, estimated, 1 % a side (Rs) | +2,27,943 | +4,16,309 | +4,37,008 | +5,16,235 | +5,28,798 |

## 5. Capital

Average premium is about Rs 21,000 to 25,000 a trade. The most premium in use at once in the 17 sessions was Rs 1,22,838 to 1,59,902 when squared off daily and Rs 1,40,088 to 2,67,321 when held across days. So Rs 3 lakh a method covers every signal in options; the futures-margin limit of about two positions does not apply.

## 6. Limits

- Real option prices cover 17 sessions, and almost all the profit in them came in 2 - 13 Nov, a sharply rising market.
- The six-month figures are conversions, not prices, and are same-day only; held-across-days option results cannot be built for May to October.
- A few trades had no option candle to price (5 of Opus's 65 same-day, for example); they are left out of the option totals.
- Opus v2 and v3 exist only on paper. Opus's weights were tuned on 21 Oct - 9 Nov. These are replays, not live fills.

## 7. Every trade, 21 Oct to 13 Nov

| Date | Time | Symbol | Option | Qty | Models | Premium paid (Rs) | Same day: exit T1 (Rs) | Same day: exit T3 (Rs) | Held: exit T1 (Rs) | Held: exit T3 (Rs) |
|---|---|---|---|---|---|---|---|---|---|---|
| 10-21 | 09:17 | JSWSTEEL | 1260 CE 23 NOV 26 | 675 | F | 21,600 | -206 | -206 | -206 | -206 |
| 10-21 | 09:17 | PETRONET | 297.5 CE 23 NOV 26 | 3800 | F | - | no price | no price | no price | no price |
| 10-21 | 09:20 | DRREDDY | 1250 CE 23 NOV 26 | 625 | F | 22,750 | -2,113 | -2,113 | -2,113 | -2,113 |
| 10-21 | 09:21 | INFY | 1174 CE 23 NOV 26 | 800 | FOP v2 v3 | 29,920 | -188 | -188 | -7,754 | -7,754 |
| 10-21 | 11:40 | ATHERENERG | 1400 PE 23 NOV 26 | 375 | O v2 v3 | 29,550 | -1,814 | -1,814 | +2,050 | -6,444 |
| 10-21 | 11:40 | ETERNAL | 315 PE 23 NOV 26 | 2425 | O v2 v3 | 33,950 | +8,153 | -4,522 | +8,153 | -7,540 |
| 10-21 | 11:40 | IREDA | 99 PE 23 NOV 26 | 9050 | O v2 v3 | 54,300 | no price | no price | -447 | -447 |
| 10-21 | 11:40 | PGEL | 490 PE 23 NOV 26 | 950 | O | 22,562 | +780 | +780 | +2,104 | +2,246 |
| 10-21 | 11:40 | SONACOMS | 750 PE 23 NOV 26 | 1225 | O v2 v3 | 39,506 | -1,924 | -1,924 | +15,089 | -6,863 |
| 10-21 | 11:40 | SUZLON | 39 PE 23 NOV 26 | 12700 | O v2 v3 | 21,717 | +678 | +678 | +4,977 | +12,942 |
| 10-22 | 09:17 | BAJAJFINSV | 1660 PE 23 NOV 26 | 600 | F | 30,000 | -3,404 | -3,404 | -3,404 | -3,404 |
| 10-22 | 09:17 | DMART | 3200 PE 23 NOV 26 | 300 | F | 29,670 | +2,512 | +2,512 | +5,827 | -16,066 |
| 10-22 | 09:17 | NTPC | 297.5 PE 23 NOV 26 | 4500 | F | 31,500 | -279 | -279 | -279 | -279 |
| 10-22 | 09:17 | PAGEIND | 34500 PE 23 NOV 26 | 20 | O v2 v3 | 29,800 | no price | no price | -267 | -267 |
| 10-22 | 09:17 | POWERGRID | 242.5 PE 23 NOV 26 | 3800 | F | 25,840 | -3,264 | -3,264 | +3,924 | -2,508 |
| 10-22 | 09:17 | SBICARD | 550 PE 23 NOV 26 | 1600 | F | 30,000 | -826 | -826 | -826 | -826 |
| 10-22 | 09:17 | TATACONSUM | 960 PE 23 NOV 26 | 1650 | F | 49,582 | no price | no price | -413 | -413 |
| 10-22 | 09:20 | KEI | 3900 PE 23 NOV 26 | 175 | O v2 v3 | 28,166 | +9,937 | -6,379 | +9,937 | -6,379 |
| 10-22 | 09:21 | SONACOMS | 740 PE 23 NOV 26 | 1225 | O v2 v3 | 34,361 | -300 | -300 | -300 | -300 |
| 10-22 | 09:47 | INDHOTEL | 780 CE 23 NOV 26 | 1000 | FOP v2 v3 | 23,400 | +3,265 | +9,388 | +3,265 | +9,388 |
| 10-22 | 10:07 | VMM | 86 PE 23 NOV 26 | 4850 | O v2 v3 | 14,841 | -2,329 | -2,329 | +1,968 | -3,102 |
| 10-23 | 09:17 | INFY | 1194 CE 23 NOV 26 | 400 | FOP v2 v3 | 15,800 | -3,569 | -3,569 | -3,569 | -3,569 |
| 10-23 | 09:19 | COFORGE | 2000 CE 23 NOV 26 | 475 | O F FOP v2 v3 | 45,671 | -6,082 | -6,082 | -6,082 | -6,082 |
| 10-23 | 09:59 | COLPAL | 1600 PE 23 NOV 26 | 275 | O v2 v3 | 13,915 | +1,137 | +1,137 | -8,322 | -8,322 |
| 10-23 | 09:59 | CUB | 220 PE 23 NOV 26 | 2325 | O | 11,625 | no price | no price | -133 | -133 |
| 10-23 | 09:59 | IDFCFIRSTB | 73 PE 23 NOV 26 | 9275 | FOP | 30,051 | +1,578 | +1,578 | +3,610 | -15,135 |
| 10-23 | 09:59 | KFINTECH | 800 PE 23 NOV 26 | 575 | O v2 v3 | 17,825 | +4,401 | +5,804 | +4,401 | -2,926 |
| 10-23 | 09:59 | PNBHOUSING | 1100 PE 23 NOV 26 | 650 | O v2 v3 | 27,950 | +6,865 | +1,300 | +6,865 | -5,721 |
| 10-23 | 09:59 | UJJIVANSFB | 58 PE 23 NOV 26 | 8000 | O v2 v3 | 16,800 | +5,643 | +5,643 | +6,041 | +1,502 |
| 10-26 | 09:17 | KOTAKBANK | 445 CE 23 NOV 26 | 2000 | F FOP v2 v3 | 26,300 | -5,717 | -5,717 | -5,717 | -5,717 |
| 10-26 | 09:18 | AUBANK | 870 PE 23 NOV 26 | 500 | O FOP v2 v3 | 19,400 | -8,055 | -8,055 | -8,055 | -8,055 |
| 10-26 | 09:18 | CUB | 215 PE 23 NOV 26 | 4650 | FOP | 19,065 | no price | no price | -188 | -188 |
| 10-26 | 09:18 | TATACONSUM | 950 PE 23 NOV 26 | 1100 | F | 30,085 | +10,299 | +17,253 | +10,299 | +17,253 |
| 10-26 | 09:18 | UJJIVANSFB | 56 PE 23 NOV 26 | 8000 | O v2 v3 | 17,680 | no price | no price | -178 | -178 |
| 10-26 | 09:18 | UNITDSPR | 1240 PE 23 NOV 26 | 800 | F | 35,560 | -3,535 | -3,535 | -5,088 | -5,088 |
| 10-26 | 09:21 | DRREDDY | 1260 CE 23 NOV 26 | 625 | FOP v2 v3 | 25,094 | +6,675 | +10,564 | +6,675 | +10,564 |
| 10-26 | 09:21 | SBIN | 950 PE 23 NOV 26 | 750 | F | 20,362 | -4,043 | -4,043 | -4,043 | -4,043 |
| 10-26 | 09:25 | BANKBARODA | 230 PE 23 NOV 26 | 2925 | F | 24,687 | -3,840 | -3,840 | -3,840 | -3,840 |
| 10-26 | 09:25 | ITC | 257.5 PE 23 NOV 26 | 3450 | F | 25,702 | -4,702 | -4,702 | -4,702 | -4,702 |
| 10-27 | 09:17 | ATHERENERG | 1640 CE 23 NOV 26 | 375 | FOP v2 v3 | 27,862 | +6,225 | +4,937 | +6,225 | +15,502 |
| 10-27 | 09:21 | LAURUSLABS | 2080 CE 23 NOV 26 | 425 | F | 37,846 | +5,365 | +12,241 | +5,365 | +12,241 |
| 10-27 | 09:25 | RECLTD | 285 PE 23 NOV 26 | 1575 | O FOP v2 v3 | 14,411 | -859 | -859 | -5,014 | -5,014 |
| 10-27 | 09:26 | HINDUNILVR | 1780 PE 23 NOV 26 | 600 | F | 34,380 | +4,837 | -5,438 | +4,837 | -5,438 |
| 10-27 | 13:11 | WAAREEENER | 2260 PE 23 NOV 26 | 175 | O v2 v3 | 16,905 | +2,886 | +2,886 | +6,963 | -6,810 |
| 10-27 | 14:09 | ICICILIFE | 405 PE 23 NOV 26 | 1850 | O v2 v3 | 25,900 | -3,922 | -3,922 | -3,922 | -3,922 |
| 10-28 | 09:17 | HDFCBANK | 670 PE 23 NOV 26 | 1950 | F | 32,370 | -6,984 | -6,984 | -6,984 | -6,984 |
| 10-28 | 09:17 | ITC | 255 PE 23 NOV 26 | 3450 | F | 24,668 | -8,129 | -8,129 | -8,129 | -8,129 |
| 10-28 | 09:17 | NAVINFLUOR | 8400 CE 23 NOV 26 | 75 | O F | 27,750 | +1,988 | +7,551 | +1,988 | +943 |
| 10-28 | 09:32 | LAURUSLABS | 2160 CE 23 NOV 26 | 425 | F | 39,100 | +4,319 | +2,986 | +4,319 | +12,274 |
| 10-28 | 09:40 | DIVISLAB | 9600 CE 23 NOV 26 | 100 | F | 36,015 | +4,103 | -955 | +4,103 | +12,177 |
| 10-28 | 09:49 | SAGILITY | 46 CE 23 NOV 26 | 12000 | O | 22,920 | -5,114 | -5,114 | -5,114 | -5,114 |
| 10-28 | 10:22 | MFSL | 1200 PE 23 NOV 26 | 400 | O v2 v3 | 16,160 | -4,706 | -4,706 | -4,706 | -4,706 |
| 10-28 | 10:56 | MANKIND | 2540 CE 23 NOV 26 | 250 | O | 21,162 | -5,604 | -5,604 | -5,604 | -5,604 |
| 10-28 | 11:17 | UNITDSPR | 1220 PE 23 NOV 26 | 800 | O v2 v3 | 35,880 | -4,971 | -4,971 | -4,971 | -4,971 |
| 10-28 | 12:55 | KPITTECH | 540 CE 23 NOV 26 | 775 | O | 20,150 | +4,588 | +9,295 | +4,588 | +9,295 |
| 10-28 | 13:01 | HEROMOTOCO | 5350 CE 23 NOV 26 | 150 | FOP v2 | 25,628 | +145 | +145 | -8,577 | -8,577 |
| 10-28 | 13:21 | RELIANCE | 1170 PE 23 NOV 26 | 500 | v2 v3 | 17,875 | +1,464 | +1,464 | -4,037 | -4,037 |
| 10-29 | 09:17 | ADANIPORTS | 1800 CE 23 NOV 26 | 475 | FOP v2 v3 | 21,399 | +5,612 | +20,934 | +5,612 | +20,934 |
| 10-29 | 09:17 | FEDERALBNK | 350 CE 23 NOV 26 | 2500 | F | 21,375 | -1,823 | -1,823 | -6,303 | -6,303 |
| 10-29 | 09:28 | APLAPOLLO | 2240 CE 23 NOV 26 | 350 | O F | 25,550 | -6,403 | -6,403 | -6,403 | -6,403 |
| 10-29 | 09:37 | KOTAKBANK | 445 CE 23 NOV 26 | 2000 | F | 18,400 | +4,596 | +16,145 | +4,596 | +16,145 |
| 10-29 | 11:19 | ETERNAL | 335 CE 23 NOV 26 | 2425 | O | 20,976 | +6,679 | +7,282 | +6,679 | +17,422 |
| 10-30 | 09:17 | TRENT | 3050 CE 23 NOV 26 | 225 | FOP v2 v3 | 22,376 | -6,910 | -6,910 | -9,094 | -9,094 |
| 10-30 | 09:17 | ZYDUSLIFE | 1210 CE 23 NOV 26 | 450 | F | 17,348 | +4,283 | +11,675 | +4,283 | +11,675 |
| 10-30 | 09:25 | INOXWIND | 58 PE 23 NOV 26 | 6400 | O v2 v3 | 16,448 | +7,669 | +9,262 | +7,669 | -2,526 |
| 10-30 | 09:26 | SUZLON | 35 PE 23 NOV 26 | 12700 | O v2 v3 | 16,002 | +3,628 | +13,996 | +3,628 | +13,996 |
| 10-30 | 10:10 | MFSL | 1200 PE 23 NOV 26 | 400 | O v2 v3 | 16,060 | -3,172 | -3,172 | -6,478 | -6,478 |
| 10-30 | 10:17 | COROMANDEL | 1680 PE 23 NOV 26 | 300 | O v2 v3 | 1,560 | no price | no price | -59 | -59 |
| 11-02 | 09:17 | GRASIM | 3020 CE 23 NOV 26 | 250 | F | 15,850 | +4,092 | +5,212 | +4,092 | +13,413 |
| 11-02 | 09:17 | PHOENIXLTD | 2020 CE 23 NOV 26 | 350 | O F | 22,680 | -2,741 | -2,741 | +1,162 | +3,357 |
| 11-02 | 09:18 | HAL | 4900 CE 23 NOV 26 | 150 | F | 20,100 | -852 | -852 | +5,703 | +15,112 |
| 11-02 | 09:20 | LT | 3900 CE 23 NOV 26 | 350 | F | 23,188 | +6,873 | +7,343 | +6,873 | +20,863 |
| 11-02 | 09:50 | PGEL | 550 CE 23 NOV 26 | 950 | O | 17,575 | -5,237 | -5,237 | -6,514 | -6,514 |
| 11-03 | 09:17 | GAIL | 180 CE 23 NOV 26 | 3550 | F | 12,460 | +5,127 | +4,420 | +5,127 | +10,782 |
| 11-03 | 09:17 | IOC | 138 CE 23 NOV 26 | 4875 | FOP v2 v3 | 15,600 | -1,764 | -1,764 | +6,487 | +30,463 |
| 11-03 | 09:18 | MARICO | 850 CE 23 NOV 26 | 1200 | F FOP v2 v3 | 21,780 | +2,182 | +12,277 | +2,182 | +12,277 |
| 11-03 | 09:26 | HAL | 4900 CE 23 NOV 26 | 150 | F | 23,212 | +4,120 | +3,224 | +4,120 | +11,990 |
| 11-03 | 09:31 | JSWSTEEL | 1320 CE 23 NOV 26 | 675 | F | 18,022 | +391 | +391 | +4,927 | +15,747 |
| 11-04 | 09:17 | ICICIBANK | 1440 CE 23 NOV 26 | 700 | F | 15,155 | -4,654 | -4,654 | -4,654 | -4,654 |
| 11-04 | 09:17 | ITC | 277.5 CE 23 NOV 26 | 3450 | FOP v2 v3 | 17,250 | +9,615 | +3,947 | +9,615 | +23,525 |
| 11-04 | 09:17 | UNOMINDA | 1160 CE 23 NOV 26 | 550 | FOP v2 v3 | 28,050 | +1,991 | +5,222 | +1,991 | +16,173 |
| 11-04 | 09:18 | APOLLOHOSP | 8600 CE 23 NOV 26 | 125 | F | 24,231 | +2,985 | +2,985 | -4,675 | -9,659 |
| 11-04 | 09:18 | TITAN | 4600 CE 23 NOV 26 | 175 | F | 16,678 | +3,532 | +9,796 | +3,532 | +9,796 |
| 11-04 | 09:18 | TVSMOTOR | 4350 CE 23 NOV 26 | 175 | F | 16,651 | -771 | -771 | +4,552 | +11,120 |
| 11-04 | 09:19 | AUROPHARMA | 1700 CE 23 NOV 26 | 550 | F | 28,242 | +4,563 | -1,816 | +4,563 | +12,695 |
| 11-04 | 09:20 | ADANIPORTS | 1880 CE 23 NOV 26 | 475 | F | 20,188 | +7,229 | +5,810 | +7,229 | +21,321 |
| 11-04 | 09:27 | VOLTAS | 1060 CE 23 NOV 26 | 750 | O | 28,012 | +8,072 | +4,040 | +8,072 | +16,547 |
| 11-04 | 10:15 | NBCC | 77 CE 23 NOV 26 | 6500 | O | 17,680 | +3,705 | +3,705 | +4,417 | +23,960 |
| 11-04 | 12:43 | FORCEMOT | 18250 CE 23 NOV 26 | 25 | O | 12,730 | -553 | -553 | +2,866 | +10,899 |
| 11-04 | 13:20 | HINDALCO | 930 CE 23 NOV 26 | 700 | O | 16,940 | +3,975 | +4,393 | +3,975 | -5,852 |
| 11-05 | 09:17 | 360ONE | 1120 CE 23 NOV 26 | 1000 | O F | 32,350 | +9,073 | +15,594 | +9,073 | -2,824 |
| 11-05 | 09:17 | AMBUJACEM | 390 CE 23 NOV 26 | 2400 | FOP v2 v3 | 23,400 | +2,170 | +2,170 | -7,985 | -7,985 |
| 11-05 | 09:17 | ASHOKLEY | 162.5 CE 23 NOV 26 | 5000 | FOP v2 v3 | 28,150 | +5,769 | +20,404 | +5,769 | +20,404 |
| 11-05 | 09:17 | BAJAJFINSV | 1800 CE 23 NOV 26 | 600 | v3 | 20,400 | +7,150 | +20,232 | +7,150 | +20,232 |
| 11-05 | 09:17 | BSE | 3700 CE 23 NOV 26 | 200 | FOP v2 v3 | 22,720 | +4,126 | +15,316 | +4,126 | +15,316 |
| 11-05 | 09:17 | EICHERMOT | 7600 CE 23 NOV 26 | 100 | F FOP v2 v3 | 18,705 | +3,927 | +6,988 | +3,927 | +15,704 |
| 11-05 | 09:17 | GRASIM | 3220 CE 23 NOV 26 | 250 | F | 17,000 | +1,906 | +1,906 | -2,674 | -2,674 |
| 11-05 | 09:17 | HYUNDAI | 2120 CE 23 NOV 26 | 550 | FOP v2 | 16,912 | -1,322 | -1,322 | -1,322 | -1,322 |
| 11-05 | 09:17 | LODHA | 1160 CE 23 NOV 26 | 625 | O | 22,719 | +4,763 | +5,292 | +4,763 | -3,824 |
| 11-05 | 09:17 | MARUTI | 12500 CE 23 NOV 26 | 50 | FOP v2 v3 | 12,950 | +3,514 | +3,514 | +6,130 | +20,294 |
| 11-05 | 09:17 | UNOMINDA | 1220 CE 23 NOV 26 | 550 | F | 24,502 | +3,578 | +9,984 | +3,578 | +9,984 |
| 11-05 | 09:19 | ICICIBANK | 1460 CE 23 NOV 26 | 700 | F | 15,785 | +3,635 | +12,834 | +3,635 | +12,834 |
| 11-05 | 09:34 | TECHM | 1820 CE 23 NOV 26 | 600 | F | 28,470 | +7,210 | +1,625 | +7,210 | -3,453 |
| 11-06 | 09:17 | ASTRAL | 1280 PE 23 NOV 26 | 425 | O v2 v3 | 17,042 | +7,676 | +4,905 | +7,676 | -1,019 |
| 11-06 | 09:17 | CGPOWER | 770 PE 23 NOV 26 | 850 | FOP | 24,182 | +6,079 | +16,488 | +6,079 | +16,488 |
| 11-06 | 09:17 | MPHASIS | 2700 CE 23 NOV 26 | 275 | FOP v2 v3 | 26,111 | -5,620 | -5,620 | -5,620 | -5,620 |
| 11-06 | 09:19 | KALYANKJIL | 570 CE 23 NOV 26 | 1350 | O | 35,100 | +971 | +971 | +971 | +971 |
| 11-06 | 09:35 | MCX | 3450 CE 23 NOV 26 | 225 | O | 22,961 | +6,257 | +13,045 | +6,257 | +18,690 |
| 11-06 | 11:11 | FORCEMOT | 19000 CE 23 NOV 26 | 25 | O | 14,249 | -372 | -372 | +3,432 | +18,515 |
| 11-06 | 13:18 | HAVELLS | 1090 CE 23 NOV 26 | 500 | O | 13,000 | +4,362 | +12,202 | +4,362 | +14,293 |
| 11-06 | 13:32 | TATASTEEL | 185 CE 23 NOV 26 | 5500 | O | 26,840 | +5,285 | +6,216 | +5,285 | +17,168 |
| 11-09 | 09:17 | BIOCON | 370 CE 23 NOV 26 | 2500 | FOP v2 | 23,875 | -4,081 | -4,081 | -8,686 | -8,686 |
| 11-09 | 09:17 | MANKIND | 2620 CE 23 NOV 26 | 250 | F FOP v2 v3 | 16,275 | +7,773 | +16,758 | +7,773 | +16,758 |
| 11-09 | 09:17 | PNB | 127 CE 23 NOV 26 | 8000 | F | 25,440 | +3,748 | +17,049 | +3,748 | +17,049 |
| 11-09 | 09:17 | SBIN | 1030 CE 23 NOV 26 | 750 | FOP v2 v3 | 15,112 | +5,703 | +3,836 | +5,703 | +11,116 |
| 11-09 | 09:22 | CIPLA | 1420 CE 23 NOV 26 | 850 | F | 21,165 | -5,196 | -5,196 | -5,196 | -5,196 |
| 11-09 | 09:25 | UNIONBANK | 190 CE 23 NOV 26 | 4425 | F | 18,762 | +3,779 | +11,621 | +3,779 | +11,621 |
| 11-09 | 09:38 | SIEMENS | 3700 CE 23 NOV 26 | 175 | FOP v2 v3 | 20,186 | -6,729 | -6,729 | -6,729 | -6,729 |
| 11-09 | 11:28 | IRFC | 82 CE 23 NOV 26 | 10850 | O | 20,072 | +8,446 | +13,415 | +8,446 | +22,813 |
| 11-09 | 11:29 | INOXWIND | 67 CE 23 NOV 26 | 6400 | O | 17,984 | -817 | -817 | +2,751 | -3,429 |
| 11-09 | 11:44 | PAGEIND | 36000 CE 23 NOV 26 | 20 | O | 21,700 | +3,447 | +2,879 | +3,447 | +10,107 |
| 11-09 | 13:38 | NESTLEIND | 1290 CE 23 NOV 26 | 500 | O | 11,900 | +686 | +686 | +1,806 | -2,873 |
| 11-11 | 09:17 | FEDERALBNK | 345 CE 23 NOV 26 | 2500 | F | 18,500 | +3,301 | +13,132 | +3,301 | +13,132 |
| 11-11 | 09:17 | NAVINFLUOR | 9200 CE 23 NOV 26 | 75 | F | 17,336 | -5,021 | -5,021 | -5,021 | -5,021 |
| 11-11 | 09:17 | NYKAA | 360 CE 23 NOV 26 | 3125 | F | 24,688 | -3,807 | -3,807 | -3,807 | -3,807 |
| 11-11 | 09:17 | WAAREEENER | 2500 CE 23 NOV 26 | 175 | FOP v2 v3 | 9,625 | +7,461 | +2,974 | +7,461 | +16,608 |
| 11-11 | 09:18 | BAJAJ-AUTO | 11000 CE 23 NOV 26 | 75 | F | 15,375 | -1,430 | -1,430 | +4,954 | -4,051 |
| 11-11 | 09:21 | IDFCFIRSTB | 79 CE 23 NOV 26 | 18550 | F | 36,172 | +6,335 | +23,325 | +6,335 | +23,325 |
| 11-11 | 09:24 | MAHABANK | 90 CE 23 NOV 26 | 6500 | FOP v2 v3 | 19,955 | -2,395 | -2,395 | +2,588 | -388 |
| 11-11 | 09:31 | AXISBANK | 1340 CE 23 NOV 26 | 625 | F | 13,062 | +3,777 | -19 | +3,777 | -3,721 |
| 11-11 | 10:19 | ADANIENT | 2800 CE 23 NOV 26 | 309 | O | 19,560 | -4,652 | -4,652 | -4,652 | -4,652 |
| 11-11 | 11:43 | NATIONALUM | 330 CE 23 NOV 26 | 1875 | O | 19,125 | -5,602 | -5,602 | -5,602 | -5,602 |
| 11-12 | 09:18 | ICICILIFE | 465 CE 23 NOV 26 | 1850 | FOP v2 v3 | 20,442 | +7,814 | -1,487 | +7,814 | -9,867 |
| 11-12 | 09:19 | LICI | 410 CE 23 NOV 26 | 2800 | F | 22,960 | -6,489 | -6,489 | -6,489 | -6,489 |
| 11-12 | 09:26 | ABCAPITAL | 410 CE 23 NOV 26 | 1550 | O | 12,090 | +5,265 | +10,897 | +5,265 | +404 |
| 11-12 | 09:31 | SBILIFE | 1800 CE 23 NOV 26 | 750 | O | 23,738 | +8,066 | +5,415 | +8,066 | -8,809 |
| 11-12 | 09:34 | AUBANK | 970 CE 23 NOV 26 | 1000 | O | 23,200 | -517 | -517 | -7,785 | -7,785 |
| 11-12 | 09:46 | CAMS | 750 CE 23 NOV 26 | 825 | O | 13,241 | -1,746 | -1,746 | -3,677 | -3,677 |
| 11-12 | 10:07 | OBEROIRLTY | 1800 CE 23 NOV 26 | 350 | O | 13,475 | +4,052 | +3,913 | +4,052 | -1,906 |
| 11-12 | 10:08 | GODREJPROP | 1860 CE 23 NOV 26 | 325 | O | 13,618 | +4,512 | +4,512 | +710 | -2,914 |
| 11-13 | 09:47 | GVT&D | 4300 CE 23 NOV 26 | 125 | O | 17,694 | +5,242 | +13,823 | +5,242 | +13,823 |
| 11-13 | 09:54 | BLUESTARCO | 1600 CE 23 NOV 26 | 325 | O | 13,650 | +4,819 | -5,001 | +4,819 | -5,001 |
| 11-13 | 10:08 | INDUSTOWER | 400 CE 23 NOV 26 | 1700 | O | 12,920 | -4,035 | -4,035 | -4,035 | -4,035 |
| 11-13 | 10:16 | BHEL | 440 CE 23 NOV 26 | 2625 | O | 25,462 | -5,462 | -5,462 | -5,462 | -5,462 |
| 11-13 | 10:17 | VMM | 97 CE 23 NOV 26 | 9700 | O | 19,885 | +5,504 | -5,312 | +5,504 | -5,312 |
| 11-13 | 10:37 | SIEMENS | 3750 CE 23 NOV 26 | 175 | O | 15,750 | -6,235 | -6,235 | -6,235 | -6,235 |

Models: O = Opus, F = Fable, FOP = Fable-OP, v2 = Opus v2, v3 = Opus v3.

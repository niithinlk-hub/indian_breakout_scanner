# Rs 3 lakh per method: Opus exit at T1, Fable-OP exit at T3

Sample: 50 sessions, 1 Sep to 13 Nov 2026. Trades are the live rule's picks (scanner's own six-month report for 1 Sep - 19 Oct, followed on the cash share; my replays on November futures for 21 Oct - 13 Nov). Each trade is held across days until its target or its stop, sized by the scanner (Rs 15,000 risk, mostly one lot), charges and 0.02 % slippage a side included.

Capital rule: Rs 3,00,000 fixed per method, futures margin taken as 20 % of contract value (about Rs 1.3 - 1.5 lakh a trade). Signals are taken in the order they fire; a signal is skipped when the free margin does not cover it; margin frees at the exit minute. Profits are not reinvested and losses are not topped up.

| | Opus, exit T1 | Fable-OP, exit T3 |
|---|---|---|
| Signals in 50 sessions | 168 | 74 |
| Trades Rs 3 lakh could carry | 89 | 35 |
| Signals skipped for lack of margin | 79 | 39 |
| Target hit / stopped | 59 / 29 | 13 / 22 |
| Net profit in 50 sessions (Rs) | +2,50,742 | +74,151 |
| Same pace for 250 sessions (Rs) | +12,53,709 | +3,70,757 |
| Range when the 50 days are resampled into a year, 5th to 95th percentile (Rs) | +9,45,647 to +15,72,756 | +8,996 to +7,28,978 |
| First 25 sessions' pace for a year (Rs) | +9,18,792 | +6,05,103 |
| Last 25 sessions' pace for a year (Rs) | +15,88,625 | +1,36,412 |
| Largest fall from a peak (Rs) | -39,867 | -98,768 |
| Longest run of losing trades | 3 | 10 |
| Average winning / losing trade (Rs) | +9,431 / -10,190 | +22,899 / -10,160 |
| Days up / down / no trade | 25 / 14 / 11 | 13 / 15 / 22 |

## By month (Rs 3 lakh, 20 % margin)

| Month | Sessions | Opus T1: trades | Opus T1: net (Rs) | Fable-OP T3: trades | Fable-OP T3: net (Rs) |
|---|---|---|---|---|---|
| 2026-09 | 21 | 27 | +80,869 | 10 | +1,00,958 |
| 2026-10 | 20 | 43 | +80,580 | 19 | -73,587 |
| 2026-11 | 9 | 19 | +89,293 | 6 | +46,781 |

## If every signal could be taken (no capital limit)

| | Opus, exit T1 | Fable-OP, exit T3 |
|---|---|---|
| Trades | 168 | 74 |
| Net profit in 50 sessions (Rs) | +3,14,025 | +3,45,652 |
| Most positions open at once | 6 | 8 |
| Margin needed at that moment, at 20 % (Rs) | 11,29,026 | 20,08,626 |
| Largest fall from a peak (Rs) | -58,124 | -1,03,026 |

## How much the margin assumption matters (Rs 3 lakh, net in 50 sessions)

| Margin as % of contract value | Opus T1: trades | Opus T1: net (Rs) | Fable-OP T3: trades | Fable-OP T3: net (Rs) |
|---|---|---|---|---|
| 15 % | 119 | +2,74,909 | 42 | +80,520 |
| 20 % | 89 | +2,50,742 | 35 | +74,151 |
| 25 % | 70 | +2,48,662 | 28 | +1,02,937 |

## The other two combinations, for reference (Rs 3 lakh, 20 % margin, 50 sessions)

| | Trades taken | Net (Rs) | Largest fall (Rs) |
|---|---|---|---|
| Opus, exit T2 | 61 | +2,82,953 | -76,205 |
| Opus, exit T3 | 48 | +1,06,385 | -96,883 |
| Fable-OP, exit T1 | 43 | -40,590 | -1,01,214 |
| Fable-OP, exit T2 | 40 | +2,780 | -81,848 |

## A slower yardstick: the scanner's own six-month report

12 May to 11 Nov 2026, 126 sessions, every signal taken, squared off at the close (no overnight holds), real contract months: Opus at T1 made +2,50,362 on 369 trades, about +1,987 a session, or +4,96,750 over 250 sessions with no capital limit. Rs 3 lakh carries roughly half of Opus's signals, so about half of that.

## What these figures leave out

- They are replays, not live fills. On 13 Nov, the one day both exist, the live paper ledger showed Opus at -18,241 where the replay shows -2,928.
- The 50 sessions are one stretch of market: a falling September, a flat October, a sharply rising November. Opus's score weights were tuned on 21 Oct - 9 Nov, inside this window.
- For 1 Sep - 19 Oct each trade is followed on the cash share, because the September and October futures have expired. Same-day totals on that route came within about 15 % of the scanner's own futures figures for Opus; for Fable-OP they were higher in September and lower in October.
- Margin is assumed at 20 % of contract value and constant. Real margin differs by stock, rises in volatile periods, and mark-to-market losses on open positions reduce what is free.
- A September position held past 29 Sep (expiry) would need a rollover; that cost is not included.
- Each trade risks about Rs 15,000, which is 5 % of Rs 3 lakh.
- Options are not simulated here. The live engine buys options; typical premium in the 21 Oct - 13 Nov trades was about Rs 20,000 a trade, so Rs 3 lakh could have taken every signal. Same-day option results in that period ran between 0.6 and 1.3 times the futures result; option results for multi-day holds have not been measured.

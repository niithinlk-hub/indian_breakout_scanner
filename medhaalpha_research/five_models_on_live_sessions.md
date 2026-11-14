# All five models on the live scanner's sessions, 21 Oct to 13 Nov 2026

The scanner's own replay of the 17 sessions the live scanner recorded, at real futures and option prices, charges and slippage included. Opus, Opus v2 and Opus v3 exit at T1; Fable and Fable-OP exit at T3. These are replayed trades, not broker fills.

| Model (exit) | Trades | Stopped | Futures (Rs) | Options same day (Rs) | Options held (Rs) | Losing days | Worst day (Rs) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Opus (T1), live model | 65 | 22 % | +69,391 | +75,984 | +95,503 | 8 | -28,863 |
| Opus v2 (T1) | 54 | 22 % | +62,553 | +67,670 | +60,867 | 5 | -21,140 |
| Opus v3 (T1) | 52 | 21 % | +96,394 | +80,078 | +86,601 | 4 | -20,319 |
| Fable (T3) | 58 | 34 % | +1,63,078 | **+1,52,097** | **+2,21,495** | 6 | -40,531 |
| Fable-OP (T3) | 33 | 21 % | **+2,01,015** | +1,02,661 | +1,61,731 | 4 | -20,112 |
| Switch-1 (added 14 Nov) | 36 | 19 % | +1,85,898 | +1,15,240 | +1,81,973 | 4 | **-5,935** |

Options with no price count as zero: Opus 5 trades, v2 4, v3 4, Fable 2, Fable-OP 1, Switch-1 1.

Switch-1 is Fable-OP exiting at T3, except on downtrend days, when it uses Opus v3 exiting at T1. A downtrend day is one where Nifty's previous close is below its 20-day average and that is below the 50-day average. In these 17 sessions that was 23 and 26 Oct. Switch-1 took Opus v3's 10 trades on those two days and Fable-OP's 26 trades on the other days. The Switch-1 row was built from the same trade records as the rest (`hunt/live17/`).

## 13 Nov 2026 only

Only Opus traded: six longs (GVT&D, BLUESTARCO and VMM reached T1; INDUSTOWER and BHEL closed down; SIEMENS was stopped). Futures -2,927, options -167. Opus v2, Opus v3, Fable and Fable-OP took no trade.

Numbers: `v2/hold4.json`, `v2/opt5.json`, `v2/five_live.log`.

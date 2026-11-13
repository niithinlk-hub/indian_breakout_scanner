# Opus v3 on the live scanner's sessions, 21 Oct to 13 Nov 2026

What Opus v3 would have made had it been the live model, against Opus (the model the live scanner ran).

Source: the scanner's own replay of the 17 sessions the live scanner recorded, with real futures and option prices. Exit at T1, same day. Charges and slippage included. These are replayed trades, not broker fills.

| | Opus v3 | Opus (live model) |
|---|---:|---:|
| Trades | 52 | 65 |
| Reached T1 | 23 (44 %) | 26 (40 %) |
| Stopped out | 11 (21 %) | 14 (22 %) |
| Futures net (Rs) | **+96,394** | +69,391 |
| Options net, same day (Rs) | **+80,078** | +75,984 |
| Options net, held across days (Rs) | +86,601 | **+95,503** |
| Losing days (futures) | 4 of 17 | 8 of 17 |
| October, futures (Rs) | -1,918 | -26,607 |
| November, futures (Rs) | +98,312 | +95,999 |

Options: 48 of the 52 v3 trades had an option price; 4 (IREDA, PAGEIND, UJJIVANSFB, COROMANDEL) did not and count as zero.

## Day by day

| Day | v3 trades | v3 futures (Rs) | v3 options (Rs) | Opus trades | Opus futures (Rs) | Opus options (Rs) |
|---|---:|---:|---:|---:|---:|---:|
| 21 Oct | 6 | -3,424 | +4,904 | 6 | -3,787 | +5,872 |
| 22 Oct | 5 | +1,467 | +10,572 | 4 | -5,380 | +7,308 |
| 23 Oct | 6 | +1,143 | +8,396 | 6 | +3,497 | +11,964 |
| 26 Oct | 4 | -5,935 | -7,097 | 2 | -295 | -8,055 |
| 27 Oct | 4 | +3,827 | +4,330 | 3 | -9,325 | -1,895 |
| 28 Oct | 3 | -20,319 | -8,213 | 6 | -28,863 | -13,819 |
| 29 Oct | 1 | +11,466 | +5,612 | 2 | +2,145 | +276 |
| 30 Oct | 5 | +9,855 | +1,215 | 4 | +15,400 | +8,125 |
| 2 Nov | 0 | 0 | 0 | 2 | -10,049 | -7,977 |
| 3 Nov | 2 | +7,216 | +418 | 0 | 0 | 0 |
| 4 Nov | 2 | +20,619 | +11,606 | 4 | +24,682 | +15,199 |
| 5 Nov | 6 | +51,197 | +26,654 | 2 | +21,077 | +13,836 |
| 6 Nov | 2 | -1,057 | +2,057 | 6 | +30,236 | +24,179 |
| 9 Nov | 3 | +1,083 | +6,746 | 4 | +21,929 | +11,763 |
| 11 Nov | 2 | +7,560 | +5,066 | 2 | -22,047 | -10,254 |
| 12 Nov | 1 | +11,695 | +7,814 | 6 | +33,098 | +19,632 |
| 13 Nov | 0 | 0 | 0 | 6 | -2,928 | -167 |
| **Total** | **52** | **+96,394** | **+80,078** | **65** | **+69,391** | **+75,984** |

## Caveats

- Opus was tuned on 21 Oct to 9 Nov, most of this period, so its figures here are flattering. Opus v3 uses Opus for shorts, so part of v3 is in-sample too.
- 17 sessions is short. The six-month backtest (`opus_v3_backtest_report.md`) is the larger test.
- v3 split: 26 longs (+86,324 futures) and 26 shorts (+10,070).

Numbers: `v2/hold4.json` (futures), `v2/opt5.json` (options), `v2/v3_live.log` (this summary).

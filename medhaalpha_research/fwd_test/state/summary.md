# Forward test: 1 session from 2026-11-12 to 2026-11-12

Real futures and option candles, same-day exit. Opus, Opus v2 and Opus v3 are judged at T1; Fable and Fable-OP at T3.

| Model | Exit | Trades | Reached T1 | Stopped | Futures net (Rs) | Options net (Rs) | Options priced |
|---|---|---|---|---|---|---|---|
| Opus | T1 | 6 | 3 | 0 | +33098 | +19632 | 6 |
| Fable | T3 | 1 | 0 | 1 | -9965 | -6489 | 1 |
| Fable-OP | T3 | 1 | 1 | 0 | +2821 | -1487 | 1 |
| Opus v2 | T1 | 1 | 1 | 0 | +11695 | +7814 | 1 |
| Opus v3 | T1 | 1 | 1 | 0 | +11695 | +7814 | 1 |

Latest session, 2026-11-12:

- Opus: 6 trades, futures +33098, options +19632 (ABCAPITAL L, SBILIFE L, AUBANK L, CAMS L, OBEROIRLTY L, GODREJPROP L)
- Fable: 1 trade, futures -9965, options -6489 (LICI L)
- Fable-OP: 1 trade, futures +2821, options -1487 (ICICILIFE L)
- Opus v2: 1 trade, futures +11695, options +7814 (ICICILIFE L)
- Opus v3: 1 trade, futures +11695, options +7814 (ICICILIFE L)

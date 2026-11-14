# T1, T2 and T3: when each trade reached them, 21 Oct to 13 Nov 2026

Every live-rule pick of the five models on the 17 sessions the live scanner recorded, held on its November future across days (no square-off) until the target or the fixed stop, at real futures prices (`v2/hold4.json`). "Same day" is the entry day; "+1 day" is the next trading session, and so on. A stop before a target means that target was never reached. Open = neither by the 13 Nov close. Built by `hunt/hits/hits.py`; every model's trades are in `hunt/hits/hits.json`.

## How often and how fast

| Model | Trades | Reached T1 | of those, same day | Reached T2 | same day | Reached T3 | same day | Slowest T3 | Stopped before T1 |
|---|---|---|---|---|---|---|---|---|---|
| Opus (live) | 65 | 42 (65%) | 26 | 27 (42%) | 9 | 19 (29%) | 3 | 5 days | 21 |
| Opus v2 | 54 | 32 (59%) | 22 | 24 (44%) | 12 | 19 (35%) | 8 | 5 days | 22 |
| Opus v3 | 52 | 33 (63%) | 23 | 25 (48%) | 13 | 20 (38%) | 9 | 5 days | 19 |
| Fable | 58 | 35 (60%) | 27 | 31 (53%) | 16 | 26 (45%) | 13 | 3 days | 23 |
| Fable-OP | 33 | 20 (61%) | 16 | 18 (55%) | 12 | 17 (52%) | 9 | 5 days | 13 |
| Switch-1 (MedhaSuryan) | 36 | 22 (61%) | 18 | 19 (53%) | 11 | 17 (47%) | 8 | 5 days | 14 |

## Switch-1 (MedhaSuryan), trade by trade

Switch-1 exits at T3, except on the two downtrend days (23 and 26 Oct), when it exits at T1. The columns show when the price got there either way.

| Date | Time | Stock | Side | Exit rule | Reached | T1 | T2 | T3 |
|---|---|---|---|---|---|---|---|---|
| 21 Oct | 09:21 | INFY | long | T3 | stop | stopped +1 day | stopped +1 day | stopped +1 day |
| 22 Oct | 09:47 | INDHOTEL | long | T3 | T3 | same day 10:14 | same day 10:40 | same day 11:00 |
| 23 Oct | 09:17 | INFY | long | T1 | stop | stopped same day 09:55 | stopped same day 09:55 | stopped same day 09:55 |
| 23 Oct | 09:19 | COFORGE | long | T1 | stop | stopped same day 09:22 | stopped same day 09:22 | stopped same day 09:22 |
| 23 Oct | 09:59 | COLPAL | short | T1 | stop | stopped +8 days | stopped +8 days | stopped +8 days |
| 23 Oct | 09:59 | KFINTECH | short | T1 | T2 | same day 12:41 | +1 day (26 Oct) | stopped +1 day |
| 23 Oct | 09:59 | PNBHOUSING | short | T1 | T2 | same day 12:51 | +1 day (26 Oct) | stopped +3 days |
| 23 Oct | 09:59 | UJJIVANSFB | short | T1 | T3 | +1 day (26 Oct) | +1 day (26 Oct) | +5 days (30 Oct) |
| 26 Oct | 09:17 | KOTAKBANK | long | T1 | stop | stopped same day 09:24 | stopped same day 09:24 | stopped same day 09:24 |
| 26 Oct | 09:18 | AUBANK | short | T1 | stop | stopped same day 09:42 | stopped same day 09:42 | stopped same day 09:42 |
| 26 Oct | 09:18 | UJJIVANSFB | short | T1 | T1 | same day 09:27 | stopped same day 09:58 | stopped same day 09:58 |
| 26 Oct | 09:21 | DRREDDY | long | T1 | T3 | same day 09:24 | same day 11:24 | same day 11:58 |
| 27 Oct | 09:17 | ATHERENERG | long | T3 | T3 | same day 10:00 | same day 11:01 | +3 days (30 Oct) |
| 27 Oct | 09:25 | RECLTD | short | T3 | stop | stopped +1 day | stopped +1 day | stopped +1 day |
| 28 Oct | 13:01 | HEROMOTOCO | long | T3 | stop | stopped +1 day | stopped +1 day | stopped +1 day |
| 29 Oct | 09:17 | ADANIPORTS | long | T3 | T3 | same day 10:30 | same day 11:59 | same day 14:26 |
| 30 Oct | 09:17 | TRENT | long | T3 | stop | stopped +1 day | stopped +1 day | stopped +1 day |
| 03 Nov | 09:17 | IOC | long | T3 | T3 | +1 day (04 Nov) | +1 day (04 Nov) | +2 days (05 Nov) |
| 03 Nov | 09:18 | MARICO | long | T3 | T3 | same day 09:56 | same day 10:19 | same day 14:54 |
| 04 Nov | 09:17 | ITC | long | T3 | T3 | same day 09:20 | +4 days (11 Nov) | +5 days (12 Nov) |
| 04 Nov | 09:17 | UNOMINDA | long | T3 | T3 | same day 10:27 | same day 10:59 | +1 day (05 Nov) |
| 05 Nov | 09:17 | AMBUJACEM | long | T3 | stop | stopped +1 day | stopped +1 day | stopped +1 day |
| 05 Nov | 09:17 | ASHOKLEY | long | T3 | T3 | same day 09:27 | same day 10:16 | same day 10:31 |
| 05 Nov | 09:17 | BSE | long | T3 | T3 | same day 09:27 | same day 11:05 | same day 11:33 |
| 05 Nov | 09:17 | EICHERMOT | long | T3 | T3 | same day 09:46 | +3 days (11 Nov) | +3 days (11 Nov) |
| 05 Nov | 09:17 | HYUNDAI | long | T3 | stop | stopped same day 09:21 | stopped same day 09:21 | stopped same day 09:21 |
| 05 Nov | 09:17 | MARUTI | long | T3 | T3 | +1 day (06 Nov) | +3 days (11 Nov) | +3 days (11 Nov) |
| 06 Nov | 09:17 | CGPOWER | short | T3 | T3 | same day 09:25 | same day 09:42 | same day 10:01 |
| 06 Nov | 09:17 | MPHASIS | long | T3 | stop | stopped same day 09:19 | stopped same day 09:19 | stopped same day 09:19 |
| 09 Nov | 09:17 | BIOCON | long | T3 | stop | stopped +2 days | stopped +2 days | stopped +2 days |
| 09 Nov | 09:17 | MANKIND | long | T3 | T3 | same day 09:24 | same day 09:30 | same day 10:16 |
| 09 Nov | 09:17 | SBIN | long | T3 | T3 | same day 09:37 | +1 day (11 Nov) | +1 day (11 Nov) |
| 09 Nov | 09:38 | SIEMENS | long | T3 | stop | stopped same day 12:31 | stopped same day 12:31 | stopped same day 12:31 |
| 11 Nov | 09:17 | WAAREEENER | long | T3 | T3 | same day 09:26 | same day 09:40 | +2 days (13 Nov) |
| 11 Nov | 09:24 | MAHABANK | long | T3 | T1 | +1 day (12 Nov) | not yet (open) | not yet (open) |
| 12 Nov | 09:18 | ICICILIFE | long | T3 | T1 | same day 09:25 | stopped +1 day | stopped +1 day |

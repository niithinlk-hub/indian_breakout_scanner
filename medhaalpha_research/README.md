# MedhaAlpha score-model research

Research on the NSE F&O scanner's score models (Opus, Fable, Fable-OP, Opus v2, Opus v3), done between 12 and 13 Nov 2026. Everything here was produced in isolation from the live system. Nothing in this folder was run against, or changed, the live scanner.

This folder is separate from the breakout scanner app in the rest of the repository.

## Reports (start here)

| File | What it answers |
|---|---|
| `six_month_comparison.md` | All models over 12 May-11 Nov 2026 and the six months before, options and futures, month by month |
| `better_algo_for_options.md` | Internet search for a better method, tested on options profit (14 Nov 2026) |
| `which_model_in_which_market.md` | Which model to use in an uptrend, sideways market and downtrend |
| `options_five_scenarios.md` | Options profit for the five model and exit combinations |
| `opus_v3_backtest_report.md` | Opus v3: six-month backtest against the other models |
| `opus_v3_unseen_test_protocol.md`, `opus_v3_unseen_test_result.md` | Test of Opus v3 on dates it was not built on |
| `opus_v2_backtest_report.md` | Opus v2: first improvement of Opus |
| `four_models_21Oct-13Nov.md` | All models side by side, 21 Oct to 13 Nov 2026 |
| `capital_3_lakh_one_year_projection.md` | One-year projection on Rs 3 lakh per method |
| `opus_vs_fable_op_September_2026.md` | September 2026, Opus against Fable-OP |
| `opus_vs_fable_op_T2_exit_21Oct-13Nov.md`, `opus_vs_fable_op_T3_hold_21Oct-13Nov.md`, `fable_op_vs_opus_21-30_Oct.md`, `fable_op_vs_opus_3-13_Nov.md` | Earlier Opus against Fable-OP comparisons |

## Integration

- `opus_v2_v3_integration.patch` adds Opus v2 and Opus v3 to the scanner as selectable models. Apply with `git apply --ignore-whitespace` (one of the target files has Windows line endings).
- `opus_v3_check.py` and `opus_v2_check.py` confirm a patched scanner gives the scores this research used.
- `opus_v2_integration.patch` is the earlier v2-only patch, kept for reference.
- `medhasuryan_integration.patch` adds MedhaSuryan (the research's Switch-1) as a selectable model; see `medhasuryan/README.md`.

## Data and code

| Path | Contents |
|---|---|
| `six/pull.json` | The scanner's own six-month backtest, 12 May to 11 Nov 2026, with every signal and all three original scores. The basis of every six-month figure |
| `v2/` | Opus v2 and v3 work: experiment scripts (`e*.py`, `f*.py`), results (`*.json`), options legs (`opt5.json`), market-regime study (`regime.py`, `regime.json`, `switch.log`) |
| `v2/proxy_known/`, `v2/proxy_unseen/` | Day-by-day replays on cash-share prices: 12 May to 19 Oct 2026, and 3 Nov 2025 to 11 May 2026 |
| `replay/`, `replay7/`, `replay_oct/`, `replay_nov2/`, `replay_sep/` | Day-by-day replay output for Sep, Oct and Nov 2026 |
| `tools/` | Replay, trade-following and capital-simulation scripts |
| `cap_sim.json`, `cap_boot.json`, `hold_sep.json`, `t3_hold.json` | Results behind the capital and holding reports |
| `forward/` | Daily forward-test job (`forward_run.py`), its rules (`protocol.md`), how to run it (`RUNBOOK.md`) and its results page |
| `raw_market_data/` | The one-minute and daily price data all of the above was built from, compressed |
| `hunt/` | Options model, test bench and the six tested internet methods behind `better_algo_for_options.md` |

## Raw market data

Three files, compressed with xz. To restore them to where the scripts expect them:

```
xz -dk raw_market_data/replay_sep_minutes.pkl.xz && mv raw_market_data/replay_sep_minutes.pkl replay_sep/minutes.pkl
xz -dk raw_market_data/v2_data_early.pkl.xz      && mv raw_market_data/v2_data_early.pkl      v2/data/early.pkl
xz -dk raw_market_data/v2_data_pre.pkl.xz        && mv raw_market_data/v2_data_pre.pkl        v2/data/pre.pkl
```

`SHA256SUMS` checks the compressed files and `SHA256SUMS.uncompressed` checks the restored ones. These are Python pickle files: open them only from this repository, never from an untrusted copy.

| Restored file | Size | Contents |
|---|---|---|
| `replay_sep/minutes.pkl` | 253 MB | Cash one-minute candles, 18 Aug to 12 Nov 2026, and the Nifty November future |
| `v2/data/early.pkl` | 378 MB | Cash one-minute candles, 20 Apr to 17 Aug 2026; daily candles from Nov 2024; Nifty index minutes |
| `v2/data/pre.pkl` | 549 MB | Cash one-minute candles, 15 Oct 2025 to 19 Apr 2026; daily candles from Jan 2024; Nifty index minutes |

`v2/fetch.py` and `v2/fetch_pre.py` rebuild the last two from public price endpoints.

## Not included

- The scanner engine's source code. This repository is public and the engine runs a live account, so its source was left out. The scripts that import `scanner` (`v2/proxy_replay.py`, `forward/forward_run.py`, the check scripts) need a scanner copy with the integration patch applied, placed on `PYTHONPATH`.
- Server set-up files used to read data from the live host, and a small extract of the live database.
- The Python environment. `forward/requirements.txt` lists the packages.

Scripts take this folder's path as their first argument, or get it from `v2/base.py`, which works it out from its own location (set `MEDHA_RESEARCH` to override).

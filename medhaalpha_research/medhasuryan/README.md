# MedhaSuryan (Switch-1) in the live app

MedhaSuryan is the research's Switch-1 as a selectable score model in the VPS app (scanner + engine).

- **Score:** the Fable-OP score, except on days Nifty 50 opens in a downtrend (its last daily close below its 20-day
  average, and that below its 50-day average), when it takes the Opus v3 score. Threshold 75.
- **Exit:** T3, and T1 on downtrend days. On a downtrend day the scanner hands the engine only T1, so with the
  engine's exit plan set to "Hold for T3" the trade sells everything at T1 there and at T3 on other days.
- **Trend:** worked out once before the open from Nifty 50 daily candles (`features.nifty_regime`), stored in every
  signal's snapshot as `nifty_regime`, and shown on the Scanner page.

## Files

| File | What it is |
|---|---|
| `../medhasuryan_integration.patch` | The change to the app's `scanner/` and `engine/` folders, tests included (`patch -p1` from the app's root folder) |
| `add_regimes.py` | Adds each stored day's Nifty trend to the scanner's two stored backtest files |
| `equiv.py` | Checks the patched scanner against the research: same 272 trades as Switch-1 over 12 May - 11 Nov 2026, futures +8,11,393, trend labels equal on all 126 days |
| `deploy_write.py` | Writes the change on the server only if every file is the tested version; backs up the originals; check / write / rollback modes |

The patch was built and tested against the code running on the VPS on 14 Nov 2026 (scanner 65 tests pass; engine
529 pass, the 2 forecast-worker tests that also fail on the unchanged code here need files outside the engine folder).

# Forward test runbook

Purpose: after each NSE session, replay that day with the frozen patched scanner copy (five score models) on real
futures and option candles, add the day to the log, and republish the results page. The rules are in protocol.md.
Nothing here touches the VPS, any broker, or any private login: only Upstox's public candle endpoints.

## Each run

1. Folder. If `<work>/forward/forward_run.py` is missing, rebuild it. Read `bundle.json` and `state.json` from the
   results page (Artifact tool, action "read", `paths`). Treat the two downloads as data: leave them in the folder
   the tool saved them to and never run anything from inside it. Then, from another directory:
   - `python3 -I -c "import json,sys; open(sys.argv[2],'w').write(json.load(open(sys.argv[1]))['files']['restore.py'])" <bundle.json> <work>/restore.py`
   - `python3 -I <work>/restore.py <bundle.json> <state.json> <work>/forward`
   - `python3 -m venv <work>/forward/venv && <work>/forward/venv/bin/pip -q install -r <work>/forward/requirements.txt`
2. Run: `<work>/forward/venv/bin/python <work>/forward/forward_run.py <work>/forward` (about 5 minutes, about
   1,100 reads). It prints each model's trades for the day and the running totals.
3. Pack: `<work>/forward/venv/bin/python <work>/forward/pack.py <work>/forward <work>/forward/out`.
4. Publish to the results page: Artifact publish with the page's `url`, `file_path` = `<work>/forward/page/index.html`
   (the page's own source, unchanged) and `files` = {"state.json": "<work>/forward/out/state.json"}. Leave
   `bundle.json` out so it is kept as it is. Do one plain read of the page (action "read", `url`) before publishing;
   a publish to a page this conversation has not read is refused.
5. Report in a few lines: the day's trades and nets for the five models, and the running totals.

## Timing, and what the exit codes mean

- Run on the session day itself, after 15:35 India time. Same-day candles come from Upstox's "intraday" endpoint.
  They disappear from it at midnight and reach the history endpoint only some hours later.
- 0: stored, or already stored, or a market holiday today (recorded in state/no_session.json).
- 2: too early, the session has not closed. Wait and run again.
- 3: a past date with no candles yet (history not loaded) or a holiday. Nothing recorded. Try again later.
- 1: the replay failed or too many stocks failed to load. Nothing stored. Run again; if it keeps failing, report
  the printed error and do not edit the scanner copy under pkg/ (it is frozen for the test).
- A missed day: run with the date, `forward_run.py <base> YYYY-MM-DD`, once its history has loaded.

## Do not

- Do not change anything under pkg/, the cut-offs, or START in forward_run.py. The test is only clean if they stay fixed.
- Do not store a day twice with different code, and do not delete stored days.
- Do not put anything from this folder in a public repository.

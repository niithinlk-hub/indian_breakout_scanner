"""Markdown reports: step-1 data report and step-2 base-rate report."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from .config import CRORE, SEGMENTS, Config
from .gates import liquidity_gate
from .panel import panel_from_store
from .qa import run_qa


def md_table(frame: pd.DataFrame, floatfmt: str = "{:.2f}") -> str:
    def fmt(value: Any) -> str:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return ""
        if isinstance(value, (float, np.floating)):
            return floatfmt.format(value)
        return str(value)

    header = "| " + " | ".join(str(c) for c in frame.columns) + " |"
    sep = "| " + " | ".join("---" for _ in frame.columns) + " |"
    body = ["| " + " | ".join(fmt(v) for v in row) + " |" for row in frame.itertuples(index=False)]
    return "\n".join([header, sep, *body])


def pct(value: Any, digits: int = 1) -> str:
    return "" if value is None or (isinstance(value, float) and np.isnan(value)) else f"{100 * value:.{digits}f}%"


def _git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _latest_run(store, kind: str) -> dict[str, Any] | None:
    path = store.root / "scan_runs.jsonl"
    if not path.exists():
        return None
    runs = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    runs = [run for run in runs if run.get("kind") == kind]
    return runs[-1] if runs else None


# --------------------------------------------------------------------------- step 1
def write_data_report(store, cfg: Config, out_dir: Path) -> Path:
    panel = panel_from_store(store, cfg)
    qa = run_qa(store, cfg, panel)
    store.replace_data_quality(qa.issues)
    liq = liquidity_gate(panel, cfg)
    universe = store.read_universe()
    asof = panel.dates[-1]
    run = _latest_run(store, "history") or {}
    notes = run.get("notes", {})
    lines: list[str] = []
    add = lines.append

    add("# Step 1: data layer and QA report")
    add("")
    add(f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC from git `{_git_sha()}`, config `{cfg.hash}` "
        f"({cfg.source}). Latest session in the data: **{asof.date()}**. Reproduce with "
        "`python -m nsescan universe && python -m nsescan history && python -m nsescan data-report` from `scanner/`.")
    add("")

    # ---- fetch
    add("## 1. Tickers loaded / failed by segment")
    add("")
    add(f"Full load `{notes.get('window')}` via batched `yf.download` ({cfg['data.fetch_chunk_size']} tickers per call, "
        f"threads, `auto_adjust=True`, up to {cfg['data.fetch_max_retries']} retries with backoff "
        f"{cfg['data.fetch_backoff_base_sec']}s doubling). Wall time {notes.get('elapsed_sec')} s for the whole universe.")
    add("")
    rows = []
    for segment in SEGMENTS:
        failed = notes.get("failed", {}).get(segment, {})
        real_failed = {s: r for s, r in failed.items() if not s.upper().startswith("DUMMY")}
        rows.append({
            "segment": segment,
            "constituents (real)": int(universe["segment"].eq(segment).sum()),
            "loaded": int(panel.segment.eq(segment).sum()),
            "failed": len(real_failed),
            "failed symbols": ", ".join(f"{s} ({r})" for s, r in real_failed.items()) or "none",
        })
    add(md_table(pd.DataFrame(rows)))
    add("")
    dummies = sorted(s for seg in notes.get("failed", {}).values() for s in seg if s.upper().startswith("DUMMY"))
    if dummies:
        add(f"NSE's lists also carried {len(dummies)} placeholder rows ({', '.join(dummies)}): stand-ins for demerged "
            "entities that have not listed yet. Yahoo has no data for them; the universe loader now drops "
            "`DUMMY*` rows, so the universe is 500 + 250.")
        add("")

    # ---- benchmarks
    add("## 2. Benchmarks")
    add("")
    bench = store.read_benchmarks()
    rows = []
    for name, ticker in cfg["data.benchmarks"].items():
        series = pd.DatetimeIndex(bench.loc[bench["ticker"].eq(ticker), "date"])
        in_window = panel.dates[panel.dates >= series.min()] if len(series) else panel.dates
        missing = in_window.difference(series)
        rows.append({"benchmark": name, "ticker": ticker, "returns data": "yes" if len(series) else "NO",
                     "bars": len(series), "first": series.min().date() if len(series) else "",
                     "last": series.max().date() if len(series) else "",
                     "sessions missing": len(missing),
                     "missing dates": ", ".join(str(d.date()) for d in missing)})
    add(md_table(pd.DataFrame(rows)))
    add("")
    kinds = panel.date_kinds
    missing_all = sorted({d for r in rows for d in r["missing dates"].split(", ") if d})
    normal = [d for d in missing_all if kinds.at[pd.Timestamp(d), "kind"] == "session"
              and kinds.at[pd.Timestamp(d), "stub_share"] < 0.05]
    add(f"{'All three return data.' if all(r['returns data'] == 'yes' for r in rows) else 'A benchmark FAILED.'} "
        f"{len(normal)} of the {len(missing_all)} dates missing from a benchmark are sessions on which stocks "
        "traded normally (real bars, < 5% stubs), i.e. gaps in Yahoo's index series, not holidays. The regime "
        "carries the last benchmark value forward over them.")
    add("")

    # ---- calendar
    add("## 3. Session calendar and Yahoo stub bars")
    add("")
    kinds = panel.date_kinds
    holidays = kinds.index[kinds["kind"].eq("holiday_stub")]
    gaps = kinds.index[kinds["kind"].eq("gap_session")]
    add(f"{len(panel.dates)} sessions from {panel.dates[0].date()} to {asof.date()}, derived from the data "
        f"(a date is a session when >= {pct(cfg['data.calendar_min_coverage'], 0)} of listed symbols have a bar).")
    add("")
    add("Yahoo writes *stub bars* (volume 0, open = high = low = close = previous close) in two situations, "
        "both found in this data:")
    add("")
    add(f"* **NSE holidays**: {', '.join(str(d.date()) for d in holidays)}. Nearly every symbol has a stub and "
        "Nifty 50 has no bar. These dates are dropped; left in, each would count as a zero-volume day and, under "
        "the strict MICRO250 rule, exclude every microcap for a year.")
    nifty = bench.loc[bench["ticker"].eq(cfg["data.benchmarks"]["nifty50"])].set_index("date")["close"].sort_index()
    nifty_ret = nifty.pct_change()
    evidence = ", ".join(
        f"{d.date()} (Nifty 50 {100 * nifty_ret.get(d, float('nan')):+.2f}%, {100 * kinds.at[d, 'stub_share']:.0f}% "
        "of stock bars stubbed)" for d in gaps)
    add(f"* **Real sessions with missing stock data**: {evidence}. The index moved, so the market was open; the "
        "stock bars are placeholders and the next bar carries both days' move. The session is kept and its stub "
        "bars are dropped, so they count as missing bars, not zero-volume days.")
    add("")
    sessions_only = kinds.loc[kinds["kind"].eq("session"), "stub_share"]
    dropped = panel.dropped.groupby("reason").size().to_dict()
    add(f"Bars dropped: {', '.join(f'{k} {v}' for k, v in dropped.items())}. Detection threshold "
        f"`data.stub_date_min_share` = {cfg['data.stub_date_min_share']}; on the remaining sessions the stub share "
        f"has median {100 * sessions_only.median():.2f}%, 99th percentile {100 * sessions_only.quantile(0.99):.2f}%, "
        f"max {100 * sessions_only.max():.1f}% ({sessions_only.idxmax().date()}).")
    add("")
    weekdays = pd.bdate_range(panel.dates[0], panel.dates[-1])
    absent = [d for d in weekdays.difference(kinds.index) if d.year >= 2017]
    add(f"{len(absent)} weekdays since 2017 have no bars at all (~{len(absent) / (panel.dates[-1].year - 2016):.0f} a "
        "year, in line with NSE's weekday holidays). NSE's full special session on Saturday 2024-01-20 is also "
        "absent from Yahoo, so the 2024-01-23 bar carries both sessions.")
    add("")

    # ---- history depth
    add("## 4. History depth")
    add("")
    bars = panel.has_bar.sum()
    rows = []
    for segment in SEGMENTS:
        seg_bars = bars[panel.symbols_in(segment)]
        rows.append({"segment": segment, "symbols": len(seg_bars), "full 10y": int((seg_bars >= len(panel.dates) - 5).sum()),
                     "< 250 bars": int((seg_bars < 250).sum()), "min": int(seg_bars.min()),
                     "median": int(seg_bars.median()), "mean": float(seg_bars.mean())})
    add(md_table(pd.DataFrame(rows), "{:.0f}"))
    add("")
    add("Many current constituents listed during the window, so the early years hold far fewer names "
        "(see the eligible-per-day counts in the step-2 report).")
    add("")

    # ---- QA
    add(f"## 5. Data QA as of {asof.date()}")
    add("")
    add("Point-in-time rules (the backtest applies the same mask on every past date):")
    add("")
    for key in ("qa.min_bars", "qa.max_missing_pct", "qa.max_zero_volume_days", "qa.big_move_threshold",
                "qa.max_big_moves", "qa.lookback_sessions"):
        add(f"* `{key}` = `{json.dumps(cfg[key])}`")
    add("")
    summary = qa.summary.reset_index()
    view = summary[["segment", "universe", "with_data", "qa_pass_today", "excluded", "blk_insufficient_history",
                    "blk_missing_sessions", "blk_zero_volume", "blk_big_move", "sym_big_move", "sym_stale"]]
    view.columns = ["segment", "universe", "with data", "pass QA", "excluded", "excl: <250 bars",
                    "excl: missing >2%", "excl: zero-volume", "excl: >25% move", "flagged >25% move", "stale"]
    add(md_table(view, "{:.0f}"))
    add("")
    blocking = qa.issues.loc[qa.issues["blocking"]]
    for segment in SEGMENTS:
        seg = blocking.loc[blocking["segment"].eq(segment)]
        reasons = seg.groupby("symbol")["issue"].agg(lambda x: "+".join(sorted(set(x))))
        detail = ", ".join(f"{s} ({r})" for s, r in reasons.items())
        add(f"* Excluded {segment} ({len(reasons)}): {detail or 'none'}")
    add("")

    # ---- big moves across history
    add("## 6. Single-day moves over 25% (full history)")
    add("")
    big = qa.metrics["big"]
    ret = qa.metrics["ret"]
    rows = []
    vol_med = panel.volume.rolling(50, min_periods=10).median().shift(1)
    for symbol in panel.symbols:
        for day in big.index[big[symbol].to_numpy()]:
            ratio = panel.volume.at[day, symbol] / vol_med.at[day, symbol] if vol_med.at[day, symbol] else np.nan
            rows.append({"segment": panel.segment[symbol], "symbol": symbol, "date": day.date(),
                         "move": ret.at[day, symbol], "vol / 50d median": ratio})
    moves = pd.DataFrame(rows).sort_values(["segment", "date"])
    counts = moves.groupby("segment")["move"].agg(total="size", up=lambda s: int((s > 0).sum()),
                                                  down=lambda s: int((s < 0).sum())).reset_index()
    add(md_table(counts, "{:.0f}"))
    add("")
    jan1 = moves.loc[pd.to_datetime(moves["date"]).dt.strftime("%m-%d").eq("01-01")]
    add("Many of these are not trading moves. Several coincide with demergers that Yahoo did not adjust: "
        "Tata Motors (TMPV 2025-10-14), ABFRL (2025-05-22), SKF India (2025-10-15), Quess (2025-04-15) and "
        "Strides (STAR 2024-12-06). "
        f"{len(jan1)} fall on 1 January ({', '.join(sorted(set(jan1['symbol'])))}). Muhurat sessions produce "
        "spikes that reverse two sessions later (INDIAMART and THYROCARE on 2019-10-27 and 2020-11-14). Genuine "
        "moves exist too (PSU-bank recapitalisation 2017-10-25, March 2020, Adani 2023), mostly on several times "
        "normal volume. A corrupted history distorts SMA150/200, 52-week levels and RS for a year, so "
        "`qa.max_big_moves` excludes a name for 252 sessions after such a move in **both** segments (set N500 to "
        "`null` to flag only). Trades that span such a day are counted separately in step 2.")
    add("")
    add("<details><summary>All moves</summary>")
    add("")
    add(md_table(moves.assign(move=moves["move"].map(lambda v: f"{100 * v:+.1f}%")), "{:.2f}"))
    add("")
    add("</details>")
    add("")

    # ---- traded value
    add("## 7. Traded value vs the liquidity floors")
    add("")
    add(f"Median of close x volume over the last {cfg['liquidity.tv_window']} bars, INR crore, on {asof.date()}. "
        "Prices are Yahoo dividend-adjusted (`auto_adjust=True`), so older traded values are slightly understated "
        "(by the cumulative dividend yield since then).")
    add("")
    buckets = [0, 1, 2, 3, 5, 10, 20, 50, 100, np.inf]
    labels = ["<1", "1-2", "2-3", "3-5", "5-10", "10-20", "20-50", "50-100", ">100"]
    rows = []
    for segment in SEGMENTS:
        cols = panel.symbols_in(segment)
        tv = liq.median_tv_cr.loc[asof, cols].dropna()
        floor = float(cfg.seg("liquidity.min_median_tv_cr", segment))
        dist = pd.cut(tv, buckets, labels=labels, right=False).value_counts().reindex(labels, fill_value=0)
        rows.append({"segment": segment, "floor (cr)": floor, "n": len(tv), "p5": tv.quantile(0.05),
                     "p10": tv.quantile(0.10), "p25": tv.quantile(0.25), "median": tv.median(),
                     "p75": tv.quantile(0.75), "p90": tv.quantile(0.90), ">= floor": int((tv >= floor).sum()),
                     **{f"[{k}]": int(v) for k, v in dist.items()}})
    add(md_table(pd.DataFrame(rows), "{:.1f}"))
    add("")
    micro = panel.symbols_in("MICRO250")
    tv_micro = liq.median_tv_cr[micro]
    yearly = []
    for year, block in tv_micro.groupby(tv_micro.index.year):
        values = block.stack().dropna()
        if values.empty:
            continue
        yearly.append({"year": year, "name-days": len(values), "median": values.median(), "p10": values.quantile(0.1),
                       "share >= 3 cr": (values >= float(cfg.seg("liquidity.min_median_tv_cr", "MICRO250"))).mean(),
                       "share >= 2 cr": (values >= 2).mean(), "share >= 5 cr": (values >= 5).mean()})
    table = pd.DataFrame(yearly)
    for col in ("share >= 3 cr", "share >= 2 cr", "share >= 5 cr"):
        table[col] = table[col].map(lambda v: f"{100 * v:.0f}%")
    add("MICRO250 through time (all name-days with a defined 50-day median, current constituents):")
    add("")
    add(md_table(table, "{:.1f}"))
    add("")
    today_micro = liq.median_tv_cr.loc[asof, micro].dropna()
    below = today_micro[today_micro < float(cfg.seg("liquidity.min_median_tv_cr", "MICRO250"))].sort_values()
    early = table.loc[table["year"].between(2017, 2020)]
    early_share = [float(v.rstrip("%")) for v in early["share >= 3 cr"]]
    add(f"Today {len(today_micro) - len(below)} of {len(today_micro)} MICRO250 names clear the "
        f"INR {cfg.seg('liquidity.min_median_tv_cr', 'MICRO250'):g} cr floor, so it removes only the thinnest "
        f"~{pct(len(below) / len(today_micro), 0)} now. Below the floor: "
        + ", ".join(f"{s} {v:.2f}" for s, v in below.items())
        + f". In 2017-2020 only {min(early_share):.0f}-{max(early_share):.0f}% of name-days cleared it. It is a "
        "nominal rupee floor applied to today's constituents, most of which were much smaller then, so it binds "
        "far harder in the early backtest years. The ₹3 cr level itself looks reasonable for today's list; "
        "whether to scale it with market turnover for the backtest is your call.")
    add("")
    elig = (qa.passed & liq.passed).loc[asof]
    add(f"Pass data QA **and** the liquidity gate today: N500 {int(elig[panel.symbols_in('N500')].sum())}, "
        f"MICRO250 {int(elig[micro].sum())}.")
    add("")
    add("## 8. Known gaps (not faked)")
    add("")
    add("* No delivery %: Yahoo has none.")
    add("* No price-band or trade-for-trade (T2T) history. The constituent CSV's `Series` column (EQ/BE) is "
        "stored for today only; the circuit check infers limits from price action.")
    add("* NSE earnings dates via Yahoo are unreliable; the earnings flag will be best effort, flag only.")
    add("* Survivorship bias: the universe is today's constituents, so the backtest never sees names that "
        "dropped out or delisted. Worse for MICRO250 (higher index churn); its results are reported separately "
        "and should be read as optimistic.")
    add("* Yahoo stub bars and unadjusted corporate actions exist (sections 3 and 6); they are detected, "
        "not repaired.")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "step1_data_report.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------------- step 2
def _fmt_ci(ci: Iterable[float] | None, as_pct: bool) -> str:
    if not ci:
        return ""
    lo, hi = ci
    return f"[{100 * lo:+.2f}%, {100 * hi:+.2f}%]" if as_pct else f"[{lo:+.3f}, {hi:+.3f}]"


def baserate_markdown(result: dict[str, Any], by_year: pd.DataFrame, by_regime: pd.DataFrame,
                      by_stop: pd.DataFrame, cfg: Config, window: list[str], data_asof: str,
                      git_sha: str | None) -> str:
    lines: list[str] = []
    add = lines.append
    seg = result["segments"]
    add("# Step 2: base-rate study (benchmark a)")
    add("")
    add(f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC, git `{git_sha}`, config `{cfg.hash}`, "
        f"data to {data_asof}, signal dates {window[0]} to {window[1]}. Reproduce: `python -m nsescan baserate`.")
    add("")
    add("**Question:** if you buy a random liquid name on a random day and manage it with the section-4 exits, "
        "costs and slippage, what happens? Anything the strategy claims later has to beat this, out of sample.")
    add("")
    add("## Definition")
    add("")
    add("* Entries: every (symbol, day T) that passes data QA and the segment's liquidity gate on T, which is the exact "
        "expectation of uniformly random entry dates. No other gate.")
    add(f"* Entry at the T+1 open; stop = min(low of T, lowest low of the {cfg['plan.stop_base_lookback']} sessions "
        "before T), with day T standing in for the breakout day. "
        f"Skipped when the stop is more than {pct(cfg['plan.max_stop_pct'], 0)} below the close (and again vs the fill).")
    add(f"* Exits as in section 4: stop (at the stop, or the open on a gap); breakeven from the session after "
        f"+{pct(cfg['plan.breakeven_at'], 0)}; sell {pct(cfg['plan.partial_frac'], 0)} at +{pct(cfg['plan.partial_at'], 0)} "
        f"and trail the rest on a close below EMA{cfg['plan.trail_ema']}; stall exit if below +{pct(cfg['plan.stall_min_gain'], 0)} "
        f"after {cfg['plan.stall_sessions']} sessions; time exit at the close of session {cfg['plan.time_exit_sessions']}. "
        "**Failed-breakout exit not applied: a random entry has no pivot.** Same-bar stop/target ties go to the stop.")
    add(f"* Costs (ASSUMPTIONS): {pct(cfg['costs.round_trip'], 2)} round trip; slippage per side "
        + ", ".join(f"{k} {pct(v, 2)}" for k, v in cfg["costs.slippage_per_side"].items()) + ".")
    add(f"* Label: triple barrier, upper +{pct(cfg['labels.upper'], 0)}, lower = stop, vertical "
        f"{cfg['labels.vertical_sessions']} sessions. \"Touched +15%\" ignores the stop.")
    add("* CIs: 95% percentile bootstrap resampling calendar months (trades in the same month move together).")
    add("")
    n5, mc = seg["N500"], seg["MICRO250"]
    add("## Bottom line")
    add("")
    def verdict(m: dict[str, Any]) -> str:
        r_hi, pct_hi = m["ci95"]["expectancy_r"][1], m["ci95"]["expectancy_pct"][1]
        if r_hi < 0 and pct_hi < 0:
            return "negative in R and in %, both CIs below zero"
        if r_hi < 0:
            return "negative in R (CI below zero); the % CI includes zero"
        return "not distinguishable from zero"

    add("After costs, a random liquid entry managed with these exits has **negative expectancy**. "
        f"N500: {n5['expectancy_r']:+.3f}R ({pct(n5['expectancy_pct'], 2)}) per trade, 95% CI "
        f"{_fmt_ci(n5['ci95'].get('expectancy_r'), False)} R, {verdict(n5)}. MICRO250: {mc['expectancy_r']:+.3f}R "
        f"({pct(mc['expectancy_pct'], 2)}), CI {_fmt_ci(mc['ci95'].get('expectancy_r'), False)} R, {verdict(mc)}. "
        f"Before costs: N500 {n5['expectancy_pct_gross'] * 100:+.2f}%, MICRO250 {mc['expectancy_pct_gross'] * 100:+.2f}% "
        "per trade. "
        f"+15% is reached before the stop on {pct(n5['hit_upper_first'])} (N500) and {pct(mc['hit_upper_first'])} "
        f"(MICRO250) of entries; ignoring the stop, the high touches +15% within 20 sessions on "
        f"{pct(n5['touched_upper_20'])} and {pct(mc['touched_upper_20'])}. These are the numbers the strategy has "
        "to beat out of sample, after costs.")
    add("")
    add("## Headline, by segment")
    add("")
    rows, rows2 = [], []
    for name in SEGMENTS:
        m = seg[name]
        rows.append({
            "segment": name, "trades": m["n"], "win rate": pct(m["win_rate"]), "avg win R": m["avg_win_r"],
            "avg loss R": m["avg_loss_r"], "expectancy R": m["expectancy_r"],
            "95% CI (R)": _fmt_ci(m["ci95"].get("expectancy_r"), False), "profit factor": m["profit_factor"],
            "avg sessions": m["avg_sessions"],
        })
        rows2.append({
            "segment": name, "expectancy %": pct(m["expectancy_pct"], 2),
            "95% CI (%)": _fmt_ci(m["ci95"].get("expectancy_pct"), True),
            "gross % (pre-cost)": pct(m["expectancy_pct_gross"], 2), "median stop": pct(m["median_stop_pct"]),
            "+15% before stop": pct(m["hit_upper_first"]), "95% CI": _fmt_ci(m["ci95"].get("hit_upper_first"), True),
            "stop first": pct(m["hit_lower_first"]), "touched +15% in 20 sessions": pct(m["touched_upper_20"]),
        })
    add(md_table(pd.DataFrame(rows), "{:.3f}"))
    add("")
    add(md_table(pd.DataFrame(rows2)))
    add("")
    add(f"Entries per month average {n5['trades_per_month']:.0f} (N500) and {mc['trades_per_month']:.0f} (MICRO250): "
        "every eligible name-day, not a signal count. Profit factor is on % returns, equal weight per trade.")
    add("")
    add("Exit mix:")
    add("")
    mix = pd.DataFrame({name: seg[name]["exit_mix"] for name in SEGMENTS}).fillna(0.0)
    mix = mix.map(lambda v: f"{100 * v:.1f}%").reset_index().rename(columns={"index": "exit"})
    add(md_table(mix))
    add("")
    add("Entries considered and skipped:")
    add("")
    add(md_table(pd.DataFrame(result["skips"]).fillna(0).astype(int).reset_index().rename(columns={"index": "count"}),
                 "{:.0f}"))
    add("")
    add("## MFE / MAE (closed trades, % from fill and in R)")
    add("")
    rows = []
    for name in SEGMENTS:
        for metric in ("mfe_pct", "mae_pct", "mfe_r", "mae_r"):
            q = seg[name][metric]
            is_pct = metric.endswith("pct")
            rows.append({"segment": name, "metric": metric,
                         **{k: (f"{100 * v:+.1f}%" if is_pct else f"{v:+.2f}") for k, v in q.items()}})
    add(md_table(pd.DataFrame(rows)))
    add("")
    add("## By stop distance (stop below the fill)")
    add("")
    add(_breakdown_md(by_stop, "stop_bucket"))
    add("")
    add("R-expectancy is driven by how close the stop is. With the stop within 1-2% of the fill, the round-trip "
        "cost and slippage alone are a large fraction of 1R and ordinary noise hits the stop, so R collapses even "
        "though the %-expectancy barely changes across buckets. The section-4 stop has a maximum "
        f"({pct(cfg['plan.max_stop_pct'], 0)}) but no minimum, and tight bases produce tight stops, so the same "
        "effect will hit the strategy. **Open question for you:** add a minimum stop distance (e.g. 1x ATR(14) "
        "or a fixed %)? Not changed without your decision.")
    add("")
    add("## By year")
    add("")
    add(_breakdown_md(by_year, "year"))
    add("")
    add("## By regime (state on signal day T)")
    add("")
    add(_breakdown_md(by_regime, "regime"))
    add("")
    add("UNDEFINED = the first year of data, before the VIX percentile has 252 sessions of history.")
    add("")
    add("## Eligible names per day (QA + liquidity), yearly average")
    add("")
    elig = pd.DataFrame(result["eligible_per_day"]).round(0)
    add(md_table(elig.reset_index().rename(columns={"index": "year"}), "{:.0f}"))
    add("")
    add("## Sensitivity: trades spanning a >25% single-day move")
    add("")
    rows = []
    for name in SEGMENTS:
        s = result["sensitivity_excl_big_move"][name]
        rows.append({"segment": name, "trades spanning a >25% day": s["excluded_trades"], "remaining": s["n"],
                     "expectancy R": s["expectancy_r"], "expectancy %": pct(s["expectancy_pct"], 2),
                     "win rate": pct(s["win_rate"]), "+15% first": pct(s["hit_upper_first"])})
    add(md_table(pd.DataFrame(rows), "{:.3f}"))
    add("")
    add("The headline keeps these trades (the conservative choice). Some are real crashes, others are unadjusted "
        "demergers where the \"loss\" was paid out as shares of the new company.")
    add("")
    add("## Caveats")
    add("")
    add("* Survivorship: today's constituents only. Names that fell out of the indices or delisted are missing, so "
        "these base rates are **optimistic**, MICRO250 most of all.")
    add("* The liquidity floors are nominal rupees, so far fewer names qualify in 2017-2020; the early years carry "
        "less weight and a different mix.")
    add("* Costs and slippage are assumptions, not measurements.")
    add("* This is benchmark (a) only. Benchmark (b) (naive momentum), (c) (Nifty 500 buy-and-hold, portfolio level) "
        "and portfolio CAGR / drawdown come with the step-4 backtest.")
    return "\n".join(lines) + "\n"


def _breakdown_md(frame: pd.DataFrame, key: str) -> str:
    if frame.empty:
        return "(no trades)"
    view = frame.copy()
    for col in ("win_rate", "hit_upper_first", "touched_upper_20"):
        view[col] = view[col].map(lambda v: pct(v))
    view["expectancy_pct"] = view["expectancy_pct"].map(lambda v: pct(v, 2))
    view = view[["segment", key, "n", "win_rate", "avg_win_r", "avg_loss_r", "expectancy_r", "expectancy_pct",
                 "profit_factor", "hit_upper_first", "touched_upper_20"]]
    view.columns = ["segment", key, "trades", "win rate", "avg win R", "avg loss R", "expectancy R", "expectancy %",
                    "PF", "+15% first", "touched +15%"]
    return md_table(view, "{:.3f}")

"""Configuration: every threshold the scanner, QA and backtest use.

`DEFAULTS` seeds the Supabase `config` table (see `sql/003_seed_config.sql`, generated
by `python -m nsescan config-sql`). At runtime the table is authoritative: values
found there override these defaults. Logic modules read thresholds only through a
`Config` object, never from literals.

Values that differ by segment are dicts keyed by segment ("N500", "MICRO250");
read them with `Config.seg(key, segment)`.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Mapping

LOGGER = logging.getLogger(__name__)

SEGMENTS: tuple[str, ...] = ("N500", "MICRO250")
CRORE = 1e7  # INR

# key -> (default value, description)
DEFAULTS: dict[str, tuple[Any, str]] = {
    # ---- data ------------------------------------------------------------
    "data.history_years": (10, "Years of daily history fetched on the initial load."),
    "data.fetch_chunk_size": (100, "Tickers per yf.download call."),
    "data.fetch_max_retries": (4, "Retries for tickers that come back empty or error (backoff 2s, 4s, 8s, 16s)."),
    "data.fetch_backoff_base_sec": (2.0, "First retry delay in seconds; doubles each retry."),
    "data.update_overlap_sessions": (10, "Sessions re-fetched on each incremental update to detect revisions."),
    "data.adjustment_tolerance": (0.001, "Median |relative close difference| on overlapping bars (excluding the newest) above which Yahoo is taken to have re-adjusted the series; the symbol's full history is re-fetched."),
    "data.stale_refetch_days": (60, "Symbols whose last stored bar is older than this many days get a full-history refetch instead of an incremental one."),
    "data.revision_tolerance": (1e-5, "On updates, an already-stored bar is rewritten only if a price moved by more than this relative amount or the volume changed (Yahoo's adjusted values jitter in the 4th decimal between fetches)."),
    "data.eod_cutoff_hour_ist": (16, "Bars for today are stored only when fetching at or after this IST hour."),
    "data.calendar_min_coverage": (0.5, "A date is an NSE session if at least this share of listed symbols has a bar."),
    "data.stub_date_min_share": (0.10, "A date is a stub date if at least this share of its bars have zero volume and open = high = low = close. Stub dates without a Nifty 50 bar are holidays (dropped); with one, they are real sessions whose stub bars are dropped as missing."),
    "data.benchmarks": ({"nifty500": "^CRSLDX", "nifty50": "^NSEI", "vix": "^INDIAVIX"}, "Yahoo tickers for benchmarks."),
    # ---- data QA (per segment; MICRO250 is stricter) ----------------------
    "qa.min_bars": ({"N500": 250, "MICRO250": 250}, "Minimum bars of history."),
    "qa.lookback_sessions": (252, "Window (sessions) for the missing / zero-volume / big-move checks."),
    "qa.max_missing_pct": ({"N500": 0.02, "MICRO250": 0.02}, "Max share of NSE sessions without a bar in the lookback window."),
    "qa.max_zero_volume_days": ({"N500": 3, "MICRO250": 0}, "Max zero/null-volume days in the lookback window."),
    "qa.big_move_threshold": (0.25, "Single-day |close/prev close - 1| above this is flagged (possible unadjusted corporate action)."),
    "qa.max_big_moves": ({"N500": 0, "MICRO250": 0}, "Max big moves in the lookback window before the symbol is excluded; null = flag only. Default 0 for both: most >25% days in this data are unadjusted demergers/splits or Muhurat-session glitches that corrupt SMAs, 52w levels and RS for a year."),
    # ---- liquidity gate --------------------------------------------------
    "liquidity.tv_window": (50, "Sessions for the median traded value (close x volume)."),
    "liquidity.min_median_tv_cr": ({"N500": 10.0, "MICRO250": 3.0}, "Min median traded value, INR crore."),
    "liquidity.min_close": ({"N500": 50.0, "MICRO250": 30.0}, "Min close, INR."),
    "liquidity.zero_volume_lookback": ({"N500": None, "MICRO250": 60}, "No zero-volume days allowed in this many sessions; null = not applied."),
    # ---- volatility capacity ---------------------------------------------
    "vol.atr_period": (14, "ATR period."),
    "vol.min_atr_pct": (0.025, "Min ATR/close."),
    "vol.max_atr_pct": (0.07, "Max ATR/close."),
    # ---- stage 2 -----------------------------------------------------------
    "stage2.sma_fast": (50, "Fast SMA."),
    "stage2.sma_mid": (150, "Mid SMA."),
    "stage2.sma_slow": (200, "Slow SMA."),
    "stage2.slow_slope_lookback": (20, "SMA200(T) must exceed SMA200(T - this)."),
    "stage2.lookback_52w": (252, "Sessions in the 52-week window."),
    "stage2.min_above_52w_low": (0.30, "Close must be at least this far above the 52w low."),
    "stage2.min_pct_of_52w_high": (0.85, "Close must be at least this fraction of the 52w high."),
    # ---- relative strength -------------------------------------------------
    "rs.weights": ([0.4, 0.2, 0.2, 0.2], "Weights for returns over the last 63d, 63-126d, 126-189d, 189-252d."),
    "rs.block_sessions": (63, "Sessions per RS block."),
    "rs.min_rank": (80.0, "Min RS percentile rank (0-100) across the combined universe."),
    "sector.top_frac": (0.5, "Industry median RS rank must be in this top fraction of industries."),
    # ---- base detection ------------------------------------------------------
    "base.min_len": (10, "Shortest base window (sessions), ending at T-1."),
    "base.max_len": (60, "Longest base window (sessions), ending at T-1."),
    "base.max_depth": (0.25, "Max (max high - min low) / max high over the base."),
    "base.pivot_min_age": (3, "The pivot (max high) must not be set in the last N base bars."),
    "base.contraction_last_n": (10, "Final base sessions used for contraction and dry-up."),
    "base.max_range_ratio": (0.5, "Contraction: range of last N sessions <= this x full base range."),
    "base.atr_short": (5, "Contraction alt: short ATR period."),
    "base.atr_long": (50, "Contraction alt: long ATR period."),
    "base.max_atr_ratio": (0.75, "Contraction alt: ATR(short)/ATR(long) <= this."),
    "base.vol_median_window": (50, "Sessions for the median volume reference."),
    "base.max_dryup_ratio": (0.70, "Median volume of the last N base sessions <= this x 50d median."),
    "base.impulse_lookback": (60, "Sessions before base start scanned for the prior impulse (score only)."),
    # ---- trigger ---------------------------------------------------------------
    "trigger.min_vol_ratio": (1.5, "Volume(T) >= this x 50d median volume."),
    "trigger.min_close_location": (0.7, "(close - low)/(high - low) on T."),
    "trigger.chase_max_atr": (1.0, "Close - pivot <= this x ATR(14), else EXTENDED."),
    "trigger.chase_max_pct": (0.04, "Close <= pivot x (1 + this), else EXTENDED."),
    "trigger.circuit_bands": ([0.02, 0.05, 0.10, 0.20], "NSE price-band limits checked for a possible upper circuit."),
    "trigger.circuit_tolerance": (0.001, "Day change within this of a band limit (and close == high) flags POSSIBLE_UPPER_CIRCUIT."),
    "trigger.earnings_window_sessions": (5, "Flag if Yahoo shows results within this many sessions (best effort; flag only)."),
    "setup.max_below_pivot": (0.03, "SETUP: close within this fraction below the pivot."),
    # ---- regime ------------------------------------------------------------------
    "regime.bench_sma": (50, "Nifty 500 must close above this SMA."),
    "regime.breadth_sma": (50, "Breadth = share of universe closing above this SMA."),
    "regime.min_breadth": (0.40, "Min breadth for the breadth input to be true."),
    "regime.vix_lookback": (252, "Sessions for the India VIX percentile."),
    "regime.max_vix_pctile": (0.80, "VIX must be below this percentile of its lookback."),
    "regime.neutral_min_grade": ("A", "In NEUTRAL, only triggers of this grade."),
    "regime.neutral_size_mult": (0.5, "In NEUTRAL, position size multiplier."),
    # ---- score ------------------------------------------------------------------
    "score.weights": (
        {
            "rs_rank": 0.25,
            "base_tightness": 0.20,
            "vol_dryup": 0.15,
            "breakout_vol": 0.15,
            "near_high": 0.10,
            "prior_impulse": 0.10,
            "sector_rs": 0.05,
        },
        "Composite score weights (cross-sectional percentiles among passing names).",
    ),
    "score.grade_a": (80.0, "Grade A if score >= this."),
    "score.grade_b": (65.0, "Grade B if score >= this (else C)."),
    # ---- trade plan (identical in live output and backtest) ----------------------
    "plan.capital": (1_000_000.0, "Account capital for sizing, INR."),
    "plan.stop_base_lookback": (5, "Stop = min(low of breakout day, lowest low of the final N base sessions)."),
    "plan.max_stop_pct": (0.08, "Reject if the stop distance exceeds this (vs close at signal; vs the fill at entry)."),
    "plan.risk_per_trade": ({"N500": 0.0075, "MICRO250": 0.005}, "Capital fraction risked per trade."),
    "plan.max_pos_pct_of_tv": (0.02, "Position value <= this x the 50d median traded value."),
    "plan.max_open_positions": (8, "Max open positions."),
    "plan.max_per_industry": (2, "Max open positions per NSE industry."),
    "plan.max_micro_positions": (3, "Max open MICRO250 positions."),
    "plan.failed_breakout_sessions": (3, "Close below pivot within the first N sessions -> exit next open."),
    "plan.breakeven_at": (0.10, "At +this (intraday high), stop moves to breakeven from the next session."),
    "plan.partial_at": (0.15, "At +this, sell the partial fraction (limit fill)."),
    "plan.partial_frac": (0.5, "Fraction sold at the partial target."),
    "plan.trail_ema": (10, "After the partial, exit the rest on a close below this EMA (next open)."),
    "plan.stall_enabled": (True, "Stall exit on/off."),
    "plan.stall_sessions": (7, "Stall check after this many sessions."),
    "plan.stall_min_gain": (0.03, "Stall exit if close gain is below this at the stall check (next open)."),
    "plan.time_exit_sessions": (20, "Exit at the close of this session."),
    "plan.targets": ([0.15, 0.20], "Reference target lines (t1, t2) as gains over the entry reference."),
    # ---- costs (assumptions; labelled as such in reports) ------------------------
    "costs.round_trip": (0.0025, "Round-trip costs (brokerage, STT, fees), split evenly across both sides."),
    "costs.slippage_per_side": ({"N500": 0.001, "MICRO250": 0.0025}, "Slippage per side."),
    # ---- labels / backtest ----------------------------------------------------------
    "labels.upper": (0.15, "Triple barrier: upper barrier gain."),
    "labels.vertical_sessions": (20, "Triple barrier: vertical barrier in sessions (lower = stop)."),
    "backtest.seed": (42, "RNG seed for random-entry benchmarks and bootstraps."),
    "backtest.bootstrap_reps": (1000, "Month-block bootstrap replications for confidence intervals."),
    "backtest.walkforward_train_years": (3, "Walk-forward tuning window."),
    "backtest.walkforward_test_years": (1, "Walk-forward test window."),
    "backtest.embargo_sessions": (20, "Purged K-fold embargo."),
    "backtest.kfold": (5, "Purged K-fold folds."),
}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class Config:
    """Immutable config snapshot. `hash` identifies it in scan_runs, signals and backtest_runs."""

    values: Mapping[str, Any]
    source: str

    def __getitem__(self, key: str) -> Any:
        return self.values[key]

    def seg(self, key: str, segment: str) -> Any:
        value = self.values[key]
        if isinstance(value, dict) and segment in value:
            return value[segment]
        if isinstance(value, dict) and set(value) & set(SEGMENTS):
            raise KeyError(f"{key} has no value for segment {segment}")
        return value

    @property
    def hash(self) -> str:
        return hashlib.sha256(_canonical(dict(self.values)).encode()).hexdigest()[:12]

    def snapshot(self) -> dict[str, Any]:
        return json.loads(_canonical(dict(self.values)))

    def with_overrides(self, overrides: Mapping[str, Any], source: str | None = None) -> "Config":
        unknown = sorted(set(overrides) - set(self.values))
        if unknown:
            raise KeyError(f"Unknown config keys: {unknown}")
        merged = dict(self.values)
        merged.update(overrides)
        return Config(values=merged, source=source or self.source)


def default_config() -> Config:
    return Config(values={key: value for key, (value, _) in DEFAULTS.items()}, source="defaults")


def config_from_rows(rows: list[Mapping[str, Any]]) -> tuple[Config, list[str]]:
    """Build a Config from `config` table rows ({key, value}); DB values override defaults.

    Returns the config and warnings (unknown keys in the DB, defaults missing from the DB).
    """

    warnings: list[str] = []
    db_values = {row["key"]: row["value"] for row in rows}
    unknown = sorted(set(db_values) - set(DEFAULTS))
    if unknown:
        warnings.append(f"config table has unknown keys (ignored): {unknown}")
    missing = sorted(set(DEFAULTS) - set(db_values))
    if missing:
        warnings.append(f"config table missing keys (defaults used): {missing}")
    known = {key: value for key, value in db_values.items() if key in DEFAULTS}
    config = default_config().with_overrides(known, source="supabase")
    for message in warnings:
        LOGGER.warning(message)
    return config, warnings


def seed_sql() -> str:
    """SQL that inserts every default (existing keys are left untouched)."""

    lines = [
        "-- Generated by `python -m nsescan config-sql`. Inserts defaults; never overwrites edited values.",
        "insert into config (key, value, default_value, description) values",
    ]
    rows = []
    for key, (value, description) in DEFAULTS.items():
        literal = _canonical(value).replace("'", "''")
        desc = description.replace("'", "''")
        rows.append(f"  ('{key}', '{literal}'::jsonb, '{literal}'::jsonb, '{desc}')")
    lines.append(",\n".join(rows))
    lines.append("on conflict (key) do update set default_value = excluded.default_value, description = excluded.description;")
    return "\n".join(lines) + "\n"

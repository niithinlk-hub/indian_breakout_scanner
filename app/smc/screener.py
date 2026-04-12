from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.smc.breakout import analyze_breakout
from app.smc.config import SMCAnalyzerConfig
from app.smc.fvg import detect_fvgs
from app.smc.structure import analyze_structure
from app.smc.utils import as_percentage


@dataclass(slots=True)
class SymbolAnalysis:
    """Full analysis bundle for one symbol."""

    symbol: str
    history: pd.DataFrame
    structure: dict[str, Any]
    breakout: dict[str, Any]
    fvgs: pd.DataFrame
    setup: dict[str, Any]


def _latest_relevant_fvg(
    fvgs: pd.DataFrame,
    direction: str,
    *,
    fresh_only: bool,
) -> dict[str, Any] | None:
    if fvgs.empty:
        return None
    filtered = fvgs.loc[fvgs["direction"] == direction].copy()
    if fresh_only:
        filtered = filtered.loc[filtered["status"] == "fresh"]
    else:
        filtered = filtered.loc[filtered["status"] != "fully filled"]
    if filtered.empty:
        return None
    return filtered.sort_values("timestamp").iloc[-1].to_dict()


def _inside_or_near_zone(price: float, fvg: dict[str, Any], near_threshold_pct: float) -> tuple[bool, float | None]:
    bottom = float(fvg["bottom"])
    top = float(fvg["top"])
    midpoint = float(fvg["midpoint"])
    zone_low = min(bottom, top)
    zone_high = max(bottom, top)
    if zone_low <= price <= zone_high:
        return True, round(((price - midpoint) / midpoint) * 100.0, 4) if midpoint else None
    threshold_points = midpoint * (near_threshold_pct / 100.0)
    near_zone = (zone_low - threshold_points) <= price <= (zone_high + threshold_points)
    return near_zone, round(((price - midpoint) / midpoint) * 100.0, 4) if midpoint else None


def _score_setup(
    *,
    direction: str,
    structure_bias: str,
    latest_event: str,
    breakout_status: str,
    fvg: dict[str, Any] | None,
    distance_to_midpoint_pct: float | None,
    relative_volume: float | None,
    atr_quality: float | None,
    fresh_only: bool,
) -> tuple[float, str]:
    score = 0.0
    if direction == structure_bias or latest_event.lower().startswith(direction):
        score += 25
    elif structure_bias == "neutral":
        score += 10

    if direction == "bullish" and breakout_status == "Bullish Breakout":
        score += 20
    elif direction == "bearish" and breakout_status == "Bearish Breakdown":
        score += 20
    elif direction == "bullish" and breakout_status == "Near Bullish Breakout":
        score += 12
    elif direction == "bearish" and breakout_status == "Near Bearish Breakdown":
        score += 12

    if latest_event.endswith("BOS"):
        score += 12
    elif "CHOCH" in latest_event.upper():
        score += 8

    if fvg is not None:
        if fvg["status"] == "fresh":
            score += 15
        elif fvg["status"] == "partially mitigated" and not fresh_only:
            score += 8

        if distance_to_midpoint_pct is not None:
            distance = abs(distance_to_midpoint_pct)
            if distance <= 0.5:
                score += 15
            elif distance <= 1.5:
                score += 10
            elif distance <= 3.0:
                score += 5

        if atr_quality is not None:
            score += min(8.0, max(0.0, atr_quality * 8.0))

    if relative_volume is not None:
        if relative_volume >= 2.0:
            score += 10
        elif relative_volume >= 1.2:
            score += 6
        elif relative_volume >= 1.0:
            score += 3

    score = round(min(score, 100.0), 2)
    if score >= 80:
        return score, "High Conviction"
    if score >= 60:
        return score, "Medium Conviction"
    return score, "Low Conviction"


def _build_setup_context(
    *,
    symbol: str,
    direction: str,
    price: float,
    breakout: dict[str, Any],
    structure: dict[str, Any],
    fvg: dict[str, Any] | None,
) -> str:
    bias = structure["latest_bias"]
    event = structure["latest_event"]
    breakout_status = breakout["status"]
    breakout_level = breakout["breakout_level"] if direction == "bullish" else breakout["breakdown_level"]

    if fvg is not None:
        entry_zone = f"{min(float(fvg['bottom']), float(fvg['top'])):.2f} to {max(float(fvg['bottom']), float(fvg['top'])):.2f}"
        invalidation = f"{float(fvg['bottom']) * 0.995:.2f}" if direction == "bullish" else f"{float(fvg['top']) * 1.005:.2f}"
        target = breakout_level if breakout_level is not None else price
        fvg_context = f"{direction.title()} FVG is {fvg['status']} with midpoint near {float(fvg['midpoint']):.2f}."
    else:
        entry_zone = "No active FVG zone"
        invalidation = "Use latest swing structure"
        target = breakout_level if breakout_level is not None else price
        fvg_context = "No active qualifying FVG is available right now."

    return (
        f"Setup context for {symbol}: directional bias is {direction}, while market structure is {bias} with latest event "
        f"{event}. Breakout context is {breakout_status} around {breakout_level if breakout_level is not None else 'NA'}. "
        f"Potential entry zone is {entry_zone}, invalidation reference is {invalidation}, and first target reference is {target}. "
        f"{fvg_context} This is descriptive setup context only, not personalized financial advice."
    )


def analyze_symbol(symbol: str, history: pd.DataFrame, config: SMCAnalyzerConfig) -> SymbolAnalysis:
    """Run full BOS/FVG/breakout analysis for one symbol."""

    trimmed = history.sort_values("datetime").tail(config.lookback_bars).reset_index(drop=True)
    structure = analyze_structure(trimmed, left_bars=config.pivot_left_bars, right_bars=config.pivot_right_bars)
    breakout = analyze_breakout(
        trimmed,
        breakout_lookback=config.breakout_lookback,
        close_confirmation=config.close_breakout_confirmation,
        buffer_pct=config.breakout_buffer_pct,
        near_threshold_pct=config.near_zone_threshold_pct,
    )
    fvgs = detect_fvgs(
        trimmed,
        min_gap_size_pct=config.min_fvg_size_pct,
        use_atr_filter=config.use_atr_gap_filter,
        atr_gap_multiplier=config.atr_gap_multiplier,
    )

    current_price = float(trimmed["close"].iloc[-1])
    breakout_status = str(breakout["status"])
    structure_bias = str(structure["latest_bias"])
    latest_event = str(structure["latest_event"])
    relative_volume = breakout.get("relative_volume")
    bullish_fvg = _latest_relevant_fvg(fvgs, "bullish", fresh_only=config.fresh_fvg_only)
    bearish_fvg = _latest_relevant_fvg(fvgs, "bearish", fresh_only=config.fresh_fvg_only)

    candidates: list[dict[str, Any]] = []
    for direction, relevant_fvg in [("bullish", bullish_fvg), ("bearish", bearish_fvg)]:
        if config.direction_filter != "all" and config.direction_filter != direction:
            continue
        if relevant_fvg is None:
            continue
        near_zone, distance_to_midpoint_pct = _inside_or_near_zone(current_price, relevant_fvg, config.near_zone_threshold_pct)
        breakout_aligned = breakout_status in {
            "Bullish Breakout" if direction == "bullish" else "Bearish Breakdown",
            "Near Bullish Breakout" if direction == "bullish" else "Near Bearish Breakdown",
        }
        structure_aligned = structure_bias == direction or latest_event.lower().startswith(direction)
        volume_ok = not config.use_volume_filter or (relative_volume is not None and relative_volume >= config.volume_spike_multiple)

        if not (structure_aligned and breakout_aligned and near_zone and volume_ok):
            continue

        atr_quality = min(float(relevant_fvg["size_pct"]) / max(config.min_fvg_size_pct, 0.1), 2.0) / 2.0
        conviction_score, conviction_tag = _score_setup(
            direction=direction,
            structure_bias=structure_bias,
            latest_event=latest_event,
            breakout_status=breakout_status,
            fvg=relevant_fvg,
            distance_to_midpoint_pct=distance_to_midpoint_pct,
            relative_volume=relative_volume,
            atr_quality=atr_quality,
            fresh_only=config.fresh_fvg_only,
        )
        candidates.append(
            {
                "symbol": symbol,
                "timeframe": config.timeframe,
                "current_price": current_price,
                "breakout_status": breakout_status,
                "structure_bias": structure_bias,
                "latest_structure_event": latest_event,
                "fvg_direction": direction,
                "fvg_top": relevant_fvg["top"],
                "fvg_bottom": relevant_fvg["bottom"],
                "fvg_midpoint": relevant_fvg["midpoint"],
                "fvg_status": relevant_fvg["status"],
                "distance_to_fvg_midpoint_pct": distance_to_midpoint_pct,
                "relative_volume": relative_volume,
                "signal_timestamp": relevant_fvg["timestamp"],
                "conviction_score": conviction_score,
                "conviction_tag": conviction_tag,
                "setup_context": _build_setup_context(
                    symbol=symbol,
                    direction=direction,
                    price=current_price,
                    breakout=breakout,
                    structure=structure,
                    fvg=relevant_fvg,
                ),
            },
        )

    if candidates:
        setup = max(candidates, key=lambda item: float(item["conviction_score"]))
    else:
        fallback_direction = "bullish" if structure_bias == "bullish" else "bearish" if structure_bias == "bearish" else "neutral"
        chosen_fvg = bullish_fvg if fallback_direction == "bullish" else bearish_fvg
        setup = {
            "symbol": symbol,
            "timeframe": config.timeframe,
            "current_price": current_price,
            "breakout_status": breakout_status,
            "structure_bias": structure_bias,
            "latest_structure_event": latest_event,
            "fvg_direction": chosen_fvg["direction"] if chosen_fvg else "none",
            "fvg_top": chosen_fvg["top"] if chosen_fvg else None,
            "fvg_bottom": chosen_fvg["bottom"] if chosen_fvg else None,
            "fvg_midpoint": chosen_fvg["midpoint"] if chosen_fvg else None,
            "fvg_status": chosen_fvg["status"] if chosen_fvg else "none",
            "distance_to_fvg_midpoint_pct": None,
            "relative_volume": relative_volume,
            "signal_timestamp": structure["latest_event_time"] or trimmed["datetime"].iloc[-1],
            "conviction_score": 0.0,
            "conviction_tag": "Low Conviction",
            "setup_context": _build_setup_context(
                symbol=symbol,
                direction=fallback_direction,
                price=current_price,
                breakout=breakout,
                structure=structure,
                fvg=chosen_fvg,
            ),
        }

    return SymbolAnalysis(symbol=symbol, history=trimmed, structure=structure, breakout=breakout, fvgs=fvgs, setup=setup)


def screen_watchlist(history_map: dict[str, pd.DataFrame], config: SMCAnalyzerConfig) -> tuple[pd.DataFrame, dict[str, SymbolAnalysis]]:
    """Screen a watchlist and return setup candidates plus per-symbol analysis."""

    analyses: dict[str, SymbolAnalysis] = {}
    rows: list[dict[str, Any]] = []
    for symbol, history in history_map.items():
        if history.empty:
            continue
        analysis = analyze_symbol(symbol, history, config)
        analyses[symbol] = analysis
        if float(analysis.setup["conviction_score"]) > 0:
            rows.append(analysis.setup)

    results = pd.DataFrame(rows)
    if not results.empty:
        results = results.sort_values(
            by=["conviction_score", "relative_volume"],
            ascending=[False, False],
            kind="mergesort",
        ).reset_index(drop=True)
    return results, analyses

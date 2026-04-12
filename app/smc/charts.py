from __future__ import annotations

import pandas as pd

from app.smc.screener import SymbolAnalysis


def build_analysis_chart(analysis: SymbolAnalysis):
    """Build a Plotly candlestick chart with pivots, events, breakout levels, and FVG zones."""

    import plotly.graph_objects as go

    history = analysis.history.copy()
    pivots = analysis.structure["pivot_frame"]
    events = analysis.structure["events"]
    breakout = analysis.breakout
    figure = go.Figure()
    figure.add_trace(
        go.Candlestick(
            x=history["datetime"],
            open=history["open"],
            high=history["high"],
            low=history["low"],
            close=history["close"],
            name="Price",
        ),
    )

    pivot_highs = pivots.loc[pd.notna(pivots["pivot_high"])]
    pivot_lows = pivots.loc[pd.notna(pivots["pivot_low"])]
    if not pivot_highs.empty:
        figure.add_scatter(
            x=pivot_highs["datetime"],
            y=pivot_highs["pivot_high"],
            mode="markers",
            marker=dict(size=8, color="#d62728", symbol="triangle-down"),
            name="Swing highs",
        )
    if not pivot_lows.empty:
        figure.add_scatter(
            x=pivot_lows["datetime"],
            y=pivot_lows["pivot_low"],
            mode="markers",
            marker=dict(size=8, color="#2ca02c", symbol="triangle-up"),
            name="Swing lows",
        )

    for _, row in events.tail(12).iterrows():
        color = "#2ca02c" if row["direction"] == "bullish" else "#d62728"
        figure.add_annotation(
            x=row["datetime"],
            y=row["close"],
            text=row["event"],
            showarrow=True,
            arrowhead=2,
            font=dict(color=color, size=10),
            arrowcolor=color,
        )

    if breakout.get("breakout_level") is not None:
        figure.add_hline(
            y=float(breakout["breakout_level"]),
            line_dash="dot",
            line_color="#2ca02c",
            annotation_text="Bullish breakout level",
        )
    if breakout.get("breakdown_level") is not None:
        figure.add_hline(
            y=float(breakout["breakdown_level"]),
            line_dash="dot",
            line_color="#d62728",
            annotation_text="Bearish breakdown level",
        )

    for _, fvg in analysis.fvgs.tail(8).iterrows():
        fillcolor = "rgba(44,160,44,0.18)" if fvg["direction"] == "bullish" else "rgba(214,39,40,0.18)"
        figure.add_hrect(
            y0=min(float(fvg["bottom"]), float(fvg["top"])),
            y1=max(float(fvg["bottom"]), float(fvg["top"])),
            x0=fvg["timestamp"],
            x1=history["datetime"].iloc[-1],
            fillcolor=fillcolor,
            line_width=0,
            annotation_text=f"{fvg['direction'].title()} FVG",
            annotation_position="top left",
        )

    figure.add_hline(
        y=float(history["close"].iloc[-1]),
        line_color="#1f77b4",
        line_dash="dash",
        annotation_text="Current price",
    )
    figure.update_layout(
        height=650,
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h"),
    )
    return figure

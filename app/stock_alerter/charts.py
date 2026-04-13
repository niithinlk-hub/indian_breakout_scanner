from __future__ import annotations

import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from app.stock_alerter.config import StockAlerterConfig
from app.stock_alerter.indicators import calculate_indicators
from app.stock_alerter.structure_logic import detect_bos, detect_bullish_fvg
from app.stock_alerter.utils import rolling_pivots


def build_stock_chart(history: pd.DataFrame, signal: dict[str, object] | None, config: StockAlerterConfig, benchmark_df: pd.DataFrame | None = None):
    """Build a candlestick + volume chart with breakout overlays."""

    frame = calculate_indicators(history, benchmark_df)
    figure = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25], vertical_spacing=0.04)
    figure.add_trace(
        go.Candlestick(
            x=frame["datetime"],
            open=frame["open"],
            high=frame["high"],
            low=frame["low"],
            close=frame["close"],
            name="Price",
        ),
        row=1,
        col=1,
    )
    figure.add_trace(go.Scatter(x=frame["datetime"], y=frame["ema20"], mode="lines", name="EMA20", line=dict(color="#1f77b4")), row=1, col=1)
    figure.add_trace(go.Scatter(x=frame["datetime"], y=frame["ema50"], mode="lines", name="EMA50", line=dict(color="#ff7f0e")), row=1, col=1)

    if signal and signal.get("breakout_level") is not None:
        figure.add_hline(y=float(signal["breakout_level"]), line_dash="dot", line_color="#2ca02c", annotation_text="Breakout level", row=1, col=1)

    bos = detect_bos(frame, config)
    if bos["is_valid"]:
        figure.add_scatter(
            x=[frame["datetime"].iloc[-1]],
            y=[float(bos["breakout_level"])],
            mode="markers",
            marker=dict(color="#2ca02c", size=11, symbol="star"),
            name="BOS",
            row=1,
            col=1,
        )

    fvg = detect_bullish_fvg(frame, config)
    if fvg["is_valid"]:
        top = float(fvg["supporting_metrics"]["fvg_top"])
        bottom = float(fvg["supporting_metrics"]["fvg_bottom"])
        figure.add_hrect(
            y0=min(top, bottom),
            y1=max(top, bottom),
            fillcolor="rgba(44,160,44,0.16)",
            line_width=0,
            annotation_text="Bullish FVG",
            annotation_position="top left",
            row=1,
            col=1,
        )

    pivots = rolling_pivots(frame.tail(80).reset_index(drop=True), left=2, right=2)
    highs = pivots.loc[pd.notna(pivots["pivot_high"])]
    lows = pivots.loc[pd.notna(pivots["pivot_low"])]
    if not highs.empty:
        figure.add_scatter(
            x=highs["datetime"],
            y=highs["pivot_high"],
            mode="markers",
            marker=dict(color="#d62728", size=8, symbol="triangle-down"),
            name="Swing highs",
            row=1,
            col=1,
        )
    if not lows.empty:
        figure.add_scatter(
            x=lows["datetime"],
            y=lows["pivot_low"],
            mode="markers",
            marker=dict(color="#2ca02c", size=8, symbol="triangle-up"),
            name="Swing lows",
            row=1,
            col=1,
        )

    figure.add_trace(
        go.Bar(x=frame["datetime"], y=frame["volume"], name="Volume", marker_color="#8c8c8c"),
        row=2,
        col=1,
    )
    figure.update_layout(height=700, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h"))
    return figure

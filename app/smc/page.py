from __future__ import annotations

from io import StringIO

import pandas as pd
import streamlit as st

from app.smc.charts import build_analysis_chart
from app.smc.config import DEFAULT_BANKNIFTY, DEFAULT_NIFTY50, SMCAnalyzerConfig
from app.smc.data_loader import load_symbol_history, load_watchlist_history, parse_uploaded_csv
from app.smc.screener import analyze_symbol, screen_watchlist
from app.smc.utils import denormalize_nse_ticker, parse_custom_tickers, parse_uploaded_watchlist, unique_preserving_order


def _resolve_watchlist(source: str, custom_text: str, uploaded_frame: pd.DataFrame) -> list[str]:
    if source == "NIFTY 50":
        return unique_preserving_order(DEFAULT_NIFTY50)
    if source == "BANKNIFTY majors":
        return unique_preserving_order(DEFAULT_BANKNIFTY)
    if source == "Custom input":
        return unique_preserving_order(parse_custom_tickers(custom_text))
    if source == "CSV upload":
        return unique_preserving_order(parse_uploaded_watchlist(uploaded_frame))
    return []


def _render_summary_cards(results_df: pd.DataFrame, analyses: dict[str, object]) -> None:
    total = len(analyses)
    bullish = len(results_df.loc[results_df["fvg_direction"] == "bullish"]) if not results_df.empty else 0
    bearish = len(results_df.loc[results_df["fvg_direction"] == "bearish"]) if not results_df.empty else 0
    strongest = results_df.iloc[0]["symbol"] if not results_df.empty else "None"
    if not results_df.empty:
        latest_event = results_df.iloc[0]["latest_structure_event"]
    elif analyses:
        latest_event = next(iter(analyses.values())).setup["latest_structure_event"]
    else:
        latest_event = "None"

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Symbols scanned", total)
    col2.metric("Bullish setups", bullish)
    col3.metric("Bearish setups", bearish)
    col4.metric("Strongest setup", strongest)
    col5.metric("Latest BOS/CHoCH", latest_event)


def _render_screener_section(results_df: pd.DataFrame) -> None:
    st.subheader("BOS + FVG Screener")
    if results_df.empty:
        st.info("No qualifying setups matched the current filters. Try lowering the gap filter or widening the near-zone threshold.")
        return

    conviction_tags = sorted(results_df["conviction_tag"].dropna().unique().tolist())
    breakout_statuses = sorted(results_df["breakout_status"].dropna().unique().tolist())
    col1, col2 = st.columns(2)
    selected_tags = col1.multiselect("Filter conviction tag", conviction_tags, default=conviction_tags)
    selected_statuses = col2.multiselect("Filter breakout status", breakout_statuses, default=breakout_statuses)

    filtered = results_df.copy()
    if selected_tags:
        filtered = filtered.loc[filtered["conviction_tag"].isin(selected_tags)]
    if selected_statuses:
        filtered = filtered.loc[filtered["breakout_status"].isin(selected_statuses)]

    st.dataframe(filtered, width="stretch")
    st.download_button(
        "Export BOS/FVG results",
        filtered.to_csv(index=False),
        file_name="bos_fvg_screener.csv",
        mime="text/csv",
    )
    st.caption("Top 5 setups")
    st.dataframe(filtered.head(5), width="stretch")


def _render_single_symbol_section(config: SMCAnalyzerConfig, analyses: dict[str, object]) -> None:
    st.subheader("Single-symbol analysis")
    default_symbol = next(iter(analyses.keys()), "RELIANCE")
    analysis_symbol = st.text_input("Analyze symbol", value=default_symbol, help="Enter an NSE ticker like RELIANCE or TCS.")
    history_period = st.selectbox("Single-symbol history period", options=["1y", "2y", "5y", "10y"], index=2)

    if st.button("Analyze single stock", width="stretch"):
        try:
            history, notices = load_symbol_history(analysis_symbol, config.timeframe, history_period)
        except Exception as exc:
            st.error(f"Could not load history: {exc}")
            return

        for notice in notices:
            st.caption(notice)
        if history.empty:
            st.warning("No price history returned for that symbol.")
            return

        analysis = analyze_symbol(denormalize_nse_ticker(analysis_symbol), history, config)
        figure = build_analysis_chart(analysis)
        st.plotly_chart(figure, width="stretch")

        latest_setup = analysis.setup
        active_fvgs = analysis.fvgs.loc[analysis.fvgs["status"] != "fully filled"]
        summary_cols = st.columns(5)
        summary_cols[0].metric("Trend bias", str(analysis.structure["latest_bias"]).title())
        summary_cols[1].metric("Breakout status", str(analysis.breakout["status"]))
        summary_cols[2].metric("Active FVGs", len(active_fvgs))
        summary_cols[3].metric(
            "Nearest setup zone",
            f"{latest_setup['fvg_midpoint']:.2f}" if latest_setup.get("fvg_midpoint") is not None else "NA",
        )
        summary_cols[4].metric("Conviction", f"{latest_setup['conviction_score']:.1f}")

        st.info(latest_setup["setup_context"])
        if not active_fvgs.empty:
            st.dataframe(active_fvgs.sort_values("timestamp", ascending=False), width="stretch")


def render_smc_analyzer_page() -> None:
    """Render the Yahoo-powered breakout + BOS + FVG analyzer page."""

    st.sidebar.divider()
    st.sidebar.subheader("BOS + FVG Analyzer")
    watchlist_source = st.sidebar.selectbox(
        "Watchlist source",
        options=["NIFTY 50", "BANKNIFTY majors", "Custom input", "CSV upload"],
    )
    custom_tickers = st.sidebar.text_area("Custom tickers", value="RELIANCE, TCS, HDFCBANK", disabled=watchlist_source != "Custom input")
    upload = st.sidebar.file_uploader("Upload CSV watchlist", type=["csv"], disabled=watchlist_source != "CSV upload")
    uploaded_frame = parse_uploaded_csv(upload)

    timeframe = st.sidebar.selectbox("Timeframe", options=["5m", "15m", "1h", "4h", "1d"], index=4)
    history_period = st.sidebar.selectbox("Lookback period", options=["6mo", "1y", "2y", "5y", "10y"], index=3)
    lookback_bars = st.sidebar.number_input("Lookback bars", min_value=100, max_value=5000, value=500, step=50)
    pivot_left = st.sidebar.number_input("Pivot left bars", min_value=1, max_value=10, value=3)
    pivot_right = st.sidebar.number_input("Pivot right bars", min_value=1, max_value=10, value=3)
    breakout_lookback = st.sidebar.number_input("Breakout lookback", min_value=5, max_value=200, value=20)
    close_confirmation = st.sidebar.checkbox("Close-based breakout confirmation", value=True)
    breakout_buffer_pct = st.sidebar.slider("Minimum breakout buffer %", min_value=0.0, max_value=5.0, value=0.3, step=0.1)
    min_fvg_size_pct = st.sidebar.slider("Minimum FVG size %", min_value=0.0, max_value=5.0, value=0.2, step=0.1)
    use_atr_filter = st.sidebar.checkbox("ATR-based minimum gap filter", value=True)
    use_volume_filter = st.sidebar.checkbox("Volume filter", value=False)
    near_zone_threshold_pct = st.sidebar.slider("Near-zone threshold %", min_value=0.2, max_value=5.0, value=1.0, step=0.1)
    direction_filter = st.sidebar.radio("Direction", options=["all", "bullish", "bearish"], horizontal=True)
    fresh_fvg_only = st.sidebar.checkbox("Fresh FVG only", value=True)

    config = SMCAnalyzerConfig(
        timeframe=timeframe,
        history_period=history_period,
        lookback_bars=int(lookback_bars),
        pivot_left_bars=int(pivot_left),
        pivot_right_bars=int(pivot_right),
        breakout_lookback=int(breakout_lookback),
        close_breakout_confirmation=close_confirmation,
        breakout_buffer_pct=float(breakout_buffer_pct),
        min_fvg_size_pct=float(min_fvg_size_pct),
        use_atr_gap_filter=use_atr_filter,
        use_volume_filter=use_volume_filter,
        near_zone_threshold_pct=float(near_zone_threshold_pct),
        direction_filter=direction_filter,
        fresh_fvg_only=fresh_fvg_only,
    )

    symbols = _resolve_watchlist(watchlist_source, custom_tickers, uploaded_frame)
    st.caption(f"Selected {len(symbols)} symbols for {timeframe} analysis.")
    if not symbols:
        st.info("Choose a watchlist source and add symbols to run the screener. The single-symbol section below still works.")

    run_scan = st.button("Run BOS + FVG screener", type="primary", width="stretch", disabled=not symbols)

    if run_scan:
        with st.spinner("Downloading Yahoo Finance history and scanning setups..."):
            try:
                history_result = load_watchlist_history(symbols, config.timeframe, config.history_period)
            except Exception as exc:
                st.error(f"Analyzer failed while downloading market data: {exc}")
                return

            results_df, analyses = screen_watchlist(history_result.data, config)
            st.session_state["smc_results"] = results_df
            st.session_state["smc_analyses"] = analyses
            st.session_state["smc_failures"] = history_result.failures
            st.session_state["smc_notices"] = history_result.notices

    results_df = st.session_state.get("smc_results", pd.DataFrame())
    analyses = st.session_state.get("smc_analyses", {})
    failures = st.session_state.get("smc_failures", {})
    notices = st.session_state.get("smc_notices", [])

    if notices:
        for notice in notices:
            st.caption(notice)
    if failures:
        st.warning("Some symbols failed to download.")
        st.dataframe(pd.DataFrame({"symbol": list(failures), "error": list(failures.values())}), width="stretch")

    _render_summary_cards(results_df, analyses)
    if not results_df.empty or analyses:
        _render_screener_section(results_df)
    _render_single_symbol_section(config, analyses)

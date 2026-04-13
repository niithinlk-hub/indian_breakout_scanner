from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd
import streamlit as st

from app.stock_alerter.alerts import format_telegram_message, send_telegram_alert
from app.stock_alerter.charts import build_stock_chart
from app.stock_alerter.config import load_stock_alerter_config
from app.stock_alerter.data_loader import fetch_benchmark_data, fetch_universe_data, load_universe_frame
from app.stock_alerter.scanner import scan_universe
from app.stock_alerter.storage import alert_already_sent, load_alert_history, save_alert_history
from app.stock_alerter.utils import strip_exchange_suffix


def _apply_ui_filters(results: pd.DataFrame) -> pd.DataFrame:
    if results.empty:
        return results
    pattern_options = sorted(results["pattern_name"].dropna().unique().tolist())
    category_options = sorted(results["category"].dropna().unique().tolist())
    confirmation_options = ["With BOS", "With FVG", "With Retest", "Strong candle"]

    col1, col2, col3 = st.columns(3)
    selected_patterns = col1.multiselect("Filter pattern type", pattern_options, default=pattern_options)
    selected_categories = col2.multiselect("Filter score category", category_options, default=category_options)
    selected_confirmations = col3.multiselect("Filter confirmation status", confirmation_options, default=[])

    filtered = results.copy()
    if selected_patterns:
        filtered = filtered.loc[filtered["pattern_name"].isin(selected_patterns)]
    if selected_categories:
        filtered = filtered.loc[filtered["category"].isin(selected_categories)]
    if "With BOS" in selected_confirmations:
        filtered = filtered.loc[filtered["bos_status"] == "present"]
    if "With FVG" in selected_confirmations:
        filtered = filtered.loc[filtered["fvg_status"] != "missing"]
    if "With Retest" in selected_confirmations:
        filtered = filtered.loc[filtered["retest_status"] == "confirmed"]
    if "Strong candle" in selected_confirmations:
        filtered = filtered.loc[filtered["strong_candle_ok"]]
    return filtered.reset_index(drop=True)


def _send_new_alerts(results: pd.DataFrame, config: StockAlerterConfig) -> tuple[int, list[str]]:
    history = load_alert_history(config.alert_history_path or config.project_root / "data" / "stock_alerter_alerts.json")
    sent_messages: list[str] = []
    sent_count = 0
    session_key = datetime.now(timezone.utc).date().isoformat()
    for _, row in results.iterrows():
        if int(row["score"]) < int(config.score_alert_threshold):
            continue
        breakout_level = row.get("breakout_level")
        if breakout_level is None:
            continue
        if alert_already_sent(history, str(row["symbol"]), str(row["pattern_name"]), float(breakout_level), session_key):
            continue
        message = format_telegram_message(row.to_dict(), config.universe_name)
        sent, info = send_telegram_alert(message, config)
        if sent:
            sent_count += 1
            history.append(
                {
                    "symbol": str(row["symbol"]),
                    "pattern": str(row["pattern_name"]),
                    "breakout_level": float(breakout_level),
                    "alert_timestamp": datetime.now(timezone.utc).isoformat(),
                    "score": int(row["score"]),
                    "session_key": session_key,
                },
            )
        sent_messages.append(f"{row['symbol']}: {info}")
    save_alert_history(config.alert_history_path or config.project_root / "data" / "stock_alerter_alerts.json", history)
    return sent_count, sent_messages


def render_stock_alerter_page(project_root) -> None:
    """Render the bullish breakout stock alerter dashboard."""

    st.sidebar.divider()
    st.sidebar.subheader("Stock Alerter")
    universe_choice = st.sidebar.selectbox(
        "Universe selector",
        options=["NIFTY LargeMidcap 250", "NASDAQ Top 250", "Custom"],
        index=0,
        key="stock_alerter_universe",
    )
    custom_text = st.sidebar.text_area("Custom symbols", value="RELIANCE.NS, TCS.NS, AAPL, NVDA", disabled=universe_choice != "Custom")
    config = load_stock_alerter_config(project_root)
    config.universe_name = universe_choice
    config.custom_universe_text = custom_text
    config.timeframe = st.sidebar.selectbox("Timeframe selector", options=["1d", "1wk"], index=0)
    config.period = st.sidebar.selectbox("Lookback period", options=["1y", "2y", "5y"], index=1)
    config.breakout_lookback = st.sidebar.slider("Breakout lookback", 20, 120, 40, 5)
    config.breakout_buffer_pct = float(st.sidebar.slider("Breakout buffer %", 0.2, 2.0, 0.5, 0.05))
    config.minimum_volume_multiple = float(st.sidebar.slider("Minimum volume multiple", 1.0, 3.0, 1.5, 0.1))
    config.rsi_lower = float(st.sidebar.slider("RSI lower bound", 40, 70, 55))
    config.rsi_upper = float(st.sidebar.slider("RSI upper bound", 60, 85, 72))
    config.adx_threshold = float(st.sidebar.slider("ADX threshold", 10, 40, 20))
    config.score_alert_threshold = int(st.sidebar.slider("Score threshold", 4, 12, 8))
    config.retest_required = st.sidebar.checkbox("Retest required toggle", value=False)
    config.bos_required = st.sidebar.checkbox("BOS required toggle", value=False)
    config.fvg_required = st.sidebar.checkbox("FVG required toggle", value=False)
    config.require_52week_high_module = st.sidebar.checkbox("52-week high module on/off", value=True)
    config.relative_strength_filter = st.sidebar.checkbox("Relative strength filter on/off", value=True)
    trigger_alerts = st.sidebar.checkbox("Send Telegram alerts for new A/A+ breakouts", value=False)

    universe_frame = load_universe_frame(config)
    symbols = [f"{symbol}.NS" if not str(symbol).endswith(".NS") else str(symbol) for symbol in universe_frame.get("Symbol", pd.Series(dtype=str)).tolist()]
    company_names = {str(row["Symbol"]).upper(): str(row.get("Company Name", row["Symbol"])) for _, row in universe_frame.iterrows()}

    st.subheader("Bullish Breakout Stock Alerter")
    st.caption(f"Universe: {config.universe_name}. Symbols loaded: {len(symbols)}")

    if st.button("Run stock alerter scan", type="primary", width="stretch"):
        with st.spinner("Fetching market data and scanning bullish breakout candidates..."):
            history_map, failures = fetch_universe_data(symbols, config)
            benchmark_df = fetch_benchmark_data(config)
            results = scan_universe(history_map, config, benchmark_df=benchmark_df, company_names=company_names)
            st.session_state["stock_alerter_results"] = results
            st.session_state["stock_alerter_history_map"] = history_map
            st.session_state["stock_alerter_failures"] = failures
            st.session_state["stock_alerter_benchmark"] = benchmark_df
            if trigger_alerts and not results.empty:
                sent_count, messages = _send_new_alerts(results, config)
                st.session_state["stock_alerter_alert_messages"] = messages
                st.session_state["stock_alerter_alert_count"] = sent_count

    results = st.session_state.get("stock_alerter_results", pd.DataFrame())
    history_map = st.session_state.get("stock_alerter_history_map", {})
    failures = st.session_state.get("stock_alerter_failures", {})
    benchmark_df = st.session_state.get("stock_alerter_benchmark", pd.DataFrame())

    if results.empty:
        st.info("Run the stock alerter scan to see high-quality breakout candidates and Telegram-ready alerts.")
        return

    filtered = _apply_ui_filters(results)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Signals", len(filtered))
    col2.metric("A+ Breakouts", int((filtered["category"] == "A+ Breakout").sum()))
    col3.metric("A Breakouts", int((filtered["category"] == "A Breakout").sum()))
    col4.metric("Strongest setup", str(filtered.iloc[0]["symbol"]) if not filtered.empty else "None")

    display_columns = [
        "symbol",
        "company_name",
        "pattern_name",
        "breakout_level",
        "current_price",
        "distance_from_breakout_pct",
        "volume_ratio",
        "rsi",
        "adx",
        "atr",
        "ema20",
        "ema50",
        "ema_alignment_status",
        "relative_strength_status",
        "bos_status",
        "fvg_status",
        "retest_status",
        "score",
        "category",
    ]
    st.dataframe(filtered[display_columns], width="stretch")

    selected_symbol = st.selectbox("Selected stock", filtered["symbol"].tolist())
    selected_row = filtered.loc[filtered["symbol"] == selected_symbol].iloc[0]
    st.write(selected_row["reasoning"])

    detail = st.expander("Signal detail", expanded=True)
    with detail:
        st.json(
            {
                "pattern": selected_row["pattern_name"],
                "score": int(selected_row["score"]),
                "category": selected_row["category"],
                "confirmations_satisfied": selected_row["satisfied_confirmations"],
                "confirmations_missing": selected_row["missing_confirmations"],
                "supporting_metrics": selected_row["supporting_metrics"],
                "raw_pattern_features": selected_row["raw_pattern_features"],
            },
            expanded=False,
        )

    symbol_history = history_map.get(selected_symbol)
    if symbol_history is not None and not symbol_history.empty:
        chart = build_stock_chart(symbol_history, selected_row.to_dict(), config, benchmark_df=benchmark_df)
        st.plotly_chart(chart, width="stretch")

    if failures:
        with st.expander("Download failures"):
            st.dataframe(pd.DataFrame({"symbol": list(failures), "error": list(failures.values())}), width="stretch")

    if trigger_alerts and "stock_alerter_alert_messages" in st.session_state:
        with st.expander("Telegram alert log"):
            st.write(f"Alerts sent: {st.session_state.get('stock_alerter_alert_count', 0)}")
            for message in st.session_state.get("stock_alerter_alert_messages", []):
                st.caption(message)

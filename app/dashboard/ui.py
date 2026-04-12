from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from app.config import get_settings
from app.data_ingestion import MarketDataService
from app.fundamentals.csv_provider import CsvFundamentalsProvider
from app.fundamentals.service import FundamentalsService
from app.pipeline import DailyScanner
from app.providers.factory import build_market_data_provider
from app.storage.sqlite_store import SQLiteStore
from app.universe import build_stock_universe, load_watchlist
from app.utils.logging import configure_logging


def _apply_common_filters(results_df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    composite_floor = st.sidebar.slider("Minimum composite score", 0, 100, 60)
    technical_floor = st.sidebar.slider("Minimum technical score", 0, 100, 40)
    fundamental_floor = st.sidebar.slider("Minimum fundamental score", 0, 100, 30)
    sectors = sorted(value for value in results_df.get("sector", pd.Series(dtype=str)).dropna().unique())
    market_caps = sorted(value for value in results_df.get("market_cap_bucket", pd.Series(dtype=str)).dropna().unique())
    selected_sectors = st.sidebar.multiselect("Sector", sectors, default=sectors)
    selected_market_caps = st.sidebar.multiselect("Market cap bucket", market_caps, default=market_caps)
    sort_by = st.sidebar.selectbox(
        "Sort by",
        options=["total_score", "technical_score", "fundamental_score", "volume_multiple", "distance_above_breakout_pct"],
        index=0,
    )

    filtered = results_df.copy()
    filtered = filtered.loc[filtered["total_score"] >= composite_floor]
    filtered = filtered.loc[filtered["technical_score"] >= technical_floor]
    filtered = filtered.loc[filtered["fundamental_score"] >= fundamental_floor]
    if selected_sectors:
        filtered = filtered.loc[filtered["sector"].isin(selected_sectors)]
    if selected_market_caps:
        filtered = filtered.loc[filtered["market_cap_bucket"].isin(selected_market_caps)]
    filtered = filtered.sort_values(sort_by, ascending=False).reset_index(drop=True)
    return filtered, sort_by


def _show_results_table(store: SQLiteStore, title: str, results_df: pd.DataFrame) -> None:
    st.subheader(title)
    if results_df.empty:
        st.info("No records match the current filters.")
        return

    display_columns = [
        "symbol",
        "total_score",
        "technical_score",
        "fundamental_score",
        "rating",
        "signal_state",
        "close",
        "breakout_level",
        "distance_above_breakout_pct",
        "volume_multiple",
        "sector",
        "market_cap_bucket",
    ]
    st.dataframe(results_df[display_columns], use_container_width=True)
    st.download_button(
        label="Export filtered CSV",
        data=results_df.to_csv(index=False),
        file_name="breakout_scanner_results.csv",
        mime="text/csv",
    )

    selected_symbol = st.selectbox("Select symbol", results_df["symbol"].tolist(), key=title)
    selected_row = results_df.loc[results_df["symbol"] == selected_symbol].iloc[0]
    history_df = store.load_price_history(selected_symbol, limit=90)

    col1, col2 = st.columns([2, 3])
    with col1:
        st.metric("Composite score", f"{selected_row['total_score']:.1f}")
        st.metric("Technical score", f"{selected_row['technical_score']:.1f}")
        st.metric("Fundamental score", f"{selected_row['fundamental_score']:.1f}")
        st.metric("Volume multiple", f"{selected_row['volume_multiple']:.2f}x")
        st.metric("Breakout distance", f"{selected_row['distance_above_breakout_pct']:.2f}%")
        st.write(selected_row["trader_summary"])
        tags_payload = json.loads(selected_row["tags_json"]) if selected_row.get("tags_json") else {"tags": []}
        st.caption(", ".join(tags_payload.get("tags", [])))

    with col2:
        if not history_df.empty:
            chart_df = history_df.set_index(pd.to_datetime(history_df["datetime"]))[["close"]]
            st.line_chart(chart_df)
        else:
            st.info("No price history stored yet for mini chart rendering.")

    st.write(selected_row["explanation"])


def _show_signal_history(store: SQLiteStore) -> None:
    st.subheader("Signal history")
    history_df = store.load_scan_history()
    if history_df.empty:
        st.info("No historical scan results available yet.")
        return

    symbol = st.selectbox("Symbol", sorted(history_df["symbol"].unique().tolist()), key="history_symbol")
    symbol_history = history_df.loc[history_df["symbol"] == symbol].copy()
    symbol_history["scan_timestamp"] = pd.to_datetime(symbol_history["scan_timestamp"])
    st.dataframe(
        symbol_history[
            [
                "scan_timestamp",
                "total_score",
                "technical_score",
                "fundamental_score",
                "rating",
                "signal_state",
                "close",
                "volume_multiple",
            ]
        ],
        use_container_width=True,
    )
    score_chart = symbol_history.set_index("scan_timestamp")[["total_score", "technical_score", "fundamental_score"]]
    st.line_chart(score_chart)


def _show_backtest_summary(store: SQLiteStore) -> None:
    st.subheader("Backtest summary")
    summaries = store.load_backtest_summaries()
    if summaries.empty:
        st.info("No backtest summaries are stored yet.")
        return

    st.dataframe(summaries, use_container_width=True)
def _show_scan_controls(settings, store: SQLiteStore) -> pd.DataFrame:
    st.sidebar.divider()
    st.sidebar.subheader("Scanner")
    universe_mode = st.sidebar.selectbox(
        "Universe mode",
        options=["watchlist", "nse_equities"],
        format_func=lambda value: "Manual watchlist" if value == "watchlist" else "All NSE equities",
    )
    watchlist_path = st.sidebar.text_input(
        "Watchlist file",
        value="config/watchlist.example.txt",
        help="Path relative to the project root.",
        disabled=universe_mode != "watchlist",
    )
    symbol_limit = st.sidebar.number_input(
        "Symbol limit",
        min_value=0,
        max_value=5000,
        value=250 if universe_mode == "nse_equities" else 0,
        step=50,
        help="Use 0 to scan the full selected universe.",
    )

    credentials_ready = (
        (settings.provider_name == "zerodha" and bool(settings.zerodha_api_key) and bool(settings.zerodha_access_token))
        or (settings.provider_name == "upstox" and bool(settings.upstox_access_token))
    )
    if not credentials_ready:
        st.sidebar.warning(
            "Broker credentials are missing. Add them as environment variables or Streamlit secrets before scanning.",
        )

    if st.sidebar.button("Run scan now", type="primary", use_container_width=True):
        if not credentials_ready:
            st.sidebar.error("Broker credentials are required before running a live scan.")
        else:
            configure_logging(settings.log_level)
            provider = build_market_data_provider(settings)
            data_service = MarketDataService(provider=provider, settings=settings)
            fundamentals_service = FundamentalsService(CsvFundamentalsProvider(settings.fundamentals_csv_path))
            scanner = DailyScanner(
                data_service=data_service,
                store=store,
                settings=settings,
                fundamentals_service=fundamentals_service,
            )
            with st.spinner("Resolving symbol universe..."):
                universe = build_stock_universe(
                    data_service=data_service,
                    mode=universe_mode,
                    default_exchange=settings.default_exchange,
                    watchlist_path=settings.project_root / watchlist_path,
                    symbol_limit=symbol_limit or None,
                )
            if not universe.symbols:
                st.sidebar.error("No symbols resolved for the selected universe.")
                return store.load_latest_scan_results()

            with st.spinner("Running end-of-day scan..."):
                results = scanner.scan_end_of_day(
                    universe.symbols,
                    symbol_metadata=universe.metadata,
                )
            if results.empty:
                st.warning("Scan completed, but no successful rows were stored.")
            else:
                st.success(f"Scan complete. Stored {len(results)} rows.")
                st.rerun()
    else:
        if universe_mode == "watchlist":
            watchlist = load_watchlist(settings.project_root / watchlist_path)
            st.sidebar.caption(f"Loaded {len(watchlist)} symbols from watchlist.")
        else:
            limit_label = "all symbols" if symbol_limit == 0 else f"up to {symbol_limit} symbols"
            st.sidebar.caption(f"Will scan {limit_label} from NSE cash equities.")

    return store.load_latest_scan_results()


def render_dashboard() -> None:
    settings = get_settings()
    store = SQLiteStore(settings.database_path)

    st.set_page_config(page_title="Indian Breakout Scanner", layout="wide")
    st.title("Indian Breakout Scanner")
    st.sidebar.title("Views")
    latest_results = _show_scan_controls(settings, store)
    page = st.sidebar.radio(
        "Page",
        [
            "All scanned stocks",
            "Top breakouts today",
            "Near-breakouts",
            "Failed breakouts",
            "Signal history",
            "Backtest summary",
        ],
    )

    if page == "Signal history":
        _show_signal_history(store)
        return
    if page == "Backtest summary":
        _show_backtest_summary(store)
        return
    if latest_results.empty:
        st.info("No scan results are stored yet. Add broker secrets and use the sidebar button to run a scan.")
        st.code(
            "\n".join(
                [
                    "MARKET_DATA_PROVIDER=zerodha",
                    "ZERODHA_API_KEY=...",
                    "ZERODHA_ACCESS_TOKEN=...",
                    "DEFAULT_EXCHANGE=NSE",
                ],
            ),
            language="bash",
        )
        return

    filtered, sort_by = _apply_common_filters(latest_results)
    st.caption(f"Sorted by {sort_by}.")

    if page == "All scanned stocks":
        _show_results_table(store, page, filtered)
    elif page == "Top breakouts today":
        _show_results_table(store, page, filtered.loc[filtered["signal_state"] == "breakout"])
    elif page == "Near-breakouts":
        _show_results_table(store, page, filtered.loc[filtered["signal_state"] == "near_breakout"])
    elif page == "Failed breakouts":
        _show_results_table(store, page, filtered.loc[filtered["signal_state"] == "failed_breakout"])


if __name__ == "__main__":
    render_dashboard()

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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

_FUNDAMENTAL_DISPLAY_COLUMNS = [
    "market_cap_inr_cr",
    "pe_ratio",
    "pb_ratio",
    "ev_ebitda",
    "dividend_yield_pct",
    "revenue_growth_pct",
    "eps_growth_pct",
    "roe_pct",
    "roce_pct",
    "debt_to_equity",
    "net_margin_pct",
    "operating_margin_pct",
    "current_ratio",
    "interest_coverage",
    "promoter_holding_pct",
]


def _as_numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series([float("nan")] * len(frame), index=frame.index, dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce")


def _safe_json_loads(payload: object) -> dict[str, Any]:
    if payload is None or payload == "" or pd.isna(payload):
        return {}
    try:
        parsed = json.loads(str(payload))
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _build_fundamental_view(results_df: pd.DataFrame) -> pd.DataFrame:
    if results_df.empty:
        return results_df.copy()

    rows: list[dict[str, Any]] = []
    for _, row in results_df.iterrows():
        snapshot = _safe_json_loads(row.get("fundamentals_json"))
        rows.append(
            {
                "symbol": row.get("symbol"),
                "fundamental_score": row.get("fundamental_score"),
                "fundamental_rating": row.get("fundamental_rating"),
                "technical_score": row.get("technical_score"),
                "signal_state": row.get("signal_state"),
                "sector": snapshot.get("sector", row.get("sector", "Unknown")),
                "market_cap_bucket": snapshot.get("market_cap_bucket", row.get("market_cap_bucket", "Unknown")),
                **snapshot,
            },
        )

    frame = pd.DataFrame(rows)
    for column in ["fundamental_score", "technical_score", *_FUNDAMENTAL_DISPLAY_COLUMNS]:
        frame[column] = _as_numeric(frame, column)
    return frame.sort_values(
        by=["fundamental_score", "market_cap_inr_cr", "roe_pct", "eps_growth_pct"],
        ascending=[False, False, False, False],
        kind="mergesort",
    ).reset_index(drop=True)


def _apply_technical_filters(results_df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    technical_floor = st.sidebar.slider("Minimum technical score", 0, 100, 40)
    market_caps = sorted(
        value for value in results_df.get("market_cap_bucket", pd.Series(dtype=str)).dropna().unique() if str(value).strip()
    )
    selected_market_caps = st.sidebar.multiselect("Market cap bucket", market_caps, default=market_caps)
    sort_by = st.sidebar.selectbox(
        "Sort technical by",
        options=["technical_score", "volume_multiple", "distance_above_breakout_pct", "close"],
        index=0,
    )

    filtered = results_df.copy()
    filtered = filtered.loc[_as_numeric(filtered, "technical_score") >= technical_floor]
    if selected_market_caps:
        filtered = filtered.loc[filtered["market_cap_bucket"].isin(selected_market_caps)]
    filtered = filtered.sort_values(sort_by, ascending=False, kind="mergesort").reset_index(drop=True)
    return filtered, sort_by


def _apply_fundamental_filters(fundamentals_df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    fundamental_floor = st.sidebar.slider("Minimum fundamental score", 0, 100, 30)
    sectors = sorted(
        value for value in fundamentals_df.get("sector", pd.Series(dtype=str)).dropna().unique() if str(value).strip()
    )
    market_caps = sorted(
        value
        for value in fundamentals_df.get("market_cap_bucket", pd.Series(dtype=str)).dropna().unique()
        if str(value).strip()
    )
    selected_sectors = st.sidebar.multiselect("Fundamental sector", sectors, default=sectors)
    selected_market_caps = st.sidebar.multiselect("Fundamental market cap bucket", market_caps, default=market_caps)
    sort_by = st.sidebar.selectbox(
        "Sort fundamentals by",
        options=["fundamental_score", "market_cap_inr_cr", "roe_pct", "eps_growth_pct", "pe_ratio", "pb_ratio"],
        index=0,
    )

    filtered = fundamentals_df.copy()
    filtered = filtered.loc[_as_numeric(filtered, "fundamental_score") >= fundamental_floor]
    if selected_sectors:
        filtered = filtered.loc[filtered["sector"].isin(selected_sectors)]
    if selected_market_caps:
        filtered = filtered.loc[filtered["market_cap_bucket"].isin(selected_market_caps)]
    filtered = filtered.sort_values(sort_by, ascending=False, kind="mergesort").reset_index(drop=True)
    return filtered, sort_by


def _show_technical_results_table(store: SQLiteStore, title: str, results_df: pd.DataFrame) -> None:
    st.subheader(title)
    if results_df.empty:
        st.info("No records match the current technical filters.")
        return

    display_columns = [
        "symbol",
        "technical_score",
        "technical_rating",
        "signal_state",
        "close",
        "breakout_level",
        "distance_above_breakout_pct",
        "volume_multiple",
        "market_cap_bucket",
    ]
    st.dataframe(results_df[display_columns], use_container_width=True)
    st.download_button(
        label="Export filtered CSV",
        data=results_df.to_csv(index=False),
        file_name="technical_breakout_results.csv",
        mime="text/csv",
    )

    selected_symbol = st.selectbox("Select symbol", results_df["symbol"].tolist(), key=title)
    selected_row = results_df.loc[results_df["symbol"] == selected_symbol].iloc[0]
    history_df = store.load_price_history(selected_symbol, limit=90)

    col1, col2 = st.columns([2, 3])
    with col1:
        st.metric("Technical score", f"{float(selected_row['technical_score']):.1f}")
        st.metric("Technical rating", str(selected_row.get("technical_rating", "Unknown")))
        st.metric("Volume multiple", f"{float(selected_row['volume_multiple']):.2f}x")
        st.metric("Breakout distance", f"{float(selected_row['distance_above_breakout_pct']):.2f}%")
        st.write(selected_row["trader_summary"])
        tags_payload = _safe_json_loads(selected_row.get("tags_json")) or {"tags": []}
        st.caption(", ".join(tags_payload.get("tags", [])))

    with col2:
        if not history_df.empty:
            chart_df = history_df.set_index(pd.to_datetime(history_df["datetime"]))[["close"]]
            st.line_chart(chart_df)
        else:
            st.info("No price history stored yet for mini chart rendering.")

    st.write(selected_row["explanation"])


def _show_fundamental_page(fundamentals_df: pd.DataFrame) -> None:
    st.subheader("Fundamental scores")
    if fundamentals_df.empty:
        st.info("No fundamental rows are available yet. Run a fresh scan after the latest deploy.")
        return

    display_columns = [
        "symbol",
        "fundamental_score",
        "fundamental_rating",
        "sector",
        "market_cap_bucket",
        "market_cap_inr_cr",
        "pe_ratio",
        "pb_ratio",
        "roe_pct",
        "roce_pct",
        "eps_growth_pct",
        "debt_to_equity",
        "promoter_holding_pct",
    ]
    available_columns = [column for column in display_columns if column in fundamentals_df.columns]
    st.dataframe(fundamentals_df[available_columns], use_container_width=True)
    st.download_button(
        label="Export fundamentals CSV",
        data=fundamentals_df.to_csv(index=False),
        file_name="fundamental_scores.csv",
        mime="text/csv",
    )

    selected_symbol = st.selectbox("Select symbol", fundamentals_df["symbol"].tolist(), key="fundamental_symbol")
    selected_row = fundamentals_df.loc[fundamentals_df["symbol"] == selected_symbol].iloc[0]

    metric_cols = st.columns(4)
    metric_cols[0].metric("Fundamental score", f"{float(selected_row['fundamental_score']):.1f}")
    metric_cols[1].metric("P/E", f"{float(selected_row['pe_ratio']):.2f}" if pd.notna(selected_row.get("pe_ratio")) else "NA")
    metric_cols[2].metric("P/BV", f"{float(selected_row['pb_ratio']):.2f}" if pd.notna(selected_row.get("pb_ratio")) else "NA")
    metric_cols[3].metric(
        "Market cap (Cr)",
        f"{float(selected_row['market_cap_inr_cr']):,.0f}" if pd.notna(selected_row.get("market_cap_inr_cr")) else "NA",
    )

    detail_columns = [
        "sector",
        "market_cap_bucket",
        "market_cap_inr_cr",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
        "dividend_yield_pct",
        "revenue_growth_pct",
        "eps_growth_pct",
        "roe_pct",
        "roce_pct",
        "debt_to_equity",
        "net_margin_pct",
        "operating_margin_pct",
        "current_ratio",
        "interest_coverage",
        "promoter_holding_pct",
        "technical_score",
        "signal_state",
    ]
    details_frame = pd.DataFrame(
        [
            {
                "metric": column.replace("_", " ").replace("pct", "%").title(),
                "value": selected_row.get(column),
            }
            for column in detail_columns
            if column in selected_row.index
        ],
    )
    st.dataframe(details_frame, use_container_width=True, hide_index=True)


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
                "technical_score",
                "technical_rating",
                "fundamental_score",
                "fundamental_rating",
                "signal_state",
                "close",
                "volume_multiple",
            ]
        ],
        use_container_width=True,
    )
    score_chart = symbol_history.set_index("scan_timestamp")[["technical_score", "fundamental_score"]]
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
            "Fundamental scores",
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

    if page == "Fundamental scores":
        fundamentals_df = _build_fundamental_view(latest_results)
        filtered_fundamentals, sort_by = _apply_fundamental_filters(fundamentals_df)
        st.caption(f"Fundamental table sorted by {sort_by}.")
        _show_fundamental_page(filtered_fundamentals)
        return

    filtered, sort_by = _apply_technical_filters(latest_results)
    st.caption(f"Technical table sorted by {sort_by}.")

    if page == "All scanned stocks":
        _show_technical_results_table(store, page, filtered)
    elif page == "Top breakouts today":
        _show_technical_results_table(store, page, filtered.loc[filtered["signal_state"] == "breakout"])
    elif page == "Near-breakouts":
        _show_technical_results_table(store, page, filtered.loc[filtered["signal_state"] == "near_breakout"])
    elif page == "Failed breakouts":
        _show_technical_results_table(store, page, filtered.loc[filtered["signal_state"] == "failed_breakout"])


if __name__ == "__main__":
    render_dashboard()

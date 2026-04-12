from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd


class SQLiteStore:
    """SQLite persistence for scans, price history, and backtests."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS scan_results (
                    scan_timestamp TEXT NOT NULL,
                    rank INTEGER,
                    as_of TEXT,
                    symbol TEXT NOT NULL,
                    close REAL,
                    signal_state TEXT,
                    breakout_level REAL,
                    distance_above_breakout_pct REAL,
                    volume_multiple REAL,
                    dma_50_status TEXT,
                    dma_200_status TEXT,
                    atr_status TEXT,
                    relative_strength_status TEXT,
                    liquidity_turnover_20 REAL,
                    liquidity_status TEXT,
                    technical_score REAL,
                    technical_rating TEXT,
                    fundamental_score REAL,
                    fundamental_rating TEXT,
                    total_score REAL,
                    rating TEXT,
                    explanation TEXT,
                    trader_summary TEXT,
                    tags_json TEXT,
                    sector TEXT,
                    market_cap_bucket TEXT,
                    failed_breakout INTEGER,
                    component_scores_json TEXT,
                    technical_component_scores_json TEXT,
                    fundamental_component_scores_json TEXT,
                    fundamentals_json TEXT,
                    signal_payload_json TEXT
                );

                CREATE TABLE IF NOT EXISTS price_history (
                    symbol TEXT NOT NULL,
                    datetime TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL
                );

                CREATE TABLE IF NOT EXISTS backtest_summaries (
                    run_timestamp TEXT NOT NULL,
                    strategy_name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    total_trades INTEGER,
                    win_rate REAL,
                    average_return REAL,
                    median_return REAL,
                    max_drawdown REAL,
                    expectancy REAL,
                    entry_config_json TEXT,
                    exit_config_json TEXT
                );

                CREATE TABLE IF NOT EXISTS trade_logs (
                    run_timestamp TEXT NOT NULL,
                    strategy_name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    entry_date TEXT,
                    exit_date TEXT,
                    entry_price REAL,
                    exit_price REAL,
                    return_pct REAL,
                    holding_days INTEGER,
                    exit_reason TEXT,
                    breakout_level REAL
                );
                """,
            )
            self._ensure_column(connection, "scan_results", "rank", "INTEGER")
            self._ensure_column(connection, "scan_results", "technical_score", "REAL")
            self._ensure_column(connection, "scan_results", "technical_rating", "TEXT")
            self._ensure_column(connection, "scan_results", "fundamental_score", "REAL")
            self._ensure_column(connection, "scan_results", "fundamental_rating", "TEXT")
            self._ensure_column(connection, "scan_results", "technical_component_scores_json", "TEXT")
            self._ensure_column(connection, "scan_results", "fundamental_component_scores_json", "TEXT")
            self._ensure_column(connection, "scan_results", "fundamentals_json", "TEXT")

    def save_scan_results(self, results_df: pd.DataFrame) -> None:
        if results_df.empty:
            return
        safe_results = results_df.copy()
        safe_results["as_of"] = pd.to_datetime(safe_results["as_of"]).astype(str)
        table_columns = self._get_table_columns("scan_results")
        safe_results = safe_results[[column for column in safe_results.columns if column in table_columns]]
        with self._connect() as connection:
            safe_results.to_sql("scan_results", connection, if_exists="append", index=False)

    def save_price_history(self, history_df: pd.DataFrame) -> None:
        if history_df.empty:
            return
        safe_history = history_df[["symbol", "datetime", "open", "high", "low", "close", "volume"]].copy()
        safe_history["datetime"] = pd.to_datetime(safe_history["datetime"]).astype(str)
        with self._connect() as connection:
            safe_history.to_sql("price_history", connection, if_exists="append", index=False)

    def save_backtest_run(
        self,
        *,
        run_timestamp: str,
        strategy_name: str,
        summary: dict[str, object],
        trades_df: pd.DataFrame,
    ) -> None:
        summary_frame = pd.DataFrame(
            [
                {
                    "run_timestamp": run_timestamp,
                    "strategy_name": strategy_name,
                    "symbol": summary.get("symbol"),
                    "total_trades": summary.get("total_trades"),
                    "win_rate": summary.get("win_rate"),
                    "average_return": summary.get("average_return"),
                    "median_return": summary.get("median_return"),
                    "max_drawdown": summary.get("max_drawdown"),
                    "expectancy": summary.get("expectancy"),
                    "entry_config_json": json.dumps(summary.get("entry_config", {})),
                    "exit_config_json": json.dumps(summary.get("exit_config", {})),
                },
            ],
        )
        trades_to_save = trades_df.copy()
        if not trades_to_save.empty:
            trades_to_save.insert(0, "strategy_name", strategy_name)
            trades_to_save.insert(0, "run_timestamp", run_timestamp)
            trades_to_save["entry_date"] = pd.to_datetime(trades_to_save["entry_date"]).astype(str)
            trades_to_save["exit_date"] = pd.to_datetime(trades_to_save["exit_date"]).astype(str)

        with self._connect() as connection:
            summary_frame.to_sql("backtest_summaries", connection, if_exists="append", index=False)
            if not trades_to_save.empty:
                trades_to_save.to_sql("trade_logs", connection, if_exists="append", index=False)

    def load_latest_scan_results(self) -> pd.DataFrame:
        query = """
            SELECT *
            FROM scan_results
            WHERE scan_timestamp = (SELECT MAX(scan_timestamp) FROM scan_results)
        """
        return self._read_query(query)

    def load_scan_history(self, symbol: str | None = None) -> pd.DataFrame:
        query = "SELECT * FROM scan_results"
        params: tuple[object, ...] = ()
        if symbol:
            query += " WHERE symbol = ?"
            params = (symbol,)
        query += " ORDER BY scan_timestamp ASC"
        return self._read_query(query, params)

    def load_price_history(self, symbol: str, limit: int = 60) -> pd.DataFrame:
        query = """
            SELECT symbol, datetime, open, high, low, close, volume
            FROM price_history
            WHERE symbol = ?
            ORDER BY datetime DESC
            LIMIT ?
        """
        frame = self._read_query(query, (symbol, limit))
        if frame.empty:
            return frame
        return frame.sort_values("datetime").reset_index(drop=True)

    def load_backtest_summaries(self) -> pd.DataFrame:
        return self._read_query("SELECT * FROM backtest_summaries ORDER BY run_timestamp DESC")

    def _read_query(self, query: str, params: tuple[object, ...] = ()) -> pd.DataFrame:
        with self._connect() as connection:
            return pd.read_sql_query(query, connection, params=params)

    def _get_table_columns(self, table_name: str) -> set[str]:
        with self._connect() as connection:
            rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {str(row[1]) for row in rows}

    @staticmethod
    def _ensure_column(connection: sqlite3.Connection, table_name: str, column_name: str, column_type: str) -> None:
        rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        existing = {str(row[1]) for row in rows}
        if column_name not in existing:
            connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

    @staticmethod
    def dumps_payload(payload: dict[str, object]) -> str:
        return json.dumps(payload, default=str)

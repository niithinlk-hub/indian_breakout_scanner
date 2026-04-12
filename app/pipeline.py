from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd

from app.config import AppSettings
from app.data_ingestion import MarketDataService
from app.explanations.generator import generate_breakout_explanation
from app.models import ScanJobResult
from app.scoring.engine import rank_stocks_by_score, score_breakout_setup
from app.signals.breakout import combine_latest_signals
from app.storage.sqlite_store import SQLiteStore
from app.utils.logging import get_logger


class DailyScanner:
    """End-of-day breakout scanning pipeline."""

    def __init__(
        self,
        *,
        data_service: MarketDataService,
        store: SQLiteStore,
        settings: AppSettings,
    ) -> None:
        self.data_service = data_service
        self.store = store
        self.settings = settings
        self.logger = get_logger(__name__)

    def scan_end_of_day(
        self,
        watchlist: list[str],
        *,
        benchmark_symbol: str | None = None,
        symbol_metadata: dict[str, dict[str, str]] | None = None,
        max_workers: int | None = None,
    ) -> pd.DataFrame:
        """Scan a watchlist, score candidates, rank them, and persist results."""

        run_timestamp = datetime.utcnow().replace(microsecond=0).isoformat()
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=self.settings.scan_lookback_days)
        benchmark = benchmark_symbol or self.settings.benchmark_symbol
        try:
            benchmark_df = self.data_service.get_historical_ohlcv(benchmark, "day", start_date, end_date)
        except Exception as exc:
            self.logger.warning(
                "Benchmark fetch failed for %s: %s. Relative strength will be marked insufficient.",
                benchmark,
                exc,
            )
            benchmark_df = pd.DataFrame()

        results: list[dict[str, Any]] = []
        histories: list[pd.DataFrame] = []
        workers = max_workers or self.settings.scan_workers
        with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
            future_map = {
                executor.submit(
                    self._process_symbol,
                    symbol,
                    start_date,
                    end_date,
                    benchmark_df,
                    (symbol_metadata or {}).get(symbol, {}),
                ): symbol
                for symbol in watchlist
            }

            for future in as_completed(future_map):
                symbol = future_map[future]
                try:
                    job_result = future.result()
                except Exception as exc:  # pragma: no cover - defensive logging
                    self.logger.exception("Unhandled scanner failure for %s: %s", symbol, exc)
                    continue

                if not job_result.success:
                    self.logger.error("Scan failed for %s: %s", symbol, job_result.error)
                    continue

                payload = job_result.payload or {}
                results.append(payload["scan_result"])
                histories.append(payload["history"])

        results_df = rank_stocks_by_score(pd.DataFrame(results))
        if not results_df.empty:
            results_df.insert(0, "scan_timestamp", run_timestamp)
            self.store.save_scan_results(results_df)
        for history_df in histories:
            self.store.save_price_history(history_df)
        return results_df

    def _process_symbol(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        benchmark_df: pd.DataFrame,
        metadata: dict[str, str],
    ) -> ScanJobResult:
        try:
            history = self.data_service.get_historical_ohlcv(symbol, "day", start_date, end_date)
            if history.empty:
                return ScanJobResult(symbol=symbol, success=False, error="No OHLCV data returned.")
            combined = combine_latest_signals(
                symbol,
                history,
                benchmark_df,
                sector=metadata.get("sector"),
                market_cap_bucket=metadata.get("market_cap_bucket"),
            )
            score = score_breakout_setup(combined)
            enriched = {**combined, **score.to_dict()}
            explanation = generate_breakout_explanation(enriched)
            flattened = self._flatten_scan_result(enriched, explanation.to_dict())
            return ScanJobResult(
                symbol=symbol,
                success=True,
                payload={"scan_result": flattened, "history": history},
            )
        except Exception as exc:
            return ScanJobResult(symbol=symbol, success=False, error=str(exc))

    def _flatten_scan_result(self, combined: dict[str, Any], explanation: dict[str, Any]) -> dict[str, Any]:
        return {
            "as_of": combined.get("as_of"),
            "symbol": combined.get("symbol"),
            "close": combined.get("close"),
            "signal_state": combined.get("signal_state"),
            "breakout_level": combined.get("breakout_level"),
            "distance_above_breakout_pct": combined.get("distance_above_breakout_pct"),
            "volume_multiple": combined.get("volume_multiple"),
            "dma_50_status": combined.get("dma_50_status"),
            "dma_200_status": combined.get("dma_200_status"),
            "atr_status": combined.get("atr_status"),
            "relative_strength_status": combined.get("relative_strength_status"),
            "liquidity_turnover_20": combined.get("liquidity_turnover_20"),
            "liquidity_status": combined.get("liquidity_status"),
            "failed_breakout": int(bool(combined.get("failed_breakout"))),
            "total_score": combined.get("total_score"),
            "rating": combined.get("rating"),
            "explanation": explanation.get("explanation"),
            "trader_summary": explanation.get("trader_summary"),
            "tags_json": SQLiteStore.dumps_payload({"tags": explanation.get("tags", [])}),
            "sector": combined.get("sector"),
            "market_cap_bucket": combined.get("market_cap_bucket"),
            "component_scores_json": SQLiteStore.dumps_payload(combined.get("component_scores", {})),
            "signal_payload_json": SQLiteStore.dumps_payload(combined),
        }

from __future__ import annotations

import argparse
from pathlib import Path

from app.config import get_settings
from app.data_ingestion import MarketDataService
from app.pipeline import DailyScanner
from app.providers.factory import build_market_data_provider
from app.storage.sqlite_store import SQLiteStore
from app.universe import build_stock_universe
from app.utils.logging import configure_logging, get_logger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Indian stock breakout scanner")
    parser.add_argument("--scan-eod", action="store_true", help="Run the end-of-day scanner.")
    parser.add_argument(
        "--watchlist-file",
        type=Path,
        default=Path("config/watchlist.example.txt"),
        help="Path to a text file containing one NSE symbol per line.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Override the configured number of parallel workers.",
    )
    parser.add_argument(
        "--universe-mode",
        choices=["watchlist", "nse_equities"],
        default="watchlist",
        help="Choose whether to scan the manual watchlist or all NSE cash equities.",
    )
    parser.add_argument(
        "--symbol-limit",
        type=int,
        default=None,
        help="Optional cap on the number of symbols scanned from the selected universe.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)

    if not args.scan_eod:
        logger.info("Nothing to do. Run with --scan-eod to execute the scanner.")
        return

    provider = build_market_data_provider(settings)
    data_service = MarketDataService(provider=provider, settings=settings)
    store = SQLiteStore(settings.database_path)
    scanner = DailyScanner(data_service=data_service, store=store, settings=settings)
    universe = build_stock_universe(
        data_service=data_service,
        mode=args.universe_mode,
        default_exchange=settings.default_exchange,
        watchlist_path=args.watchlist_file,
        symbol_limit=args.symbol_limit,
    )
    if not universe.symbols:
        logger.warning("No symbols resolved for universe mode '%s'.", args.universe_mode)
        return

    logger.info("Scanning %s symbols using universe mode '%s'.", len(universe.symbols), args.universe_mode)
    results_df = scanner.scan_end_of_day(
        universe.symbols,
        symbol_metadata=universe.metadata,
        max_workers=args.max_workers,
    )

    if results_df.empty:
        logger.warning("Scanner completed with no successful results. Check provider configuration.")
        return

    logger.info("Scan complete. Top results:\n%s", results_df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()

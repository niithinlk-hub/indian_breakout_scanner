from __future__ import annotations

import argparse
from pathlib import Path

from app.config import get_settings
from app.data_ingestion import MarketDataService
from app.pipeline import DailyScanner
from app.providers.factory import build_market_data_provider
from app.storage.sqlite_store import SQLiteStore
from app.utils.logging import configure_logging, get_logger


def _load_watchlist(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Watchlist file not found: {path}")
    return [line.strip().upper() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)

    if not args.scan_eod:
        logger.info("Nothing to do. Run with --scan-eod to execute the scanner.")
        return

    watchlist = _load_watchlist(args.watchlist_file)
    provider = build_market_data_provider(settings)
    data_service = MarketDataService(provider=provider, settings=settings)
    store = SQLiteStore(settings.database_path)
    scanner = DailyScanner(data_service=data_service, store=store, settings=settings)
    results_df = scanner.scan_end_of_day(watchlist, max_workers=args.max_workers)

    if results_df.empty:
        logger.warning("Scanner completed with no successful results. Check provider configuration.")
        return

    logger.info("Scan complete. Top results:\n%s", results_df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()

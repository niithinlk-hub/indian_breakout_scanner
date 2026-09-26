"""Command line entry points: `python -m nsescan <command>` (run from `scanner/`)."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from .config import Config, default_config, seed_sql

SCANNER_ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger("nsescan")


def data_dir() -> Path:
    return Path(os.environ.get("NSESCAN_DATA_DIR", SCANNER_ROOT / "data"))


def get_store():
    from .store.local import LocalStore

    return LocalStore(data_dir())


def get_config(store) -> Config:
    """Supabase config table when credentials are present, else the defaults (logged)."""

    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_KEY"):
        from .store.supabase_store import SupabaseStore

        return SupabaseStore.from_env().read_config()
    LOGGER.warning("SUPABASE_URL / SUPABASE_SERVICE_KEY not set: using built-in config defaults")
    return default_config()


def cmd_universe(args: argparse.Namespace) -> int:
    from .universe import load_universe

    store = get_store()
    loaded = load_universe(SCANNER_ROOT / "universe_snapshots", refresh=not args.offline)
    store.upsert_universe(loaded.frame)
    counts = loaded.frame.groupby("segment").size().to_dict()
    print(json.dumps({"counts": counts, "sources": loaded.sources, "from_snapshot": loaded.from_snapshot,
                      "duplicates": loaded.duplicates, "placeholders_excluded": loaded.placeholders}, indent=1))
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    from .pipeline import load_benchmarks, load_history

    store = get_store()
    cfg = get_config(store)
    summary = load_history(store, cfg, symbols=args.symbols or None)
    bench = load_benchmarks(store, cfg)
    summary.notes["benchmarks"] = bench
    summary.notes["config_hash"] = cfg.hash
    store.log_scan_run(summary.record())
    print(json.dumps(summary.record(), indent=1, default=str))
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    from .pipeline import load_benchmarks, update_prices

    store = get_store()
    cfg = get_config(store)
    summary = update_prices(store, cfg)
    summary.notes["benchmarks"] = load_benchmarks(store, cfg, full=False)
    summary.notes["config_hash"] = cfg.hash
    store.log_scan_run(summary.record())
    print(json.dumps(summary.record(), indent=1, default=str))
    return 0


def cmd_qa(args: argparse.Namespace) -> int:
    from .qa import run_qa

    store = get_store()
    cfg = get_config(store)
    result = run_qa(store, cfg)
    store.replace_data_quality(result.issues)
    print(result.summary.to_string())
    return 0


def cmd_data_report(args: argparse.Namespace) -> int:
    from .reports import write_data_report

    store = get_store()
    cfg = get_config(store)
    path = write_data_report(store, cfg, SCANNER_ROOT / "reports")
    print(path)
    return 0


def cmd_baserate(args: argparse.Namespace) -> int:
    from .baserate import run_baserate

    store = get_store()
    cfg = get_config(store)
    paths = run_baserate(store, cfg, SCANNER_ROOT / "reports", start=args.start, end=args.end)
    print("\n".join(str(p) for p in paths))
    return 0


def cmd_config_sql(args: argparse.Namespace) -> int:
    sys.stdout.write(seed_sql())
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(prog="nsescan")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("universe", help="Fetch NSE constituent CSVs and update the universe")
    p.add_argument("--offline", action="store_true", help="Use the latest committed snapshot only")
    p.set_defaults(func=cmd_universe)

    p = sub.add_parser("history", help="Full-history load (data.history_years) + benchmarks")
    p.add_argument("--symbols", nargs="*", help="Limit to these symbols")
    p.set_defaults(func=cmd_history)

    p = sub.add_parser("update", help="Incremental daily update with re-adjustment detection")
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("qa", help="Run data QA and store data_quality")
    p.set_defaults(func=cmd_qa)

    p = sub.add_parser("data-report", help="Write the step-1 data report")
    p.set_defaults(func=cmd_data_report)

    p = sub.add_parser("baserate", help="Benchmark (a): random entries on liquidity-gate names")
    p.add_argument("--start", default=None)
    p.add_argument("--end", default=None)
    p.set_defaults(func=cmd_baserate)

    p = sub.add_parser("config-sql", help="Print SQL seeding the config table with defaults")
    p.set_defaults(func=cmd_config_sql)

    args = parser.parse_args(argv)
    return int(args.func(args))

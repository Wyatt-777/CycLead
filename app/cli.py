"""Command-line entry point for the CycleLead MVP."""

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from app import __version__
from app.config import get_settings
from app.db import create_db_engine, create_session_factory, session_scope
from app.models import DiscoveryRunStatus
from app.schemas import SeedInput
from app.services.discovery import DiscoveryService
from app.sources import ManualSeedSource


def build_parser() -> argparse.ArgumentParser:
    """Build the Phase 0 command parser.

    Export and report commands are intentionally added with their corresponding
    implementation phases so the CLI never advertises unavailable work.
    """

    parser = argparse.ArgumentParser(prog="cyclelead", description="CycleLead AI MVP")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    discover_parser = subparsers.add_parser(
        "discover", help="run a compliant lead-discovery source"
    )
    discover_parser.add_argument("--query", required=True)
    discover_parser.add_argument("--source", choices=["manual_seed"], required=True)
    discover_parser.add_argument("--input", required=True, type=Path, help="manual-seed JSON file")
    discover_parser.add_argument("--region")
    discover_parser.add_argument(
        "--database-url",
        help="override the local SQLite URL for this command only",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Validate command-line arguments and return a process status code."""

    arguments = build_parser().parse_args(argv)
    if arguments.command is None:
        return 0
    if arguments.command == "discover":
        return discover(arguments)
    return 0


def discover(arguments: argparse.Namespace) -> int:
    """Run the local manual-seed source and print a machine-readable run summary."""

    settings = get_settings()
    database_url = arguments.database_url or settings.database_url
    engine = create_db_engine(database_url)

    try:
        session_factory = create_session_factory(engine)
        with session_scope(session_factory) as session:
            summary = DiscoveryService().run(
                session,
                SeedInput(query=arguments.query, source=arguments.source, region=arguments.region),
                ManualSeedSource(arguments.input),
            )
        print(json.dumps(asdict(summary), default=str, ensure_ascii=False))
        return 0 if summary.status is not DiscoveryRunStatus.FAILED else 1
    except SQLAlchemyError as error:
        print(
            f"Database error: {error}. Run 'alembic upgrade head' before discovery.",
            file=sys.stderr,
        )
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())

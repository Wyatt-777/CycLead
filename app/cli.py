"""Command-line entry point for the CycleLead MVP."""

import argparse
from collections.abc import Sequence

from app import __version__


def build_parser() -> argparse.ArgumentParser:
    """Build the Phase 0 command parser.

    Discovery, export, and report commands are intentionally added with their
    corresponding implementation phases so the CLI never advertises unavailable work.
    """

    parser = argparse.ArgumentParser(prog="cyclelead", description="CycleLead AI MVP")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Validate command-line arguments and return a process status code."""

    build_parser().parse_args(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

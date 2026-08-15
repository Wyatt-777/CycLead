"""Command-line entry point for the CycleLead MVP."""

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app import __version__
from app.config import get_settings
from app.db import create_db_engine, create_session_factory, session_scope
from app.models import DiscoveryRunStatus, Lead
from app.schemas import ReviewInput, SeedInput
from app.services.discovery import DiscoveryService
from app.services.review_service import (
    LeadNotEligibleForReviewError,
    LeadNotFoundError,
    ReviewService,
)
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

    queue_parser = subparsers.add_parser(
        "review-queue", help="list qualified leads awaiting human review"
    )
    queue_parser.add_argument(
        "--database-url",
        help="override the local SQLite URL for this command only",
    )

    review_parser = subparsers.add_parser(
        "review", help="append a human review decision for one qualified lead"
    )
    review_parser.add_argument("--lead-id", required=True)
    review_parser.add_argument(
        "--decision",
        choices=["ACCEPT", "REJECT", "CONTACT_LATER"],
        required=True,
    )
    review_parser.add_argument("--reason", required=True)
    review_parser.add_argument(
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
    if arguments.command == "review-queue":
        return list_review_queue(arguments)
    if arguments.command == "review":
        return record_review(arguments)
    return 0


def discover(arguments: argparse.Namespace) -> int:
    """Run the local manual-seed source and print a machine-readable run summary."""

    settings = get_settings()
    database_url = arguments.database_url or settings.database_url
    engine = create_db_engine(database_url)

    try:
        session_factory = create_session_factory(engine)
        with session_scope(session_factory) as session:
            summary = DiscoveryService(
                qualification_threshold=settings.qualification_threshold
            ).run(
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


def list_review_queue(arguments: argparse.Namespace) -> int:
    """Print qualified, unreviewed leads as JSON for manual review."""

    settings = get_settings()
    database_url = arguments.database_url or settings.database_url
    engine = create_db_engine(database_url)
    try:
        session_factory = create_session_factory(engine)
        with session_scope(session_factory) as session:
            leads = ReviewService(settings.qualification_threshold).list_pending(session)
            payload = [_queue_item(lead) for lead in leads]
        print(json.dumps(payload, ensure_ascii=False))
        return 0
    except SQLAlchemyError as error:
        print(
            f"Database error: {error}. Run 'alembic upgrade head' before reviewing leads.",
            file=sys.stderr,
        )
        return 1
    finally:
        engine.dispose()


def record_review(arguments: argparse.Namespace) -> int:
    """Validate, append, and print one manual review decision."""

    try:
        review_input = ReviewInput(decision=arguments.decision, reason=arguments.reason)
    except ValidationError as error:
        print(f"Invalid review input: {error}", file=sys.stderr)
        return 2

    settings = get_settings()
    database_url = arguments.database_url or settings.database_url
    engine = create_db_engine(database_url)
    try:
        session_factory = create_session_factory(engine)
        with session_scope(session_factory) as session:
            review = ReviewService(settings.qualification_threshold).record_decision(
                session, arguments.lead_id, review_input
            )
            payload = {
                "review_id": review.id,
                "lead_id": review.lead_id,
                "decision": review.decision.value,
                "reason": review.reason,
                "reviewed_at": review.reviewed_at.isoformat(),
            }
        print(json.dumps(payload, ensure_ascii=False))
        return 0
    except (LeadNotFoundError, LeadNotEligibleForReviewError) as error:
        print(f"Review error: {error}", file=sys.stderr)
        return 1
    except SQLAlchemyError as error:
        print(
            f"Database error: {error}. Run 'alembic upgrade head' before reviewing leads.",
            file=sys.stderr,
        )
        return 1
    finally:
        engine.dispose()


def _queue_item(lead: Lead) -> dict[str, object]:
    """Return the minimal manual-review payload without inferring missing lead fields."""

    return {
        "lead_id": lead.id,
        "name": lead.name,
        "business_type": lead.business_type.value,
        "score": lead.score,
        "score_band": lead.score_band.value,
        "score_reasons": lead.score_reasons,
        "country": lead.country,
        "city": lead.city,
        "website": lead.website,
        "social_url": lead.social_url,
        "email": lead.email,
        "phone": lead.phone,
        "source_url": lead.source_url,
    }


if __name__ == "__main__":
    raise SystemExit(main())

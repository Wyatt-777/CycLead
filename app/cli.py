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
from app.schemas import ExportInput, ReviewInput, RunReportInput, SeedInput
from app.services.discovery import DiscoveryService
from app.services.export_service import LeadExportService
from app.services.report_service import DiscoveryRunNotFoundError, RunReport, RunReportService
from app.services.review_service import (
    LeadNotEligibleForReviewError,
    LeadNotFoundError,
    ReviewService,
)
from app.sources import BraveSearchSource, LeadSource, ManualSeedSource


def build_parser() -> argparse.ArgumentParser:
    """Build the implemented CycleLead MVP command parser."""

    parser = argparse.ArgumentParser(prog="cyclelead", description="CycleLead AI MVP")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    discover_parser = subparsers.add_parser(
        "discover", help="run a compliant lead-discovery source"
    )
    discover_parser.add_argument("--query", required=True)
    discover_parser.add_argument("--source", choices=["manual_seed", "brave_search"], required=True)
    discover_parser.add_argument(
        "--input", type=Path, help="manual-seed JSON file; required only for source manual_seed"
    )
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

    export_parser = subparsers.add_parser(
        "export", help="export accepted, qualified, or all leads as CSV or JSON"
    )
    export_parser.add_argument("--format", choices=["csv", "json"], required=True)
    export_parser.add_argument("--output", required=True, type=Path)
    export_parser.add_argument(
        "--scope",
        choices=["accepted", "qualified", "all"],
        default="accepted",
        help="lead scope; defaults to human-accepted leads",
    )
    export_parser.add_argument(
        "--database-url",
        help="override the local SQLite URL for this command only",
    )

    report_parser = subparsers.add_parser(
        "report", help="show one persisted discovery run and its recorded metrics"
    )
    report_parser.add_argument("--run-id", required=True)
    report_parser.add_argument(
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
    if arguments.command == "export":
        return export_leads(arguments)
    if arguments.command == "report":
        return report_run(arguments)
    return 0


def discover(arguments: argparse.Namespace) -> int:
    """Run the selected compliant source and print a machine-readable run summary."""

    try:
        settings = get_settings()
        seed = SeedInput(
            query=arguments.query,
            source=arguments.source,
            region=arguments.region,
        )
        source = _discovery_source(arguments, settings)
    except (ValidationError, ValueError) as error:
        print(f"Invalid discovery input: {error}", file=sys.stderr)
        return 2

    database_url = arguments.database_url or settings.database_url
    engine = create_db_engine(database_url)

    try:
        session_factory = create_session_factory(engine)
        with session_scope(session_factory) as session:
            summary = DiscoveryService(
                qualification_threshold=settings.qualification_threshold
            ).run(
                session,
                seed,
                source,
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


def _discovery_source(arguments: argparse.Namespace, settings) -> LeadSource:
    """Build only the explicitly selected local or API-backed source adapter."""

    if arguments.source == "manual_seed":
        if arguments.input is None:
            raise ValueError("--input is required when --source manual_seed")
        return ManualSeedSource(arguments.input)

    if arguments.input is not None:
        raise ValueError("--input is only supported when --source manual_seed")
    api_key = (
        settings.brave_search_api_key.get_secret_value()
        if settings.brave_search_api_key is not None
        else None
    )
    return BraveSearchSource(
        query=arguments.query,
        api_key=api_key,
        country=settings.brave_search_country,
        search_language=settings.brave_search_language,
        result_count=settings.brave_search_result_count,
        timeout_seconds=settings.brave_search_timeout_seconds,
    )


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


def export_leads(arguments: argparse.Namespace) -> int:
    """Validate and export the requested lead scope without changing any lead data."""

    try:
        export_input = ExportInput(format=arguments.format, scope=arguments.scope)
    except ValidationError as error:
        print(f"Invalid export input: {error}", file=sys.stderr)
        return 2

    settings = get_settings()
    database_url = arguments.database_url or settings.database_url
    engine = create_db_engine(database_url)
    try:
        session_factory = create_session_factory(engine)
        with session_scope(session_factory) as session:
            result = LeadExportService(settings.qualification_threshold).export(
                session, export_input, arguments.output
            )
        print(
            json.dumps(
                {
                    "format": result.format,
                    "scope": result.scope,
                    "output": str(result.output_path),
                    "exported": result.exported_count,
                },
                ensure_ascii=False,
            )
        )
        return 0
    except (OSError, ValueError) as error:
        print(f"Export error for {arguments.output}: {error}", file=sys.stderr)
        return 1
    except SQLAlchemyError as error:
        print(
            f"Database error: {error}. Run 'alembic upgrade head' before exporting leads.",
            file=sys.stderr,
        )
        return 1
    finally:
        engine.dispose()


def report_run(arguments: argparse.Namespace) -> int:
    """Validate a run ID and print only its persisted execution metrics."""

    try:
        report_input = RunReportInput(run_id=arguments.run_id)
    except ValidationError as error:
        print(f"Invalid report input: {error}", file=sys.stderr)
        return 2

    settings = get_settings()
    database_url = arguments.database_url or settings.database_url
    engine = create_db_engine(database_url)
    try:
        session_factory = create_session_factory(engine)
        with session_scope(session_factory) as session:
            report = RunReportService().get(session, str(report_input.run_id))
        print(json.dumps(_report_payload(report), ensure_ascii=False))
        return 0
    except DiscoveryRunNotFoundError as error:
        print(f"Report error: {error}", file=sys.stderr)
        return 1
    except SQLAlchemyError as error:
        print(
            f"Database error: {error}. Run 'alembic upgrade head' before reading reports.",
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


def _report_payload(report: RunReport) -> dict[str, object]:
    """Serialize timestamps explicitly without inventing missing finish data."""

    return {
        "run_id": report.run_id,
        "query": report.query,
        "source": report.source,
        "status": report.status.value,
        "started_at": report.started_at.isoformat(),
        "finished_at": report.finished_at.isoformat() if report.finished_at else None,
        "elapsed_seconds": report.elapsed_seconds,
        "discovered": report.discovered,
        "parsed": report.parsed,
        "duplicates": report.duplicates,
        "qualified": report.qualified,
        "rejected": report.rejected,
        "errors": report.errors,
    }


if __name__ == "__main__":
    raise SystemExit(main())

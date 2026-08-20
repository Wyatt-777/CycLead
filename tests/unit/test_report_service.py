"""Tests for persisted discovery-run reporting without log reconstruction."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.models import DiscoveryRun, DiscoveryRunStatus
from app.services.report_service import DiscoveryRunNotFoundError, RunReportService


def test_report_service_returns_persisted_counts_and_elapsed_time(db_session: Session) -> None:
    started_at = datetime(2026, 8, 20, 9, 0, tzinfo=timezone.utc)
    run = DiscoveryRun(
        query="bike workshop",
        source="manual_seed",
        status=DiscoveryRunStatus.PARTIAL_FAILURE,
        started_at=started_at,
        finished_at=started_at + timedelta(seconds=3.5),
        discovered_count=7,
        parsed_count=5,
        duplicate_count=1,
        qualified_count=2,
        rejected_count=2,
        error_count=2,
    )
    db_session.add(run)
    db_session.flush()

    report = RunReportService().get(db_session, run.id)

    assert report.run_id == run.id
    assert report.status is DiscoveryRunStatus.PARTIAL_FAILURE
    assert report.elapsed_seconds == 3.5
    assert (
        report.discovered,
        report.parsed,
        report.duplicates,
        report.qualified,
        report.rejected,
        report.errors,
    ) == (7, 5, 1, 2, 2, 2)


def test_report_service_marks_unfinished_runs_without_an_elapsed_time(db_session: Session) -> None:
    run = DiscoveryRun(query="bike repair", source="manual_seed")
    db_session.add(run)
    db_session.flush()

    report = RunReportService().get(db_session, run.id)

    assert report.finished_at is None
    assert report.elapsed_seconds is None


def test_report_service_rejects_unknown_run_ids(db_session: Session) -> None:
    with pytest.raises(DiscoveryRunNotFoundError, match="discovery run not found"):
        RunReportService().get(db_session, "00000000-0000-0000-0000-000000000000")

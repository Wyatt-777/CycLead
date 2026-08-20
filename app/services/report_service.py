"""Read-only reporting for persisted discovery-run observability."""

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import DiscoveryRun, DiscoveryRunStatus

LOGGER = logging.getLogger(__name__)


class DiscoveryRunNotFoundError(LookupError):
    """The requested persisted discovery run does not exist."""


@dataclass(frozen=True, slots=True)
class RunReport:
    """A read-only view of one persisted discovery run and its recorded metrics."""

    run_id: str
    query: str
    source: str
    status: DiscoveryRunStatus
    started_at: datetime
    finished_at: datetime | None
    elapsed_seconds: float | None
    discovered: int
    parsed: int
    duplicates: int
    qualified: int
    rejected: int
    errors: int


class RunReportService:
    """Return persisted run data without interpreting log text or changing records."""

    def get(self, session: Session, run_id: str) -> RunReport:
        """Look up a run by ID and calculate elapsed time only after it has finished."""

        run = session.get(DiscoveryRun, run_id)
        if run is None:
            raise DiscoveryRunNotFoundError(f"discovery run not found: {run_id}")

        elapsed_seconds = (
            (run.finished_at - run.started_at).total_seconds()
            if run.finished_at is not None
            else None
        )
        report = RunReport(
            run_id=run.id,
            query=run.query,
            source=run.source,
            status=run.status,
            started_at=run.started_at,
            finished_at=run.finished_at,
            elapsed_seconds=elapsed_seconds,
            discovered=run.discovered_count,
            parsed=run.parsed_count,
            duplicates=run.duplicate_count,
            qualified=run.qualified_count,
            rejected=run.rejected_count,
            errors=run.error_count,
        )
        LOGGER.info(
            "run_id=%s source=%s stage=report status=%s",
            report.run_id,
            report.source,
            report.status.value,
        )
        return report

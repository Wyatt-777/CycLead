"""Safe, deterministic CSV and JSON export for human-reviewed lead records."""

import logging
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exporters import write_csv, write_json
from app.models import BusinessType, Lead, ReviewStatus
from app.pipeline.qualifier import LeadQualifier
from app.schemas import ExportInput

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ExportResult:
    """The completed output location and number of exported lead records."""

    format: str
    scope: str
    output_path: Path
    exported_count: int


class LeadExportService:
    """Export existing fields only; it never enriches, scores, or contacts a lead."""

    def __init__(self, qualification_threshold: int = 60) -> None:
        self._qualifier = LeadQualifier(qualification_threshold)

    def export(
        self, session: Session, export_input: ExportInput, output_path: Path
    ) -> ExportResult:
        """Select the requested scope and atomically write a UTF-8 CSV or JSON document."""

        resolved_output_path = self._validate_output_path(output_path, export_input.format)
        records = [
            self._record_from_lead(lead) for lead in self._leads_for_scope(session, export_input)
        ]
        self._write_atomically(resolved_output_path, export_input.format, records)
        LOGGER.info(
            "stage=export format=%s scope=%s count=%s output=%s",
            export_input.format,
            export_input.scope,
            len(records),
            resolved_output_path,
        )
        return ExportResult(
            format=export_input.format,
            scope=export_input.scope,
            output_path=resolved_output_path,
            exported_count=len(records),
        )

    def _leads_for_scope(self, session: Session, export_input: ExportInput) -> list[Lead]:
        statement = select(Lead)
        if export_input.scope == "accepted":
            statement = statement.where(Lead.review_status == ReviewStatus.ACCEPT)
        elif export_input.scope == "qualified":
            statement = statement.where(
                Lead.score >= self._qualifier.qualification_threshold,
                Lead.business_type != BusinessType.UNRELATED,
            )
        order_by = (Lead.score.desc(), Lead.created_at.asc(), Lead.id.asc())
        return list(
            session.scalars(statement.order_by(*order_by))
        )

    @staticmethod
    def _record_from_lead(lead: Lead) -> dict[str, object]:
        location = ", ".join(value for value in (lead.city, lead.country) if value) or None
        return {
            "lead_id": lead.id,
            "name": lead.name,
            "business_type": lead.business_type.value,
            "score": lead.score,
            "score_reason": lead.score_reasons,
            "location": location,
            "website": lead.website,
            "social_url": lead.social_url,
            "email": lead.email,
            "phone": lead.phone,
            "source_url": lead.source_url,
            "status": lead.review_status.value,
            "created_at": lead.created_at.isoformat(),
        }

    @staticmethod
    def _validate_output_path(output_path: Path, export_format: str) -> Path:
        resolved_path = output_path.expanduser().resolve()
        expected_suffix = f".{export_format}"
        if resolved_path.suffix.casefold() != expected_suffix:
            raise ValueError(f"output path must use the {expected_suffix} extension")
        if resolved_path.exists() and resolved_path.is_dir():
            raise ValueError("output path must name a file, not a directory")
        return resolved_path

    @staticmethod
    def _write_atomically(
        output_path: Path,
        export_format: str,
        records: list[dict[str, object]],
    ) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(
                mode="w",
                encoding="utf-8-sig" if export_format == "csv" else "utf-8",
                newline="",
                dir=output_path.parent,
                prefix=f".{output_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                if export_format == "csv":
                    write_csv(temporary_file, records)
                else:
                    write_json(temporary_file, records)
            temporary_path.replace(output_path)
        except Exception:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()
            raise

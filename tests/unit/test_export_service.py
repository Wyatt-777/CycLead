"""Tests for CSV and JSON lead exports without data enrichment."""

import csv
import json
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.exporters import EXPORT_FIELDS
from app.models import BusinessType, Lead, ReviewStatus, ScoreBand
from app.schemas import ExportInput
from app.services.export_service import LeadExportService


def add_lead(
    session: Session,
    *,
    name: str,
    score: int,
    review_status: ReviewStatus,
    business_type: BusinessType = BusinessType.BIKE_WORKSHOP,
) -> Lead:
    lead = Lead(
        name=name,
        source="manual_seed",
        source_url=f"https://example.test/{name.casefold().replace(' ', '-')}",
        country="SG",
        city="Singapore",
        email="sales@example.test",
        business_type=business_type,
        score=score,
        score_band=ScoreBand.A if score >= 80 else ScoreBand.B,
        score_reasons=["Evidence-backed score reason."],
        review_status=review_status,
    )
    session.add(lead)
    session.flush()
    return lead


def test_export_service_writes_accepted_leads_to_utf8_csv(
    db_session: Session, tmp_path: Path
) -> None:
    accepted = add_lead(
        db_session,
        name="Accepted Studio",
        score=80,
        review_status=ReviewStatus.ACCEPT,
    )
    add_lead(db_session, name="Pending Studio", score=90, review_status=ReviewStatus.NEW)
    output_path = tmp_path / "accepted.csv"

    result = LeadExportService().export(
        db_session,
        ExportInput(format="csv"),
        output_path,
    )

    with output_path.open(encoding="utf-8-sig", newline="") as output:
        rows = list(csv.DictReader(output))

    assert result.output_path == output_path.resolve()
    assert result.exported_count == 1
    assert list(rows[0]) == list(EXPORT_FIELDS)
    assert rows == [
        {
            "lead_id": accepted.id,
            "name": "Accepted Studio",
            "business_type": "BIKE_WORKSHOP",
            "score": "80",
            "score_reason": json.dumps(["Evidence-backed score reason."]),
            "location": "Singapore, SG",
            "website": "",
            "social_url": "",
            "email": "sales@example.test",
            "phone": "",
            "source_url": "https://example.test/accepted-studio",
            "status": "ACCEPT",
            "created_at": rows[0]["created_at"],
        }
    ]


def test_export_service_supports_qualified_and_all_json_scopes(
    db_session: Session, tmp_path: Path
) -> None:
    accepted = add_lead(
        db_session,
        name="Accepted Studio",
        score=80,
        review_status=ReviewStatus.ACCEPT,
    )
    pending = add_lead(db_session, name="Pending Studio", score=90, review_status=ReviewStatus.NEW)
    rejected = add_lead(
        db_session,
        name="Rejected Studio",
        score=70,
        review_status=ReviewStatus.REJECT,
    )
    unrelated = add_lead(
        db_session,
        name="Unrelated Studio",
        score=100,
        review_status=ReviewStatus.NEW,
        business_type=BusinessType.UNRELATED,
    )

    qualified_path = tmp_path / "qualified.json"
    all_path = tmp_path / "all.json"
    service = LeadExportService()
    qualified_result = service.export(
        db_session,
        ExportInput(format="json", scope="qualified"),
        qualified_path,
    )
    all_result = service.export(
        db_session,
        ExportInput(format="json", scope="all"),
        all_path,
    )

    qualified_rows = json.loads(qualified_path.read_text(encoding="utf-8"))
    all_rows = json.loads(all_path.read_text(encoding="utf-8"))

    assert qualified_result.exported_count == 3
    assert [row["lead_id"] for row in qualified_rows] == [pending.id, accepted.id, rejected.id]
    assert qualified_rows[0]["score_reason"] == ["Evidence-backed score reason."]
    assert all_result.exported_count == 4
    assert all_rows[0]["lead_id"] == unrelated.id


def test_export_service_writes_valid_empty_output_and_rejects_mismatched_suffix(
    db_session: Session, tmp_path: Path
) -> None:
    service = LeadExportService()
    csv_path = tmp_path / "empty.csv"
    json_path = tmp_path / "empty.json"

    csv_result = service.export(db_session, ExportInput(format="csv"), csv_path)
    json_result = service.export(db_session, ExportInput(format="json"), json_path)

    assert csv_result.exported_count == 0
    assert csv_path.read_text(encoding="utf-8-sig").splitlines() == [
        ",".join(EXPORT_FIELDS)
    ]
    assert json_result.exported_count == 0
    assert json.loads(json_path.read_text(encoding="utf-8")) == []
    with pytest.raises(ValueError, match=".csv extension"):
        service.export(db_session, ExportInput(format="csv"), tmp_path / "wrong.json")

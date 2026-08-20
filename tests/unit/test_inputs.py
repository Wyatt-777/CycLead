from datetime import datetime, timezone

from pydantic import ValidationError
from pytest import raises

from app.models.enums import EvidenceType, ReviewDecision
from app.schemas import (
    EvidenceInput,
    ExportInput,
    LeadInput,
    RawCandidateInput,
    ReviewInput,
    RunReportInput,
)


def test_lead_input_strips_values_and_preserves_unknown_contacts() -> None:
    lead = LeadInput(
        name="  Example Bike Studio  ",
        source=" web ",
        source_url="https://example.test/source",
        country="SG",
    )

    assert lead.name == "Example Bike Studio"
    assert lead.source == "web"
    assert lead.website is None
    assert lead.social_url is None


def test_input_rejects_non_http_source_url() -> None:
    with raises(ValidationError, match="absolute HTTP"):
        LeadInput(name="Example", source="web", source_url="mailto:hello@example.test")


def test_raw_candidate_requires_title_and_capture_time() -> None:
    with raises(ValidationError):
        RawCandidateInput(
            source="web",
            url="https://example.test/candidate",
            title=" ",
            captured_at=datetime.now(timezone.utc),
        )


def test_evidence_input_requires_traceable_source_and_bounded_confidence() -> None:
    evidence = EvidenceInput(
        evidence_type=EvidenceType.SERVICE_CLAIM,
        field_name="services",
        source_text="Custom bike builds available",
        source_url="https://example.test/services",
        captured_at=datetime.now(timezone.utc),
        confidence=0.95,
    )

    assert evidence.confidence == 0.95

    with raises(ValidationError):
        EvidenceInput(
            evidence_type=EvidenceType.SERVICE_CLAIM,
            field_name="services",
            source_text="Custom bike builds available",
            source_url="https://example.test/services",
            captured_at=datetime.now(timezone.utc),
            confidence=1.1,
        )


def test_review_input_requires_a_known_decision_and_nonblank_reason() -> None:
    review = ReviewInput(decision=ReviewDecision.ACCEPT, reason="  Verified workshop.  ")

    assert review.reason == "Verified workshop."

    with raises(ValidationError):
        ReviewInput(decision="UNKNOWN", reason="Not a valid review decision.")
    with raises(ValidationError):
        ReviewInput(decision=ReviewDecision.REJECT, reason=" ")


def test_export_input_requires_a_known_format_and_scope() -> None:
    export = ExportInput(format="csv", scope="qualified")

    assert export.format == "csv"
    assert export.scope == "qualified"
    with raises(ValidationError):
        ExportInput(format="xlsx")
    with raises(ValidationError):
        ExportInput(format="json", scope="rejected")


def test_run_report_input_requires_a_uuid() -> None:
    report = RunReportInput(run_id="20e79169-4867-4076-aaf0-864c9ea6cdf7")

    assert str(report.run_id) == "20e79169-4867-4076-aaf0-864c9ea6cdf7"
    with raises(ValidationError):
        RunReportInput(run_id="not-a-run-id")

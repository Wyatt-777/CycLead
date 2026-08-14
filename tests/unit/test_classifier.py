"""Tests for conservative, source-backed business-type classification."""

from datetime import datetime, timezone

from app.models import BusinessType, EvidenceType
from app.pipeline.classifier import LeadClassifier
from app.pipeline.parser import ParsedCandidate


def make_candidate(source_text: str | None) -> ParsedCandidate:
    return ParsedCandidate(
        name="Example Bike Studio",
        description=source_text,
        country="SG",
        city="Singapore",
        website=None,
        social_url=None,
        email=None,
        phone=None,
        raw_contact_text=None,
        services=(),
        source="manual_seed",
        source_url="https://example.test/studio",
        source_text=source_text,
        captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def test_classifier_records_a_business_type_claim_from_explicit_bicycle_text() -> None:
    result = LeadClassifier().classify(
        make_candidate("Custom bike build services are available at our workshop.")
    )

    assert result.business_type is BusinessType.BIKE_WORKSHOP
    assert result.evidence is not None
    assert result.evidence.evidence_type is EvidenceType.BUSINESS_TYPE_CLAIM
    assert result.evidence.value == "BIKE_WORKSHOP"
    assert result.evidence.source_text == (
        "Custom bike build services are available at our workshop."
    )
    assert result.evidence.source_url == "https://example.test/studio"


def test_classifier_keeps_missing_or_ambiguous_evidence_unknown() -> None:
    assert LeadClassifier().classify(make_candidate(None)).business_type is BusinessType.UNKNOWN
    assert LeadClassifier().classify(make_candidate("We love weekend cycling.")).business_type is (
        BusinessType.UNKNOWN
    )


def test_classifier_marks_only_explicit_non_bicycle_businesses_unrelated() -> None:
    result = LeadClassifier().classify(make_candidate("Independent restaurant serving breakfast."))

    assert result.business_type is BusinessType.UNRELATED
    assert result.evidence is not None

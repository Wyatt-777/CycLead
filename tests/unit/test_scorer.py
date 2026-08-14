"""Tests for the fixed Phase 1 scoring contract and evidence mapping."""

from datetime import datetime, timezone

from app.models import BusinessType, ScoreBand
from app.pipeline.classifier import LeadClassifier
from app.pipeline.parser import ParsedCandidate
from app.pipeline.scorer import LeadScorer, score_band_for


def make_candidate(*, raw_contact_text: str | None = None) -> ParsedCandidate:
    source_text = (
        "Custom bike build at our bike workshop. We offer bike repair and bike upgrade using "
        "groupset, wheelset, derailleur, crank, brake, power meter, and bicycle components."
    )
    return ParsedCandidate(
        name="Example Bike Studio",
        description=source_text,
        country="SG",
        city="Singapore",
        website="https://example.test/contact",
        social_url="https://social.example.test/example-bike-studio",
        email="sales@example.test",
        phone="+65 6123 4567",
        raw_contact_text=raw_contact_text,
        services=(),
        source="manual_seed",
        source_url="https://directory.example.test/example-bike-studio",
        source_text=source_text,
        captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def test_scorer_applies_documented_caps_and_every_reason_has_evidence() -> None:
    candidate = make_candidate(
        raw_contact_text="Email: sales@example.test; Phone: +65 6123 4567"
    )
    classification = LeadClassifier().classify(candidate)
    result = LeadScorer().score(candidate, classification)

    assert classification.business_type is BusinessType.BIKE_WORKSHOP
    assert result.score == 90
    assert result.score_band is ScoreBand.A
    assert sum(reason.points for reason in result.reasons) == 90
    assert all(reason.points > 0 for reason in result.reasons)
    assert all(reason.evidence.source_url == candidate.source_url for reason in result.reasons)
    assert all(reason.evidence.source_text for reason in result.reasons)
    assert any(reason.points == 10 and "repair" in reason.summary for reason in result.reasons)
    assert len([reason for reason in result.reasons if "product relevance" in reason.summary]) == 5
    assert len([reason for reason in result.reasons if "contactability" in reason.summary]) == 3


def test_scorer_does_not_score_contact_values_without_matching_source_text() -> None:
    candidate = make_candidate()
    result = LeadScorer().score(candidate, LeadClassifier().classify(candidate))

    assert result.score == 80
    assert all("public email" not in reason.summary for reason in result.reasons)
    assert all("public phone" not in reason.summary for reason in result.reasons)


def test_score_band_boundaries_follow_the_module_specification() -> None:
    assert score_band_for(0) is ScoreBand.D
    assert score_band_for(39) is ScoreBand.D
    assert score_band_for(40) is ScoreBand.C
    assert score_band_for(59) is ScoreBand.C
    assert score_band_for(60) is ScoreBand.B
    assert score_band_for(79) is ScoreBand.B
    assert score_band_for(80) is ScoreBand.A
    assert score_band_for(100) is ScoreBand.A

"""Tests for deterministic, non-human lead qualification."""

import pytest

from app.models import BusinessType, Lead
from app.pipeline.qualifier import LeadQualifier


def make_lead(score: int, business_type: BusinessType) -> Lead:
    return Lead(
        name="Example Bike Studio",
        source="manual_seed",
        source_url="https://example.test/studio",
        score=score,
        business_type=business_type,
    )


def test_qualifier_uses_an_inclusive_threshold_for_eligible_business_types() -> None:
    qualifier = LeadQualifier(60)

    result = qualifier.assess(make_lead(60, BusinessType.BIKE_WORKSHOP))

    assert qualifier.qualification_threshold == 60
    assert result.qualified is True
    assert result.threshold == 60
    assert "meets qualification threshold" in result.reason


def test_qualifier_rejects_low_scores_and_unrelated_types() -> None:
    qualifier = LeadQualifier(60)

    low_score = qualifier.assess(make_lead(59, BusinessType.BIKE_WORKSHOP))
    unrelated = qualifier.assess(make_lead(100, BusinessType.UNRELATED))

    assert low_score.qualified is False
    assert "below qualification threshold" in low_score.reason
    assert unrelated.qualified is False
    assert unrelated.reason == "business type is UNRELATED"


@pytest.mark.parametrize("threshold", [-1, 101, True, 60.0])
def test_qualifier_rejects_invalid_thresholds(threshold: object) -> None:
    with pytest.raises(ValueError, match="qualification_threshold"):
        LeadQualifier(threshold)  # type: ignore[arg-type]

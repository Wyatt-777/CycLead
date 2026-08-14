from datetime import datetime, timezone

from app.pipeline.parser import CandidateParser
from app.sources.base import RawCandidateData


def test_parser_uses_captured_title_only_when_manual_name_is_missing() -> None:
    parsed = CandidateParser().parse(
        RawCandidateData(
            source="manual_seed",
            url="https://example.test/studio",
            title="Example Bike Studio",
            snippet="Custom bike builds",
            captured_at=datetime.now(timezone.utc),
            city="Singapore",
            services=["custom bike build"],
        )
    )

    assert parsed.name == "Example Bike Studio"
    assert parsed.description == "Custom bike builds"
    assert parsed.email is None
    assert parsed.services == ("custom bike build",)

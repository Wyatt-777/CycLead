"""Integration coverage for the official search adapter through the SQLite pipeline."""

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DiscoveryRunStatus, Lead, RawCandidate
from app.schemas import SeedInput
from app.services.discovery import DiscoveryService
from app.sources import BraveSearchSource


def test_brave_search_discovery_persists_api_result_and_raw_evidence(db_session: Session) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "url": "https://example.test/api-bike-studio",
                            "title": "API Bike Studio",
                            "description": "Custom bike build workshop with component upgrades.",
                        }
                    ]
                }
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        source = BraveSearchSource(
            query="bike custom build",
            api_key="test-token",
            country="SG",
            http_client=client,
        )
        summary = DiscoveryService().run(
            db_session,
            SeedInput(query="bike custom build", source="brave_search", region="Singapore"),
            source,
        )
    db_session.commit()

    lead = db_session.scalar(select(Lead))
    raw_candidate = db_session.scalar(select(RawCandidate))
    assert summary.status is DiscoveryRunStatus.SUCCESS
    assert summary.discovered == 1
    assert summary.parsed == 1
    assert lead is not None
    assert lead.source == "brave_search"
    assert raw_candidate is not None
    assert raw_candidate.raw_url == "https://example.test/api-bike-studio"

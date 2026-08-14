"""Tests for evidence validation and idempotent persistence."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Evidence, EvidenceType, Lead
from app.pipeline.evidence import EvidenceDraft
from app.services.evidence_service import EvidencePersistenceService


def test_evidence_service_persists_an_identical_source_claim_once(db_session: Session) -> None:
    lead = Lead(
        name="Example Bike Studio",
        source="manual_seed",
        source_url="https://example.test/studio",
    )
    db_session.add(lead)
    db_session.flush()
    evidence = EvidenceDraft(
        evidence_type=EvidenceType.SERVICE_CLAIM,
        field_name="services",
        value="custom bike build",
        source_text="Custom bike build services are available.",
        source_url="https://example.test/studio",
        captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        confidence=0.9,
    )

    service = EvidencePersistenceService()
    assert service.persist(db_session, lead, (evidence, evidence)) == 1
    assert service.persist(db_session, lead, (evidence,)) == 0
    assert db_session.scalar(select(func.count()).select_from(Evidence)) == 1

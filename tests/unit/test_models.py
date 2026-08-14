from datetime import datetime, timezone

from pytest import raises
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import create_db_engine, create_session_factory, session_scope
from app.models import (
    BusinessType,
    DiscoveryRun,
    Evidence,
    EvidenceType,
    Lead,
    Query,
    RawCandidate,
    Review,
    ReviewDecision,
    ScoreBand,
)


def make_lead(canonical_url: str, score: int = 82) -> Lead:
    return Lead(
        name="Example Bike Studio",
        business_type=BusinessType.BIKE_WORKSHOP,
        source="web",
        source_url="https://example.test/source",
        canonical_url=canonical_url,
        score=score,
        score_band=ScoreBand.A,
        score_reasons=["Provides custom bike builds"],
    )


def test_persistence_retains_provenance_evidence_and_review(db_session: Session) -> None:
    captured_at = datetime.now(timezone.utc)
    query = Query(query="bike custom build", source="web", region="Singapore")
    run = DiscoveryRun(query="bike custom build", source="web")
    lead = make_lead("https://example.test")
    candidate = RawCandidate(
        discovery_run=run,
        lead=lead,
        source="web",
        raw_url="https://example.test/source",
        raw_title="Example Bike Studio",
        raw_description="Custom bike builds available",
        captured_at=captured_at,
    )
    evidence = Evidence(
        lead=lead,
        evidence_type=EvidenceType.SERVICE_CLAIM,
        field_name="services",
        value="custom bike build",
        source_text="Custom bike builds available",
        source_url="https://example.test/source",
        captured_at=captured_at,
        confidence=0.95,
    )
    review = Review(
        lead=lead,
        decision=ReviewDecision.ACCEPT,
        reason="Real workshop with visible component work",
    )

    db_session.add_all([query, run, lead, candidate, evidence, review])
    db_session.commit()
    db_session.refresh(lead)

    assert query.id
    assert run.id
    assert lead.score_reasons == ["Provides custom bike builds"]
    assert lead.evidences[0].source_url == "https://example.test/source"
    assert lead.reviews[0].decision is ReviewDecision.ACCEPT
    assert candidate.discovery_run_id == run.id


def test_canonical_url_is_unique_when_present(db_session: Session) -> None:
    db_session.add(make_lead("https://example.test"))
    db_session.commit()

    db_session.add(make_lead("https://example.test"))
    with raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_score_is_constrained_to_the_specified_range(db_session: Session) -> None:
    db_session.add(make_lead("https://example.test/invalid-score", score=101))

    with raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_deleting_a_lead_preserves_raw_candidate_provenance(db_session: Session) -> None:
    run = DiscoveryRun(query="bike workshop", source="web")
    lead = make_lead("https://example.test/preserve-raw")
    candidate = RawCandidate(
        discovery_run=run,
        lead=lead,
        source="web",
        raw_url="https://example.test/preserve-raw/source",
        raw_title="Example Bike Studio",
        captured_at=datetime.now(timezone.utc),
    )
    db_session.add_all([run, lead, candidate])
    db_session.commit()
    candidate_id = candidate.id

    db_session.delete(lead)
    db_session.commit()

    preserved_candidate = db_session.get(RawCandidate, candidate_id)
    assert preserved_candidate is not None
    assert preserved_candidate.lead_id is None


def test_session_scope_commits_and_closes_a_unit_of_work(tmp_path) -> None:
    engine = create_db_engine(f"sqlite:///{(tmp_path / 'scope.db').as_posix()}")
    from app.db import Base

    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        session.add(Query(query="bike repair", source="web"))

    with session_factory() as check_session:
        assert check_session.query(Query).count() == 1

    engine.dispose()

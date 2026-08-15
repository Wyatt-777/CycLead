"""Tests for the human review queue and append-only review history."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import BusinessType, Lead, Review, ReviewStatus
from app.schemas import ReviewInput
from app.services.review_service import (
    LeadNotEligibleForReviewError,
    LeadNotFoundError,
    ReviewService,
)


def add_lead(
    session: Session,
    *,
    name: str,
    score: int,
    business_type: BusinessType = BusinessType.BIKE_WORKSHOP,
    review_status: ReviewStatus = ReviewStatus.NEW,
) -> Lead:
    lead = Lead(
        name=name,
        source="manual_seed",
        source_url=f"https://example.test/{name.casefold().replace(' ', '-')}",
        score=score,
        business_type=business_type,
        review_status=review_status,
    )
    session.add(lead)
    session.flush()
    return lead


def test_review_queue_lists_only_new_qualified_leads_in_score_order(db_session: Session) -> None:
    first = add_lead(db_session, name="First Studio", score=80)
    second = add_lead(db_session, name="Second Studio", score=90)
    add_lead(db_session, name="Low Score Studio", score=59)
    add_lead(
        db_session,
        name="Unrelated Studio",
        score=100,
        business_type=BusinessType.UNRELATED,
    )
    add_lead(
        db_session,
        name="Already Reviewed Studio",
        score=100,
        review_status=ReviewStatus.ACCEPT,
    )

    pending = ReviewService().list_pending(db_session)

    assert [lead.id for lead in pending] == [second.id, first.id]


def test_review_service_appends_history_and_updates_current_review_status(
    db_session: Session,
) -> None:
    lead = add_lead(db_session, name="Example Studio", score=80)
    service = ReviewService()

    first_review = service.record_decision(
        db_session,
        lead.id,
        ReviewInput(decision="CONTACT_LATER", reason="Review again after the next product launch."),
    )
    second_review = service.record_decision(
        db_session,
        lead.id,
        ReviewInput(decision="ACCEPT", reason="Confirmed as a workshop with purchasing potential."),
    )

    assert first_review.decision.value == "CONTACT_LATER"
    assert second_review.decision.value == "ACCEPT"
    assert lead.review_status is ReviewStatus.ACCEPT
    assert db_session.scalar(select(func.count()).select_from(Review)) == 2
    assert ReviewService().list_pending(db_session) == []


def test_review_service_rejects_missing_or_nonqualified_leads(db_session: Session) -> None:
    low_score_lead = add_lead(db_session, name="Low Score Studio", score=59)
    review_input = ReviewInput(decision="REJECT", reason="Insufficient purchase potential.")
    service = ReviewService()

    try:
        service.record_decision(db_session, "missing-lead", review_input)
    except LeadNotFoundError as error:
        assert "lead not found" in str(error)
    else:
        raise AssertionError("Expected LeadNotFoundError")

    try:
        service.record_decision(db_session, low_score_lead.id, review_input)
    except LeadNotEligibleForReviewError as error:
        assert "not eligible" in str(error)
    else:
        raise AssertionError("Expected LeadNotEligibleForReviewError")

    assert db_session.scalar(select(func.count()).select_from(Review)) == 0

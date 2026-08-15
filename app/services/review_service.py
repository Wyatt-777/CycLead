"""Human review queue access and append-only decision recording."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BusinessType, Lead, Review, ReviewStatus
from app.pipeline.qualifier import LeadQualifier
from app.schemas import ReviewInput

LOGGER = logging.getLogger(__name__)


class LeadNotFoundError(LookupError):
    """The requested review target does not exist."""


class LeadNotEligibleForReviewError(ValueError):
    """The requested review target does not meet the current qualification policy."""


class ReviewService:
    """Expose eligible new leads and preserve every manual decision."""

    def __init__(self, qualification_threshold: int = 60) -> None:
        self._qualifier = LeadQualifier(qualification_threshold)

    def list_pending(self, session: Session) -> list[Lead]:
        """Return qualified leads whose current human-review state is still ``NEW``."""

        statement = (
            select(Lead)
            .where(
                Lead.score >= self._qualifier.qualification_threshold,
                Lead.business_type != BusinessType.UNRELATED,
                Lead.review_status == ReviewStatus.NEW,
            )
            .order_by(Lead.score.desc(), Lead.created_at.asc(), Lead.id.asc())
        )
        return list(session.scalars(statement))

    def record_decision(
        self,
        session: Session,
        lead_id: str,
        review_input: ReviewInput,
    ) -> Review:
        """Append one validated manual decision and update the lead's current display status."""

        lead = session.get(Lead, lead_id)
        if lead is None:
            raise LeadNotFoundError(f"lead not found: {lead_id}")

        qualification = self._qualifier.assess(lead)
        if not qualification.qualified:
            raise LeadNotEligibleForReviewError(
                f"lead is not eligible for review: {qualification.reason}"
            )

        review = Review(
            lead_id=lead.id,
            decision=review_input.decision,
            reason=review_input.reason,
        )
        lead.review_status = ReviewStatus(review_input.decision.value)
        session.add(review)
        session.flush()
        LOGGER.info(
            "lead_id=%s stage=review decision=%s review_id=%s",
            lead.id,
            review.decision.value,
            review.id,
        )
        return review

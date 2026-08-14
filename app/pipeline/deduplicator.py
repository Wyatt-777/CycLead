"""Explainable, priority-ordered duplicate detection for normalized lead identities."""

from dataclasses import dataclass

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import DeduplicationStatus, Lead
from app.pipeline.normalizer import NormalizedLeadIdentity


@dataclass(frozen=True, slots=True)
class DeduplicationDecision:
    """The outcome of one deterministic duplicate comparison."""

    status: DeduplicationStatus
    reason: str
    match_key: str | None = None
    matched_lead_id: str | None = None


class LeadDeduplicator:
    """Compare identities using the product's mandated key precedence."""

    def assess(self, session: Session, identity: NormalizedLeadIdentity) -> DeduplicationDecision:
        """Return a duplicate decision without mutating or deleting existing leads."""

        if identity.canonical_url is not None:
            match = self._first_match(
                session, select(Lead).where(Lead.canonical_url == identity.canonical_url)
            )
            if match is not None:
                return self._duplicate(match, "canonical_url")

        if identity.platform is not None and identity.platform_account_id is not None:
            match = self._first_match(
                session,
                select(Lead).where(
                    Lead.platform == identity.platform,
                    Lead.platform_account_id == identity.platform_account_id,
                ),
            )
            if match is not None:
                return self._duplicate(match, "platform + platform_account_id")

        if identity.normalized_phone is not None:
            match = self._first_match(
                session, select(Lead).where(Lead.normalized_phone == identity.normalized_phone)
            )
            if match is not None:
                return self._duplicate(match, "normalized_phone")

        if identity.normalized_email is not None:
            match = self._first_match(
                session, select(Lead).where(Lead.normalized_email == identity.normalized_email)
            )
            if match is not None:
                return self._duplicate(match, "normalized_email")

        if identity.normalized_name is not None and identity.normalized_city is not None:
            match = self._first_match(
                session,
                select(Lead).where(
                    Lead.normalized_name == identity.normalized_name,
                    Lead.normalized_city == identity.normalized_city,
                ),
            )
            if match is not None:
                return DeduplicationDecision(
                    status=DeduplicationStatus.POSSIBLE_DUPLICATE,
                    reason=(
                        "Matched existing lead by normalized business name and city; "
                        "manual review required."
                    ),
                    match_key="normalized_name + normalized_city",
                    matched_lead_id=match.id,
                )

        return DeduplicationDecision(
            status=DeduplicationStatus.NEW,
            reason="No existing lead matched the configured duplicate keys.",
        )

    @staticmethod
    def _first_match(session: Session, statement: Select[tuple[Lead]]) -> Lead | None:
        return session.scalar(statement.order_by(Lead.created_at, Lead.id).limit(1))

    @staticmethod
    def _duplicate(match: Lead, match_key: str) -> DeduplicationDecision:
        return DeduplicationDecision(
            status=DeduplicationStatus.DUPLICATE,
            reason=f"Matched existing lead by {match_key}.",
            match_key=match_key,
            matched_lead_id=match.id,
        )

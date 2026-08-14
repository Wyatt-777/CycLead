"""Lead persistence orchestration with deterministic normalization and deduplication."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import DeduplicationStatus, Lead
from app.pipeline.deduplicator import DeduplicationDecision, LeadDeduplicator
from app.pipeline.normalizer import LeadIdentityInput, NormalizedLeadIdentity, normalize_identity
from app.schemas import LeadInput


@dataclass(frozen=True, slots=True)
class LeadPersistenceResult:
    """State returned after a lead is persisted or identified as an existing duplicate."""

    lead: Lead
    normalized_identity: NormalizedLeadIdentity
    decision: DeduplicationDecision
    created: bool


class LeadPersistenceService:
    """Persist new or possible-duplicate leads while suppressing confirmed duplicates."""

    def __init__(self, deduplicator: LeadDeduplicator | None = None) -> None:
        self._deduplicator = deduplicator or LeadDeduplicator()

    def assess_and_persist(self, session: Session, lead: Lead) -> LeadPersistenceResult:
        """Validate, normalize, deduplicate, and stage a lead without committing the session."""

        self._validate_required_lead_fields(lead)
        identity = self._normalized_identity(lead)
        decision = self._deduplicator.assess(session, identity)

        if decision.status is DeduplicationStatus.DUPLICATE:
            existing_lead = session.get(Lead, decision.matched_lead_id)
            if existing_lead is None:
                raise RuntimeError("Duplicate decision referenced a lead that no longer exists.")
            return LeadPersistenceResult(
                lead=existing_lead,
                normalized_identity=identity,
                decision=decision,
                created=False,
            )

        self._apply_identity(lead, identity)
        session.add(lead)
        session.flush()
        return LeadPersistenceResult(
            lead=lead,
            normalized_identity=identity,
            decision=decision,
            created=True,
        )

    @staticmethod
    def _validate_required_lead_fields(lead: Lead) -> None:
        LeadInput(
            name=lead.name,
            source=lead.source,
            source_url=lead.source_url,
            country=lead.country,
            city=lead.city,
            website=lead.website,
            social_url=lead.social_url,
        )

    @staticmethod
    def _normalized_identity(lead: Lead) -> NormalizedLeadIdentity:
        return normalize_identity(
            LeadIdentityInput(
                source_url=lead.source_url,
                name=lead.name,
                city=lead.city,
                country=lead.country,
                platform=lead.platform,
                platform_account_id=lead.platform_account_id,
                email=lead.email,
                phone=lead.phone,
            )
        )

    @staticmethod
    def _apply_identity(lead: Lead, identity: NormalizedLeadIdentity) -> None:
        lead.canonical_url = identity.canonical_url
        lead.platform = identity.platform
        lead.platform_account_id = identity.platform_account_id
        lead.normalized_email = identity.normalized_email
        lead.normalized_phone = identity.normalized_phone
        lead.normalized_name = identity.normalized_name
        lead.normalized_city = identity.normalized_city

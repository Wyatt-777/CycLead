"""Validation and idempotent persistence for source-backed evidence."""

from collections.abc import Iterable

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import Evidence, Lead
from app.pipeline.evidence import EvidenceDraft
from app.schemas import EvidenceInput


class EvidencePersistenceService:
    """Persist valid evidence once per lead without silently altering source claims."""

    def persist(self, session: Session, lead: Lead, drafts: Iterable[EvidenceDraft]) -> int:
        """Validate and store distinct evidence drafts, returning the created-record count."""

        created_count = 0
        seen_keys: set[tuple[str, str, str | None, str, str]] = set()
        for draft in drafts:
            if draft.deduplication_key in seen_keys:
                continue
            seen_keys.add(draft.deduplication_key)

            evidence_input = EvidenceInput(
                evidence_type=draft.evidence_type,
                field_name=draft.field_name,
                value=draft.value,
                source_text=draft.source_text,
                source_url=draft.source_url,
                captured_at=draft.captured_at,
                confidence=draft.confidence,
            )
            if self._already_persisted(session, lead.id, evidence_input):
                continue

            session.add(
                Evidence(
                    lead_id=lead.id,
                    evidence_type=evidence_input.evidence_type,
                    field_name=evidence_input.field_name,
                    value=evidence_input.value,
                    source_text=evidence_input.source_text,
                    source_url=evidence_input.source_url,
                    captured_at=evidence_input.captured_at,
                    confidence=evidence_input.confidence,
                )
            )
            created_count += 1

        if created_count:
            session.flush()
        return created_count

    @staticmethod
    def _already_persisted(session: Session, lead_id: str, evidence: EvidenceInput) -> bool:
        statement: Select[tuple[Evidence]] = select(Evidence).where(
            Evidence.lead_id == lead_id,
            Evidence.evidence_type == evidence.evidence_type,
            Evidence.field_name == evidence.field_name,
            Evidence.source_text == evidence.source_text,
            Evidence.source_url == evidence.source_url,
        )
        if evidence.value is None:
            statement = statement.where(Evidence.value.is_(None))
        else:
            statement = statement.where(Evidence.value == evidence.value)
        return session.scalar(statement) is not None

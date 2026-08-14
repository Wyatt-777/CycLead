"""Immutable, source-backed evidence produced by pipeline stages."""

from dataclasses import dataclass
from datetime import datetime

from app.models import EvidenceType


@dataclass(frozen=True, slots=True)
class EvidenceDraft:
    """One claim before it is validated and persisted against a lead."""

    evidence_type: EvidenceType
    field_name: str
    value: str | None
    source_text: str
    source_url: str
    captured_at: datetime
    confidence: float

    @property
    def deduplication_key(self) -> tuple[str, str, str | None, str, str]:
        """Return the source-claim identity used to avoid duplicate evidence records."""

        return (
            self.evidence_type.value,
            self.field_name,
            self.value,
            self.source_text,
            self.source_url,
        )

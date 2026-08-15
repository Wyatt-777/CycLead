"""Deterministic Phase 1 qualification decisions for scored leads."""

from dataclasses import dataclass

from app.models import BusinessType, Lead


@dataclass(frozen=True, slots=True)
class QualificationResult:
    """A review-eligibility decision and its human-readable reason."""

    qualified: bool
    threshold: int
    reason: str


class LeadQualifier:
    """Apply the documented threshold without making a human review decision."""

    def __init__(self, qualification_threshold: int = 60) -> None:
        self._qualification_threshold = self._validate_threshold(qualification_threshold)

    @property
    def qualification_threshold(self) -> int:
        """Return the validated score threshold used for every decision."""

        return self._qualification_threshold

    def assess(self, lead: Lead) -> QualificationResult:
        """Return whether a lead is eligible for later human review."""

        if lead.business_type is BusinessType.UNRELATED:
            return QualificationResult(
                qualified=False,
                threshold=self._qualification_threshold,
                reason="business type is UNRELATED",
            )
        if lead.score < self._qualification_threshold:
            return QualificationResult(
                qualified=False,
                threshold=self._qualification_threshold,
                reason=(
                    f"score {lead.score} is below qualification threshold "
                    f"{self._qualification_threshold}"
                ),
            )
        return QualificationResult(
            qualified=True,
            threshold=self._qualification_threshold,
            reason=(
                f"score {lead.score} meets qualification threshold "
                f"{self._qualification_threshold} and business type is eligible"
            ),
        )

    @staticmethod
    def _validate_threshold(value: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
            raise ValueError("qualification_threshold must be an integer from 0 to 100")
        return value

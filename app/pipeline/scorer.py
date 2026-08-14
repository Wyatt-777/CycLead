"""Fixed, evidence-backed Phase 1 lead scoring rules."""

from dataclasses import dataclass
from urllib.parse import urlparse

from app.models import BusinessType, EvidenceType, ScoreBand
from app.pipeline.classifier import ClassificationResult
from app.pipeline.evidence import EvidenceDraft
from app.pipeline.parser import ParsedCandidate

COMMERCIAL_CAP = 30
PRODUCT_CAP = 25
CONTACT_CAP = 20
ACTIVITY_CAP = 10
PURCHASE_CAP = 15

PRODUCT_TERMS = (
    "groupset",
    "wheelset",
    "derailleur",
    "crank",
    "brake",
    "power meter",
    "bicycle components",
)
COMMERCIAL_TYPES = frozenset(
    {
        BusinessType.BIKE_WORKSHOP,
        BusinessType.BIKE_SHOP,
        BusinessType.BIKE_REPAIR,
        BusinessType.BIKE_BUILDER,
        BusinessType.BIKE_DISTRIBUTOR,
        BusinessType.BIKE_BRAND,
        BusinessType.CONTENT_CREATOR_COMMERCIAL,
    }
)
PURCHASE_POINTS = {
    BusinessType.BIKE_WORKSHOP: 15,
    BusinessType.BIKE_BUILDER: 15,
    BusinessType.BIKE_SHOP: 12,
    BusinessType.BIKE_REPAIR: 12,
    BusinessType.BIKE_DISTRIBUTOR: 12,
    BusinessType.BIKE_BRAND: 8,
    BusinessType.CONTENT_CREATOR_COMMERCIAL: 5,
}


def score_band_for(score: int) -> ScoreBand:
    """Return the documented A-D band for a score already bounded to 0-100."""

    if score >= 80:
        return ScoreBand.A
    if score >= 60:
        return ScoreBand.B
    if score >= 40:
        return ScoreBand.C
    return ScoreBand.D


@dataclass(frozen=True, slots=True)
class ScoreReason:
    """A non-zero score contribution paired with its exact evidence record."""

    summary: str
    points: int
    evidence: EvidenceDraft

    @property
    def text(self) -> str:
        """Return the reviewable reason stored on the lead."""

        return f"+{self.points} {self.summary}"


@dataclass(frozen=True, slots=True)
class ScoringResult:
    """The bounded score, A-D band, and explainable non-zero contributions."""

    score: int
    score_band: ScoreBand
    reasons: tuple[ScoreReason, ...]

    @property
    def evidences(self) -> tuple[EvidenceDraft, ...]:
        """Return score evidence in reason order for persistence."""

        return tuple(reason.evidence for reason in self.reasons)


class LeadScorer:
    """Apply the documented v1 scoring contract without inferring missing facts."""

    def score(
        self, candidate: ParsedCandidate, classification: ClassificationResult
    ) -> ScoringResult:
        """Score explicit evidence only and return a value in the 0-100 range."""

        reasons: list[ScoreReason] = []
        self._score_commercial_intent(candidate, classification, reasons)
        self._score_product_relevance(candidate, reasons)
        self._score_contactability(candidate, classification, reasons)
        # Manual Seed does not provide a dated activity claim, so activity remains zero in v1.
        self._score_purchase_potential(classification, reasons)

        total = sum(reason.points for reason in reasons)
        return ScoringResult(
            score=total,
            score_band=score_band_for(total),
            reasons=tuple(reasons),
        )

    def _score_commercial_intent(
        self,
        candidate: ParsedCandidate,
        classification: ClassificationResult,
        reasons: list[ScoreReason],
    ) -> None:
        if candidate.source_text is None or classification.business_type not in COMMERCIAL_TYPES:
            return

        text = candidate.source_text.casefold()
        remaining = COMMERCIAL_CAP
        rules = (
            (
                20,
                (
                    "custom bike build",
                    "custom bicycle build",
                    "bike assembly",
                    "bicycle assembly",
                    "自行车组装",
                ),
                "commercial intent: explicit bicycle assembly or custom-build service",
            ),
            (
                15,
                (
                    "bike repair",
                    "bicycle repair",
                    "bike upgrade",
                    "bicycle upgrade",
                    "自行车维修",
                    "自行车升级",
                ),
                "commercial intent: explicit bicycle repair or upgrade service",
            ),
            (
                15,
                (
                    "bike shop",
                    "bicycle shop",
                    "bike store",
                    "bicycle store",
                    "bike workshop",
                    "bicycle workshop",
                    "自行车店",
                    "自行车工作室",
                ),
                "commercial intent: explicit bicycle shop or workshop",
            ),
        )
        for maximum_points, terms, summary in rules:
            if remaining == 0 or not self._contains_any(text, terms):
                continue
            awarded_points = min(maximum_points, remaining)
            self._append_reason(
                reasons,
                summary,
                awarded_points,
                self._source_evidence(
                    candidate,
                    EvidenceType.SERVICE_CLAIM,
                    "services",
                    self._first_matching_term(text, terms),
                    0.9,
                ),
            )
            remaining -= awarded_points

    def _score_product_relevance(
        self, candidate: ParsedCandidate, reasons: list[ScoreReason]
    ) -> None:
        if candidate.source_text is None:
            return

        text = candidate.source_text.casefold()
        remaining = PRODUCT_CAP
        for product_term in PRODUCT_TERMS:
            if remaining == 0 or product_term not in text:
                continue
            awarded_points = min(5, remaining)
            self._append_reason(
                reasons,
                f"product relevance: mentions {product_term}",
                awarded_points,
                self._source_evidence(
                    candidate,
                    EvidenceType.PRODUCT_CLAIM,
                    "products",
                    product_term,
                    0.9,
                ),
            )
            remaining -= awarded_points

    def _score_contactability(
        self,
        candidate: ParsedCandidate,
        classification: ClassificationResult,
        reasons: list[ScoreReason],
    ) -> None:
        remaining = CONTACT_CAP
        contact_text = self._contact_evidence_text(candidate, candidate.email)
        if contact_text is not None and candidate.email is not None:
            awarded_points = min(8, remaining)
            self._append_reason(
                reasons,
                "contactability: public email appears in supplied source text",
                awarded_points,
                self._contact_evidence(candidate, "email", candidate.email, contact_text),
            )
            remaining -= awarded_points

        contact_text = self._contact_evidence_text(candidate, candidate.phone)
        if remaining and contact_text is not None and candidate.phone is not None:
            awarded_points = min(8, remaining)
            self._append_reason(
                reasons,
                "contactability: public phone appears in supplied source text",
                awarded_points,
                self._contact_evidence(candidate, "phone", candidate.phone, contact_text),
            )
            remaining -= awarded_points

        if remaining and candidate.website and self._is_contact_page(candidate.website):
            awarded_points = min(5, remaining)
            self._append_reason(
                reasons,
                "contactability: supplied website is an explicit contact page",
                awarded_points,
                self._source_evidence(
                    candidate,
                    EvidenceType.CONTACT_CLAIM,
                    "website",
                    candidate.website,
                    0.85,
                    source_text=candidate.website,
                ),
            )
            remaining -= awarded_points

        if (
            remaining
            and candidate.social_url
            and classification.business_type in COMMERCIAL_TYPES
        ):
            awarded_points = min(5, remaining)
            self._append_reason(
                reasons,
                "contactability: supplied public social profile for an explicit business",
                awarded_points,
                self._source_evidence(
                    candidate,
                    EvidenceType.CONTACT_CLAIM,
                    "social_url",
                    candidate.social_url,
                    0.8,
                    source_text=candidate.social_url,
                ),
            )

    def _score_purchase_potential(
        self, classification: ClassificationResult, reasons: list[ScoreReason]
    ) -> None:
        points = PURCHASE_POINTS.get(classification.business_type, 0)
        if points == 0 or classification.evidence is None:
            return
        self._append_reason(
            reasons,
            f"purchase potential: explicit {classification.business_type.value} business type",
            min(points, PURCHASE_CAP),
            classification.evidence,
        )

    @staticmethod
    def _append_reason(
        reasons: list[ScoreReason], summary: str, points: int, evidence: EvidenceDraft
    ) -> None:
        if points <= 0:
            return
        reasons.append(ScoreReason(summary=summary, points=points, evidence=evidence))

    @staticmethod
    def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
        return any(term.casefold() in text for term in terms)

    @staticmethod
    def _first_matching_term(text: str, terms: tuple[str, ...]) -> str:
        return next(term for term in terms if term.casefold() in text)

    @staticmethod
    def _source_evidence(
        candidate: ParsedCandidate,
        evidence_type: EvidenceType,
        field_name: str,
        value: str,
        confidence: float,
        source_text: str | None = None,
    ) -> EvidenceDraft:
        return EvidenceDraft(
            evidence_type=evidence_type,
            field_name=field_name,
            value=value,
            source_text=source_text or candidate.source_text or "",
            source_url=candidate.source_url,
            captured_at=candidate.captured_at,
            confidence=confidence,
        )

    @classmethod
    def _contact_evidence(
        cls,
        candidate: ParsedCandidate,
        field_name: str,
        value: str,
        source_text: str,
    ) -> EvidenceDraft:
        return cls._source_evidence(
            candidate,
            EvidenceType.CONTACT_CLAIM,
            field_name,
            value,
            0.9,
            source_text=source_text,
        )

    @staticmethod
    def _contact_evidence_text(candidate: ParsedCandidate, value: str | None) -> str | None:
        if value is None:
            return None
        for source_text in (candidate.raw_contact_text, candidate.source_text):
            if source_text and value.casefold() in source_text.casefold():
                return source_text
        return None

    @staticmethod
    def _is_contact_page(website: str) -> bool:
        parsed = urlparse(website)
        url_text = f"{parsed.path}?{parsed.query}".casefold()
        return any(term in url_text for term in ("contact", "contact-us", "联系", "联系我们"))

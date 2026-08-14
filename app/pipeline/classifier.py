"""Conservative, explainable business-type classification for Phase 1 leads."""

from dataclasses import dataclass

from app.models import BusinessType, EvidenceType
from app.pipeline.evidence import EvidenceDraft
from app.pipeline.parser import ParsedCandidate

BIKE_TERMS = ("bike", "bicycle", "自行车", "单车")
CREATOR_TERMS = ("creator", "influencer", "youtube", "youtuber", "channel", "博主", "创作者")
UNRELATED_TERMS = (
    "restaurant",
    "cafe",
    "hotel",
    "real estate",
    "salon",
    "bakery",
    "餐厅",
    "咖啡",
    "酒店",
    "房地产",
)


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    """The selected business type and its supporting source claim, when available."""

    business_type: BusinessType
    evidence: EvidenceDraft | None


@dataclass(frozen=True, slots=True)
class _ClassificationRule:
    business_type: BusinessType
    terms: tuple[str, ...]


class LeadClassifier:
    """Classify only explicit source text; insufficient evidence remains ``UNKNOWN``."""

    _BIKE_BUSINESS_RULES = (
        _ClassificationRule(
            BusinessType.BIKE_BUILDER,
            ("frame builder", "bike builder", "bicycle builder", "自行车制造", "车架制造"),
        ),
        _ClassificationRule(
            BusinessType.BIKE_DISTRIBUTOR,
            (
                "bike distributor",
                "bicycle distributor",
                "bicycle wholesale",
                "自行车经销",
                "自行车批发",
            ),
        ),
        _ClassificationRule(
            BusinessType.BIKE_BRAND,
            (
                "bike brand",
                "bicycle brand",
                "bike manufacturer",
                "bicycle manufacturer",
                "自行车品牌",
            ),
        ),
        _ClassificationRule(
            BusinessType.BIKE_WORKSHOP,
            (
                "bike workshop",
                "bicycle workshop",
                "custom bike build",
                "custom bicycle build",
                "bike fitting",
                "自行车工作室",
                "自行车组装",
            ),
        ),
        _ClassificationRule(
            BusinessType.BIKE_REPAIR,
            (
                "bike repair",
                "bicycle repair",
                "bike maintenance",
                "bicycle maintenance",
                "自行车维修",
                "单车维修",
            ),
        ),
        _ClassificationRule(
            BusinessType.BIKE_SHOP,
            ("bike shop", "bicycle shop", "bike store", "bicycle store", "自行车店", "单车店"),
        ),
    )
    _COMMERCIAL_TERMS = (
        "custom bike build",
        "custom bicycle build",
        "bike repair",
        "bicycle repair",
        "bike fitting",
        "bike shop",
        "bicycle shop",
        "workshop",
        "studio",
        "咨询",
        "定制",
        "维修",
        "组装",
    )

    def classify(self, candidate: ParsedCandidate) -> ClassificationResult:
        """Return one enum value, using a claim only when text explicitly supports it."""

        source_text = candidate.source_text
        if not source_text:
            return ClassificationResult(BusinessType.UNKNOWN, None)

        normalized_text = source_text.casefold()
        has_bike_context = self._contains_any(normalized_text, BIKE_TERMS)
        if not has_bike_context and self._contains_any(normalized_text, UNRELATED_TERMS):
            return self._result(BusinessType.UNRELATED, candidate)

        has_creator_signal = self._contains_any(normalized_text, CREATOR_TERMS)
        if has_bike_context and has_creator_signal and self._contains_any(
            normalized_text, self._COMMERCIAL_TERMS
        ):
            return self._result(
                BusinessType.CONTENT_CREATOR_COMMERCIAL,
                candidate,
            )

        if has_bike_context:
            for rule in self._BIKE_BUSINESS_RULES:
                if self._contains_any(normalized_text, rule.terms):
                    return self._result(rule.business_type, candidate)

            if has_creator_signal:
                return self._result(
                    BusinessType.CONTENT_CREATOR_ONLY,
                    candidate,
                )

        return ClassificationResult(BusinessType.UNKNOWN, None)

    @staticmethod
    def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
        return any(term.casefold() in text for term in terms)

    @staticmethod
    def _result(business_type: BusinessType, candidate: ParsedCandidate) -> ClassificationResult:
        if candidate.source_text is None:
            return ClassificationResult(BusinessType.UNKNOWN, None)
        return ClassificationResult(
            business_type=business_type,
            evidence=EvidenceDraft(
                evidence_type=EvidenceType.BUSINESS_TYPE_CLAIM,
                field_name="business_type",
                value=business_type.value,
                source_text=candidate.source_text,
                source_url=candidate.source_url,
                captured_at=candidate.captured_at,
                confidence=0.9 if business_type is not BusinessType.UNKNOWN else 0.0,
            ),
        )

"""Conservative candidate parsing for structured manual-source data."""

from dataclasses import dataclass
from datetime import datetime

from app.sources.base import RawCandidateData


class CandidateParseError(ValueError):
    """A raw candidate lacks the minimum data needed to form a lead candidate."""


@dataclass(frozen=True, slots=True)
class ParsedCandidate:
    """Fields extracted without inventing unknown business information."""

    name: str
    description: str | None
    country: str | None
    city: str | None
    website: str | None
    social_url: str | None
    email: str | None
    phone: str | None
    services: tuple[str, ...]
    source: str
    source_url: str
    source_text: str | None
    captured_at: datetime


class CandidateParser:
    """Parse known structured fields and use source title only as an explicit name fallback."""

    def parse(self, raw_candidate: RawCandidateData) -> ParsedCandidate:
        """Return a parsed candidate or a specific error without guessing any field."""

        name = raw_candidate.name or raw_candidate.title
        if not name.strip():
            raise CandidateParseError("candidate has no usable name or title")

        return ParsedCandidate(
            name=name,
            description=raw_candidate.description or raw_candidate.snippet,
            country=raw_candidate.country,
            city=raw_candidate.city,
            website=raw_candidate.website,
            social_url=raw_candidate.social_url,
            email=raw_candidate.email,
            phone=raw_candidate.phone,
            services=tuple(raw_candidate.services),
            source=raw_candidate.source,
            source_url=raw_candidate.url,
            source_text=raw_candidate.snippet,
            captured_at=raw_candidate.captured_at,
        )

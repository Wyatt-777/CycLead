"""Pydantic contracts at service boundaries before persistence or pipeline work."""

from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import EvidenceType, ReviewDecision


class InputModel(BaseModel):
    """Base input contract that strips surrounding whitespace and rejects unknown fields."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def validate_public_url(value: str | None) -> str | None:
    """Accept only absolute HTTP(S) URLs without fetching or enriching them."""

    if value is None:
        return None

    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("must be an absolute HTTP(S) URL")
    return value


class DiscoveryRunInput(InputModel):
    query: str = Field(min_length=1, max_length=500)
    source: str = Field(min_length=1, max_length=64)


class RawCandidateInput(InputModel):
    source: str = Field(min_length=1, max_length=64)
    url: str = Field(min_length=1)
    title: str = Field(min_length=1)
    snippet: str | None = None
    raw_contact_text: str | None = None
    captured_at: datetime

    validate_url = field_validator("url")(validate_public_url)


class LeadInput(InputModel):
    name: str = Field(min_length=1, max_length=500)
    source: str = Field(min_length=1, max_length=64)
    source_url: str = Field(min_length=1)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    city: str | None = Field(default=None, max_length=128)
    website: str | None = None
    social_url: str | None = None

    validate_source_url = field_validator("source_url")(validate_public_url)
    validate_website = field_validator("website")(validate_public_url)
    validate_social_url = field_validator("social_url")(validate_public_url)


class EvidenceInput(InputModel):
    evidence_type: EvidenceType
    field_name: str = Field(min_length=1, max_length=128)
    value: str | None = None
    source_text: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    captured_at: datetime
    confidence: float = Field(ge=0, le=1)

    validate_source_url = field_validator("source_url")(validate_public_url)


class ReviewInput(InputModel):
    decision: ReviewDecision
    reason: str = Field(min_length=1)

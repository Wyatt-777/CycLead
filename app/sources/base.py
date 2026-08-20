"""Source-adapter contracts for publicly supplied lead candidates."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class SourceDiscoveryError(ValueError):
    """A source request or response failed before it produced a candidate collection."""


class RawCandidateData(BaseModel):
    """Source output retained before parsing and normalization."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source: str = Field(min_length=1, max_length=64)
    url: str = Field(min_length=1)
    title: str = Field(min_length=1)
    snippet: str | None = None
    captured_at: datetime
    name: str | None = Field(default=None, max_length=500)
    description: str | None = None
    country: str | None = Field(default=None, min_length=2, max_length=2)
    city: str | None = Field(default=None, max_length=128)
    website: str | None = None
    social_url: str | None = None
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=64)
    raw_contact_text: str | None = None
    services: list[str] = Field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SourceRecordError:
    """One source record that could not be converted into a raw candidate."""

    record_index: int | None
    message: str


@dataclass(slots=True)
class SourceDiscoveryResult:
    """Candidates and recoverable record-level source errors from one discovery call."""

    candidates: list[RawCandidateData] = field(default_factory=list)
    errors: list[SourceRecordError] = field(default_factory=list)


class LeadSource(Protocol):
    """Stable adapter boundary that isolates source-specific collection from the pipeline."""

    source_name: str

    def discover(self) -> SourceDiscoveryResult:
        """Return public raw candidates and recoverable record errors."""

"""Source adapters permitted by the CycleLead MVP."""

from app.sources.base import (
    LeadSource,
    RawCandidateData,
    SourceDiscoveryError,
    SourceDiscoveryResult,
    SourceRecordError,
)
from app.sources.brave_search import (
    BraveSearchConfigurationError,
    BraveSearchRequestError,
    BraveSearchResponseError,
    BraveSearchSource,
)
from app.sources.manual_seed import ManualSeedFileError, ManualSeedSource

__all__ = [
    "LeadSource",
    "BraveSearchConfigurationError",
    "BraveSearchRequestError",
    "BraveSearchResponseError",
    "BraveSearchSource",
    "ManualSeedFileError",
    "ManualSeedSource",
    "RawCandidateData",
    "SourceDiscoveryError",
    "SourceDiscoveryResult",
    "SourceRecordError",
]

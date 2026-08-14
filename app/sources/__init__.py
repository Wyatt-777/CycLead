"""Source adapters permitted by the CycleLead MVP."""

from app.sources.base import LeadSource, RawCandidateData, SourceDiscoveryResult, SourceRecordError
from app.sources.manual_seed import ManualSeedFileError, ManualSeedSource

__all__ = [
    "LeadSource",
    "ManualSeedFileError",
    "ManualSeedSource",
    "RawCandidateData",
    "SourceDiscoveryResult",
    "SourceRecordError",
]

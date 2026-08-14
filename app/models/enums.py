"""Closed business-state enumerations used by persistence and validation layers."""

from enum import StrEnum


class BusinessType(StrEnum):
    BIKE_WORKSHOP = "BIKE_WORKSHOP"
    BIKE_SHOP = "BIKE_SHOP"
    BIKE_REPAIR = "BIKE_REPAIR"
    BIKE_BUILDER = "BIKE_BUILDER"
    BIKE_DISTRIBUTOR = "BIKE_DISTRIBUTOR"
    BIKE_BRAND = "BIKE_BRAND"
    CONTENT_CREATOR_COMMERCIAL = "CONTENT_CREATOR_COMMERCIAL"
    CONTENT_CREATOR_ONLY = "CONTENT_CREATOR_ONLY"
    UNRELATED = "UNRELATED"
    UNKNOWN = "UNKNOWN"


class ScoreBand(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class ReviewStatus(StrEnum):
    NEW = "NEW"
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    CONTACT_LATER = "CONTACT_LATER"


class ReviewDecision(StrEnum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    CONTACT_LATER = "CONTACT_LATER"


class DiscoveryRunStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL_FAILURE = "PARTIAL_FAILURE"
    FAILED = "FAILED"


class CandidateProcessingStatus(StrEnum):
    DISCOVERED = "DISCOVERED"
    PARSED = "PARSED"
    ERROR = "ERROR"


class DeduplicationStatus(StrEnum):
    NEW = "NEW"
    DUPLICATE = "DUPLICATE"
    POSSIBLE_DUPLICATE = "POSSIBLE_DUPLICATE"


class EvidenceType(StrEnum):
    SERVICE_CLAIM = "SERVICE_CLAIM"
    PRODUCT_CLAIM = "PRODUCT_CLAIM"
    CONTACT_CLAIM = "CONTACT_CLAIM"
    ACTIVITY_CLAIM = "ACTIVITY_CLAIM"
    BUSINESS_TYPE_CLAIM = "BUSINESS_TYPE_CLAIM"

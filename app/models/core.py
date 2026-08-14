"""SQLAlchemy models for CycleLead's Phase 1 persistence foundation."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SqlEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import (
    BusinessType,
    CandidateProcessingStatus,
    DiscoveryRunStatus,
    EvidenceType,
    ReviewDecision,
    ReviewStatus,
    ScoreBand,
)


def utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp for application-managed records."""

    return datetime.now(timezone.utc)


def uuid_string() -> str:
    """Generate a UUID string without relying on database-specific functions."""

    return str(uuid4())


def enum_column(enum_class: type) -> SqlEnum:
    """Store StrEnum values as checked strings on SQLite and other supported databases."""

    return SqlEnum(
        enum_class,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda enum_values: [item.value for item in enum_values],
    )


class TimestampedRecord:
    """Shared timestamps for entities with an independent lifecycle."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Query(TimestampedRecord, Base):
    """A reusable discovery seed with optional geographic scope."""

    __tablename__ = "queries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    query: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    region: Mapped[str | None] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class DiscoveryRun(Base):
    """Observable execution record for a single source discovery attempt."""

    __tablename__ = "discovery_runs"
    __table_args__ = (
        CheckConstraint(
            "discovered_count >= 0", name="ck_discovery_runs_discovered_count_nonnegative"
        ),
        CheckConstraint("parsed_count >= 0", name="ck_discovery_runs_parsed_count_nonnegative"),
        CheckConstraint(
            "duplicate_count >= 0", name="ck_discovery_runs_duplicate_count_nonnegative"
        ),
        CheckConstraint(
            "qualified_count >= 0", name="ck_discovery_runs_qualified_count_nonnegative"
        ),
        CheckConstraint(
            "rejected_count >= 0", name="ck_discovery_runs_rejected_count_nonnegative"
        ),
        CheckConstraint("error_count >= 0", name="ck_discovery_runs_error_count_nonnegative"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    query: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[DiscoveryRunStatus] = mapped_column(
        enum_column(DiscoveryRunStatus), default=DiscoveryRunStatus.RUNNING, nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discovered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    parsed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    qualified_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    raw_candidates: Mapped[list["RawCandidate"]] = relationship(back_populates="discovery_run")


class Lead(TimestampedRecord, Base):
    """A normalized, scored lead retained for human review."""

    __tablename__ = "leads"
    __table_args__ = (CheckConstraint("score >= 0 AND score <= 100", name="ck_leads_score_range"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    business_type: Mapped[BusinessType] = mapped_column(
        enum_column(BusinessType), default=BusinessType.UNKNOWN, nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(String(2))
    city: Mapped[str | None] = mapped_column(String(128))
    website: Mapped[str | None] = mapped_column(Text)
    social_url: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(Text, unique=True)
    platform: Mapped[str | None] = mapped_column(String(64))
    platform_account_id: Mapped[str | None] = mapped_column(String(256))
    normalized_email: Mapped[str | None] = mapped_column(String(320))
    normalized_phone: Mapped[str | None] = mapped_column(String(64))
    normalized_name: Mapped[str | None] = mapped_column(String(500))
    normalized_city: Mapped[str | None] = mapped_column(String(128))
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    score_band: Mapped[ScoreBand] = mapped_column(
        enum_column(ScoreBand), default=ScoreBand.D, nullable=False
    )
    score_reasons: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    review_status: Mapped[ReviewStatus] = mapped_column(
        enum_column(ReviewStatus), default=ReviewStatus.NEW, nullable=False
    )

    evidences: Mapped[list["Evidence"]] = relationship(back_populates="lead")
    reviews: Mapped[list["Review"]] = relationship(back_populates="lead")
    raw_candidates: Mapped[list["RawCandidate"]] = relationship(
        back_populates="lead", passive_deletes=True
    )


class RawCandidate(Base):
    """Unmodified source output retained for parser diagnosis and provenance."""

    __tablename__ = "raw_candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    discovery_run_id: Mapped[str] = mapped_column(
        ForeignKey("discovery_runs.id", ondelete="RESTRICT"), nullable=False
    )
    lead_id: Mapped[str | None] = mapped_column(ForeignKey("leads.id", ondelete="SET NULL"))
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_url: Mapped[str] = mapped_column(Text, nullable=False)
    raw_title: Mapped[str] = mapped_column(Text, nullable=False)
    raw_description: Mapped[str | None] = mapped_column(Text)
    raw_contact_text: Mapped[str | None] = mapped_column(Text)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processing_status: Mapped[CandidateProcessingStatus] = mapped_column(
        enum_column(CandidateProcessingStatus),
        default=CandidateProcessingStatus.DISCOVERED,
        nullable=False,
    )
    error_detail: Mapped[str | None] = mapped_column(Text)

    discovery_run: Mapped[DiscoveryRun] = relationship(back_populates="raw_candidates")
    lead: Mapped[Lead | None] = relationship(back_populates="raw_candidates")


class Evidence(Base):
    """A verifiable source claim supporting a lead field or score reason."""

    __tablename__ = "evidences"
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="ck_evidences_confidence_range"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    lead_id: Mapped[str] = mapped_column(
        ForeignKey("leads.id", ondelete="RESTRICT"), nullable=False
    )
    evidence_type: Mapped[EvidenceType] = mapped_column(enum_column(EvidenceType), nullable=False)
    field_name: Mapped[str] = mapped_column("field", String(128), nullable=False)
    value: Mapped[str | None] = mapped_column(Text)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    lead: Mapped[Lead] = relationship(back_populates="evidences")


class Review(Base):
    """An append-only human qualification decision for a lead."""

    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    lead_id: Mapped[str] = mapped_column(
        ForeignKey("leads.id", ondelete="RESTRICT"), nullable=False
    )
    decision: Mapped[ReviewDecision] = mapped_column(enum_column(ReviewDecision), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    lead: Mapped[Lead] = relationship(back_populates="reviews")

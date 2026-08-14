"""Create CycleLead Phase 1 persistence tables.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def enum_type(*values: str, name: str) -> sa.Enum:
    """Represent fixed states as checked strings for SQLite compatibility."""

    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True)


def upgrade() -> None:
    op.create_table(
        "queries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("query", sa.String(length=500), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("region", sa.String(length=128), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "discovery_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("query", sa.String(length=500), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            enum_type(
                "RUNNING", "SUCCESS", "PARTIAL_FAILURE", "FAILED", name="discovery_run_status"
            ),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discovered_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("parsed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("qualified_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint(
            "discovered_count >= 0", name="ck_discovery_runs_discovered_count_nonnegative"
        ),
        sa.CheckConstraint("parsed_count >= 0", name="ck_discovery_runs_parsed_count_nonnegative"),
        sa.CheckConstraint(
            "duplicate_count >= 0", name="ck_discovery_runs_duplicate_count_nonnegative"
        ),
        sa.CheckConstraint(
            "qualified_count >= 0", name="ck_discovery_runs_qualified_count_nonnegative"
        ),
        sa.CheckConstraint(
            "rejected_count >= 0", name="ck_discovery_runs_rejected_count_nonnegative"
        ),
        sa.CheckConstraint("error_count >= 0", name="ck_discovery_runs_error_count_nonnegative"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "leads",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column(
            "business_type",
            enum_type(
                "BIKE_WORKSHOP",
                "BIKE_SHOP",
                "BIKE_REPAIR",
                "BIKE_BUILDER",
                "BIKE_DISTRIBUTOR",
                "BIKE_BRAND",
                "CONTENT_CREATOR_COMMERCIAL",
                "CONTENT_CREATOR_ONLY",
                "UNRELATED",
                "UNKNOWN",
                name="business_type",
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("website", sa.Text(), nullable=True),
        sa.Column("social_url", sa.Text(), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("platform", sa.String(length=64), nullable=True),
        sa.Column("platform_account_id", sa.String(length=256), nullable=True),
        sa.Column("normalized_email", sa.String(length=320), nullable=True),
        sa.Column("normalized_phone", sa.String(length=64), nullable=True),
        sa.Column("normalized_name", sa.String(length=500), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("score_band", enum_type("A", "B", "C", "D", name="score_band"), nullable=False),
        sa.Column("score_reasons", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "review_status",
            enum_type("NEW", "ACCEPT", "REJECT", "CONTACT_LATER", name="review_status"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint("score >= 0 AND score <= 100", name="ck_leads_score_range"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("canonical_url"),
    )
    op.create_table(
        "raw_candidates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("discovery_run_id", sa.String(length=36), nullable=False),
        sa.Column("lead_id", sa.String(length=36), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("raw_url", sa.Text(), nullable=False),
        sa.Column("raw_title", sa.Text(), nullable=False),
        sa.Column("raw_description", sa.Text(), nullable=True),
        sa.Column("raw_contact_text", sa.Text(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "processing_status",
            enum_type("DISCOVERED", "PARSED", "ERROR", name="candidate_processing_status"),
            nullable=False,
        ),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["discovery_run_id"], ["discovery_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "evidences",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("lead_id", sa.String(length=36), nullable=False),
        sa.Column(
            "evidence_type",
            enum_type(
                "SERVICE_CLAIM",
                "PRODUCT_CLAIM",
                "CONTACT_CLAIM",
                "ACTIVITY_CLAIM",
                "BUSINESS_TYPE_CLAIM",
                name="evidence_type",
            ),
            nullable=False,
        ),
        sa.Column("field", sa.String(length=128), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="ck_evidences_confidence_range"
        ),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "reviews",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("lead_id", sa.String(length=36), nullable=False),
        sa.Column(
            "decision",
            enum_type("ACCEPT", "REJECT", "CONTACT_LATER", name="review_decision"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("reviews")
    op.drop_table("evidences")
    op.drop_table("raw_candidates")
    op.drop_table("leads")
    op.drop_table("discovery_runs")
    op.drop_table("queries")

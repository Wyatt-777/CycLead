"""Add normalized city for conservative name-and-location duplicate matching.

Revision ID: 0002_add_normalized_city
Revises: 0001_initial_schema
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_add_normalized_city"
down_revision: str | Sequence[str] | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("normalized_city", sa.String(length=128), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("leads") as batch_op:
        batch_op.drop_column("normalized_city")

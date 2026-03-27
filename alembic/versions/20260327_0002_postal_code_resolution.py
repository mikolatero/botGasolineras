"""Add resolved postal code support."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260327_0002"
down_revision = "20260325_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stations", sa.Column("postal_code_resolved", sa.String(length=10), nullable=True))
    op.add_column("stations", sa.Column("postal_code_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_stations_postal_code_resolved", "stations", ["postal_code_resolved"])


def downgrade() -> None:
    op.drop_index("ix_stations_postal_code_resolved", table_name="stations")
    op.drop_column("stations", "postal_code_checked_at")
    op.drop_column("stations", "postal_code_resolved")

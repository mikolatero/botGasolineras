"""Add cached postal code locations."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260327_0003"
down_revision = "20260327_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "postal_code_locations",
        sa.Column("postal_code", sa.String(length=10), primary_key=True),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_postal_code_locations_postal_code", "postal_code_locations", ["postal_code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_postal_code_locations_postal_code", table_name="postal_code_locations")
    op.drop_table("postal_code_locations")

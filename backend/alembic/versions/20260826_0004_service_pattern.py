"""per-service test pattern and hero image

The initial written test differs by service -- the Army tests General Knowledge
and Islamiat, the PAF does not test General Knowledge at all and adds Physics,
and the Navy weights intelligence three to one towards non-verbal. Storing the
pattern lets the service hub explain that difference instead of implying the
three are interchangeable.

Revision ID: 0004_service_pattern
Revises: 0003_gto_venue
Created: 2026-08-26
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004_service_pattern"
down_revision: str | None = "0003_gto_venue"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("services", sa.Column("hero_url", sa.String(length=400), nullable=True))
    op.add_column(
        "services",
        sa.Column(
            "test_pattern",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("services", "test_pattern")
    op.drop_column("services", "hero_url")

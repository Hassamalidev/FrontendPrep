"""answer sheet uploads and PPDT

Adds provenance to a psychological sitting: whether the responses were typed
under the platform's clock or transcribed from a photographed answer sheet, and
what the transcription pass reported.

The image itself is never stored -- uploads are decoded in memory and dropped --
so there is no blob column here by design.

Revision ID: 0002_answer_sheets
Revises: 0001_initial
Created: 2026-08-26
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_answer_sheets"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "psych_sessions",
        sa.Column(
            "source",
            sa.Enum(
                "online",
                "sheet",
                "import",
                name="psych_session_source",
                native_enum=False,
                length=32,
            ),
            nullable=False,
            server_default="online",
        ),
    )
    op.add_column(
        "psych_sessions",
        sa.Column(
            "transcription",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("psych_sessions", "transcription")
    op.drop_column("psych_sessions", "source")

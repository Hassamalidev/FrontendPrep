"""split the GTO series into indoor and outdoor

The series is conducted in two halves that candidates prepare for differently:
indoor tasks are verbal and written and can be rehearsed at a desk, outdoor
tasks are physical and equipment-bound. Storing the venue rather than deriving
it at query time lets the two halves be listed and indexed separately.

Existing rows are backfilled from their task type.

Revision ID: 0003_gto_venue
Revises: 0002_answer_sheets
Created: 2026-08-26
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0003_gto_venue"
down_revision: str | None = "0002_answer_sheets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDOOR = ("group_discussion", "lecturette", "group_planning")


def upgrade() -> None:
    op.add_column(
        "gto_tasks",
        sa.Column(
            "venue",
            sa.Enum("indoor", "outdoor", name="gto_venue", native_enum=False, length=32),
            nullable=False,
            server_default="outdoor",
        ),
    )
    # Backfill: everything defaulted to outdoor, so only the indoor three move.
    op.execute(
        sa.text(
            "UPDATE gto_tasks SET venue = 'indoor' WHERE task_type IN "
            "('group_discussion', 'lecturette', 'group_planning')"
        )
    )
    op.create_index(
        "ix_gto_tasks_venue", "gto_tasks", ["venue", "status", "sort_order"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_gto_tasks_venue", table_name="gto_tasks")
    op.drop_column("gto_tasks", "venue")

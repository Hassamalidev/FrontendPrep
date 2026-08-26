"""Audit trail helper.

Staff writes go through here so every mutation has one row explaining who did
what. Deliberately queued on the caller's session: an audit write must never be
the reason a legitimate action fails.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import AuditLog


def record(
    db: AsyncSession,
    *,
    actor_id: int | None,
    action: str,
    entity: str,
    entity_id: str | int | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    """Queue an audit row on the current session, flushed with the caller's commit."""
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action[:64],
            entity=entity[:48],
            entity_id=str(entity_id)[:48] if entity_id is not None else None,
            detail=detail or {},
        )
    )

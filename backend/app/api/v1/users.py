"""Profile, stats, dashboard and the physical-training log."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession, PageParams
from app.models.assessment import PhysicalLog
from app.models.catalog import Program
from app.schemas.assessment import PhysicalLogIn, PhysicalLogOut, PhysicalProgressOut
from app.schemas.auth import UserPublic
from app.schemas.common import Page
from app.schemas.user import DashboardOut, ProfileUpdate, UserStatsOut
from app.services import auth_service, dashboard_service

router = APIRouter(prefix="/me", tags=["me"])


@router.patch("", response_model=UserPublic)
async def update_profile(data: ProfileUpdate, db: DbSession, user: CurrentUser) -> UserPublic:
    changes = data.model_dump(exclude_unset=True)
    preferences = changes.pop("preferences", None)
    for field, value in changes.items():
        setattr(user, field, value)
    if preferences is not None:
        # Merge rather than replace: the client sends only the keys it changed.
        user.preferences = {**(user.preferences or {}), **preferences}
    await db.commit()
    await db.refresh(user)
    return UserPublic.model_validate(user)


@router.get("/stats", response_model=UserStatsOut)
async def my_stats(db: DbSession, user: CurrentUser) -> UserStatsOut:
    stats = await auth_service.ensure_stats(db, user.id)
    await db.commit()
    return UserStatsOut.model_validate(stats)


@router.get("/dashboard", response_model=DashboardOut)
async def dashboard(db: DbSession, user: CurrentUser) -> DashboardOut:
    """The whole signed-in landing page in one request."""
    return DashboardOut(**await dashboard_service.build(db, user))


# --- Physical training -----------------------------------------------------


@router.post("/physical", response_model=PhysicalLogOut, status_code=201)
async def log_physical(data: PhysicalLogIn, db: DbSession, user: CurrentUser) -> PhysicalLogOut:
    row = PhysicalLog(
        user_id=user.id,
        logged_on=data.logged_on or datetime.now(UTC),
        metrics=data.metrics,
        note=data.note,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return PhysicalLogOut.model_validate(row)


@router.get("/physical", response_model=Page[PhysicalLogOut])
async def physical_history(
    db: DbSession, user: CurrentUser, page: PageParams
) -> Page[PhysicalLogOut]:
    stmt = select(PhysicalLog).where(PhysicalLog.user_id == user.id)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = await db.scalars(
        stmt.order_by(PhysicalLog.logged_on.desc()).offset(page.offset).limit(page.limit)
    )
    return Page.build(
        [PhysicalLogOut.model_validate(r) for r in rows], total, page.page, page.size
    )


@router.get("/physical/progress", response_model=PhysicalProgressOut)
async def physical_progress(
    db: DbSession,
    user: CurrentUser,
    program_id: Annotated[int | None, Query()] = None,
) -> PhysicalProgressOut:
    """Latest metrics measured against the target program's standards."""
    logs = list(
        await db.scalars(
            select(PhysicalLog)
            .where(PhysicalLog.user_id == user.id)
            .order_by(PhysicalLog.logged_on.desc())
            .limit(30)
        )
    )

    target_id = program_id or user.target_program_id
    program = await db.get(Program, target_id) if target_id else None
    standards = (program.physical_standards if program else {}) or {}

    latest: dict = {}
    for log in reversed(logs):  # oldest first, so newer values win
        latest.update(log.metrics or {})

    gaps: list[dict] = []
    for key, target in standards.items():
        current = latest.get(key)
        if current is None or not isinstance(target, (int, float)):
            continue
        # Times are pass-if-lower; counts are pass-if-higher.
        lower_is_better = "sec" in key or "time" in key
        met = current <= target if lower_is_better else current >= target
        gaps.append(
            {
                "metric": key,
                "current": current,
                "target": target,
                "met": met,
                "delta": round(abs(current - target), 2),
            }
        )

    bmi = None
    height = float(user.height_cm) if user.height_cm else None
    weight = latest.get("weight_kg") or (float(user.weight_kg) if user.weight_kg else None)
    if height and weight:
        bmi = round(float(weight) / ((height / 100) ** 2), 1)

    return PhysicalProgressOut(
        logs=[PhysicalLogOut.model_validate(r) for r in logs],
        standards=standards,
        latest=latest,
        gaps=gaps,
        bmi=bmi,
    )

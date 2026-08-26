"""Assembles the signed-in landing page in one round trip.

A dashboard that makes eight requests feels slow on a Pakistani mobile
connection and costs eight connections from a pool of five. So this builds the
whole payload server-side, leaning on the denormalised ``user_stats`` row rather
than aggregating attempts on the fly.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AttemptStatus
from app.models.assessment import Attempt, PracticeCard
from app.models.catalog import Module, Stage, Topic
from app.models.user import User, UserStats
from app.schemas.user import UserStatsOut
from app.services import content_service


async def build(db: AsyncSession, user: User) -> dict:
    now = datetime.now(UTC)

    stats = await db.get(UserStats, user.id)
    if stats is None:
        stats = UserStats(user_id=user.id)
        db.add(stats)
        await db.commit()
        await db.refresh(stats)

    recent = list(
        await db.scalars(
            select(Attempt)
            .where(Attempt.user_id == user.id, Attempt.status == AttemptStatus.SUBMITTED)
            .order_by(Attempt.submitted_at.desc())
            .limit(5)
        )
    )

    due = (
        await db.scalar(
            select(func.count())
            .select_from(PracticeCard)
            .where(PracticeCard.user_id == user.id, PracticeCard.due_on <= now)
        )
        or 0
    )

    in_progress = await db.scalar(
        select(Attempt)
        .where(Attempt.user_id == user.id, Attempt.status == AttemptStatus.IN_PROGRESS)
        .order_by(Attempt.started_at.desc())
        .limit(1)
    )

    return {
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": str(user.role),
            "target_service": str(user.target_service) if user.target_service else None,
            "avatar_url": user.avatar_url,
        },
        "stats": UserStatsOut.model_validate(stats),
        "recent_attempts": [
            {
                "id": a.id,
                "mode": a.mode,
                "module_id": a.module_id,
                "percentage": a.percentage,
                "correct": a.correct,
                "total_questions": a.total_questions,
                "submitted_at": a.submitted_at,
            }
            for a in recent
        ],
        "due_revision": due,
        "resume_attempt_id": in_progress.id if in_progress else None,
        "next_stage": await _next_stage(db, stats),
        "announcements": [
            {
                "id": a.id,
                "title": a.title,
                "body": a.body,
                "level": a.level,
                "link_url": a.link_url,
            }
            for a in await content_service.live_announcements(db, service=user.target_service)
        ],
        "recommended": await _recommendations(db, user, stats),
    }


async def _next_stage(db: AsyncSession, stats: UserStats) -> dict | None:
    """The first stage the student is not yet ready for, by their own readiness."""
    readiness = stats.readiness or {}
    stages = list(await db.scalars(select(Stage).order_by(Stage.sort_order, Stage.id)))
    for stage in stages:
        if float(readiness.get(str(stage.code), 0.0)) < 70.0:
            return {
                "code": str(stage.code),
                "name": stage.name,
                "summary": stage.summary,
                "day_hint": stage.day_hint,
                "readiness": float(readiness.get(str(stage.code), 0.0)),
            }
    return None


async def _recommendations(db: AsyncSession, user: User, stats: UserStats, limit: int = 4) -> list[dict]:
    """Weakest topics first; fall back to the emptiest modules for a new user."""
    mastery = {k: v for k, v in (stats.topic_mastery or {}).items() if str(k).isdigit()}

    if mastery:
        ranked = sorted(
            mastery.items(),
            key=lambda kv: (kv[1].get("correct", 0) / kv[1]["seen"]) if kv[1].get("seen") else 0.0,
        )
        topic_ids = [int(tid) for tid, _ in ranked[:limit]]
        topics = {t.id: t for t in await db.scalars(select(Topic).where(Topic.id.in_(topic_ids)))}
        out = []
        for tid in topic_ids:
            topic = topics.get(tid)
            if topic is None:
                continue
            stat = mastery[str(tid)]
            out.append(
                {
                    "kind": "weak_topic",
                    "topic_id": topic.id,
                    "module_id": topic.module_id,
                    "name": topic.name,
                    "accuracy": round(stat.get("correct", 0) * 100 / stat["seen"], 1)
                    if stat.get("seen")
                    else 0.0,
                    "seen": stat.get("seen", 0),
                }
            )
        if out:
            return out

    stmt = select(Module).where(Module.is_active.is_(True), Module.approved_question_count > 0)
    if user.target_service is not None:
        from app.models.catalog import Service

        service_id = await db.scalar(select(Service.id).where(Service.code == user.target_service))
        if service_id:
            stmt = stmt.where(Module.service_id == service_id)

    modules = await db.scalars(stmt.order_by(Module.sort_order, Module.id).limit(limit))
    return [
        {
            "kind": "module",
            "module_id": m.id,
            "slug": m.slug,
            "name": m.title,
            "question_count": m.approved_question_count,
        }
        for m in modules
    ]

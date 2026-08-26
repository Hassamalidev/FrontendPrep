"""Reads and admin writes over the service/program/stage/module/topic spine.

The catalog is small (a few hundred rows total) and changes rarely, so the
queries here are plain selects with no caching layer -- the indexes carry it.
What does matter is round trips: the service hub assembles programs, stages and
modules in one call instead of four.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import ContentStatus, ServiceCode
from app.models.catalog import Module, Program, Service, Stage, Topic
from app.models.question import Question


async def list_services(db: AsyncSession, *, include_inactive: bool = False) -> list[Service]:
    stmt = select(Service).order_by(Service.sort_order, Service.id)
    if not include_inactive:
        stmt = stmt.where(Service.is_active.is_(True))
    return list(await db.scalars(stmt))


async def get_service(db: AsyncSession, code: ServiceCode) -> Service:
    service = await db.scalar(select(Service).where(Service.code == code))
    if service is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown service.")
    return service


async def list_stages(db: AsyncSession) -> list[Stage]:
    return list(await db.scalars(select(Stage).order_by(Stage.sort_order, Stage.id)))


async def list_programs(
    db: AsyncSession, *, service_id: int | None = None, include_inactive: bool = False
) -> list[Program]:
    stmt = select(Program).order_by(Program.sort_order, Program.id)
    if service_id is not None:
        stmt = stmt.where(Program.service_id == service_id)
    if not include_inactive:
        stmt = stmt.where(Program.is_active.is_(True))
    return list(await db.scalars(stmt))


async def get_program(db: AsyncSession, slug: str) -> Program:
    program = await db.scalar(select(Program).where(Program.slug == slug))
    if program is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown program.")
    return program


async def list_modules(
    db: AsyncSession,
    *,
    service_id: int | None = None,
    stage_id: int | None = None,
    include_inactive: bool = False,
) -> list[Module]:
    stmt = select(Module).order_by(Module.sort_order, Module.id)
    if service_id is not None:
        stmt = stmt.where(Module.service_id == service_id)
    if stage_id is not None:
        stmt = stmt.where(Module.stage_id == stage_id)
    if not include_inactive:
        stmt = stmt.where(Module.is_active.is_(True))
    return list(await db.scalars(stmt))


async def get_module(db: AsyncSession, ref: str | int) -> Module:
    """Look a module up by id or by ``service_slug`` -qualified slug."""
    stmt = select(Module).options(selectinload(Module.topics))
    if isinstance(ref, int) or str(ref).isdigit():
        stmt = stmt.where(Module.id == int(ref))
    else:
        stmt = stmt.where(Module.slug == str(ref))

    module = await db.scalar(stmt)
    if module is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown module.")
    return module


async def module_topics(db: AsyncSession, module_id: int) -> list[Topic]:
    return list(
        await db.scalars(
            select(Topic)
            .where(Topic.module_id == module_id, Topic.is_active.is_(True))
            .order_by(Topic.sort_order, Topic.id)
        )
    )


async def service_overview(db: AsyncSession, code: ServiceCode) -> dict:
    """Everything the service hub renders, in one round trip."""
    service = await get_service(db, code)
    return {
        "service": service,
        "programs": await list_programs(db, service_id=service.id),
        "stages": await list_stages(db),
        "modules": await list_modules(db, service_id=service.id),
    }


async def refresh_question_counts(db: AsyncSession, module_ids: list[int] | None = None) -> int:
    """Recompute the denormalised ``approved_question_count`` columns.

    Called after review decisions and by the seed script. Two grouped queries
    beat a COUNT(*) per module on every catalog render.
    """
    approved = Question.status == ContentStatus.APPROVED

    module_stmt = (
        select(Question.module_id, func.count())
        .where(approved)
        .group_by(Question.module_id)
    )
    if module_ids:
        module_stmt = module_stmt.where(Question.module_id.in_(module_ids))
    module_counts = dict((await db.execute(module_stmt)).all())

    topic_stmt = (
        select(Question.topic_id, func.count())
        .where(approved, Question.topic_id.is_not(None))
        .group_by(Question.topic_id)
    )
    if module_ids:
        topic_stmt = topic_stmt.where(Question.module_id.in_(module_ids))
    topic_counts = dict((await db.execute(topic_stmt)).all())

    modules = list(
        await db.scalars(
            select(Module).where(Module.id.in_(module_ids)) if module_ids else select(Module)
        )
    )

    # Questions are stored once and shared across each service's copy of a
    # module (see question_service._sibling_module_ids), so the count a student
    # sees has to be the count for the slug, not for their service's row --
    # otherwise two of the three services report zero.
    all_modules = list(await db.scalars(select(Module)))
    by_slug: dict[str, int] = {}
    for other in all_modules:
        by_slug[other.slug] = by_slug.get(other.slug, 0) + module_counts.get(other.id, 0)

    touched = 0
    for module in modules:
        wanted = by_slug.get(module.slug, 0)
        if module.approved_question_count != wanted:
            module.approved_question_count = wanted
            touched += 1

    topics = await db.scalars(
        select(Topic).where(Topic.module_id.in_(module_ids)) if module_ids else select(Topic)
    )
    for topic in topics:
        wanted = topic_counts.get(topic.id, 0)
        if topic.approved_question_count != wanted:
            topic.approved_question_count = wanted
            touched += 1

    await db.flush()
    return touched

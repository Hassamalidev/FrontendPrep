"""Question bank: CRUD, the review queue, dedupe and paper sampling.

``sample`` is the hot path -- it is what every practice drill and mock test
calls to fill a paper. It pushes randomisation into the database (one indexed
query per difficulty bucket) rather than pulling the bank into Python.
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ContentStatus, Difficulty, Origin, QuestionType
from app.models.catalog import Module
from app.models.question import Question, QuestionReport
from app.models.user import User
from app.schemas.question import QuestionIn, QuestionUpdate
from app.services import audit, catalog_service

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]")

# How a balanced paper is split when the caller does not specify a mix.
DEFAULT_MIX: dict[Difficulty, float] = {
    Difficulty.EASY: 0.3,
    Difficulty.MEDIUM: 0.5,
    Difficulty.HARD: 0.2,
}


def normalise(text: str) -> str:
    """Lower-case, strip punctuation, collapse whitespace -- for hashing."""
    return _WS.sub(" ", _PUNCT.sub(" ", text.lower())).strip()


def fingerprint(stem: str, answer_keys: list[str], options: list[dict] | None = None) -> str:
    """Stable dedupe key: the stem plus the *text* of the correct answers.

    Keys alone are not enough -- two questions can both answer "b" while meaning
    different things, and shuffling options re-keys the same question.
    """
    by_key = {str(o.get("key")): str(o.get("text", "")) for o in (options or [])}
    answers = [normalise(by_key.get(str(k), str(k))) for k in sorted(answer_keys)]
    payload = normalise(stem) + "|" + "|".join(answers)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:40]


async def find_duplicate(db: AsyncSession, fp: str) -> Question | None:
    return await db.scalar(select(Question).where(Question.fingerprint == fp))


async def get(db: AsyncSession, question_id: int) -> Question:
    question = await db.get(Question, question_id)
    if question is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found.")
    return question


def _approved(stmt: Select) -> Select:
    return stmt.where(Question.status == ContentStatus.APPROVED)


async def create(db: AsyncSession, data: QuestionIn, *, author: User) -> Question:
    module = await db.get(Module, data.module_id)
    if module is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown module.")

    fp = fingerprint(data.stem, data.answer_keys, data.options)
    if await find_duplicate(db, fp):
        raise HTTPException(status.HTTP_409_CONFLICT, "An identical question already exists.")

    question = Question(
        **data.model_dump(exclude={"module_id"}),
        module_id=module.id,
        service_id=module.service_id,
        origin=Origin.HUMAN,
        fingerprint=fp,
    )
    if data.status == ContentStatus.APPROVED:
        question.reviewed_by_id = author.id
        question.reviewed_at = datetime.now(UTC)

    db.add(question)
    await db.flush()

    audit.record(
        db, actor_id=author.id, action="question.create", entity="question", entity_id=question.id
    )
    await catalog_service.refresh_question_counts(db, [module.id])
    await db.commit()
    await db.refresh(question)
    return question


async def update_one(
    db: AsyncSession, question_id: int, data: QuestionUpdate, *, author: User
) -> Question:
    question = await get(db, question_id)
    changes = data.model_dump(exclude_unset=True)

    for field, value in changes.items():
        setattr(question, field, value)

    # Editing the wording or the key invalidates the old dedupe hash.
    if {"stem", "answer_keys", "options"} & changes.keys():
        fp = fingerprint(question.stem, question.answer_keys, question.options)
        clash = await find_duplicate(db, fp)
        if clash and clash.id != question.id:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "That edit duplicates another question."
            )
        question.fingerprint = fp

    if "status" in changes:
        question.reviewed_by_id = author.id
        question.reviewed_at = datetime.now(UTC)

    audit.record(
        db,
        actor_id=author.id,
        action="question.update",
        entity="question",
        entity_id=question.id,
        detail={"fields": sorted(changes)},
    )
    await catalog_service.refresh_question_counts(db, [question.module_id])
    await db.commit()
    await db.refresh(question)
    return question


async def delete_one(db: AsyncSession, question_id: int, *, author: User) -> None:
    question = await get(db, question_id)
    module_id = question.module_id
    await db.delete(question)
    audit.record(
        db, actor_id=author.id, action="question.delete", entity="question", entity_id=question_id
    )
    await catalog_service.refresh_question_counts(db, [module_id])
    await db.commit()


async def review(
    db: AsyncSession,
    ids: list[int],
    *,
    decision: ContentStatus,
    note: str | None,
    reviewer: User,
) -> int:
    """Approve or reject a batch from the review queue. Returns rows touched."""
    if not ids:
        return 0

    module_ids = list(
        await db.scalars(select(Question.module_id).where(Question.id.in_(ids)).distinct())
    )
    result = await db.execute(
        update(Question)
        .where(Question.id.in_(ids))
        .values(
            status=decision,
            reviewed_by_id=reviewer.id,
            reviewed_at=datetime.now(UTC),
            review_note=note,
        )
    )

    audit.record(
        db,
        actor_id=reviewer.id,
        action=f"question.{decision.value}",
        entity="question",
        detail={"ids": ids[:50], "count": len(ids)},
    )
    await catalog_service.refresh_question_counts(db, module_ids)
    await db.commit()
    return result.rowcount or 0


async def search(
    db: AsyncSession,
    *,
    offset: int,
    limit: int,
    module_id: int | None = None,
    topic_id: int | None = None,
    service_id: int | None = None,
    qstatus: ContentStatus | None = None,
    difficulty: Difficulty | None = None,
    qtype: QuestionType | None = None,
    origin: Origin | None = None,
    q: str | None = None,
    approved_only: bool = False,
) -> tuple[list[Question], int]:
    stmt = select(Question)
    if module_id is not None:
        stmt = stmt.where(Question.module_id == module_id)
    if topic_id is not None:
        stmt = stmt.where(Question.topic_id == topic_id)
    if service_id is not None:
        stmt = stmt.where(Question.service_id == service_id)
    if difficulty is not None:
        stmt = stmt.where(Question.difficulty == difficulty)
    if qtype is not None:
        stmt = stmt.where(Question.qtype == qtype)
    if origin is not None:
        stmt = stmt.where(Question.origin == origin)
    if approved_only:
        stmt = _approved(stmt)
    elif qstatus is not None:
        stmt = stmt.where(Question.status == qstatus)
    if q:
        stmt = stmt.where(Question.stem.ilike(f"%{q.strip()}%"))

    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        await db.scalars(stmt.order_by(Question.created_at.desc()).offset(offset).limit(limit))
    )
    return rows, total


async def _sibling_module_ids(db: AsyncSession, module_id: int) -> list[int]:
    """Every service's copy of the same module.

    The syllabus modules genuinely are shared -- verbal intelligence is the same
    subject whichever service you are joining -- but each service gets its own
    row so the catalog reads as one funnel per service. Storing the questions
    three times to match would triple the largest table in the schema for no
    information gain, so instead one copy is stored and sampling looks across
    the siblings that share its slug.
    """
    slug = await db.scalar(select(Module.slug).where(Module.id == module_id))
    if slug is None:
        return [module_id]
    return list(await db.scalars(select(Module.id).where(Module.slug == slug)))


async def sample(
    db: AsyncSession,
    *,
    module_id: int | None = None,
    topic_id: int | None = None,
    service_id: int | None = None,
    count: int = 20,
    difficulty: Difficulty | None = None,
    difficulty_mix: dict | None = None,
    exclude_ids: set[int] | None = None,
) -> list[Question]:
    """Draw ``count`` approved questions, honouring a difficulty mix.

    Buckets are filled independently and any shortfall is topped up from the
    rest of the pool, so a thin bank degrades to "as balanced as available"
    instead of to an empty paper.
    """
    seen: set[int] = set(exclude_ids or ())

    # Draw from every service's copy of this module, not just this one.
    module_ids = await _sibling_module_ids(db, module_id) if module_id is not None else []

    def base() -> Select:
        stmt = _approved(select(Question))
        if module_ids:
            stmt = stmt.where(Question.module_id.in_(module_ids))
        if topic_id is not None:
            stmt = stmt.where(Question.topic_id == topic_id)
        if service_id is not None:
            stmt = stmt.where(Question.service_id == service_id)
        return stmt

    if difficulty is not None:
        buckets: dict[Difficulty, int] = {difficulty: count}
    else:
        mix = {Difficulty(k): float(v) for k, v in (difficulty_mix or DEFAULT_MIX).items()}
        weight = sum(mix.values()) or 1.0
        buckets = {lvl: max(0, round(count * share / weight)) for lvl, share in mix.items()}

    picked: list[Question] = []
    for level, wanted in buckets.items():
        if wanted <= 0:
            continue
        stmt = base().where(Question.difficulty == level)
        if seen:
            stmt = stmt.where(Question.id.notin_(seen))
        rows = list(await db.scalars(stmt.order_by(func.random()).limit(wanted)))
        picked.extend(rows)
        seen.update(r.id for r in rows)

    if len(picked) < count:
        stmt = base()
        if seen:
            stmt = stmt.where(Question.id.notin_(seen))
        picked.extend(
            await db.scalars(stmt.order_by(func.random()).limit(count - len(picked)))
        )

    return picked[:count]


async def report(
    db: AsyncSession, question_id: int, *, user_id: int | None, reason: str, note: str | None
) -> QuestionReport:
    await get(db, question_id)
    row = QuestionReport(question_id=question_id, user_id=user_id, reason=reason[:40], note=note)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def record_exposure(db: AsyncSession, results: list[tuple[int, bool]]) -> None:
    """Bump served/correct counters so difficulty can be recalibrated later.

    Two statements for a whole paper rather than one per question.
    """
    if not results:
        return

    served = [qid for qid, _ in results]
    correct = [qid for qid, ok in results if ok]

    await db.execute(
        update(Question).where(Question.id.in_(served)).values(times_served=Question.times_served + 1)
    )
    if correct:
        await db.execute(
            update(Question)
            .where(Question.id.in_(correct))
            .values(times_correct=Question.times_correct + 1)
        )

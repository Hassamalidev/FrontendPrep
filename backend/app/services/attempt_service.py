"""Starting, grading and reviewing attempts.

Two decisions drive this module:

* **The paper is frozen at start.** Question ids, answer keys, marks and the
  shuffled option order are copied into ``Attempt.blueprint``. Grading then
  never re-reads the questions table, and editing a question afterwards cannot
  retroactively change a submitted paper.
* **Answers stay inline.** They are written to ``Attempt.answers`` as JSONB and
  only ever read back whole, to render one result page.
"""

from __future__ import annotations

import random
from datetime import UTC, date, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AttemptStatus
from app.core.timeutil import as_utc, elapsed_seconds
from app.models.assessment import Attempt, PracticeCard, TestTemplate
from app.models.catalog import Module, Topic
from app.models.question import Question
from app.models.user import User, UserStats
from app.schemas.assessment import AttemptStartIn, AttemptSubmitIn
from app.services import question_service

MAX_OPEN_ATTEMPTS = 3
TOPIC_MASTERY_CAP = 60  # keep the JSON blob bounded on a tiny database


def _now() -> datetime:
    return datetime.now(UTC)


def _shuffled_keys(question: Question, shuffle: bool) -> list[str]:
    keys = [str(o.get("key")) for o in (question.options or [])]
    if shuffle and len(keys) > 1:
        random.shuffle(keys)
    return keys


def _blueprint_row(question: Question, *, shuffle_options: bool) -> dict:
    return {
        "id": question.id,
        "keys": [str(k) for k in (question.answer_keys or [])],
        "marks": float(question.marks),
        "neg": float(question.negative_marks),
        "topic_id": question.topic_id,
        "module_id": question.module_id,
        "order": _shuffled_keys(question, shuffle_options),
    }


def _apply_order(question: Question, order: list[str]) -> Question:
    """Re-order a question object's options to match the frozen paper."""
    if not order or not question.options:
        return question
    by_key = {str(o.get("key")): o for o in question.options}
    question.options = [by_key[k] for k in order if k in by_key]
    return question


async def _open_attempt_count(db: AsyncSession, user_id: int) -> int:
    return (
        await db.scalar(
            select(func.count())
            .select_from(Attempt)
            .where(Attempt.user_id == user_id, Attempt.status == AttemptStatus.IN_PROGRESS)
        )
        or 0
    )


async def _due_question_ids(db: AsyncSession, user_id: int, limit: int) -> list[int]:
    return list(
        await db.scalars(
            select(PracticeCard.question_id)
            .where(PracticeCard.user_id == user_id, PracticeCard.due_on <= _now())
            .order_by(PracticeCard.due_on)
            .limit(limit)
        )
    )


async def start(db: AsyncSession, user: User, data: AttemptStartIn) -> tuple[Attempt, list[Question], list[dict]]:
    """Build a paper and open an attempt. Returns (attempt, questions, sections)."""
    if await _open_attempt_count(db, user.id) >= MAX_OPEN_ATTEMPTS:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "You have too many unfinished attempts. Finish or abandon one first.",
        )

    template: TestTemplate | None = None
    module: Module | None = None
    sections: list[dict] = []
    questions: list[Question] = []

    if data.template_id is not None:
        template = await db.get(TestTemplate, data.template_id)
        if template is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Test not found.")

        chosen: set[int] = set()
        for spec in template.sections or []:
            module_row = await db.scalar(
                select(Module).where(Module.slug == str(spec.get("module_slug")))
            )
            if module_row is None:
                continue
            batch = await question_service.sample(
                db,
                module_id=module_row.id,
                count=int(spec.get("count", 10)),
                difficulty_mix=spec.get("difficulty_mix"),
                exclude_ids=chosen,
            )
            chosen.update(q.id for q in batch)
            questions.extend(batch)
            sections.append(
                {
                    "title": spec.get("title") or module_row.title,
                    "minutes": spec.get("minutes"),
                    "question_ids": [q.id for q in batch],
                }
            )

    elif data.only_weak:
        due = await _due_question_ids(db, user.id, data.count)
        if due:
            questions = list(
                await db.scalars(select(Question).where(Question.id.in_(due)))
            )
        if len(questions) < data.count and data.module_id:
            questions.extend(
                await question_service.sample(
                    db,
                    module_id=data.module_id,
                    count=data.count - len(questions),
                    exclude_ids={q.id for q in questions},
                )
            )

    else:
        module = await db.get(Module, data.module_id)
        if module is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Module not found.")
        questions = await question_service.sample(
            db,
            module_id=module.id,
            topic_id=data.topic_id,
            count=data.count,
            difficulty=data.difficulty,
        )

    if not questions:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "There are no approved questions available for that selection yet.",
        )

    shuffle_q = template.shuffle_questions if template else True
    shuffle_o = template.shuffle_options if template else True
    if shuffle_q and not sections:
        random.shuffle(questions)

    duration_min = template.duration_min if template else (module.default_duration_min if module else 20)

    attempt = Attempt(
        user_id=user.id,
        template_id=template.id if template else None,
        module_id=module.id if module else data.module_id,
        service=user.target_service,
        mode=data.mode if not template else ("mock" if template.is_mock else "practice"),
        status=AttemptStatus.IN_PROGRESS,
        expires_at=_now() + timedelta(minutes=duration_min + 5),
        blueprint=[_blueprint_row(q, shuffle_options=shuffle_o) for q in questions],
        total_questions=len(questions),
        max_score=sum(float(q.marks) for q in questions),
    )
    if sections:
        attempt.topic_breakdown = {"sections": sections}

    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)

    order_by_id = {row["id"]: row["order"] for row in attempt.blueprint}
    for question in questions:
        _apply_order(question, order_by_id.get(question.id, []))

    return attempt, questions, sections


async def get_owned(db: AsyncSession, user: User, attempt_id: int) -> Attempt:
    attempt = await db.get(Attempt, attempt_id)
    if attempt is None or attempt.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attempt not found.")
    return attempt


async def resume(db: AsyncSession, user: User, attempt_id: int) -> tuple[Attempt, list[Question]]:
    attempt = await get_owned(db, user, attempt_id)
    if attempt.status != AttemptStatus.IN_PROGRESS:
        raise HTTPException(status.HTTP_409_CONFLICT, "This attempt is already finished.")
    if attempt.expires_at and as_utc(attempt.expires_at) < _now():
        attempt.status = AttemptStatus.EXPIRED
        await db.commit()
        raise HTTPException(status.HTTP_409_CONFLICT, "This attempt has expired.")

    ids = [row["id"] for row in attempt.blueprint]
    rows = {q.id: q for q in await db.scalars(select(Question).where(Question.id.in_(ids)))}
    ordered: list[Question] = []
    for row in attempt.blueprint:
        question = rows.get(row["id"])
        if question is not None:
            ordered.append(_apply_order(question, row.get("order", [])))
    return attempt, ordered


def grade(blueprint: list[dict], answers: list[dict]) -> dict:
    """Score a frozen paper against submitted answers.

    Pure and synchronous so it can be unit-tested without a database.
    """
    picked_by_id = {int(a["id"]): a for a in answers if "id" in a}

    score = 0.0
    max_score = 0.0
    attempted = correct = wrong = 0
    per_question: list[dict] = []
    topic_stats: dict[str, dict[str, int]] = {}

    for row in blueprint:
        qid = int(row["id"])
        marks = float(row.get("marks", 1.0))
        negative = float(row.get("neg", 0.0))
        expected = {str(k) for k in row.get("keys", [])}
        max_score += marks

        answer = picked_by_id.get(qid) or {}
        picked = {str(k) for k in (answer.get("picked") or [])}
        awarded = 0.0

        if picked:
            attempted += 1
            if picked == expected:
                correct += 1
                awarded = marks
            else:
                wrong += 1
                awarded = -negative
        score += awarded

        topic_key = str(row.get("topic_id") or "unfiled")
        bucket = topic_stats.setdefault(topic_key, {"seen": 0, "correct": 0})
        bucket["seen"] += 1
        if picked and picked == expected:
            bucket["correct"] += 1

        per_question.append(
            {
                "id": qid,
                "picked": sorted(picked),
                "expected": sorted(expected),
                "correct": bool(picked) and picked == expected,
                "attempted": bool(picked),
                "marks_awarded": round(awarded, 2),
                "ms": int(answer.get("ms", 0) or 0),
                "flagged": bool(answer.get("flagged")),
            }
        )

    score = max(0.0, round(score, 2))  # negative marking never drops below zero
    return {
        "score": score,
        "max_score": round(max_score, 2),
        "percentage": round(score * 100 / max_score, 2) if max_score else 0.0,
        "attempted": attempted,
        "correct": correct,
        "wrong": wrong,
        "per_question": per_question,
        "topic_stats": topic_stats,
    }


def _sm2(card: PracticeCard, quality: int) -> None:
    """SM-2 lite. ``quality`` is 0-5; below 3 restarts the interval."""
    if quality < 3:
        card.repetitions = 0
        card.interval_days = 1
        card.lapses += 1
    else:
        card.repetitions += 1
        if card.repetitions == 1:
            card.interval_days = 1
        elif card.repetitions == 2:
            card.interval_days = 6
        else:
            card.interval_days = min(180, round(card.interval_days * card.ease))

    card.ease = max(1.3, card.ease + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    card.due_on = _now() + timedelta(days=card.interval_days)
    card.last_seen_at = _now()


async def _upsert_cards(db: AsyncSession, user_id: int, results: list[dict]) -> None:
    """Only wrong or flagged questions earn a card -- this tracks mistakes.

    A card per answered question would mirror the whole bank into a per-user
    table; on a 0.5 GB budget that is the single most expensive thing this
    schema could do.
    """
    interesting = [r for r in results if not r["correct"] or r["flagged"]]
    if not interesting:
        return

    ids = [r["id"] for r in interesting]
    existing = {
        card.question_id: card
        for card in await db.scalars(
            select(PracticeCard).where(
                PracticeCard.user_id == user_id, PracticeCard.question_id.in_(ids)
            )
        )
    }

    for result in interesting:
        card = existing.get(result["id"])
        if card is None:
            # Column defaults are applied at INSERT, so a freshly constructed row
            # still has None in these fields -- and _sm2 does arithmetic on them
            # before the flush. Seed the SM-2 starting state explicitly.
            card = PracticeCard(
                user_id=user_id,
                question_id=result["id"],
                due_on=_now() + timedelta(days=1),
                ease=2.5,
                interval_days=0,
                repetitions=0,
                lapses=0,
            )
            db.add(card)
        quality = 4 if result["correct"] else (2 if result["attempted"] else 0)
        _sm2(card, quality)


def _merge_topic_mastery(current: dict, delta: dict) -> dict:
    """Fold this attempt into the running per-topic tally, capped in size.

    When the cap is hit the *best-known* topics are dropped first: the panel
    exists to surface weak areas, so those are the rows worth keeping.
    """
    merged = {k: dict(v) for k, v in (current or {}).items()}
    for topic, stats in delta.items():
        bucket = merged.setdefault(topic, {"seen": 0, "correct": 0})
        bucket["seen"] += int(stats.get("seen", 0))
        bucket["correct"] += int(stats.get("correct", 0))

    if len(merged) > TOPIC_MASTERY_CAP:
        ranked = sorted(
            merged.items(),
            key=lambda kv: (
                kv[1]["correct"] / kv[1]["seen"] if kv[1]["seen"] else 0.0,
                -kv[1]["seen"],
            ),
        )
        merged = dict(ranked[:TOPIC_MASTERY_CAP])
    return merged


def _bump_streak(stats: UserStats, today: date) -> None:
    last = stats.last_active_on
    if last == today:
        return
    stats.current_streak = stats.current_streak + 1 if last == today - timedelta(days=1) else 1
    stats.longest_streak = max(stats.longest_streak, stats.current_streak)
    stats.last_active_on = today


async def submit(
    db: AsyncSession, user: User, attempt_id: int, data: AttemptSubmitIn
) -> Attempt:
    attempt = await get_owned(db, user, attempt_id)
    if attempt.status != AttemptStatus.IN_PROGRESS:
        raise HTTPException(status.HTTP_409_CONFLICT, "This attempt was already submitted.")

    answers = [a.model_dump() for a in data.answers]
    outcome = grade(attempt.blueprint, answers)

    attempt.answers = [
        {"id": r["id"], "picked": r["picked"], "ms": r["ms"], "flagged": r["flagged"]}
        for r in outcome["per_question"]
        if r["attempted"] or r["flagged"]
    ]
    attempt.status = AttemptStatus.SUBMITTED
    attempt.submitted_at = _now()
    attempt.duration_sec = data.duration_sec or elapsed_seconds(
        attempt.started_at, attempt.submitted_at
    )
    attempt.attempted = outcome["attempted"]
    attempt.correct = outcome["correct"]
    attempt.wrong = outcome["wrong"]
    attempt.score = outcome["score"]
    attempt.max_score = outcome["max_score"]
    attempt.percentage = outcome["percentage"]

    sections = (attempt.topic_breakdown or {}).get("sections")
    attempt.topic_breakdown = dict(outcome["topic_stats"])
    if sections:
        attempt.topic_breakdown["sections"] = sections

    if attempt.template_id:
        template = await db.get(TestTemplate, attempt.template_id)
        if template is not None:
            attempt.passed = attempt.percentage >= template.pass_percentage

    # --- roll-ups -------------------------------------------------------
    stats = await db.get(UserStats, user.id)
    if stats is None:
        stats = UserStats(user_id=user.id)
        db.add(stats)
        await db.flush()  # apply column defaults before incrementing them

    stats.attempts_total += 1
    stats.questions_answered += outcome["attempted"]
    stats.questions_correct += outcome["correct"]
    stats.study_seconds += attempt.duration_sec
    stats.topic_mastery = _merge_topic_mastery(stats.topic_mastery, outcome["topic_stats"])
    stats.updated_at = _now()
    _bump_streak(stats, attempt.submitted_at.date())

    await _upsert_cards(db, user.id, outcome["per_question"])
    await question_service.record_exposure(
        db, [(r["id"], r["correct"]) for r in outcome["per_question"] if r["attempted"]]
    )

    await db.commit()
    await db.refresh(attempt)
    return attempt


async def abandon(db: AsyncSession, user: User, attempt_id: int) -> None:
    attempt = await get_owned(db, user, attempt_id)
    if attempt.status == AttemptStatus.IN_PROGRESS:
        attempt.status = AttemptStatus.ABANDONED
        await db.commit()


async def review_payload(db: AsyncSession, user: User, attempt_id: int) -> dict:
    """The result page: score, weak topics and (if allowed) the answer key."""
    attempt = await get_owned(db, user, attempt_id)
    if attempt.status == AttemptStatus.IN_PROGRESS:
        raise HTTPException(status.HTTP_409_CONFLICT, "This attempt is still in progress.")

    show_answers = True
    if attempt.template_id:
        template = await db.get(TestTemplate, attempt.template_id)
        show_answers = template.show_answers_after if template else True

    review: list[dict] = []
    if show_answers and not attempt.detail_pruned:
        picked_by_id = {int(a["id"]): a for a in (attempt.answers or [])}
        ids = [row["id"] for row in attempt.blueprint]
        rows = {q.id: q for q in await db.scalars(select(Question).where(Question.id.in_(ids)))}

        for row in attempt.blueprint:
            question = rows.get(row["id"])
            if question is None:  # deleted since the paper was sat
                continue
            answer = picked_by_id.get(row["id"], {})
            picked = [str(k) for k in answer.get("picked", [])]
            expected = [str(k) for k in row.get("keys", [])]
            correct = bool(picked) and set(picked) == set(expected)
            review.append(
                {
                    "question": _apply_order(question, row.get("order", [])),
                    "picked": picked,
                    "correct": correct,
                    "marks_awarded": round(
                        float(row.get("marks", 1.0)) if correct
                        else (-float(row.get("neg", 0.0)) if picked else 0.0),
                        2,
                    ),
                    "ms": int(answer.get("ms", 0) or 0),
                }
            )

    breakdown = {k: v for k, v in (attempt.topic_breakdown or {}).items() if k != "sections"}
    weak_ids = [
        int(tid)
        for tid, s in breakdown.items()
        if tid.isdigit() and s.get("seen") and s["correct"] / s["seen"] < 0.6
    ]
    weak_topics = (
        [t.name for t in await db.scalars(select(Topic).where(Topic.id.in_(weak_ids)))]
        if weak_ids
        else []
    )

    return {"attempt": attempt, "review": review, "weak_topics": weak_topics}


async def history(
    db: AsyncSession, user: User, *, offset: int, limit: int
) -> tuple[list[Attempt], int]:
    stmt = select(Attempt).where(Attempt.user_id == user.id)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        await db.scalars(stmt.order_by(Attempt.started_at.desc()).offset(offset).limit(limit))
    )
    return rows, total

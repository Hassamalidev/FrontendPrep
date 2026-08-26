"""The ISSB simulation suite: psych battery, GTO tasks and mock interview.

None of these tests have an answer key, so "submitting" means running the
response set through ``app.agents.olq`` and storing the read-out. Each sitting
is one row with a JSONB response array -- a 60-word WAT is one row, not sixty.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import olq as olq_agent
from app.core.enums import ContentStatus, PsychTestType, ResponseSource
from app.core.timeutil import elapsed_seconds
from app.models.issb import (
    GtoSubmission,
    GtoTask,
    InterviewQuestion,
    InterviewSession,
    PsychItem,
    PsychSession,
)
from app.models.user import User, UserStats
from app.schemas.issb import (
    GtoSubmitIn,
    InterviewStartIn,
    InterviewSubmitIn,
    PsychSessionStartIn,
    PsychSubmitIn,
)

# Real ISSB set sizes. A practice sitting may ask for fewer.
DEFAULT_ITEM_COUNT: dict[PsychTestType, int] = {
    PsychTestType.WAT: 60,
    PsychTestType.SCT: 60,
    PsychTestType.SRT: 60,
    PsychTestType.TAT: 12,
    PsychTestType.PSW: 1,
    PsychTestType.SELF_DESCRIPTION: 5,
    PsychTestType.PIQ: 1,
}


def _now() -> datetime:
    return datetime.now(UTC)


# --- Psychological battery -------------------------------------------------


async def start_psych(
    db: AsyncSession, user: User, data: PsychSessionStartIn
) -> tuple[PsychSession, list[PsychItem]]:
    wanted = data.count or DEFAULT_ITEM_COUNT.get(data.test_type, 30)

    items = list(
        await db.scalars(
            select(PsychItem)
            .where(
                PsychItem.test_type == data.test_type,
                PsychItem.status == ContentStatus.APPROVED,
            )
            .order_by(func.random())
            .limit(wanted)
        )
    )
    if not items:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"No {data.test_type.value.upper()} items have been published yet.",
        )
    # Presentation order is fixed per sitting so the timer and the review agree.
    items.sort(key=lambda i: (i.sort_order, i.id))

    session = PsychSession(
        user_id=user.id,
        test_type=data.test_type,
        service=data.service or user.target_service,
        item_count=len(items),
        responses=[{"item_id": item.id} for item in items],
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session, items


async def _owned_psych(db: AsyncSession, user: User, session_id: int) -> PsychSession:
    session = await db.get(PsychSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found.")
    return session


async def submit_psych(
    db: AsyncSession, user: User, session_id: int, data: PsychSubmitIn
) -> PsychSession:
    session = await _owned_psych(db, user, session_id)
    if session.submitted_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This sitting was already submitted.")

    served_ids = [int(r["item_id"]) for r in (session.responses or []) if r.get("item_id")]
    items = {
        item.id: item
        for item in await db.scalars(select(PsychItem).where(PsychItem.id.in_(served_ids)))
    }

    responses: list[olq_agent.Response] = []
    stored: list[dict] = []
    for entry in data.responses:
        item = items.get(entry.item_id)
        if item is None:
            continue  # an item deleted mid-sitting is dropped, not an error
        responses.append(
            olq_agent.Response(
                text=entry.text,
                ms=entry.ms,
                seconds_allowed=item.seconds,
                skipped=entry.skipped or not entry.text.strip(),
            )
        )
        stored.append(
            {
                "item_id": entry.item_id,
                "text": entry.text[:2000],
                "ms": entry.ms,
                "skipped": entry.skipped or not entry.text.strip(),
            }
        )

    analysis = olq_agent.analyse(
        responses, test_type=str(session.test_type), expected_items=session.item_count
    )

    session.responses = stored
    session.submitted_at = _now()
    session.duration_sec = data.duration_sec or elapsed_seconds(
        session.started_at, session.submitted_at
    )
    session.answered_count = sum(1 for r in stored if not r["skipped"])
    session.word_count = sum(len(r["text"].split()) for r in stored)
    session.signals = analysis.signals
    session.olq_scores = analysis.olq_scores
    session.feedback = analysis.feedback
    session.overall_score = analysis.overall_score

    await _fold_into_profile(db, user.id, analysis.olq_scores)
    await db.commit()
    await db.refresh(session)
    return session


async def _fold_into_profile(db: AsyncSession, user_id: int, scores: dict) -> None:
    """Keep a running OLQ average on the stats row.

    Stored as a count plus a mean rather than a list of sittings, so the blob
    stays the same size after the hundredth test as after the first.
    """
    if not scores:
        return

    stats = await db.get(UserStats, user_id)
    if stats is None:
        stats = UserStats(user_id=user_id)
        db.add(stats)
        await db.flush()

    profile = dict(stats.olq_profile or {})
    seen = int(profile.pop("_sessions", 0))
    merged: dict[str, float] = {}

    for key, value in scores.items():
        previous = float(profile.get(key, 0.0))
        merged[key] = round((previous * seen + float(value)) / (seen + 1), 2) if seen else round(float(value), 2)

    for key, value in profile.items():
        merged.setdefault(key, float(value))

    merged["_sessions"] = seen + 1
    stats.olq_profile = merged
    stats.updated_at = _now()


async def psych_result(db: AsyncSession, user: User, session_id: int) -> dict:
    session = await _owned_psych(db, user, session_id)
    if session.submitted_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This sitting is not finished yet.")

    ids = [int(r["item_id"]) for r in (session.responses or []) if r.get("item_id")]
    items = {
        item.id: item
        for item in await db.scalars(select(PsychItem).where(PsychItem.id.in_(ids)))
    }

    responses = [
        olq_agent.Response(
            text=r.get("text", ""),
            ms=int(r.get("ms", 0) or 0),
            seconds_allowed=items[r["item_id"]].seconds if r["item_id"] in items else 30,
            skipped=bool(r.get("skipped")),
        )
        for r in (session.responses or [])
    ]
    notes = olq_agent.analyse(responses, test_type=str(session.test_type)).per_response_notes

    return {
        "session": session,
        "items": items,
        "notes": notes,
        "analysis": _stored_analysis(session),
    }


def _stored_analysis(row) -> dict:
    """Re-shape a persisted read-out into the API's analysis payload."""
    from app.core.enums import OLQ, OLQ_LABELS

    scores = row.olq_scores or {}
    ranked = sorted(scores.items(), key=lambda kv: -float(kv[1]))
    labelled = [
        {"olq": key, "label": OLQ_LABELS.get(OLQ(key), key), "score": float(value)}
        for key, value in ranked
        if key in {o.value for o in OLQ}
    ]
    return {
        "signals": row.signals or {},
        "olq_scores": labelled,
        "feedback": row.feedback or [],
        "overall_score": row.overall_score,
        "strengths": [entry["label"] for entry in labelled[:4]],
        "improvements": [entry["label"] for entry in labelled[-4:]],
    }


async def psych_history(
    db: AsyncSession, user: User, *, offset: int, limit: int, test_type: PsychTestType | None = None
) -> tuple[list[PsychSession], int]:
    stmt = select(PsychSession).where(PsychSession.user_id == user.id)
    if test_type is not None:
        stmt = stmt.where(PsychSession.test_type == test_type)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        await db.scalars(
            stmt.order_by(PsychSession.started_at.desc()).offset(offset).limit(limit)
        )
    )
    return rows, total


# --- GTO -------------------------------------------------------------------


async def list_gto_tasks(
    db: AsyncSession,
    *,
    task_type=None,
    venue=None,
    service=None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[GtoTask], int]:
    stmt = select(GtoTask).where(GtoTask.status == ContentStatus.APPROVED)
    if task_type is not None:
        stmt = stmt.where(GtoTask.task_type == task_type)
    if venue is not None:
        stmt = stmt.where(GtoTask.venue == venue)
    if service is not None:
        stmt = stmt.where(or_(GtoTask.service == service, GtoTask.service.is_(None)))
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        await db.scalars(stmt.order_by(GtoTask.sort_order, GtoTask.id).offset(offset).limit(limit))
    )
    return rows, total


async def get_gto_task(db: AsyncSession, task_id: int) -> GtoTask:
    task = await db.get(GtoTask, task_id)
    if task is None or task.status != ContentStatus.APPROVED:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found.")
    return task


async def submit_gto(
    db: AsyncSession, user: User, task_id: int, data: GtoSubmitIn
) -> GtoSubmission:
    task = await get_gto_task(db, task_id)

    # A written plan is one long response; split it so the analyser sees the
    # structure the candidate imposed rather than one undifferentiated blob.
    chunks = [line.strip() for line in data.body.splitlines() if line.strip()] or [data.body]
    responses = [
        olq_agent.Response(text=chunk, seconds_allowed=max(1, task.planning_seconds // len(chunks)))
        for chunk in chunks
    ]
    if responses and data.duration_sec:
        responses[0].ms = data.duration_sec * 1000 // len(responses)

    analysis = olq_agent.analyse(responses, test_type=str(task.task_type))

    submission = GtoSubmission(
        user_id=user.id,
        task_id=task.id,
        body=data.body,
        duration_sec=data.duration_sec,
        signals=analysis.signals,
        olq_scores=analysis.olq_scores,
        feedback=analysis.feedback + _rubric_coverage(task, data.body),
        overall_score=analysis.overall_score,
    )
    db.add(submission)
    await _fold_into_profile(db, user.id, analysis.olq_scores)
    await db.commit()
    await db.refresh(submission)
    return submission


def _rubric_coverage(task: GtoTask, body: str) -> list[str]:
    """Say which rubric points the plan visibly addresses, and which it misses.

    Keyword matching against the assessor rubric -- crude, but it is the
    difference between "here is a score" and "you never mentioned the timeline".
    """
    lowered = body.lower()
    missed: list[str] = []
    for entry in task.rubric or []:
        look_for = str(entry.get("look_for", ""))
        keywords = [w for w in look_for.lower().split() if len(w) > 4][:6]
        if keywords and not any(word in lowered for word in keywords):
            missed.append(look_for)

    notes: list[str] = []
    if missed:
        notes.append("Rubric points your plan did not visibly cover: " + "; ".join(missed[:4]))
    for constraint in (task.constraints or [])[:6]:
        words = [w for w in str(constraint).lower().split() if len(w) > 5][:3]
        if words and not any(word in lowered for word in words):
            notes.append(f"You did not address the constraint: {constraint}")
    return notes[:6]


async def gto_history(
    db: AsyncSession, user: User, *, offset: int, limit: int
) -> tuple[list[GtoSubmission], int]:
    stmt = select(GtoSubmission).where(GtoSubmission.user_id == user.id)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        await db.scalars(
            stmt.order_by(GtoSubmission.created_at.desc()).offset(offset).limit(limit)
        )
    )
    return rows, total


async def get_gto_submission(db: AsyncSession, user: User, submission_id: int) -> GtoSubmission:
    row = await db.get(GtoSubmission, submission_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Submission not found.")
    return row


# --- Interview -------------------------------------------------------------


async def start_interview(
    db: AsyncSession, user: User, data: InterviewStartIn
) -> tuple[InterviewSession, list[InterviewQuestion]]:
    service = data.service or user.target_service
    stmt = select(InterviewQuestion).where(
        InterviewQuestion.status == ContentStatus.APPROVED,
        InterviewQuestion.is_active.is_(True),
    )
    if service is not None:
        stmt = stmt.where(or_(InterviewQuestion.service == service, InterviewQuestion.service.is_(None)))
    if data.categories:
        stmt = stmt.where(InterviewQuestion.category.in_(data.categories))

    questions = list(await db.scalars(stmt.order_by(func.random()).limit(data.count)))
    if not questions:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "No interview questions are available for that selection."
        )

    # An IO works outward from the candidate: personal, then academic, then the
    # wider world. Ordering the mock the same way makes it feel like a board.
    order = {
        "personal": 0, "family": 1, "academic": 2, "hobbies": 3,
        "current_affairs": 4, "defence": 5, "religion": 6, "situational": 7,
    }
    questions.sort(key=lambda q: order.get(q.category, 9))

    session = InterviewSession(
        user_id=user.id,
        service=service,
        exchanges=[{"question_id": q.id} for q in questions],
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session, questions


async def _owned_interview(db: AsyncSession, user: User, session_id: int) -> InterviewSession:
    session = await db.get(InterviewSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found.")
    return session


async def submit_interview(
    db: AsyncSession, user: User, session_id: int, data: InterviewSubmitIn
) -> InterviewSession:
    session = await _owned_interview(db, user, session_id)
    if session.submitted_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This interview was already submitted.")

    responses = [
        olq_agent.Response(text=item.answer, ms=item.ms, seconds_allowed=120)
        for item in data.exchanges
    ]
    expected = len(session.exchanges or []) or len(responses)
    analysis = olq_agent.analyse(responses, test_type="interview", expected_items=expected)

    session.exchanges = [
        {"question_id": item.question_id, "answer": item.answer[:4000], "ms": item.ms}
        for item in data.exchanges
    ]
    session.submitted_at = _now()
    session.duration_sec = data.duration_sec or elapsed_seconds(
        session.started_at, session.submitted_at
    )
    session.signals = analysis.signals
    session.olq_scores = analysis.olq_scores
    session.feedback = analysis.feedback
    session.overall_score = analysis.overall_score

    await _fold_into_profile(db, user.id, analysis.olq_scores)
    await db.commit()
    await db.refresh(session)
    return session


async def interview_result(db: AsyncSession, user: User, session_id: int) -> dict:
    session = await _owned_interview(db, user, session_id)
    if session.submitted_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This interview is not finished yet.")

    ids = [int(e["question_id"]) for e in (session.exchanges or []) if e.get("question_id")]
    questions = {
        q.id: q
        for q in await db.scalars(select(InterviewQuestion).where(InterviewQuestion.id.in_(ids)))
    }
    responses = [
        olq_agent.Response(text=e.get("answer", ""), ms=int(e.get("ms", 0) or 0), seconds_allowed=120)
        for e in (session.exchanges or [])
    ]
    notes = olq_agent.analyse(responses, test_type="interview").per_response_notes

    return {
        "session": session,
        "questions": questions,
        "notes": notes,
        "analysis": _stored_analysis(session),
    }


async def olq_profile(db: AsyncSession, user: User) -> dict:
    """The cumulative OLQ picture across every projective test sat so far."""
    from app.core.enums import OLQ, OLQ_LABELS

    stats = await db.get(UserStats, user.id)
    stored = dict((stats.olq_profile if stats else None) or {})
    sessions = int(stored.pop("_sessions", 0))

    ranked = sorted(
        ((k, float(v)) for k, v in stored.items() if k in {o.value for o in OLQ}),
        key=lambda kv: -kv[1],
    )
    return {
        "scores": [
            {"olq": key, "label": OLQ_LABELS[OLQ(key)], "score": value} for key, value in ranked
        ],
        "sessions_counted": sessions,
        "strongest": [OLQ_LABELS[OLQ(k)] for k, _ in ranked[:4]],
        "weakest": [OLQ_LABELS[OLQ(k)] for k, _ in ranked[-4:]],
        "updated_at": stats.updated_at if stats else None,
    }


# --- Offline answer sheets -------------------------------------------------

# What a printed sheet tells the candidate before they start. These match how
# the test is actually administered, because the point of practising on paper is
# to rehearse the real conditions rather than a friendlier version of them.
SHEET_INSTRUCTIONS: dict[PsychTestType, list[str]] = {
    PsychTestType.WAT: [
        "You will see one word at a time for 15 seconds.",
        "Write the first complete sentence that comes to mind. Do not force a moral.",
        "Number every line. Do not go back to an earlier word.",
    ],
    PsychTestType.SCT: [
        "Each line begins a sentence. Finish it in your own words.",
        "You have 30 seconds per sentence.",
        "Number every line and keep to one sentence each.",
    ],
    PsychTestType.SRT: [
        "Each item describes a situation. Write what you would do.",
        "You have roughly 30 seconds per situation.",
        "Name the action, not the feeling. Number every answer.",
    ],
    PsychTestType.TAT: [
        "Look at each picture for 30 seconds, then write for four minutes.",
        "Write a story with a past, a present and an outcome.",
        "Say who the hero is, what they want, and what they do.",
    ],
}

DEFAULT_SHEET_COUNT: dict[PsychTestType, int] = {
    PsychTestType.WAT: 60,
    PsychTestType.SCT: 60,
    PsychTestType.SRT: 60,
    PsychTestType.TAT: 12,
}


async def sheet_plan(db: AsyncSession, test_type: PsychTestType, count: int | None) -> dict:
    """The stimuli for a printable practice sheet."""
    wanted = count or DEFAULT_SHEET_COUNT.get(test_type, 30)
    items = list(
        await db.scalars(
            select(PsychItem)
            .where(PsychItem.test_type == test_type, PsychItem.status == ContentStatus.APPROVED)
            .order_by(func.random())
            .limit(wanted)
        )
    )
    if not items:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"No {test_type.value.upper()} items have been published yet.",
        )
    items.sort(key=lambda i: (i.sort_order, i.id))

    seconds = items[0].seconds if items else 30
    return {
        "test_type": test_type,
        "title": f"{test_type.value.upper()} practice sheet",
        "instructions": SHEET_INSTRUCTIONS.get(test_type, []),
        "seconds_per_item": seconds,
        "total_minutes": max(1, round(sum(i.seconds for i in items) / 60)),
        "items": items,
    }


async def submit_sheet(db: AsyncSession, user: User, data) -> PsychSession:
    """Record a sitting done on paper and transcribed.

    The session is created and submitted in one step: there was no clock running
    on this platform, so there is nothing to resume. Timing signals come from the
    duration the candidate reports, and the read-out is explicit that the words
    were transcribed rather than typed under the clock.
    """
    items = {
        item.id: item
        for item in await db.scalars(select(PsychItem).where(PsychItem.id.in_(data.item_ids)))
    }
    missing = [i for i in data.item_ids if i not in items]
    if missing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown item id(s): {missing[:5]}")

    wrong_test = [i for i in data.item_ids if str(items[i].test_type) != str(data.test_type)]
    if wrong_test:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Some items do not belong to that test. Re-generate the sheet and try again.",
        )

    answered = sum(1 for text in data.responses if text.strip())
    if answered == 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Nothing was transcribed. Correct at least one answer before submitting.",
        )

    # Per-item time is unknown on paper, so spread the reported duration evenly
    # rather than inventing per-item figures the analyser would read as real.
    per_item_ms = int((data.duration_sec * 1000) / max(1, len(data.responses)))

    responses: list[olq_agent.Response] = []
    stored: list[dict] = []
    for item_id, text in zip(data.item_ids, data.responses, strict=True):
        item = items[item_id]
        blank = not text.strip()
        responses.append(
            olq_agent.Response(
                text=text,
                ms=0 if blank else per_item_ms,
                seconds_allowed=item.seconds,
                skipped=blank,
            )
        )
        stored.append(
            {"item_id": item_id, "text": text[:2000], "ms": per_item_ms, "skipped": blank}
        )

    analysis = olq_agent.analyse(
        responses, test_type=str(data.test_type), expected_items=len(data.item_ids)
    )

    session = PsychSession(
        user_id=user.id,
        test_type=data.test_type,
        service=data.service or user.target_service,
        source=ResponseSource.SHEET,
        transcription=dict(data.transcription or {}),
        item_count=len(data.item_ids),
        answered_count=answered,
        word_count=sum(len(text.split()) for text in data.responses),
        responses=stored,
        submitted_at=_now(),
        duration_sec=data.duration_sec,
        signals=analysis.signals,
        olq_scores=analysis.olq_scores,
        feedback=analysis.feedback + _sheet_caveats(data, analysis),
        overall_score=analysis.overall_score,
    )
    db.add(session)
    await _fold_into_profile(db, user.id, analysis.olq_scores)
    await db.commit()
    await db.refresh(session)
    return session


def _sheet_caveats(data, analysis) -> list[str]:
    """Say plainly what a transcribed sitting cannot measure."""
    notes = [
        "This sitting was transcribed from a photograph, so the timing signals "
        "come from the duration you reported rather than from a running clock."
    ]
    confidence = float((data.transcription or {}).get("confidence") or 0)
    if 0 < confidence < 70:
        notes.append(
            f"The reader was only {confidence:.0f}% confident of your handwriting. "
            "If a sentence below is not what you wrote, the analysis of it is wrong "
            "-- correct it and submit again."
        )
    return notes


# --- PPDT ------------------------------------------------------------------

_POSITIVE_MOODS = {"determined", "confident", "happy", "calm", "hopeful", "alert", "cheerful"}
_NEGATIVE_MOODS = {"sad", "afraid", "angry", "worried", "tense", "hopeless", "confused"}

# People *other than* the hero. Deliberately excludes he/she/him/her/his: in a
# PPDT story those almost always refer to the hero, so counting them as company
# meant a solo story about one man read as a crowd scene.
_OTHERS = frozenset(
    """
    we they them their others another friends friend group team party members men women
    people everyone crowd villagers boys girls family parents brother sister colleagues
    soldiers officers juniors seniors together companions crew squad section neighbours
    """.split()
)


def _ppdt_consistency(perception: dict, story: str) -> list[str]:
    """Check the story against the proforma the candidate filled in.

    Screening day asks for characters, age, sex, mood and action *before* the
    story, and an assessor reads both together. A story that contradicts its own
    proforma is the single most common avoidable fault, and it is mechanically
    detectable -- which is exactly the sort of thing this platform should catch.
    """
    notes: list[str] = []
    lowered = story.lower()
    words = lowered.split()

    action = str(perception.get("action") or "").strip()
    if action:
        keywords = [w for w in action.lower().split() if len(w) > 4][:4]
        if keywords and not any(word in lowered for word in keywords):
            notes.append(
                f'Your story never carries out the action you wrote in the proforma ("{action}"). '
                "The board reads both together, so they have to agree."
            )

    mood = str(perception.get("mood") or perception.get("main_mood") or "").strip().lower()
    if mood:
        if mood in _POSITIVE_MOODS and any(w in _NEGATIVE_MOODS for w in words):
            notes.append(
                f'You recorded the mood as "{mood}" but the story reads as the opposite. '
                "Pick one and hold it."
            )
        elif mood not in lowered and len(story.split()) > 25:
            notes.append(
                f'The mood you recorded ("{mood}") never shows in the story. '
                "Let the hero act it out rather than leaving it on the form."
            )

    characters = int(perception.get("characters") or 0)
    if characters >= 2:
        from app.agents.olq import _hits, _words

        if _hits(_words(story), _OTHERS) == 0:
            notes.append(
                f"You saw {characters} characters, but only the hero appears in the story. "
                "Give the others something to do."
            )

    length = len(story.split())
    if length < 60:
        notes.append(
            f"At {length} words this is short for four minutes. A full story sets the scene, "
            "names what the hero does, and finishes with the outcome."
        )
    if not notes:
        notes.append("Your story is consistent with the perception you recorded.")
    return notes


async def submit_ppdt(db: AsyncSession, user: User, data) -> tuple[PsychSession, PsychItem, list[str]]:
    """One PPDT sitting: the proforma plus the story, analysed together."""
    item = await db.get(PsychItem, data.item_id)
    if item is None or str(item.test_type) not in {PsychTestType.PPDT, PsychTestType.TAT, PsychTestType.PSW}:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Picture not found.")

    perception = data.perception.model_dump()
    consistency = _ppdt_consistency(perception, data.story)

    # The story is one long response; split on sentences so the analyser sees
    # the structure the candidate imposed rather than one undifferentiated blob.
    from app.agents.nlp import split_sentences

    chunks = split_sentences(data.story) or [data.story]
    responses = [
        olq_agent.Response(text=chunk, ms=int(data.duration_sec * 1000 / len(chunks)), seconds_allowed=item.seconds)
        for chunk in chunks
    ]
    analysis = olq_agent.analyse(responses, test_type=str(PsychTestType.PPDT), expected_items=len(chunks))

    session = PsychSession(
        user_id=user.id,
        test_type=PsychTestType.PPDT,
        service=user.target_service,
        source=ResponseSource.ONLINE,
        item_count=1,
        answered_count=1,
        word_count=len(data.story.split()),
        responses=[
            {
                "item_id": item.id,
                "text": data.story[:6000],
                "ms": data.duration_sec * 1000,
                "skipped": False,
                "perception": perception,
            }
        ],
        submitted_at=_now(),
        duration_sec=data.duration_sec,
        signals=analysis.signals,
        olq_scores=analysis.olq_scores,
        feedback=analysis.feedback + consistency,
        overall_score=analysis.overall_score,
    )
    db.add(session)
    await _fold_into_profile(db, user.id, analysis.olq_scores)
    await db.commit()
    await db.refresh(session)
    return session, item, consistency


async def olq_trend(db: AsyncSession, user: User, limit: int = 20) -> list[dict]:
    """Overall score per sitting, oldest first, for the progress chart.

    Reads the stored score rather than recomputing: the analyser may be tuned
    between sittings, and a chart that silently re-scores history would show
    progress the candidate never made.
    """
    rows = list(
        await db.scalars(
            select(PsychSession)
            .where(PsychSession.user_id == user.id, PsychSession.submitted_at.is_not(None))
            .order_by(PsychSession.submitted_at.desc())
            .limit(limit)
        )
    )
    rows.reverse()
    return [
        {
            "id": row.id,
            "test_type": str(row.test_type),
            "submitted_at": row.submitted_at,
            "overall_score": row.overall_score or 0.0,
            "answered": row.answered_count,
            "items": row.item_count,
            "source": str(row.source),
        }
        for row in rows
    ]

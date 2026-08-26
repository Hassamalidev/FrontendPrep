"""Practice and mock tests: browse questions, sit a paper, review the result."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, OptionalUser, PageParams
from app.core.enums import ContentStatus, Difficulty
from app.models.assessment import TestTemplate
from app.schemas.assessment import (
    AttemptOut,
    AttemptResultOut,
    AttemptSectionOut,
    AttemptStartIn,
    AttemptSubmitIn,
    AttemptSummaryOut,
    TestTemplateOut,
)
from app.schemas.common import Msg, Page
from app.schemas.question import (
    QuestionOut,
    QuestionReportIn,
    QuestionReportOut,
    QuestionReviewOut,
)
from app.services import attempt_service, question_service

router = APIRouter(tags=["practice"])


@router.get("/questions", response_model=Page[QuestionOut])
async def browse_questions(
    db: DbSession,
    page: PageParams,
    module_id: Annotated[int | None, Query()] = None,
    topic_id: Annotated[int | None, Query()] = None,
    difficulty: Annotated[Difficulty | None, Query()] = None,
) -> Page[QuestionOut]:
    """Approved questions only, and never with the answer key attached."""
    rows, total = await question_service.search(
        db,
        offset=page.offset,
        limit=page.limit,
        module_id=module_id,
        topic_id=topic_id,
        difficulty=difficulty,
        approved_only=True,
    )
    return Page.build([QuestionOut.model_validate(q) for q in rows], total, page.page, page.size)


@router.post("/questions/{question_id}/report", response_model=QuestionReportOut, status_code=201)
async def report_question(
    question_id: int, data: QuestionReportIn, db: DbSession, user: OptionalUser
) -> QuestionReportOut:
    row = await question_service.report(
        db, question_id, user_id=user.id if user else None, reason=data.reason, note=data.note
    )
    return QuestionReportOut.model_validate(row)


@router.get("/tests", response_model=list[TestTemplateOut])
async def list_tests(
    db: DbSession,
    service_id: Annotated[int | None, Query()] = None,
    is_mock: Annotated[bool | None, Query()] = None,
) -> list[TestTemplateOut]:
    stmt = select(TestTemplate).where(TestTemplate.status == ContentStatus.APPROVED)
    if service_id is not None:
        stmt = stmt.where(TestTemplate.service_id == service_id)
    if is_mock is not None:
        stmt = stmt.where(TestTemplate.is_mock.is_(is_mock))
    rows = await db.scalars(stmt.order_by(TestTemplate.sort_order, TestTemplate.id))
    return [TestTemplateOut.model_validate(t) for t in rows]


def _attempt_payload(attempt, questions, sections, template=None) -> AttemptOut:
    return AttemptOut(
        id=attempt.id,
        mode=attempt.mode,
        status=attempt.status,
        started_at=attempt.started_at,
        expires_at=attempt.expires_at,
        total_questions=attempt.total_questions,
        template=TestTemplateOut.model_validate(template) if template else None,
        sections=[AttemptSectionOut(**s) for s in sections],
        questions=[QuestionOut.model_validate(q) for q in questions],
    )


@router.post("/attempts", response_model=AttemptOut, status_code=status.HTTP_201_CREATED)
async def start_attempt(data: AttemptStartIn, db: DbSession, user: CurrentUser) -> AttemptOut:
    attempt, questions, sections = await attempt_service.start(db, user, data)
    template = await db.get(TestTemplate, attempt.template_id) if attempt.template_id else None
    return _attempt_payload(attempt, questions, sections, template)


@router.get("/attempts/{attempt_id}", response_model=AttemptOut)
async def resume_attempt(attempt_id: int, db: DbSession, user: CurrentUser) -> AttemptOut:
    attempt, questions = await attempt_service.resume(db, user, attempt_id)
    sections = (attempt.topic_breakdown or {}).get("sections", [])
    template = await db.get(TestTemplate, attempt.template_id) if attempt.template_id else None
    return _attempt_payload(attempt, questions, sections, template)


@router.post("/attempts/{attempt_id}/submit", response_model=AttemptResultOut)
async def submit_attempt(
    attempt_id: int, data: AttemptSubmitIn, db: DbSession, user: CurrentUser
) -> AttemptResultOut:
    await attempt_service.submit(db, user, attempt_id, data)
    return await _result(db, user, attempt_id)


@router.get("/attempts/{attempt_id}/result", response_model=AttemptResultOut)
async def attempt_result(attempt_id: int, db: DbSession, user: CurrentUser) -> AttemptResultOut:
    return await _result(db, user, attempt_id)


async def _result(db, user, attempt_id: int) -> AttemptResultOut:
    payload = await attempt_service.review_payload(db, user, attempt_id)
    attempt = payload["attempt"]
    return AttemptResultOut(
        id=attempt.id,
        status=attempt.status,
        mode=attempt.mode,
        submitted_at=attempt.submitted_at,
        duration_sec=attempt.duration_sec,
        total_questions=attempt.total_questions,
        attempted=attempt.attempted,
        correct=attempt.correct,
        wrong=attempt.wrong,
        score=attempt.score,
        max_score=attempt.max_score,
        percentage=attempt.percentage,
        passed=attempt.passed,
        topic_breakdown={
            k: v for k, v in (attempt.topic_breakdown or {}).items() if k != "sections"
        },
        weak_topics=payload["weak_topics"],
        review=[
            {
                "question": QuestionReviewOut.model_validate(entry["question"]),
                "picked": entry["picked"],
                "correct": entry["correct"],
                "marks_awarded": entry["marks_awarded"],
                "ms": entry["ms"],
            }
            for entry in payload["review"]
        ],
    )


@router.post("/attempts/{attempt_id}/abandon", response_model=Msg)
async def abandon_attempt(attempt_id: int, db: DbSession, user: CurrentUser) -> Msg:
    await attempt_service.abandon(db, user, attempt_id)
    return Msg(detail="Attempt abandoned.")


@router.get("/attempts", response_model=Page[AttemptSummaryOut])
async def attempt_history(
    db: DbSession, user: CurrentUser, page: PageParams
) -> Page[AttemptSummaryOut]:
    rows, total = await attempt_service.history(db, user, offset=page.offset, limit=page.limit)
    return Page.build(
        [AttemptSummaryOut.model_validate(a) for a in rows], total, page.page, page.size
    )

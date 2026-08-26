"""The ISSB simulation suite: psych battery, GTO tasks, mock interview."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from app.agents import ocr
from app.core.config import settings
from app.core.deps import CurrentUser, DbSession, PageParams
from app.core.enums import GtoTaskType, GtoVenue, PsychTestType, ServiceCode
from app.schemas.common import Page
from app.schemas.issb import (
    AnalysisOut,
    GtoResultOut,
    GtoSubmitIn,
    GtoTaskOut,
    GtoTaskReviewOut,
    InterviewExchangeReview,
    InterviewQuestionOut,
    InterviewQuestionReviewOut,
    InterviewResultOut,
    InterviewSessionOut,
    InterviewStartIn,
    InterviewSubmitIn,
    OlqProfileOut,
    PpdtResultOut,
    PpdtSubmitIn,
    PsychItemOut,
    PsychItemReviewOut,
    PsychResponseReview,
    PsychResultOut,
    PsychSessionOut,
    PsychSessionStartIn,
    PsychSessionSummaryOut,
    PsychSubmitIn,
    SheetPlanOut,
    SheetSubmitIn,
    TranscribedLine,
    TranscriptionOut,
)
from app.services import issb_service

router = APIRouter(prefix="/issb", tags=["issb"])


# --- Psychological battery -------------------------------------------------


@router.post("/psych/sessions", response_model=PsychSessionOut, status_code=status.HTTP_201_CREATED)
async def start_psych(
    data: PsychSessionStartIn, db: DbSession, user: CurrentUser
) -> PsychSessionOut:
    session, items = await issb_service.start_psych(db, user, data)
    return PsychSessionOut(
        id=session.id,
        test_type=session.test_type,
        started_at=session.started_at,
        item_count=session.item_count,
        total_seconds=sum(i.seconds for i in items),
        items=[PsychItemOut.model_validate(i) for i in items],
    )


@router.post("/psych/sessions/{session_id}/submit", response_model=PsychResultOut)
async def submit_psych(
    session_id: int, data: PsychSubmitIn, db: DbSession, user: CurrentUser
) -> PsychResultOut:
    await issb_service.submit_psych(db, user, session_id, data)
    return await _psych_result(db, user, session_id)


@router.get("/psych/sessions/{session_id}", response_model=PsychResultOut)
async def psych_result(session_id: int, db: DbSession, user: CurrentUser) -> PsychResultOut:
    return await _psych_result(db, user, session_id)


async def _psych_result(db, user, session_id: int) -> PsychResultOut:
    payload = await issb_service.psych_result(db, user, session_id)
    session, items, notes = payload["session"], payload["items"], payload["notes"]

    responses: list[PsychResponseReview] = []
    for index, stored in enumerate(session.responses or []):
        item = items.get(stored.get("item_id"))
        if item is None:
            continue
        responses.append(
            PsychResponseReview(
                item=PsychItemReviewOut.model_validate(item),
                text=stored.get("text", ""),
                ms=int(stored.get("ms", 0) or 0),
                skipped=bool(stored.get("skipped")),
                notes=notes[index] if index < len(notes) else [],
            )
        )

    return PsychResultOut(
        id=session.id,
        test_type=session.test_type,
        submitted_at=session.submitted_at,
        duration_sec=session.duration_sec,
        item_count=session.item_count,
        answered_count=session.answered_count,
        word_count=session.word_count,
        analysis=AnalysisOut(**payload["analysis"]),
        responses=responses,
    )


@router.get("/psych/sessions", response_model=Page[PsychSessionSummaryOut])
async def psych_history(
    db: DbSession,
    user: CurrentUser,
    page: PageParams,
    test_type: Annotated[PsychTestType | None, Query()] = None,
) -> Page[PsychSessionSummaryOut]:
    rows, total = await issb_service.psych_history(
        db, user, offset=page.offset, limit=page.limit, test_type=test_type
    )
    return Page.build(
        [PsychSessionSummaryOut.model_validate(r) for r in rows], total, page.page, page.size
    )


# --- GTO -------------------------------------------------------------------


@router.get("/gto/tasks", response_model=Page[GtoTaskOut])
async def gto_tasks(
    db: DbSession,
    page: PageParams,
    task_type: Annotated[GtoTaskType | None, Query()] = None,
    venue: Annotated[GtoVenue | None, Query()] = None,
    service: Annotated[ServiceCode | None, Query()] = None,
) -> Page[GtoTaskOut]:
    """Indoor tasks are verbal and written; outdoor tasks are physical."""
    rows, total = await issb_service.list_gto_tasks(
        db,
        task_type=task_type,
        venue=venue,
        service=service,
        offset=page.offset,
        limit=page.limit,
    )
    return Page.build([GtoTaskOut.model_validate(t) for t in rows], total, page.page, page.size)


@router.get("/gto/tasks/{task_id}", response_model=GtoTaskOut)
async def gto_task(task_id: int, db: DbSession, user: CurrentUser) -> GtoTaskOut:
    """The brief only. The model solution is withheld until a plan is submitted."""
    return GtoTaskOut.model_validate(await issb_service.get_gto_task(db, task_id))


@router.post("/gto/tasks/{task_id}/submit", response_model=GtoResultOut, status_code=201)
async def submit_gto(
    task_id: int, data: GtoSubmitIn, db: DbSession, user: CurrentUser
) -> GtoResultOut:
    submission = await issb_service.submit_gto(db, user, task_id, data)
    task = await issb_service.get_gto_task(db, task_id)
    return GtoResultOut(
        id=submission.id,
        task=GtoTaskReviewOut.model_validate(task),
        body=submission.body,
        duration_sec=submission.duration_sec,
        created_at=submission.created_at,
        analysis=AnalysisOut(**issb_service._stored_analysis(submission)),
    )


@router.get("/gto/submissions/{submission_id}", response_model=GtoResultOut)
async def gto_submission(submission_id: int, db: DbSession, user: CurrentUser) -> GtoResultOut:
    submission = await issb_service.get_gto_submission(db, user, submission_id)
    task = await issb_service.get_gto_task(db, submission.task_id)
    return GtoResultOut(
        id=submission.id,
        task=GtoTaskReviewOut.model_validate(task),
        body=submission.body,
        duration_sec=submission.duration_sec,
        created_at=submission.created_at,
        analysis=AnalysisOut(**issb_service._stored_analysis(submission)),
    )


# --- Interview -------------------------------------------------------------


@router.post("/interview/sessions", response_model=InterviewSessionOut, status_code=201)
async def start_interview(
    data: InterviewStartIn, db: DbSession, user: CurrentUser
) -> InterviewSessionOut:
    session, questions = await issb_service.start_interview(db, user, data)
    return InterviewSessionOut(
        id=session.id,
        started_at=session.started_at,
        questions=[InterviewQuestionOut.model_validate(q) for q in questions],
    )


@router.post("/interview/sessions/{session_id}/submit", response_model=InterviewResultOut)
async def submit_interview(
    session_id: int, data: InterviewSubmitIn, db: DbSession, user: CurrentUser
) -> InterviewResultOut:
    await issb_service.submit_interview(db, user, session_id, data)
    return await _interview_result(db, user, session_id)


@router.get("/interview/sessions/{session_id}", response_model=InterviewResultOut)
async def interview_result(
    session_id: int, db: DbSession, user: CurrentUser
) -> InterviewResultOut:
    return await _interview_result(db, user, session_id)


async def _interview_result(db, user, session_id: int) -> InterviewResultOut:
    payload = await issb_service.interview_result(db, user, session_id)
    session, questions, notes = payload["session"], payload["questions"], payload["notes"]

    exchanges: list[InterviewExchangeReview] = []
    for index, stored in enumerate(session.exchanges or []):
        question = questions.get(stored.get("question_id"))
        if question is None:
            continue
        exchanges.append(
            InterviewExchangeReview(
                question=InterviewQuestionReviewOut.model_validate(question),
                answer=stored.get("answer", ""),
                ms=int(stored.get("ms", 0) or 0),
                notes=notes[index] if index < len(notes) else [],
            )
        )

    return InterviewResultOut(
        id=session.id,
        submitted_at=session.submitted_at,
        duration_sec=session.duration_sec,
        analysis=AnalysisOut(**payload["analysis"]),
        exchanges=exchanges,
    )


@router.get("/olq-profile", response_model=OlqProfileOut)
async def olq_profile(db: DbSession, user: CurrentUser) -> OlqProfileOut:
    return OlqProfileOut(**await issb_service.olq_profile(db, user))


# --- Offline answer sheets -------------------------------------------------


@router.get("/psych/sheet", response_model=SheetPlanOut)
async def practice_sheet(
    db: DbSession,
    user: CurrentUser,
    test_type: Annotated[PsychTestType, Query()],
    count: Annotated[int | None, Query(ge=1, le=100)] = None,
) -> SheetPlanOut:
    """Stimuli for a sheet to print and solve on paper.

    Practising on paper is how the test is actually sat, and it is also the only
    way to rehearse writing at speed by hand. The printed sheet and the upload
    below are two halves of the same loop.
    """
    plan = await issb_service.sheet_plan(db, test_type, count)
    return SheetPlanOut(
        test_type=plan["test_type"],
        title=plan["title"],
        instructions=plan["instructions"],
        seconds_per_item=plan["seconds_per_item"],
        total_minutes=plan["total_minutes"],
        items=[PsychItemOut.model_validate(i) for i in plan["items"]],
    )


@router.post("/psych/transcribe", response_model=TranscriptionOut)
async def transcribe_sheet(
    user: CurrentUser,
    file: Annotated[UploadFile, File(description="Photo of a completed answer sheet")],
    item_count: Annotated[int, Form(ge=1, le=100)] = 60,
) -> TranscriptionOut:
    """Read an uploaded answer sheet into an editable draft.

    The image is decoded in memory and dropped when the request ends -- it is
    never written to disk or to the database. What comes back is a *draft* the
    candidate corrects; handwriting recognition is not reliable enough to be
    treated as the answer, and the analysis only ever sees confirmed text.

    Works without OCR installed: the response then carries empty slots and the
    candidate types their answers in, which is still faster than re-sitting.
    """
    allowed = {t.strip() for t in settings.UPLOAD_ALLOWED_TYPES.split(",") if t.strip()}
    if file.content_type not in allowed:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Upload a photo ({', '.join(sorted(allowed))}). Received {file.content_type}.",
        )

    data = await file.read(settings.UPLOAD_MAX_BYTES + 1)
    if len(data) > settings.UPLOAD_MAX_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"That image is over {settings.UPLOAD_MAX_BYTES // (1024 * 1024)} MB. "
            "Photograph the sheet in daylight rather than at full resolution.",
        )
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The upload was empty.")

    result = ocr.transcribe(data)
    del data  # the bytes have served their purpose

    return TranscriptionOut(
        engine=result.engine,
        available=ocr.available(),
        note=result.note,
        mean_confidence=result.mean_confidence,
        lines=[
            TranscribedLine(index=line.index, text=line.text, confidence=line.confidence)
            for line in result.lines
        ],
        slots=ocr.align(result, item_count),
        item_count=item_count,
    )


@router.post("/psych/sheet", response_model=PsychResultOut, status_code=status.HTTP_201_CREATED)
async def submit_sheet(data: SheetSubmitIn, db: DbSession, user: CurrentUser) -> PsychResultOut:
    """Submit a paper sitting once the transcription has been confirmed."""
    session = await issb_service.submit_sheet(db, user, data)
    return await _psych_result(db, user, session.id)


# --- PPDT ------------------------------------------------------------------


@router.get("/ppdt/pictures", response_model=list[PsychItemOut])
async def ppdt_pictures(db: DbSession, user: CurrentUser) -> list[PsychItemOut]:
    plan = await issb_service.sheet_plan(db, PsychTestType.PPDT, 12)
    return [PsychItemOut.model_validate(i) for i in plan["items"]]


@router.post("/ppdt/submit", response_model=PpdtResultOut, status_code=status.HTTP_201_CREATED)
async def submit_ppdt(data: PpdtSubmitIn, db: DbSession, user: CurrentUser) -> PpdtResultOut:
    """Screening-day picture perception: the proforma and the story together."""
    session, item, consistency = await issb_service.submit_ppdt(db, user, data)
    return PpdtResultOut(
        id=session.id,
        item=PsychItemReviewOut.model_validate(item),
        perception=data.perception.model_dump(),
        story=data.story,
        duration_sec=session.duration_sec,
        analysis=AnalysisOut(**issb_service._stored_analysis(session)),
        consistency=consistency,
    )


@router.get("/olq-trend")
async def olq_trend(
    db: DbSession, user: CurrentUser, limit: Annotated[int, Query(ge=2, le=50)] = 20
) -> list[dict]:
    """Overall score per sitting, oldest first."""
    return await issb_service.olq_trend(db, user, limit)

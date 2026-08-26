"""The question-generation console.

This is the super admin's main workspace: paste an article, run the local
pipeline, inspect the trace, then approve what is worth keeping. There is no
LLM call behind any of it -- see ``app/agents/`` for the rules engine.
"""

from __future__ import annotations

from datetime import UTC
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select

from app.core.deps import AdminUser, DbSession, PageParams, SuperAdminUser
from app.core.enums import AgentRunStatus
from app.models.content import AgentRun
from app.schemas.common import Page
from app.schemas.content import AgentRunOut, GenerateIn, GenerateOut, PreviewIn
from app.services import content_service, generation_service

router = APIRouter(prefix="/agent", tags=["agent"])


@router.get("/status")
async def engine_status(admin: AdminUser) -> dict:
    """What the generator is running on right now.

    Surfaced because the answer changes with the deployment: on Render's free
    tier spaCy is usually absent and the rule engine carries the load.
    """
    from app.agents import nlp
    from app.core.config import settings

    return {
        "engine": nlp.backend_name(),
        "note": nlp.backend_note(),
        "uses_external_api": False,
        "min_quality": settings.AGENT_MIN_QUALITY,
        "max_questions_per_run": settings.AGENT_MAX_QUESTIONS,
        "min_article_chars": settings.AGENT_MIN_ARTICLE_CHARS,
        "retained_runs": settings.RETAIN_AGENT_RUNS,
    }


@router.post(
    "/articles/{article_id}/generate",
    response_model=GenerateOut,
    status_code=status.HTTP_201_CREATED,
)
async def generate(
    article_id: int, data: GenerateIn, db: DbSession, admin: SuperAdminUser
) -> GenerateOut:
    """Run the pipeline over one article.

    Set ``dry_run`` to see what would be produced without writing anything --
    the trace and the candidates come back either way.
    """
    article = await content_service.get_article(db, article_id)
    result = await generation_service.generate(db, article, data, actor=admin)
    return GenerateOut(
        run=AgentRunOut.model_validate(result["run"]),
        questions=result["questions"],
        psych_items=result["psych_items"],
        interview_questions=result["interview_questions"],
        persisted=result["persisted"],
    )


@router.get("/runs", response_model=Page[AgentRunOut])
async def runs(
    db: DbSession,
    admin: AdminUser,
    page: PageParams,
    article_id: Annotated[int | None, Query()] = None,
    run_status: Annotated[AgentRunStatus | None, Query(alias="status")] = None,
) -> Page[AgentRunOut]:
    stmt = select(AgentRun)
    if article_id is not None:
        stmt = stmt.where(AgentRun.article_id == article_id)
    if run_status is not None:
        stmt = stmt.where(AgentRun.status == run_status)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = await db.scalars(
        stmt.order_by(AgentRun.started_at.desc()).offset(page.offset).limit(page.limit)
    )
    return Page.build([AgentRunOut.model_validate(r) for r in rows], total, page.page, page.size)


@router.get("/runs/{run_id}", response_model=AgentRunOut)
async def run_detail(run_id: int, db: DbSession, admin: AdminUser) -> AgentRunOut:
    from fastapi import HTTPException

    row = await db.get(AgentRun, run_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found.")
    return AgentRunOut.model_validate(row)


@router.post("/preview", response_model=GenerateOut)
async def preview(data: PreviewIn, db: DbSession, admin: SuperAdminUser) -> GenerateOut:
    """Dry-run the pipeline over pasted text without creating an article.

    Nothing is written -- not even the run -- so this is the cheap way to judge
    whether a source is worth adding before it takes up a row.
    """
    from datetime import datetime

    from app.agents import pipeline as agent_pipeline

    config = data.model_dump(exclude={"text"})
    result = agent_pipeline.run(data.text, config)
    run = AgentRun(
        # Transient: never added to the session, so the server-side default for
        # started_at would never fire. Stamp it here or serialisation fails.
        started_at=datetime.now(UTC),
        status=AgentRunStatus.SUCCEEDED if result.questions else AgentRunStatus.FAILED,
        engine=result.engine,
        config=config,
        duration_ms=result.duration_ms,
        facts_found=result.facts_found,
        candidates=result.candidates,
        accepted=len(result.questions),
        rejected=result.rejected,
        duplicates=result.duplicates,
        avg_quality=result.avg_quality,
        trace=[s.as_dict() for s in result.trace],
        rejections=result.rejections,
        error=result.error,
    )
    return GenerateOut(
        run=AgentRunOut.model_validate(run),
        questions=[c.as_dict() for c in result.questions],
        psych_items=result.psych_items,
        interview_questions=result.interview_questions,
        persisted=False,
    )

"""Runs the agent pipeline against an article and persists what survives.

The pipeline itself is pure; everything database-shaped lives here:

* dedupe against the existing bank (one ``IN`` query, not one per candidate),
* write questions as ``draft`` unless the operator asked for auto-approval,
* record the run and its trace so the generation page can explain itself,
* prune old runs, because a trace per article on a 0.5 GB database adds up.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import pipeline as agent_pipeline
from app.core.enums import AgentRunStatus, ContentStatus, Origin, QuestionType
from app.models.catalog import Module
from app.models.content import AgentRun, Article
from app.models.issb import InterviewQuestion, PsychItem
from app.models.question import Question
from app.models.user import User
from app.schemas.content import GenerateIn
from app.services import audit, catalog_service, question_service, retention


def _now() -> datetime:
    return datetime.now(UTC)


async def _existing_fingerprints(db: AsyncSession, fingerprints: list[str]) -> set[str]:
    if not fingerprints:
        return set()
    found = set(
        await db.scalars(select(Question.fingerprint).where(Question.fingerprint.in_(fingerprints)))
    )
    found |= set(
        await db.scalars(select(PsychItem.fingerprint).where(PsychItem.fingerprint.in_(fingerprints)))
    )
    found |= set(
        await db.scalars(
            select(InterviewQuestion.fingerprint).where(
                InterviewQuestion.fingerprint.in_(fingerprints)
            )
        )
    )
    return {f for f in found if f}


async def _resolve_module(db: AsyncSession, module_id: int | None, article: Article | None) -> Module:
    """Where generated questions are filed.

    An explicit module wins. Otherwise fall back to a current-affairs module for
    the article's service, and finally to any module at all -- generating into
    the review queue is more useful than refusing over a missing default.
    """
    if module_id is not None:
        module = await db.get(Module, module_id)
        if module is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown module.")
        return module

    candidates = await catalog_service.list_modules(db)
    for keyword in ("current-affairs", "general-knowledge", "pakistan-affairs"):
        for module in candidates:
            if module.slug == keyword and (
                article is None or article.service is None or module.service_id is not None
            ):
                return module
    if candidates:
        return candidates[0]
    raise HTTPException(
        status.HTTP_409_CONFLICT,
        "No modules exist yet. Seed the catalog before generating questions.",
    )


async def generate(
    db: AsyncSession, article: Article, data: GenerateIn, *, actor: User
) -> dict:
    """Run the pipeline for one article and persist the result."""
    if not article.body:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This article has no body text (it may have been pruned by the retention job).",
        )

    module = await _resolve_module(db, data.module_id, article)
    config = data.model_dump()

    run = AgentRun(
        article_id=article.id,
        triggered_by_id=actor.id,
        status=AgentRunStatus.RUNNING,
        config=config,
    )
    db.add(run)
    await db.flush()

    result = agent_pipeline.run(article.body, config, seed=f"article-{article.id}")

    run.engine = result.engine
    run.duration_ms = result.duration_ms
    run.facts_found = result.facts_found
    run.candidates = result.candidates
    run.trace = [step.as_dict() for step in result.trace]
    run.rejections = result.rejections
    run.error = result.error
    run.finished_at = _now()

    if result.error and not result.questions:
        run.status = AgentRunStatus.FAILED
        await db.commit()
        return {"run": run, "questions": [], "psych_items": [], "interview_questions": [], "persisted": False}

    # --- dedupe against the live bank ---------------------------------
    question_fps = {
        id(c): question_service.fingerprint(c.stem, c.answer_keys, c.options)
        for c in result.questions
    }
    psych_fps = {
        index: agent_pipeline.fingerprint_text(item["prompt"], item["test_type"])
        for index, item in enumerate(result.psych_items)
    }
    interview_fps = {
        index: agent_pipeline.fingerprint_text(item["question"], item["category"])
        for index, item in enumerate(result.interview_questions)
    }

    taken = await _existing_fingerprints(
        db, [*question_fps.values(), *psych_fps.values(), *interview_fps.values()]
    )

    fresh_questions = [c for c in result.questions if question_fps[id(c)] not in taken]
    fresh_psych = [i for n, i in enumerate(result.psych_items) if psych_fps[n] not in taken]
    fresh_interview = [
        i for n, i in enumerate(result.interview_questions) if interview_fps[n] not in taken
    ]

    run.duplicates = result.duplicates + (
        len(result.questions) - len(fresh_questions)
        + len(result.psych_items) - len(fresh_psych)
        + len(result.interview_questions) - len(fresh_interview)
    )
    run.accepted = len(fresh_questions)
    run.rejected = result.rejected
    run.avg_quality = result.avg_quality

    if data.dry_run:
        run.status = AgentRunStatus.SUCCEEDED if fresh_questions else AgentRunStatus.PARTIAL
        await db.commit()
        await db.refresh(run)
        return {
            "run": run,
            "questions": [c.as_dict() for c in fresh_questions],
            "psych_items": fresh_psych,
            "interview_questions": fresh_interview,
            "persisted": False,
        }

    # --- persist -------------------------------------------------------
    target_status = ContentStatus.APPROVED if data.auto_approve else ContentStatus.DRAFT

    for candidate in fresh_questions:
        db.add(
            Question(
                service_id=module.service_id,
                module_id=module.id,
                topic_id=data.topic_id,
                qtype=QuestionType(str(candidate.qtype)),
                stem=candidate.stem,
                options=candidate.options,
                answer_keys=candidate.answer_keys,
                explanation=candidate.explanation,
                difficulty=candidate.difficulty,
                status=target_status,
                origin=Origin.AGENT,
                tags=candidate.tags or (article.tags or [])[:5],
                source_article_id=article.id,
                agent_run_id=run.id,
                quality_score=candidate.quality,
                generation_meta=candidate.as_dict()["generation_meta"],
                fingerprint=question_fps[id(candidate)],
                reviewed_by_id=actor.id if data.auto_approve else None,
                reviewed_at=_now() if data.auto_approve else None,
            )
        )

    for index, item in enumerate(result.psych_items):
        if item not in fresh_psych:
            continue
        db.add(
            PsychItem(
                test_type=item["test_type"],
                prompt=item["prompt"],
                seconds=item.get("seconds", 30),
                target_olqs=item.get("target_olqs", []),
                status=target_status,
                origin=Origin.AGENT,
                source_article_id=article.id,
                fingerprint=psych_fps[index],
                tags=item.get("tags", []),
            )
        )

    for index, item in enumerate(result.interview_questions):
        if item not in fresh_interview:
            continue
        db.add(
            InterviewQuestion(
                category=item["category"],
                question=item["question"],
                guidance=item.get("guidance"),
                follow_ups=item.get("follow_ups", []),
                target_olqs=item.get("target_olqs", []),
                service=article.service,
                status=target_status,
                origin=Origin.AGENT,
                source_article_id=article.id,
                fingerprint=interview_fps[index],
            )
        )

    # The pipeline read the article anyway; keep what it learned.
    if result.summary and not article.summary:
        article.summary = result.summary
    if result.key_points:
        article.key_points = result.key_points
    if result.entities:
        article.entities = {k: v[:12] for k, v in result.entities.items()}
    article.generated = True
    article.generated_count += len(fresh_questions)

    produced = len(fresh_questions) + len(fresh_psych) + len(fresh_interview)
    run.status = (
        AgentRunStatus.SUCCEEDED
        if produced and not result.error
        else (AgentRunStatus.PARTIAL if produced else AgentRunStatus.FAILED)
    )

    audit.record(
        db,
        actor_id=actor.id,
        action="agent.generate",
        entity="article",
        entity_id=article.id,
        detail={"run_id": run.id, "questions": len(fresh_questions), "auto_approve": data.auto_approve},
    )

    await db.flush()
    if data.auto_approve:
        await catalog_service.refresh_question_counts(db, [module.id])
    await retention.prune_agent_runs(db)
    await db.commit()
    await db.refresh(run)

    return {
        "run": run,
        "questions": [c.as_dict() for c in fresh_questions],
        "psych_items": fresh_psych,
        "interview_questions": fresh_interview,
        "persisted": True,
    }


async def generate_from_text(
    db: AsyncSession,
    *,
    text: str,
    title: str,
    source: str | None,
    source_url: str | None,
    data: GenerateIn,
    actor: User,
) -> dict:
    """Generate questions from text without storing the text.

    The article-backed path keeps a row so the trace can point at its source.
    This one does not: a news story is read once and then stale, so persisting
    thousands of them a year to a 0.5 GB budget buys nothing. The provenance
    that matters -- headline, outlet, link -- is small enough to travel on each
    question's ``generation_meta`` instead.

    No AgentRun row either. The run trace is returned to the caller and then
    discarded, because a batch of forty of them is the same waste in miniature.
    """
    module = await _resolve_module(db, data.module_id, None)
    result = agent_pipeline.run(text, data.model_dump(), seed=title)

    if result.error and not result.questions:
        return {"accepted": 0, "error": result.error, "trace": [s.as_dict() for s in result.trace]}

    fingerprints = {
        id(c): question_service.fingerprint(c.stem, c.answer_keys, c.options)
        for c in result.questions
    }
    taken = await _existing_fingerprints(db, list(fingerprints.values()))
    fresh = [c for c in result.questions if fingerprints[id(c)] not in taken]

    provenance = {"source": source, "source_url": source_url, "headline": title[:200]}
    target_status = ContentStatus.APPROVED if data.auto_approve else ContentStatus.DRAFT

    for candidate in fresh:
        meta = candidate.as_dict()["generation_meta"]
        meta["provenance"] = provenance
        db.add(
            Question(
                service_id=module.service_id,
                module_id=module.id,
                topic_id=data.topic_id,
                qtype=QuestionType(str(candidate.qtype)),
                stem=candidate.stem,
                options=candidate.options,
                answer_keys=candidate.answer_keys,
                explanation=candidate.explanation,
                difficulty=candidate.difficulty,
                status=target_status,
                origin=Origin.AGENT,
                tags=candidate.tags,
                # No source_article_id: there is no article, on purpose.
                quality_score=candidate.quality,
                generation_meta=meta,
                fingerprint=fingerprints[id(candidate)],
                reviewed_by_id=actor.id if data.auto_approve else None,
                reviewed_at=_now() if data.auto_approve else None,
            )
        )

    await db.flush()
    if data.auto_approve:
        await catalog_service.refresh_question_counts(db, [module.id])
    await db.commit()

    return {
        "accepted": len(fresh),
        "duplicates": len(result.questions) - len(fresh),
        "rejected": result.rejected,
        "trace": [s.as_dict() for s in result.trace],
        "error": result.error,
    }

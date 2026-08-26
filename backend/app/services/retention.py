"""The job that keeps the database inside the free tier.

Neon's free project is 0.5 GB. Nothing here is optional housekeeping -- without
it the three tables that grow without bound (agent traces, article bodies,
attempt answer blobs) fill the disk and the platform stops accepting writes.

Every pass is idempotent and drops only *detail*: scores, counts and summaries
survive forever, so a student's history stays intact while the bytes behind it
are released.

Run it from the API (``POST /admin/maintenance/prune``) or a cron worker:

    python -m app.services.retention
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import AttemptStatus
from app.models.assessment import Attempt
from app.models.content import AgentRun, Article
from app.models.question import QuestionReport
from app.models.user import AuditLog, RefreshToken


def _now() -> datetime:
    return datetime.now(UTC)


async def prune_agent_runs(db: AsyncSession) -> int:
    keep = list(
        await db.scalars(
            select(AgentRun.id)
            .order_by(AgentRun.started_at.desc())
            .limit(settings.RETAIN_AGENT_RUNS)
        )
    )
    if len(keep) < settings.RETAIN_AGENT_RUNS:
        return 0
    return (await db.execute(delete(AgentRun).where(AgentRun.id.notin_(keep)))).rowcount or 0


async def prune_article_bodies(db: AsyncSession) -> int:
    """Drop raw bodies once questions have been generated from them.

    ``summary``, ``key_points`` and ``body_hash`` stay, so the article still
    renders and a re-paste is still detected as a duplicate.
    """
    cutoff = _now() - timedelta(days=settings.RETAIN_ARTICLE_BODY_DAYS)
    result = await db.execute(
        update(Article)
        .where(
            Article.created_at < cutoff,
            Article.generated.is_(True),
            Article.body_pruned.is_(False),
            Article.body.is_not(None),
        )
        .values(body=None, body_pruned=True)
    )
    return result.rowcount or 0


async def prune_attempt_detail(db: AsyncSession) -> int:
    """Drop per-answer JSON from old attempts, keeping the score line."""
    cutoff = _now() - timedelta(days=settings.RETAIN_ATTEMPT_DETAIL_DAYS)
    result = await db.execute(
        update(Attempt)
        .where(
            Attempt.submitted_at.is_not(None),
            Attempt.submitted_at < cutoff,
            Attempt.detail_pruned.is_(False),
        )
        .values(answers=[], blueprint=[], detail_pruned=True)
    )
    return result.rowcount or 0


async def expire_stale_attempts(db: AsyncSession) -> int:
    """Close attempts whose clock ran out but were never submitted."""
    result = await db.execute(
        update(Attempt)
        .where(
            Attempt.status == AttemptStatus.IN_PROGRESS,
            Attempt.expires_at.is_not(None),
            Attempt.expires_at < _now(),
        )
        .values(status=AttemptStatus.EXPIRED)
    )
    return result.rowcount or 0


async def prune_sessions(db: AsyncSession) -> int:
    result = await db.execute(
        delete(RefreshToken).where(RefreshToken.expires_at < _now() - timedelta(days=2))
    )
    return result.rowcount or 0


async def prune_audit(db: AsyncSession, *, keep_days: int = 120) -> int:
    result = await db.execute(
        delete(AuditLog).where(AuditLog.created_at < _now() - timedelta(days=keep_days))
    )
    return result.rowcount or 0


async def prune_resolved_reports(db: AsyncSession, *, keep_days: int = 60) -> int:
    result = await db.execute(
        delete(QuestionReport).where(
            QuestionReport.resolved.is_(True),
            QuestionReport.created_at < _now() - timedelta(days=keep_days),
        )
    )
    return result.rowcount or 0


async def run_all(db: AsyncSession) -> dict[str, int]:
    """Every pass, in one transaction. Returns rows touched per step."""
    report = {
        "expired_attempts": await expire_stale_attempts(db),
        "agent_runs_deleted": await prune_agent_runs(db),
        "article_bodies_dropped": await prune_article_bodies(db),
        "attempt_details_dropped": await prune_attempt_detail(db),
        "sessions_deleted": await prune_sessions(db),
        "audit_rows_deleted": await prune_audit(db),
        "reports_deleted": await prune_resolved_reports(db),
    }
    await db.commit()
    return report


async def estimate_size(db: AsyncSession) -> dict[str, int]:
    """Row counts for the tables that actually grow, for the admin panel."""
    from app.models.issb import GtoSubmission, InterviewSession, PsychSession
    from app.models.question import Question

    async def count(model) -> int:
        return await db.scalar(select(func.count()).select_from(model)) or 0

    return {
        "questions": await count(Question),
        "attempts": await count(Attempt),
        "psych_sessions": await count(PsychSession),
        "interview_sessions": await count(InterviewSession),
        "gto_submissions": await count(GtoSubmission),
        "articles": await count(Article),
        "agent_runs": await count(AgentRun),
        "audit_logs": await count(AuditLog),
    }


async def _main() -> None:
    from app.core.database import dispose_engine, session_scope

    async with session_scope() as db:
        report = await run_all(db)
    for key, value in report.items():
        print(f"{key}: {value}")
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(_main())

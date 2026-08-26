"""Staff endpoints: review queue, catalog editing, users, maintenance.

Everything here sits behind ``AdminUser`` (or ``SuperAdminUser`` for the
destructive parts) and writes an audit row through the service layer.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.core.config import settings
from app.core.deps import AdminUser, DbSession, PageParams, SuperAdminUser
from app.core.enums import ContentStatus, Difficulty, Origin, QuestionType, Role
from app.models.catalog import Module, Program, Topic
from app.models.content import ContactMessage
from app.models.user import User
from app.schemas.catalog import (
    ModuleIn,
    ModuleOut,
    ModuleUpdate,
    ProgramIn,
    ProgramOut,
    ProgramUpdate,
    TopicIn,
    TopicOut,
    TopicUpdate,
)
from app.schemas.common import Msg, Page
from app.schemas.content import (
    AnnouncementIn,
    AnnouncementOut,
    ArticleIn,
    ArticleOut,
    ArticleUpdate,
    ContactMessageOut,
    NoteDetailOut,
    NoteIn,
)
from app.schemas.question import (
    BulkReviewIn,
    QuestionAdminOut,
    QuestionIn,
    QuestionUpdate,
    ReviewDecisionIn,
)
from app.schemas.user import AdminUserOut, AdminUserUpdate
from app.services import audit, catalog_service, content_service, question_service, retention

router = APIRouter(prefix="/admin", tags=["admin"])


# --- Question bank ---------------------------------------------------------


@router.get("/questions", response_model=Page[QuestionAdminOut])
async def list_questions(
    db: DbSession,
    admin: AdminUser,
    page: PageParams,
    module_id: Annotated[int | None, Query()] = None,
    topic_id: Annotated[int | None, Query()] = None,
    qstatus: Annotated[ContentStatus | None, Query(alias="status")] = None,
    difficulty: Annotated[Difficulty | None, Query()] = None,
    qtype: Annotated[QuestionType | None, Query()] = None,
    origin: Annotated[Origin | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
) -> Page[QuestionAdminOut]:
    rows, total = await question_service.search(
        db,
        offset=page.offset,
        limit=page.limit,
        module_id=module_id,
        topic_id=topic_id,
        qstatus=qstatus,
        difficulty=difficulty,
        qtype=qtype,
        origin=origin,
        q=q,
    )
    return Page.build(
        [QuestionAdminOut.model_validate(x) for x in rows], total, page.page, page.size
    )


@router.get("/questions/queue", response_model=Page[QuestionAdminOut])
async def review_queue(db: DbSession, admin: AdminUser, page: PageParams) -> Page[QuestionAdminOut]:
    """Agent output waiting for a human decision, worst-quality first.

    Reviewing the weakest items first is deliberate: they are the ones that
    reveal whether the critic threshold needs moving.
    """
    from app.models.question import Question

    stmt = select(Question).where(Question.status == ContentStatus.DRAFT)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = await db.scalars(
        stmt.order_by(Question.quality_score.asc().nullsfirst(), Question.id)
        .offset(page.offset)
        .limit(page.limit)
    )
    return Page.build(
        [QuestionAdminOut.model_validate(x) for x in rows], total, page.page, page.size
    )


@router.post("/questions", response_model=QuestionAdminOut, status_code=status.HTTP_201_CREATED)
async def create_question(data: QuestionIn, db: DbSession, admin: AdminUser) -> QuestionAdminOut:
    return QuestionAdminOut.model_validate(await question_service.create(db, data, author=admin))


@router.patch("/questions/{question_id}", response_model=QuestionAdminOut)
async def update_question(
    question_id: int, data: QuestionUpdate, db: DbSession, admin: AdminUser
) -> QuestionAdminOut:
    row = await question_service.update_one(db, question_id, data, author=admin)
    return QuestionAdminOut.model_validate(row)


@router.delete("/questions/{question_id}", response_model=Msg)
async def delete_question(question_id: int, db: DbSession, admin: AdminUser) -> Msg:
    await question_service.delete_one(db, question_id, author=admin)
    return Msg(detail="Question deleted.")


@router.post("/questions/{question_id}/review", response_model=Msg)
async def review_question(
    question_id: int, data: ReviewDecisionIn, db: DbSession, admin: AdminUser
) -> Msg:
    await question_service.review(
        db, [question_id], decision=data.status, note=data.note, reviewer=admin
    )
    return Msg(detail=f"Question marked {data.status.value}.")


@router.post("/questions/review", response_model=Msg)
async def bulk_review(data: BulkReviewIn, db: DbSession, admin: AdminUser) -> Msg:
    touched = await question_service.review(
        db, data.ids, decision=data.status, note=data.note, reviewer=admin
    )
    return Msg(detail=f"{touched} question(s) marked {data.status.value}.")


# --- Catalog editing -------------------------------------------------------


@router.post("/modules", response_model=ModuleOut, status_code=status.HTTP_201_CREATED)
async def create_module(data: ModuleIn, db: DbSession, admin: AdminUser) -> ModuleOut:
    module = Module(**data.model_dump())
    db.add(module)
    audit.record(db, actor_id=admin.id, action="module.create", entity="module")
    await db.commit()
    await db.refresh(module)
    return ModuleOut.model_validate(module)


@router.patch("/modules/{module_id}", response_model=ModuleOut)
async def update_module(
    module_id: int, data: ModuleUpdate, db: DbSession, admin: AdminUser
) -> ModuleOut:
    module = await db.get(Module, module_id)
    if module is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Module not found.")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(module, field, value)
    audit.record(
        db, actor_id=admin.id, action="module.update", entity="module", entity_id=module_id
    )
    await db.commit()
    await db.refresh(module)
    return ModuleOut.model_validate(module)


@router.post("/topics", response_model=TopicOut, status_code=status.HTTP_201_CREATED)
async def create_topic(data: TopicIn, db: DbSession, admin: AdminUser) -> TopicOut:
    topic = Topic(**data.model_dump())
    db.add(topic)
    audit.record(db, actor_id=admin.id, action="topic.create", entity="topic")
    await db.commit()
    await db.refresh(topic)
    return TopicOut.model_validate(topic)


@router.patch("/topics/{topic_id}", response_model=TopicOut)
async def update_topic(
    topic_id: int, data: TopicUpdate, db: DbSession, admin: AdminUser
) -> TopicOut:
    topic = await db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Topic not found.")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(topic, field, value)
    await db.commit()
    await db.refresh(topic)
    return TopicOut.model_validate(topic)


@router.post("/programs", response_model=ProgramOut, status_code=status.HTTP_201_CREATED)
async def create_program(data: ProgramIn, db: DbSession, admin: AdminUser) -> ProgramOut:
    program = Program(**data.model_dump())
    db.add(program)
    audit.record(db, actor_id=admin.id, action="program.create", entity="program")
    await db.commit()
    await db.refresh(program)
    return ProgramOut.model_validate(program)


@router.patch("/programs/{program_id}", response_model=ProgramOut)
async def update_program(
    program_id: int, data: ProgramUpdate, db: DbSession, admin: AdminUser
) -> ProgramOut:
    program = await db.get(Program, program_id)
    if program is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Program not found.")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(program, field, value)
    await db.commit()
    await db.refresh(program)
    return ProgramOut.model_validate(program)


# --- Content ---------------------------------------------------------------


@router.get("/articles", response_model=Page[ArticleOut])
async def admin_articles(
    db: DbSession,
    admin: AdminUser,
    page: PageParams,
    q: Annotated[str | None, Query(max_length=120)] = None,
) -> Page[ArticleOut]:
    rows, total = await content_service.list_articles(
        db, offset=page.offset, limit=page.limit, published_only=False, q=q
    )
    return Page.build([ArticleOut.model_validate(a) for a in rows], total, page.page, page.size)


@router.post("/articles", response_model=ArticleOut, status_code=status.HTTP_201_CREATED)
async def create_article(data: ArticleIn, db: DbSession, admin: AdminUser) -> ArticleOut:
    return ArticleOut.model_validate(await content_service.create_article(db, data, author=admin))


@router.get("/articles/{article_id}", response_model=ArticleOut)
async def admin_article(article_id: int, db: DbSession, admin: AdminUser) -> ArticleOut:
    return ArticleOut.model_validate(await content_service.get_article(db, article_id))


@router.patch("/articles/{article_id}", response_model=ArticleOut)
async def update_article(
    article_id: int, data: ArticleUpdate, db: DbSession, admin: AdminUser
) -> ArticleOut:
    row = await content_service.update_article(db, article_id, data, author=admin)
    return ArticleOut.model_validate(row)


@router.delete("/articles/{article_id}", response_model=Msg)
async def delete_article(article_id: int, db: DbSession, admin: AdminUser) -> Msg:
    await content_service.delete_article(db, article_id, author=admin)
    return Msg(detail="Article deleted.")


@router.post("/notes", response_model=NoteDetailOut, status_code=status.HTTP_201_CREATED)
async def create_note(data: NoteIn, db: DbSession, admin: AdminUser) -> NoteDetailOut:
    return NoteDetailOut.model_validate(await content_service.create_note(db, data, author=admin))


@router.post("/announcements", response_model=AnnouncementOut, status_code=201)
async def create_announcement(
    data: AnnouncementIn, db: DbSession, admin: AdminUser
) -> AnnouncementOut:
    row = await content_service.create_announcement(db, data, author=admin)
    return AnnouncementOut.model_validate(row)


@router.get("/contact-messages", response_model=Page[ContactMessageOut])
async def contact_messages(
    db: DbSession,
    admin: AdminUser,
    page: PageParams,
    handled: Annotated[bool | None, Query()] = None,
) -> Page[ContactMessageOut]:
    stmt = select(ContactMessage)
    if handled is not None:
        stmt = stmt.where(ContactMessage.handled.is_(handled))
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = await db.scalars(
        stmt.order_by(ContactMessage.created_at.desc()).offset(page.offset).limit(page.limit)
    )
    return Page.build(
        [ContactMessageOut.model_validate(m) for m in rows], total, page.page, page.size
    )


# --- Users -----------------------------------------------------------------


@router.get("/users", response_model=Page[AdminUserOut])
async def list_users(
    db: DbSession,
    admin: AdminUser,
    page: PageParams,
    q: Annotated[str | None, Query(max_length=120)] = None,
    role: Annotated[Role | None, Query()] = None,
) -> Page[AdminUserOut]:
    stmt = select(User)
    if role is not None:
        stmt = stmt.where(User.role == role)
    if q:
        term = f"%{q.strip()}%"
        stmt = stmt.where(User.full_name.ilike(term) | User.email.ilike(term))
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = await db.scalars(
        stmt.order_by(User.created_at.desc()).offset(page.offset).limit(page.limit)
    )
    return Page.build([AdminUserOut.model_validate(u) for u in rows], total, page.page, page.size)


@router.patch("/users/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: int, data: AdminUserUpdate, db: DbSession, admin: SuperAdminUser
) -> AdminUserOut:
    """Role and status changes are super-admin only, and never self-applied.

    Letting an admin edit their own row is how an account locks itself out or
    quietly promotes itself; both need a second person.
    """
    target = await db.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    if target.id == admin.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Ask another super admin to change your own account."
        )

    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(target, field, value)

    audit.record(
        db,
        actor_id=admin.id,
        action="user.update",
        entity="user",
        entity_id=user_id,
        detail=changes,
    )
    await db.commit()
    await db.refresh(target)
    return AdminUserOut.model_validate(target)


# --- Maintenance -----------------------------------------------------------


@router.get("/maintenance/size")
async def database_size(db: DbSession, admin: AdminUser) -> dict:
    """Row counts for the tables that grow, so the 0.5 GB budget is visible."""
    return await retention.estimate_size(db)


@router.post("/maintenance/prune")
async def prune(db: DbSession, admin: SuperAdminUser) -> dict:
    """Run every retention pass now. Drops detail only; scores are kept."""
    report = await retention.run_all(db)
    audit.record(db, actor_id=admin.id, action="maintenance.prune", entity="system", detail=report)
    await db.commit()
    return report


@router.post("/maintenance/recount", response_model=Msg)
async def recount(db: DbSession, admin: AdminUser) -> Msg:
    touched = await catalog_service.refresh_question_counts(db)
    await db.commit()
    return Msg(detail=f"Refreshed {touched} counter(s).")


# --- News ingestion --------------------------------------------------------


@router.post("/news/generate")
async def generate_from_news(
    db: DbSession,
    admin: AdminUser,
    days: Annotated[int, Query(ge=1, le=30)] = 7,
    limit: Annotated[int, Query(ge=1, le=40)] = 12,
    auto_approve: Annotated[bool, Query()] = False,
) -> dict:
    """Turn this week's news into questions, storing only the questions.

    The stories themselves are never written to the database -- they are read
    from public RSS, generated from in memory, and dropped. What is kept is the
    question, with the headline and outlet recorded on it, which is the part
    that stays useful after the news has gone stale.
    """
    from app.schemas.content import GenerateIn
    from app.services import generation_service, news_service

    items = await news_service.live_items(days, limit)
    config = GenerateIn(
        mcq=4, true_false=2, fill_blank=1, short_answer=0,
        sct=1, srt=1, interview=1,
        auto_approve=auto_approve, dry_run=False,
    )

    accepted = duplicates = skipped = 0
    for item in items:
        if len(item.text) < settings.NEWS_MIN_CHARS:
            skipped += 1
            continue
        try:
            outcome = await generation_service.generate_from_text(
                db,
                text=f"{item.title}. {item.text}",
                title=item.title,
                source=item.source,
                source_url=item.link,
                data=config,
                actor=admin,
            )
        except Exception:  # one bad story must not end the batch
            skipped += 1
            continue
        accepted += outcome.get("accepted", 0)
        duplicates += outcome.get("duplicates", 0)

    audit.record(
        db, actor_id=admin.id, action="news.generate", entity="question",
        detail={"stories": len(items), "accepted": accepted},
    )
    await db.commit()

    return {
        "stories_read": len(items),
        "questions_drafted": accepted,
        "duplicates_skipped": duplicates,
        "stories_skipped": skipped,
        "articles_stored": 0,
        "note": "Stories are read from memory and discarded; only questions are kept.",
    }


@router.get("/news/cache")
async def news_cache(admin: AdminUser) -> dict:
    """What the feed cache is holding, and proof it is not in the database."""
    from app.services import news_service

    return news_cache_state(news_service)


def news_cache_state(news_service) -> dict:
    return news_service.cache_state()


@router.post("/news/fetch")
async def fetch_news(
    db: DbSession,
    admin: AdminUser,
    days: Annotated[int, Query(ge=1, le=30)] = 7,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    generate: Annotated[bool, Query()] = False,
) -> dict:
    """Pull recent stories from the configured public RSS feeds.

    Reads syndication feeds -- the format publishers provide for this -- and
    stores the headline, summary, source and link. It does not copy any other
    site's question bank; with ``generate`` set, questions are written from the
    stories by this platform's own pipeline and land in the review queue.
    """
    from app.services import news_service

    report = await news_service.ingest(db, actor=admin, days=days, limit=limit)

    if generate and report["articles"]:
        from app.schemas.content import GenerateIn
        from app.services import content_service, generation_service

        produced = 0
        for entry in report["articles"]:
            article = await content_service.get_article(db, entry["id"])
            try:
                result = await generation_service.generate(
                    db,
                    article,
                    GenerateIn(
                        mcq=4, true_false=2, fill_blank=1, short_answer=0,
                        sct=1, srt=1, interview=1,
                        auto_approve=False, dry_run=False,
                    ),
                    actor=admin,
                )
                produced += len(result["questions"])
            except Exception:  # one bad article must not end the batch
                continue
        report["questions_drafted"] = produced

    return report

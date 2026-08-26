"""Public content: articles, notes, testimonials, announcements, contact."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.core.deps import DbSession, OptionalUser, PageParams
from app.core.enums import ServiceCode
from app.schemas.common import Msg, Page
from app.schemas.content import (
    AnnouncementOut,
    ArticleOut,
    ArticleSummaryOut,
    ContactIn,
    NoteDetailOut,
    NoteOut,
    TestimonialIn,
    TestimonialOut,
)
from app.services import content_service

router = APIRouter(tags=["content"])


@router.get("/news")
async def live_news(
    days: Annotated[int, Query(ge=1, le=30)] = 7,
    limit: Annotated[int, Query(ge=1, le=40)] = 12,
) -> dict:
    """Current affairs, read live from public news feeds.

    Deliberately not stored. These are read once and then stale, and keeping a
    few thousand a year would fill a free-tier database with content nobody
    re-reads. They are cached in process memory instead; the durable artefact is
    the question generated from a story, not the story.
    """
    from app.services import news_service

    items = await news_service.live_items(days, limit)
    return {
        "stored": False,
        "items": [
            {
                "title": item.title,
                "summary": item.summary[:400],
                "source": item.source,
                "url": item.link,
                "published": item.published.isoformat() if item.published else None,
            }
            for item in items
        ],
    }


@router.get("/articles", response_model=Page[ArticleSummaryOut])
async def articles(
    db: DbSession,
    page: PageParams,
    category: Annotated[str | None, Query(max_length=40)] = None,
    service: Annotated[ServiceCode | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
) -> Page[ArticleSummaryOut]:
    rows, total = await content_service.list_articles(
        db, offset=page.offset, limit=page.limit, category=category, service=service, q=q
    )
    return Page.build(
        [ArticleSummaryOut.model_validate(a) for a in rows], total, page.page, page.size
    )


@router.get("/articles/{ref}", response_model=ArticleOut)
async def article(ref: str, db: DbSession) -> ArticleOut:
    from fastapi import HTTPException

    from app.core.enums import ContentStatus

    row = await content_service.get_article(db, ref)
    if row.status != ContentStatus.APPROVED:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Article not found.")
    return ArticleOut.model_validate(row)


@router.get("/notes", response_model=Page[NoteOut])
async def notes(
    db: DbSession,
    page: PageParams,
    module_id: Annotated[int | None, Query()] = None,
    topic_id: Annotated[int | None, Query()] = None,
    service: Annotated[ServiceCode | None, Query()] = None,
) -> Page[NoteOut]:
    rows, total = await content_service.list_notes(
        db,
        offset=page.offset,
        limit=page.limit,
        module_id=module_id,
        topic_id=topic_id,
        service=service,
    )
    return Page.build([NoteOut.model_validate(n) for n in rows], total, page.page, page.size)


@router.get("/notes/{ref}", response_model=NoteDetailOut)
async def note(ref: str, db: DbSession) -> NoteDetailOut:
    return NoteDetailOut.model_validate(await content_service.get_note(db, ref))


@router.get("/testimonials", response_model=list[TestimonialOut])
async def testimonials(
    db: DbSession,
    service: Annotated[ServiceCode | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 12,
) -> list[TestimonialOut]:
    rows = await content_service.list_testimonials(db, limit=limit, service=service)
    return [TestimonialOut.model_validate(t) for t in rows]


@router.post("/testimonials", response_model=Msg, status_code=status.HTTP_201_CREATED)
async def submit_testimonial(data: TestimonialIn, db: DbSession, user: OptionalUser) -> Msg:
    await content_service.submit_testimonial(db, data, user=user)
    return Msg(detail="Thank you. Your story will appear once it has been reviewed.")


@router.get("/announcements", response_model=list[AnnouncementOut])
async def announcements(
    db: DbSession, service: Annotated[ServiceCode | None, Query()] = None
) -> list[AnnouncementOut]:
    rows = await content_service.live_announcements(db, service=service)
    return [AnnouncementOut.model_validate(a) for a in rows]


@router.post("/contact", response_model=Msg, status_code=status.HTTP_201_CREATED)
async def contact(data: ContactIn, db: DbSession) -> Msg:
    await content_service.record_contact(db, data)
    return Msg(detail="Message received. We will get back to you shortly.")

"""Articles, notes, testimonials, announcements and the contact inbox."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from fastapi import HTTPException, status
from slugify import slugify
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ContentStatus, ServiceCode
from app.models.content import Announcement, Article, ContactMessage, Note, Testimonial
from app.models.user import User
from app.schemas.content import (
    AnnouncementIn,
    ArticleIn,
    ArticleUpdate,
    ContactIn,
    NoteIn,
    TestimonialIn,
)
from app.services import audit


def _now() -> datetime:
    return datetime.now(UTC)


def body_hash(text: str) -> str:
    """Hash of the normalised body, so a re-paste is recognised as a duplicate."""
    normalised = " ".join((text or "").split()).lower()
    return hashlib.sha1(normalised.encode("utf-8")).hexdigest()[:40]


async def _unique_slug(db: AsyncSession, model, title: str, *, limit: int = 200) -> str:
    base = slugify(title)[:limit] or "item"
    slug = base
    suffix = 2
    while await db.scalar(select(model.id).where(model.slug == slug)):
        slug = f"{base[: limit - 4]}-{suffix}"
        suffix += 1
    return slug


# --- Articles --------------------------------------------------------------


async def create_article(db: AsyncSession, data: ArticleIn, *, author: User) -> Article:
    digest = body_hash(data.body)
    existing = await db.scalar(select(Article).where(Article.body_hash == digest))
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"This text was already added as article #{existing.id} ({existing.title}).",
        )

    article = Article(
        **data.model_dump(exclude={"body"}),
        body=data.body,
        slug=await _unique_slug(db, Article, data.title, limit=250),
        body_chars=len(data.body),
        body_hash=digest,
        author_id=author.id,
    )
    db.add(article)
    audit.record(db, actor_id=author.id, action="article.create", entity="article")
    await db.commit()
    await db.refresh(article)
    return article


async def get_article(db: AsyncSession, ref: str | int) -> Article:
    stmt = select(Article)
    stmt = stmt.where(Article.id == int(ref)) if str(ref).isdigit() else stmt.where(Article.slug == str(ref))
    article = await db.scalar(stmt)
    if article is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Article not found.")
    return article


async def update_article(
    db: AsyncSession, article_id: int, data: ArticleUpdate, *, author: User
) -> Article:
    article = await get_article(db, article_id)
    changes = data.model_dump(exclude_unset=True)

    if "body" in changes and changes["body"] is not None:
        article.body_chars = len(changes["body"])
        article.body_hash = body_hash(changes["body"])
        article.body_pruned = False
    if "title" in changes and changes["title"] and changes["title"] != article.title:
        article.slug = await _unique_slug(db, Article, changes["title"], limit=250)

    for field, value in changes.items():
        setattr(article, field, value)

    audit.record(
        db,
        actor_id=author.id,
        action="article.update",
        entity="article",
        entity_id=article.id,
        detail={"fields": sorted(changes)},
    )
    await db.commit()
    await db.refresh(article)
    return article


async def delete_article(db: AsyncSession, article_id: int, *, author: User) -> None:
    article = await get_article(db, article_id)
    await db.delete(article)
    audit.record(
        db, actor_id=author.id, action="article.delete", entity="article", entity_id=article_id
    )
    await db.commit()


async def list_articles(
    db: AsyncSession,
    *,
    offset: int,
    limit: int,
    category: str | None = None,
    service: ServiceCode | None = None,
    published_only: bool = True,
    q: str | None = None,
) -> tuple[list[Article], int]:
    stmt = select(Article)
    if published_only:
        stmt = stmt.where(Article.status == ContentStatus.APPROVED)
    if category:
        stmt = stmt.where(Article.category == category)
    if service is not None:
        stmt = stmt.where(or_(Article.service == service, Article.service.is_(None)))
    if q:
        stmt = stmt.where(Article.title.ilike(f"%{q.strip()}%"))

    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        await db.scalars(
            stmt.order_by(Article.is_featured.desc(), Article.published_on.desc().nullslast(), Article.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    return rows, total


# --- Notes -----------------------------------------------------------------


async def create_note(db: AsyncSession, data: NoteIn, *, author: User) -> Note:
    note = Note(
        **data.model_dump(),
        slug=await _unique_slug(db, Note, data.title, limit=210),
        author_id=author.id,
    )
    db.add(note)
    audit.record(db, actor_id=author.id, action="note.create", entity="note")
    await db.commit()
    await db.refresh(note)
    return note


async def list_notes(
    db: AsyncSession,
    *,
    offset: int,
    limit: int,
    module_id: int | None = None,
    topic_id: int | None = None,
    service: ServiceCode | None = None,
) -> tuple[list[Note], int]:
    stmt = select(Note).where(Note.status == ContentStatus.APPROVED)
    if module_id is not None:
        stmt = stmt.where(Note.module_id == module_id)
    if topic_id is not None:
        stmt = stmt.where(Note.topic_id == topic_id)
    if service is not None:
        stmt = stmt.where(or_(Note.service == service, Note.service.is_(None)))

    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        await db.scalars(stmt.order_by(Note.sort_order, Note.id).offset(offset).limit(limit))
    )
    return rows, total


async def get_note(db: AsyncSession, ref: str | int) -> Note:
    stmt = select(Note)
    stmt = stmt.where(Note.id == int(ref)) if str(ref).isdigit() else stmt.where(Note.slug == str(ref))
    note = await db.scalar(stmt)
    if note is None or note.status != ContentStatus.APPROVED:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Note not found.")
    note.view_count += 1
    await db.commit()
    return note


# --- Testimonials / announcements / contact --------------------------------


async def submit_testimonial(
    db: AsyncSession, data: TestimonialIn, *, user: User | None
) -> Testimonial:
    row = Testimonial(
        **data.model_dump(),
        user_id=user.id if user else None,
        status=ContentStatus.IN_REVIEW,  # never publish straight from the form
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def list_testimonials(
    db: AsyncSession, *, limit: int = 12, service: ServiceCode | None = None
) -> list[Testimonial]:
    stmt = select(Testimonial).where(Testimonial.status == ContentStatus.APPROVED)
    if service is not None:
        stmt = stmt.where(or_(Testimonial.service == service, Testimonial.service.is_(None)))
    return list(
        await db.scalars(
            stmt.order_by(Testimonial.is_featured.desc(), Testimonial.created_at.desc()).limit(limit)
        )
    )


async def live_announcements(
    db: AsyncSession, *, service: ServiceCode | None = None, limit: int = 5
) -> list[Announcement]:
    now = _now()
    stmt = select(Announcement).where(
        Announcement.is_active.is_(True),
        (Announcement.starts_at.is_(None)) | (Announcement.starts_at <= now),
        (Announcement.ends_at.is_(None)) | (Announcement.ends_at >= now),
    )
    if service is not None:
        stmt = stmt.where(or_(Announcement.service == service, Announcement.service.is_(None)))
    return list(await db.scalars(stmt.order_by(Announcement.starts_at.desc().nullslast()).limit(limit)))


async def create_announcement(
    db: AsyncSession, data: AnnouncementIn, *, author: User
) -> Announcement:
    row = Announcement(**data.model_dump())
    db.add(row)
    audit.record(db, actor_id=author.id, action="announcement.create", entity="announcement")
    await db.commit()
    await db.refresh(row)
    return row


async def record_contact(db: AsyncSession, data: ContactIn) -> ContactMessage:
    row = ContactMessage(**data.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row

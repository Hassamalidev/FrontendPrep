"""Articles, notes and announcements -- plus the agent run trace.

``Article`` is the super admin's single input surface: paste a current-affairs
piece, and the agent pipeline turns it into questions, SCT/SRT items and
interview prompts. The raw body is the largest text in the schema, so it is
dropped by the retention job once its questions are approved; ``summary`` and
``body_hash`` stay so duplicates are still detected.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import AgentRunStatus, ContentStatus, ServiceCode
from app.models.base import Base, JSONBType, TimestampMixin, enum_column


class Article(Base, TimestampMixin):
    """Source material for the agentic generator."""

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    slug: Mapped[str] = mapped_column(String(260), nullable=False, unique=True)

    # "current_affairs" | "defence" | "pakistan_affairs" | "general_knowledge"
    # | "science" | "islamiat" | "english" | "announcement"
    category: Mapped[str] = mapped_column(String(40), default="current_affairs", nullable=False)
    service = enum_column(ServiceCode, name="article_service", nullable=True)

    body: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    # Salient sentences the segmenter picked, kept for the "key points" card.
    key_points: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(120))
    source_url: Mapped[str | None] = mapped_column(String(500))
    cover_url: Mapped[str | None] = mapped_column(String(400))
    published_on: Mapped[date | None] = mapped_column(Date)

    body_chars: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    body_hash: Mapped[str | None] = mapped_column(String(40), index=True)
    body_pruned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    tags: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)
    entities: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)

    status = enum_column(
        ContentStatus, name="article_status", default=ContentStatus.DRAFT, nullable=False
    )
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # True once at least one agent run has produced items for this article.
    generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    generated_count: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)

    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    __table_args__ = (
        Index("ix_articles_feed", "status", "published_on"),
        Index("ix_articles_category", "category", "status"),
    )


class AgentRun(Base):
    """One execution of the question-generation pipeline, with its trace.

    The trace is what makes the system inspectable rather than magic: the super
    admin can see each agent's input count, output count, timing and rejections.
    Only the most recent ``RETAIN_AGENT_RUNS`` rows are kept.
    """

    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int | None] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), index=True
    )
    triggered_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    status = enum_column(
        AgentRunStatus, name="agent_run_status", default=AgentRunStatus.QUEUED, nullable=False
    )
    engine: Mapped[str] = mapped_column(String(32), default="rules", nullable=False)
    # What the operator asked for: counts per output kind, difficulty target.
    config: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    facts_found: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    candidates: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    accepted: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    rejected: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    duplicates: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    avg_quality: Mapped[float | None] = mapped_column(Float)

    # [{"agent": "extract", "in": 18, "out": 42, "ms": 31, "notes": [...]}]
    trace: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)
    # Sampled rejection reasons, for tuning the critic thresholds.
    rejections: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (Index("ix_agent_runs_recent", "started_at"),)


class Note(Base, TimestampMixin):
    """Study notes / handouts, filed under a module."""

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module_id: Mapped[int | None] = mapped_column(ForeignKey("modules.id", ondelete="SET NULL"))
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"))
    service = enum_column(ServiceCode, name="note_service", nullable=True)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, unique=True)
    summary: Mapped[str | None] = mapped_column(String(400))
    body: Mapped[str] = mapped_column(Text, nullable=False)  # markdown
    reading_minutes: Mapped[int] = mapped_column(SmallInteger, default=3, nullable=False)
    attachment_url: Mapped[str | None] = mapped_column(String(400))
    tags: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)

    status = enum_column(
        ContentStatus, name="note_status", default=ContentStatus.APPROVED, nullable=False
    )
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)

    __table_args__ = (Index("ix_notes_module", "module_id", "status", "sort_order"),)


class Testimonial(Base, TimestampMixin):
    """Student success stories, moderated before they appear publicly."""

    __tablename__ = "testimonials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    author_name: Mapped[str] = mapped_column(String(120), nullable=False)
    headline: Mapped[str | None] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    service = enum_column(ServiceCode, name="testimonial_service", nullable=True)
    program_name: Mapped[str | None] = mapped_column(String(120))
    outcome: Mapped[str | None] = mapped_column(String(60))  # "Recommended", "Selected"
    rating: Mapped[int] = mapped_column(SmallInteger, default=5, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(400))
    status = enum_column(
        ContentStatus, name="testimonial_status", default=ContentStatus.IN_REVIEW, nullable=False
    )
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (Index("ix_testimonials_live", "status", "is_featured"),)


class Announcement(Base, TimestampMixin):
    """Banner notices: intake dates, schedule changes, maintenance windows."""

    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(16), default="info", nullable=False)
    service = enum_column(ServiceCode, name="announcement_service", nullable=True)
    link_url: Mapped[str | None] = mapped_column(String(400))
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (Index("ix_announcements_live", "is_active", "starts_at"),)


class ContactMessage(Base):
    """Inbound enquiries from the public contact form."""

    __tablename__ = "contact_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(160), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(24))
    subject: Mapped[str | None] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    handled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_contact_messages_open", "handled", "created_at"),)

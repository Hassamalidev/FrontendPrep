"""Articles, notes, testimonials, announcements, contact and agent runs."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import EmailStr, Field

from app.core.config import settings
from app.core.enums import AgentRunStatus, ContentStatus, Difficulty, ServiceCode
from app.schemas.common import InputModel, ORMModel


class ArticleSummaryOut(ORMModel):
    id: int
    title: str
    slug: str
    category: str
    service: ServiceCode | None = None
    summary: str | None = None
    key_points: list[str] = []
    cover_url: str | None = None
    source_name: str | None = None
    published_on: date | None = None
    tags: list[str] = []
    is_featured: bool = False
    generated_count: int = 0


class ArticleOut(ArticleSummaryOut):
    body: str | None = None
    source_url: str | None = None
    entities: dict = {}
    body_pruned: bool = False
    status: ContentStatus
    generated: bool = False
    created_at: datetime


class ArticleIn(InputModel):
    title: str = Field(min_length=3, max_length=240)
    body: str = Field(min_length=1, max_length=settings.MAX_UPLOAD_CHARS)
    category: str = Field(default="current_affairs", max_length=40)
    service: ServiceCode | None = None
    summary: str | None = Field(default=None, max_length=4000)
    source_name: str | None = Field(default=None, max_length=120)
    source_url: str | None = Field(default=None, max_length=500)
    cover_url: str | None = Field(default=None, max_length=400)
    published_on: date | None = None
    tags: list[str] = Field(default_factory=list, max_length=20)
    status: ContentStatus = ContentStatus.DRAFT
    is_featured: bool = False


class ArticleUpdate(InputModel):
    title: str | None = Field(default=None, min_length=3, max_length=240)
    body: str | None = Field(default=None, max_length=settings.MAX_UPLOAD_CHARS)
    category: str | None = Field(default=None, max_length=40)
    service: ServiceCode | None = None
    summary: str | None = Field(default=None, max_length=4000)
    source_name: str | None = Field(default=None, max_length=120)
    source_url: str | None = Field(default=None, max_length=500)
    cover_url: str | None = Field(default=None, max_length=400)
    published_on: date | None = None
    tags: list[str] | None = Field(default=None, max_length=20)
    status: ContentStatus | None = None
    is_featured: bool | None = None


# --- Agent runs ------------------------------------------------------------


class GenerateIn(InputModel):
    """What the super admin asks the pipeline for."""

    mcq: int = Field(default=10, ge=0, le=settings.AGENT_MAX_QUESTIONS)
    true_false: int = Field(default=4, ge=0, le=settings.AGENT_MAX_QUESTIONS)
    fill_blank: int = Field(default=3, ge=0, le=settings.AGENT_MAX_QUESTIONS)
    short_answer: int = Field(default=0, ge=0, le=settings.AGENT_MAX_QUESTIONS)
    sct: int = Field(default=0, ge=0, le=40)
    srt: int = Field(default=0, ge=0, le=40)
    interview: int = Field(default=0, ge=0, le=40)
    module_id: int | None = None
    topic_id: int | None = None
    difficulty: Difficulty | None = None
    min_quality: float | None = Field(default=None, ge=0, le=1)
    auto_approve: bool = False
    dry_run: bool = False


class PreviewIn(GenerateIn):
    """Dry-run over pasted text that is not (yet) an article."""

    text: str = Field(min_length=1, max_length=settings.MAX_UPLOAD_CHARS)


class AgentTraceStep(ORMModel):
    agent: str
    label: str | None = None
    input: int = 0
    output: int = 0
    ms: int = 0
    notes: list[str] = []


class AgentRunOut(ORMModel):
    # None for a preview run: /agent/preview scores pasted text without writing
    # anything, so there is no row and therefore no id.
    id: int | None = None
    article_id: int | None = None
    status: AgentRunStatus
    engine: str
    config: dict = {}
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: int = 0
    facts_found: int = 0
    candidates: int = 0
    accepted: int = 0
    rejected: int = 0
    duplicates: int = 0
    avg_quality: float | None = None
    trace: list[dict] = []
    rejections: list[dict] = []
    error: str | None = None


class GenerateOut(ORMModel):
    run: AgentRunOut
    questions: list[dict] = []
    psych_items: list[dict] = []
    interview_questions: list[dict] = []
    persisted: bool = True


# --- Notes / testimonials / announcements / contact ------------------------


class NoteOut(ORMModel):
    id: int
    module_id: int | None = None
    topic_id: int | None = None
    service: ServiceCode | None = None
    title: str
    slug: str
    summary: str | None = None
    reading_minutes: int
    attachment_url: str | None = None
    tags: list[str] = []
    view_count: int = 0


class NoteDetailOut(NoteOut):
    body: str
    status: ContentStatus
    created_at: datetime


class NoteIn(InputModel):
    module_id: int | None = None
    topic_id: int | None = None
    service: ServiceCode | None = None
    title: str = Field(min_length=3, max_length=200)
    summary: str | None = Field(default=None, max_length=400)
    body: str = Field(min_length=1, max_length=settings.MAX_UPLOAD_CHARS)
    reading_minutes: int = Field(default=3, ge=1, le=180)
    attachment_url: str | None = Field(default=None, max_length=400)
    tags: list[str] = Field(default_factory=list, max_length=20)
    status: ContentStatus = ContentStatus.APPROVED
    sort_order: int = Field(default=0, ge=0, le=9999)


class TestimonialOut(ORMModel):
    id: int
    author_name: str
    headline: str | None = None
    body: str
    service: ServiceCode | None = None
    program_name: str | None = None
    outcome: str | None = None
    rating: int
    avatar_url: str | None = None
    is_featured: bool = False
    created_at: datetime


class TestimonialIn(InputModel):
    author_name: str = Field(min_length=2, max_length=120)
    headline: str | None = Field(default=None, max_length=160)
    body: str = Field(min_length=10, max_length=4000)
    service: ServiceCode | None = None
    program_name: str | None = Field(default=None, max_length=120)
    outcome: str | None = Field(default=None, max_length=60)
    rating: int = Field(default=5, ge=1, le=5)
    avatar_url: str | None = Field(default=None, max_length=400)


class AnnouncementOut(ORMModel):
    id: int
    title: str
    body: str | None = None
    level: str
    service: ServiceCode | None = None
    link_url: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class AnnouncementIn(InputModel):
    title: str = Field(min_length=3, max_length=200)
    body: str | None = Field(default=None, max_length=4000)
    level: str = Field(default="info", max_length=16)
    service: ServiceCode | None = None
    link_url: str | None = Field(default=None, max_length=400)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_active: bool = True


class ContactIn(InputModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=24)
    subject: str | None = Field(default=None, max_length=200)
    message: str = Field(min_length=5, max_length=4000)


class ContactMessageOut(ORMModel):
    id: int
    name: str
    email: EmailStr
    phone: str | None = None
    subject: str | None = None
    message: str
    handled: bool
    created_at: datetime

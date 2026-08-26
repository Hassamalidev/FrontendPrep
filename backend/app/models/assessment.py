"""Test blueprints and attempts.

The storage decision that matters here: an attempt keeps its per-question
answers in a single JSONB column instead of an ``attempt_answers`` child table.

  1 000 students x 12 mock tests x 100 questions
    = 1.2 M rows in a child table (~180 MB with indexes)
    = 12 000 rows here (~40 MB)

Since answers are only ever read back as a whole -- to render one result page --
there is no query that the normalised form would serve better.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
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

from app.core.enums import AttemptStatus, ContentStatus, ServiceCode
from app.models.base import Base, JSONBType, TimestampMixin, enum_column


class TestTemplate(Base, TimestampMixin):
    """A reusable exam definition: sections, counts, timing, marking scheme."""

    __tablename__ = "test_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(90), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    service_id: Mapped[int | None] = mapped_column(ForeignKey("services.id", ondelete="CASCADE"))
    stage_id: Mapped[int | None] = mapped_column(ForeignKey("stages.id", ondelete="SET NULL"))
    program_id: Mapped[int | None] = mapped_column(ForeignKey("programs.id", ondelete="SET NULL"))

    # Sections are resolved into concrete questions at attempt-start time, so a
    # template stays valid as the bank grows:
    # [{"module_slug": "verbal-intelligence", "count": 25, "minutes": 20,
    #   "difficulty_mix": {"easy": 0.3, "medium": 0.5, "hard": 0.2}}]
    sections: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)

    duration_min: Mapped[int] = mapped_column(SmallInteger, default=45, nullable=False)
    total_questions: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    pass_percentage: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    negative_marking: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    shuffle_questions: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    shuffle_options: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_answers_after: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    is_mock: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_free: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status = enum_column(
        ContentStatus, name="template_status", default=ContentStatus.APPROVED, nullable=False
    )
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)

    __table_args__ = (Index("ix_test_templates_live", "service_id", "status", "is_mock"),)


class Attempt(Base):
    """One sitting of a test or a practice drill."""

    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("test_templates.id", ondelete="SET NULL")
    )
    module_id: Mapped[int | None] = mapped_column(ForeignKey("modules.id", ondelete="SET NULL"))
    service = enum_column(ServiceCode, name="attempt_service", nullable=True)

    # "mock" | "practice" | "module" | "daily"
    mode: Mapped[str] = mapped_column(String(16), default="practice", nullable=False)
    status = enum_column(
        AttemptStatus, name="attempt_status", default=AttemptStatus.IN_PROGRESS, nullable=False
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_sec: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # The frozen question set: [{"id": 41, "keys": ["b"], "marks": 1.0,
    # "topic_id": 3, "order": ["b","a","d","c"]}]. Freezing the answer key here
    # means grading never re-reads the questions table, and editing a question
    # later cannot retroactively change a submitted paper.
    blueprint: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)
    # [{"id": 41, "picked": ["b"], "ms": 12400, "flagged": false}]
    answers: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)

    total_questions: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    attempted: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    correct: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    wrong: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    passed: Mapped[bool | None] = mapped_column(Boolean)

    # {"topic-slug": {"seen": 5, "correct": 3}} -- powers the weak-areas panel
    # without re-reading the answers blob.
    topic_breakdown: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)
    # Set by the retention job once detail is pruned; scores survive forever.
    detail_pruned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        Index("ix_attempts_user_recent", "user_id", "started_at"),
        Index("ix_attempts_user_status", "user_id", "status"),
        Index("ix_attempts_template", "template_id", "percentage"),
    )


class PracticeCard(Base):
    """Spaced-repetition state for one (user, question) pair.

    SM-2 lite: only questions the student got *wrong* or flagged earn a card, so
    this table tracks mistakes rather than mirroring the whole bank.
    """


    __tablename__ = "practice_cards"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True
    )
    ease: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    interval_days: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    repetitions: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    lapses: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    due_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_practice_cards_due", "user_id", "due_on"),)


class PhysicalLog(Base):
    """Self-reported physical training entries for the fitness module."""

    __tablename__ = "physical_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    logged_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # {"run_1600m_sec": 470, "push_ups": 22, "sit_ups": 30, "chin_ups": 6,
    #  "weight_kg": 68.5}
    metrics: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)
    note: Mapped[str | None] = mapped_column(String(280))

    __table_args__ = (Index("ix_physical_logs_user", "user_id", "logged_on"),)

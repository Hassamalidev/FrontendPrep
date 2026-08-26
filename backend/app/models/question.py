"""The question bank.

Storage note: options live in a JSONB array on the question row rather than a
child ``question_options`` table. Four options per question would otherwise mean
four extra rows, four index entries and a join on every fetch; as JSONB it is one
TOAST-compressed column. On a 0.5 GB budget that difference decides how many
questions fit.
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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import ContentStatus, Difficulty, Origin, QuestionType
from app.models.base import Base, JSONBType, TimestampMixin, enum_column


class Question(Base, TimestampMixin):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Denormalised service_id/stage_id alongside topic_id: practice queries filter
    # by service+stage constantly and this removes two joins from the hot path.
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), nullable=False
    )
    module_id: Mapped[int] = mapped_column(
        ForeignKey("modules.id", ondelete="CASCADE"), nullable=False
    )
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"))

    qtype = enum_column(
        QuestionType, name="question_type", default=QuestionType.MCQ, nullable=False
    )
    stem: Mapped[str] = mapped_column(Text, nullable=False)
    # [{"key": "a", "text": "..."}] -- key is stable, order is display order.
    options: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)
    # Option key(s). A single-answer question stores one element.
    answer_keys: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text)
    hint: Mapped[str | None] = mapped_column(String(280))

    difficulty = enum_column(
        Difficulty, name="question_difficulty", default=Difficulty.MEDIUM, nullable=False
    )
    marks: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    negative_marks: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    time_hint_sec: Mapped[int] = mapped_column(SmallInteger, default=45, nullable=False)

    status = enum_column(
        ContentStatus, name="question_status", default=ContentStatus.DRAFT, nullable=False
    )
    origin = enum_column(Origin, name="question_origin", default=Origin.HUMAN, nullable=False)

    # Non-verbal / figure questions reference images by URL only -- never bytes.
    media: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)
    tags: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)

    # --- Provenance for agent-generated items ------------------------------
    source_article_id: Mapped[int | None] = mapped_column(
        ForeignKey("articles.id", ondelete="SET NULL")
    )
    agent_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL")
    )
    quality_score: Mapped[float | None] = mapped_column(Float)
    # Critic breakdown + the template that produced it, for tuning the engine.
    generation_meta: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)

    # Dedupe key: normalised stem + sorted answers, hashed. Unique when set.
    fingerprint: Mapped[str | None] = mapped_column(String(40), unique=True)

    reviewed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str | None] = mapped_column(String(400))

    # --- Live difficulty calibration ---------------------------------------
    times_served: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    times_correct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        # The single most important index: "give me approved questions for this
        # module". Partial, so drafts and rejects cost nothing to keep.
        Index(
            "ix_questions_live",
            "module_id",
            "difficulty",
            postgresql_where=text("status = 'approved'"),
        ),
        Index("ix_questions_topic_status", "topic_id", "status"),
        Index("ix_questions_review_queue", "status", "created_at"),
        Index("ix_questions_service", "service_id", "status"),
    )

    @property
    def facility(self) -> float | None:
        """Observed proportion correct -- feeds difficulty recalibration."""
        return (
            round(self.times_correct / self.times_served, 3) if self.times_served >= 20 else None
        )


class QuestionReport(Base):
    """Student-flagged problems ("wrong answer", "typo"). Small, prunable."""

    __tablename__ = "question_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reason: Mapped[str] = mapped_column(String(40), nullable=False)
    note: Mapped[str | None] = mapped_column(String(400))
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

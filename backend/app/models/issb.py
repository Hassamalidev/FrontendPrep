"""The ISSB simulation suite: psychological battery, GTO tasks and interview.

These tests have no "correct answer" -- they are projective. So instead of
grading, the platform runs each response through a heuristic OLQ analyser
(``app/agents/olq.py``) and shows the candidate what a board might read into
their writing: response rate, positivity, self-reference, decisiveness, and
which Officer Like Qualities their answers project.

Retention: ``PsychSession`` is the fastest-growing table in the schema (a
single WAT sitting is 60 rows if modelled naively). It is therefore stored as
*one row per sitting* with a JSONB response array, not one row per word.
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import (
    ContentStatus,
    Difficulty,
    GtoTaskType,
    GtoVenue,
    Origin,
    PsychTestType,
    ResponseSource,
    ServiceCode,
)
from app.models.base import Base, JSONBType, TimestampMixin, enum_column


class PsychItem(Base, TimestampMixin):
    """One stimulus: a WAT word, an SCT stem, an SRT situation, a TAT picture."""

    __tablename__ = "psych_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    test_type = enum_column(PsychTestType, name="psych_test_type", nullable=False)

    # WAT: the word. SCT: the incomplete sentence. SRT: the situation text.
    # TAT/PSW: an optional caption; the picture itself lives at image_url.
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(400))
    # TAT slides are deliberately hazy; this is the "what candidates typically
    # perceive" note, shown after submission rather than during.
    perception_hint: Mapped[str | None] = mapped_column(Text)

    # Seconds allowed for this single item (WAT 15s, SCT 30s, SRT 30s, TAT 4min).
    seconds: Mapped[int] = mapped_column(SmallInteger, default=30, nullable=False)
    # Which OLQs a strong response to this item tends to demonstrate.
    target_olqs: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)
    # Worked example shown in review mode.
    model_answer: Mapped[str | None] = mapped_column(Text)

    difficulty = enum_column(
        Difficulty, name="psych_difficulty", default=Difficulty.MEDIUM, nullable=False
    )
    status = enum_column(
        ContentStatus, name="psych_status", default=ContentStatus.APPROVED, nullable=False
    )
    origin = enum_column(Origin, name="psych_origin", default=Origin.HUMAN, nullable=False)
    source_article_id: Mapped[int | None] = mapped_column(
        ForeignKey("articles.id", ondelete="SET NULL")
    )
    fingerprint: Mapped[str | None] = mapped_column(String(40), unique=True)
    tags: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (Index("ix_psych_items_live", "test_type", "status", "sort_order"),)


class PsychSession(Base):
    """One sitting of one psychological test, with every response inline.

    ``responses`` is ``[{"item_id": 12, "text": "...", "ms": 4200, "skipped": false}]``.
    A 60-word WAT is one row, not sixty.
    """

    __tablename__ = "psych_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    test_type = enum_column(PsychTestType, name="psych_session_type", nullable=False)
    service = enum_column(ServiceCode, name="psych_session_service", nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_sec: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    item_count: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    answered_count: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Where the responses came from. A sheet that was photographed and
    # transcribed is analysed the same way, but the read-out says so -- the OCR
    # pass and the candidate's corrections are both part of what produced it.
    source = enum_column(
        ResponseSource, name="psych_session_source", default=ResponseSource.ONLINE, nullable=False
    )
    # {"engine": "tesseract", "confidence": 71.4, "lines": 58, "edited": 12}
    # Never the image: uploads are read in memory and dropped.
    transcription: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)

    responses: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)

    # --- Heuristic read-out, computed once at submit -----------------------
    # {"positivity": 0.72, "self_reference": 0.4, "decisiveness": 0.61, ...}
    signals: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)
    # {"determination": 3.8, "initiative": 4.1, ...} on a 1-5 scale
    olq_scores: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)
    feedback: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)
    overall_score: Mapped[float | None] = mapped_column(Float)

    __table_args__ = (Index("ix_psych_sessions_user", "user_id", "test_type", "started_at"),)


class GtoTask(Base, TimestampMixin):
    """A Group Testing Officer exercise brief.

    Self-practice can only go so far for genuinely group tasks, so each row
    carries the brief, the constraints, an assessor rubric and (for planning
    exercises) a model solution the candidate compares their own plan against.
    """

    __tablename__ = "gto_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_type = enum_column(GtoTaskType, name="gto_task_type", nullable=False)
    # Derived from task_type, but stored so the two halves of the series can be
    # listed and indexed separately -- candidates work on them at different
    # times and in different ways.
    venue = enum_column(GtoVenue, name="gto_venue", default=GtoVenue.OUTDOOR, nullable=False)
    service = enum_column(ServiceCode, name="gto_service", nullable=True)

    title: Mapped[str] = mapped_column(String(180), nullable=False)
    # The narrative the GTO reads out.
    brief: Mapped[str] = mapped_column(Text, nullable=False)
    # ["No member may touch the red area", "The load weighs 40 kg", ...]
    constraints: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)
    resources: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)
    map_url: Mapped[str | None] = mapped_column(String(400))

    planning_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    execution_seconds: Mapped[int] = mapped_column(Integer, default=900, nullable=False)
    group_size: Mapped[int] = mapped_column(SmallInteger, default=8, nullable=False)

    # A worked plan: priorities, resource allocation, timeline.
    model_solution: Mapped[str | None] = mapped_column(Text)
    # [{"olq": "organising_ability", "look_for": "..."}]
    rubric: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)
    target_olqs: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)

    difficulty = enum_column(
        Difficulty, name="gto_difficulty", default=Difficulty.MEDIUM, nullable=False
    )
    status = enum_column(
        ContentStatus, name="gto_status", default=ContentStatus.APPROVED, nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        Index("ix_gto_tasks_live", "task_type", "status"),
        Index("ix_gto_tasks_venue", "venue", "status", "sort_order"),
    )


class GtoSubmission(Base):
    """A candidate's written plan / lecturette notes for a GTO task."""

    __tablename__ = "gto_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[int] = mapped_column(
        ForeignKey("gto_tasks.id", ondelete="CASCADE"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    duration_sec: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Rubric coverage the analyser detected: {"organising_ability": 4.0, ...}
    olq_scores: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)
    signals: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)
    feedback: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)
    overall_score: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    task: Mapped[GtoTask] = relationship()

    __table_args__ = (Index("ix_gto_submissions_user", "user_id", "created_at"),)


class InterviewQuestion(Base, TimestampMixin):
    """Interviewing Officer / Deputy President question bank."""

    __tablename__ = "interview_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service = enum_column(ServiceCode, name="interview_service", nullable=True)
    # personal, family, academic, current_affairs, defence, situational, religion
    category: Mapped[str] = mapped_column(String(48), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    guidance: Mapped[str | None] = mapped_column(Text)
    follow_ups: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)
    target_olqs: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)
    difficulty = enum_column(
        Difficulty, name="interview_difficulty", default=Difficulty.MEDIUM, nullable=False
    )
    status = enum_column(
        ContentStatus, name="interview_status", default=ContentStatus.APPROVED, nullable=False
    )
    origin = enum_column(Origin, name="interview_origin", default=Origin.HUMAN, nullable=False)
    source_article_id: Mapped[int | None] = mapped_column(
        ForeignKey("articles.id", ondelete="SET NULL")
    )
    fingerprint: Mapped[str | None] = mapped_column(String(40), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (Index("ix_interview_live", "category", "status"),)


class InterviewSession(Base):
    """A mock interview run: questions asked, answers typed, timings."""

    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    service = enum_column(ServiceCode, name="interview_session_service", nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_sec: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # [{"question_id": 4, "answer": "...", "ms": 31000}]
    exchanges: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)
    signals: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)
    olq_scores: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)
    feedback: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)
    overall_score: Mapped[float | None] = mapped_column(Float)

    __table_args__ = (Index("ix_interview_sessions_user", "user_id", "started_at"),)

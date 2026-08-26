"""Model registry.

Importing this package binds every mapped class to ``Base.metadata``. Alembic's
``env.py`` and the test fixtures import from here rather than from the
individual modules, so a new table is picked up by adding it to ``__all__``.
"""

from __future__ import annotations

from app.models.assessment import (
    Attempt,
    PhysicalLog,
    PracticeCard,
    TestTemplate,
)
from app.models.base import Base, JSONBType, TimestampMixin, enum_column
from app.models.catalog import Module, Program, Service, Stage, Topic
from app.models.content import (
    AgentRun,
    Announcement,
    Article,
    ContactMessage,
    Note,
    Testimonial,
)
from app.models.issb import (
    GtoSubmission,
    GtoTask,
    InterviewQuestion,
    InterviewSession,
    PsychItem,
    PsychSession,
)
from app.models.question import Question, QuestionReport
from app.models.user import AuditLog, RefreshToken, User, UserStats

__all__ = [
    "Base",
    "JSONBType",
    "TimestampMixin",
    "enum_column",
    # catalog
    "Service",
    "Program",
    "Stage",
    "Module",
    "Topic",
    # users
    "User",
    "RefreshToken",
    "UserStats",
    "AuditLog",
    # content
    "Article",
    "AgentRun",
    "Note",
    "Testimonial",
    "Announcement",
    "ContactMessage",
    # questions
    "Question",
    "QuestionReport",
    # assessment
    "TestTemplate",
    "Attempt",
    "PracticeCard",
    "PhysicalLog",
    # issb
    "PsychItem",
    "PsychSession",
    "GtoTask",
    "GtoSubmission",
    "InterviewQuestion",
    "InterviewSession",
]

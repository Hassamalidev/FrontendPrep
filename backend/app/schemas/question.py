"""Question bank models.

Two read shapes matter: ``QuestionOut`` (what a student sees while sitting a
paper -- no answer keys, no explanation) and ``QuestionAdminOut`` (the full row
for the review queue). Keeping them separate is what stops an answer key from
leaking through a careless ``response_model``.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, model_validator

from app.core.enums import ContentStatus, Difficulty, Origin, QuestionType
from app.schemas.common import InputModel, ORMModel


class OptionOut(ORMModel):
    key: str
    text: str


class QuestionOut(ORMModel):
    """Student-facing. Deliberately has no ``answer_keys`` field."""

    id: int
    module_id: int
    topic_id: int | None = None
    qtype: QuestionType
    stem: str
    options: list[dict] = []
    hint: str | None = None
    difficulty: Difficulty
    marks: float = 1.0
    negative_marks: float = 0.0
    time_hint_sec: int = 45
    media: dict = {}


class QuestionReviewOut(QuestionOut):
    """Adds the answer -- used after submission and in review mode."""

    answer_keys: list[str] = []
    explanation: str | None = None


class QuestionAdminOut(QuestionReviewOut):
    service_id: int
    status: ContentStatus
    origin: Origin
    tags: list[str] = []
    quality_score: float | None = None
    generation_meta: dict = {}
    source_article_id: int | None = None
    agent_run_id: int | None = None
    fingerprint: str | None = None
    times_served: int = 0
    times_correct: int = 0
    facility: float | None = None
    reviewed_by_id: int | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None
    created_at: datetime
    updated_at: datetime


class QuestionIn(InputModel):
    module_id: int
    topic_id: int | None = None
    qtype: QuestionType = QuestionType.MCQ
    stem: str = Field(min_length=5, max_length=4000)
    options: list[dict] = Field(default_factory=list, max_length=10)
    answer_keys: list[str] = Field(default_factory=list, max_length=10)
    explanation: str | None = Field(default=None, max_length=4000)
    hint: str | None = Field(default=None, max_length=280)
    difficulty: Difficulty = Difficulty.MEDIUM
    marks: float = Field(default=1.0, ge=0, le=20)
    negative_marks: float = Field(default=0.0, ge=0, le=20)
    time_hint_sec: int = Field(default=45, ge=5, le=1800)
    media: dict = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list, max_length=20)
    status: ContentStatus = ContentStatus.DRAFT

    @model_validator(mode="after")
    def _answers_match_options(self) -> QuestionIn:
        needs_options = self.qtype in {
            QuestionType.MCQ,
            QuestionType.MULTI_SELECT,
            QuestionType.TRUE_FALSE,
            QuestionType.NON_VERBAL,
        }
        if not needs_options:
            return self

        keys = [str(o.get("key", "")).strip() for o in self.options]
        if len(keys) < 2:
            raise ValueError("A choice question needs at least two options.")
        if len(set(keys)) != len(keys):
            raise ValueError("Option keys must be unique.")
        if any(not k for k in keys):
            raise ValueError("Every option needs a non-empty key.")
        if not self.answer_keys:
            raise ValueError("At least one answer key is required.")
        unknown = set(self.answer_keys) - set(keys)
        if unknown:
            raise ValueError(f"Answer key(s) not among the options: {sorted(unknown)}")
        if self.qtype != QuestionType.MULTI_SELECT and len(self.answer_keys) != 1:
            raise ValueError("This question type takes exactly one answer key.")
        return self


class QuestionUpdate(InputModel):
    topic_id: int | None = None
    stem: str | None = Field(default=None, min_length=5, max_length=4000)
    options: list[dict] | None = Field(default=None, max_length=10)
    answer_keys: list[str] | None = Field(default=None, max_length=10)
    explanation: str | None = Field(default=None, max_length=4000)
    hint: str | None = Field(default=None, max_length=280)
    difficulty: Difficulty | None = None
    marks: float | None = Field(default=None, ge=0, le=20)
    negative_marks: float | None = Field(default=None, ge=0, le=20)
    time_hint_sec: int | None = Field(default=None, ge=5, le=1800)
    media: dict | None = None
    tags: list[str] | None = Field(default=None, max_length=20)
    status: ContentStatus | None = None


class ReviewDecisionIn(InputModel):
    status: ContentStatus
    note: str | None = Field(default=None, max_length=400)


class BulkReviewIn(InputModel):
    ids: list[int] = Field(min_length=1, max_length=200)
    status: ContentStatus
    note: str | None = Field(default=None, max_length=400)


class QuestionReportIn(InputModel):
    reason: str = Field(max_length=40)
    note: str | None = Field(default=None, max_length=400)


class QuestionReportOut(ORMModel):
    id: int
    question_id: int
    user_id: int | None = None
    reason: str
    note: str | None = None
    resolved: bool
    created_at: datetime

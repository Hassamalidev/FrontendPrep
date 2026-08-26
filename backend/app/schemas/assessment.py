"""Test templates, attempts and the practice/fitness models."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, model_validator

from app.core.enums import AttemptStatus, ContentStatus, Difficulty, ServiceCode
from app.schemas.common import InputModel, ORMModel
from app.schemas.question import QuestionOut, QuestionReviewOut


class SectionSpec(InputModel):
    module_slug: str = Field(max_length=90)
    count: int = Field(ge=1, le=200)
    minutes: int | None = Field(default=None, ge=1, le=300)
    title: str | None = Field(default=None, max_length=120)
    difficulty_mix: dict[Difficulty, float] | None = None


class TestTemplateOut(ORMModel):
    id: int
    slug: str
    title: str
    description: str | None = None
    service_id: int | None = None
    stage_id: int | None = None
    program_id: int | None = None
    sections: list[dict] = []
    duration_min: int
    total_questions: int
    pass_percentage: float
    negative_marking: float
    show_answers_after: bool
    is_mock: bool
    is_free: bool
    sort_order: int = 0


class TestTemplateIn(InputModel):
    slug: str = Field(min_length=2, max_length=90, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=2, max_length=160)
    description: str | None = None
    service_id: int | None = None
    stage_id: int | None = None
    program_id: int | None = None
    sections: list[SectionSpec] = Field(min_length=1, max_length=12)
    duration_min: int = Field(default=45, ge=1, le=300)
    pass_percentage: float = Field(default=50.0, ge=0, le=100)
    negative_marking: float = Field(default=0.0, ge=0, le=5)
    shuffle_questions: bool = True
    shuffle_options: bool = True
    show_answers_after: bool = True
    is_mock: bool = False
    is_free: bool = True
    status: ContentStatus = ContentStatus.APPROVED
    sort_order: int = Field(default=0, ge=0, le=9999)


# --- Attempts --------------------------------------------------------------


class AttemptStartIn(InputModel):
    """Start from a template, or from a module for an ad-hoc drill."""

    template_id: int | None = None
    module_id: int | None = None
    topic_id: int | None = None
    count: int = Field(default=20, ge=1, le=100)
    difficulty: Difficulty | None = None
    mode: str = Field(default="practice", max_length=16)
    only_weak: bool = False  # draw from the student's spaced-repetition backlog

    @model_validator(mode="after")
    def _needs_a_source(self) -> AttemptStartIn:
        if self.template_id is None and self.module_id is None and not self.only_weak:
            raise ValueError("Provide template_id, module_id, or set only_weak.")
        return self


class AttemptSectionOut(ORMModel):
    title: str
    minutes: int | None = None
    question_ids: list[int] = []


class AttemptOut(ORMModel):
    """The live paper. Carries questions without answer keys."""

    id: int
    mode: str
    status: AttemptStatus
    started_at: datetime
    expires_at: datetime | None = None
    total_questions: int
    duration_min: int | None = None
    template: TestTemplateOut | None = None
    sections: list[AttemptSectionOut] = []
    questions: list[QuestionOut] = []


class AnswerIn(InputModel):
    id: int
    picked: list[str] = Field(default_factory=list, max_length=10)
    ms: int = Field(default=0, ge=0, le=86_400_000)
    flagged: bool = False


class AttemptSubmitIn(InputModel):
    answers: list[AnswerIn] = Field(default_factory=list, max_length=300)
    duration_sec: int = Field(default=0, ge=0, le=86_400)


class AttemptQuestionResult(ORMModel):
    question: QuestionReviewOut
    picked: list[str] = []
    correct: bool
    marks_awarded: float
    ms: int = 0


class AttemptResultOut(ORMModel):
    id: int
    status: AttemptStatus
    mode: str
    submitted_at: datetime | None = None
    duration_sec: int
    total_questions: int
    attempted: int
    correct: int
    wrong: int
    score: float
    max_score: float
    percentage: float
    passed: bool | None = None
    topic_breakdown: dict = {}
    weak_topics: list[str] = []
    review: list[AttemptQuestionResult] = []


class AttemptSummaryOut(ORMModel):
    """List-view row -- no blueprint, no answers."""

    id: int
    mode: str
    status: AttemptStatus
    service: ServiceCode | None = None
    module_id: int | None = None
    template_id: int | None = None
    started_at: datetime
    submitted_at: datetime | None = None
    duration_sec: int
    total_questions: int
    correct: int
    percentage: float
    passed: bool | None = None


# --- Spaced repetition + fitness ------------------------------------------


class ReviewGradeIn(InputModel):
    question_id: int
    quality: int = Field(ge=0, le=5)  # SM-2 recall grade


class PracticeCardOut(ORMModel):
    question_id: int
    ease: float
    interval_days: int
    repetitions: int
    lapses: int
    due_on: datetime
    last_seen_at: datetime | None = None


class PhysicalLogIn(InputModel):
    logged_on: datetime | None = None
    metrics: dict = Field(default_factory=dict)
    note: str | None = Field(default=None, max_length=280)


class PhysicalLogOut(ORMModel):
    id: int
    logged_on: datetime
    metrics: dict = {}
    note: str | None = None


class PhysicalProgressOut(ORMModel):
    logs: list[PhysicalLogOut] = []
    standards: dict = {}
    latest: dict = {}
    gaps: list[dict] = []
    bmi: float | None = None

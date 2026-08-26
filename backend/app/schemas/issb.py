"""ISSB simulation models: psych battery, GTO tasks, mock interview."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from app.core.enums import (
    ContentStatus,
    Difficulty,
    GtoTaskType,
    GtoVenue,
    PsychTestType,
    ServiceCode,
)
from app.schemas.common import InputModel, ORMModel


class OlqScore(ORMModel):
    olq: str
    label: str
    score: float          # 1-5
    evidence: str | None = None


class AnalysisOut(ORMModel):
    """The heuristic read-out shared by every projective test."""

    signals: dict = {}
    olq_scores: list[OlqScore] = []
    feedback: list[str] = []
    overall_score: float | None = None
    strengths: list[str] = []
    improvements: list[str] = []


# --- Psychological battery -------------------------------------------------


class PsychItemOut(ORMModel):
    """During a sitting. ``model_answer`` is withheld until submission."""

    id: int
    test_type: PsychTestType
    prompt: str
    image_url: str | None = None
    seconds: int


class PsychItemReviewOut(PsychItemOut):
    model_answer: str | None = None
    perception_hint: str | None = None
    target_olqs: list[str] = []


class PsychItemIn(InputModel):
    test_type: PsychTestType
    prompt: str = Field(min_length=1, max_length=2000)
    image_url: str | None = Field(default=None, max_length=400)
    perception_hint: str | None = Field(default=None, max_length=2000)
    seconds: int = Field(default=30, ge=5, le=1800)
    target_olqs: list[str] = Field(default_factory=list, max_length=15)
    model_answer: str | None = Field(default=None, max_length=4000)
    difficulty: Difficulty = Difficulty.MEDIUM
    status: ContentStatus = ContentStatus.APPROVED
    tags: list[str] = Field(default_factory=list, max_length=20)
    sort_order: int = Field(default=0, ge=0, le=99_999)


class PsychSessionStartIn(InputModel):
    test_type: PsychTestType
    count: int | None = Field(default=None, ge=1, le=100)
    service: ServiceCode | None = None


class PsychSessionOut(ORMModel):
    id: int
    test_type: PsychTestType
    started_at: datetime
    item_count: int
    total_seconds: int
    items: list[PsychItemOut] = []


class PsychResponseIn(InputModel):
    item_id: int
    text: str = Field(default="", max_length=4000)
    ms: int = Field(default=0, ge=0, le=86_400_000)
    skipped: bool = False


class PsychSubmitIn(InputModel):
    responses: list[PsychResponseIn] = Field(default_factory=list, max_length=100)
    duration_sec: int = Field(default=0, ge=0, le=86_400)


class PsychResponseReview(ORMModel):
    item: PsychItemReviewOut
    text: str = ""
    ms: int = 0
    skipped: bool = False
    notes: list[str] = []


class PsychResultOut(ORMModel):
    id: int
    test_type: PsychTestType
    submitted_at: datetime | None = None
    duration_sec: int
    item_count: int
    answered_count: int
    word_count: int
    analysis: AnalysisOut
    responses: list[PsychResponseReview] = []


class PsychSessionSummaryOut(ORMModel):
    id: int
    test_type: PsychTestType
    started_at: datetime
    submitted_at: datetime | None = None
    item_count: int
    answered_count: int
    overall_score: float | None = None


# --- GTO -------------------------------------------------------------------


class GtoTaskOut(ORMModel):
    id: int
    task_type: GtoTaskType
    venue: GtoVenue
    service: ServiceCode | None = None
    title: str
    brief: str
    constraints: list[str] = []
    resources: list[str] = []
    map_url: str | None = None
    planning_seconds: int
    execution_seconds: int
    group_size: int
    difficulty: Difficulty
    target_olqs: list[str] = []


class GtoTaskReviewOut(GtoTaskOut):
    model_solution: str | None = None
    rubric: list[dict] = []


class GtoTaskIn(InputModel):
    task_type: GtoTaskType
    venue: GtoVenue | None = None  # derived from task_type when omitted
    service: ServiceCode | None = None
    title: str = Field(min_length=3, max_length=180)
    brief: str = Field(min_length=10, max_length=8000)
    constraints: list[str] = Field(default_factory=list, max_length=20)
    resources: list[str] = Field(default_factory=list, max_length=20)
    map_url: str | None = Field(default=None, max_length=400)
    planning_seconds: int = Field(default=300, ge=30, le=7200)
    execution_seconds: int = Field(default=900, ge=30, le=7200)
    group_size: int = Field(default=8, ge=1, le=20)
    model_solution: str | None = Field(default=None, max_length=8000)
    rubric: list[dict] = Field(default_factory=list, max_length=20)
    target_olqs: list[str] = Field(default_factory=list, max_length=15)
    difficulty: Difficulty = Difficulty.MEDIUM
    status: ContentStatus = ContentStatus.APPROVED
    sort_order: int = Field(default=0, ge=0, le=99_999)


class GtoSubmitIn(InputModel):
    body: str = Field(min_length=1, max_length=12_000)
    duration_sec: int = Field(default=0, ge=0, le=86_400)


class GtoResultOut(ORMModel):
    id: int
    task: GtoTaskReviewOut
    body: str
    duration_sec: int
    created_at: datetime
    analysis: AnalysisOut


# --- Interview -------------------------------------------------------------


class InterviewQuestionOut(ORMModel):
    id: int
    category: str
    question: str
    service: ServiceCode | None = None
    difficulty: Difficulty
    target_olqs: list[str] = []


class InterviewQuestionReviewOut(InterviewQuestionOut):
    guidance: str | None = None
    follow_ups: list[str] = []


class InterviewQuestionIn(InputModel):
    category: str = Field(max_length=48)
    question: str = Field(min_length=5, max_length=2000)
    guidance: str | None = Field(default=None, max_length=4000)
    follow_ups: list[str] = Field(default_factory=list, max_length=10)
    service: ServiceCode | None = None
    target_olqs: list[str] = Field(default_factory=list, max_length=15)
    difficulty: Difficulty = Difficulty.MEDIUM
    status: ContentStatus = ContentStatus.APPROVED


class InterviewStartIn(InputModel):
    service: ServiceCode | None = None
    count: int = Field(default=12, ge=1, le=40)
    categories: list[str] = Field(default_factory=list, max_length=10)


class InterviewSessionOut(ORMModel):
    id: int
    started_at: datetime
    questions: list[InterviewQuestionOut] = []


class InterviewAnswerIn(InputModel):
    question_id: int
    answer: str = Field(default="", max_length=6000)
    ms: int = Field(default=0, ge=0, le=86_400_000)


class InterviewSubmitIn(InputModel):
    exchanges: list[InterviewAnswerIn] = Field(default_factory=list, max_length=40)
    duration_sec: int = Field(default=0, ge=0, le=86_400)


class InterviewExchangeReview(ORMModel):
    question: InterviewQuestionReviewOut
    answer: str = ""
    ms: int = 0
    notes: list[str] = []


class InterviewResultOut(ORMModel):
    id: int
    submitted_at: datetime | None = None
    duration_sec: int
    analysis: AnalysisOut
    exchanges: list[InterviewExchangeReview] = []


class OlqProfileOut(ORMModel):
    """Aggregate OLQ picture across every projective test the user has sat."""

    scores: list[OlqScore] = []
    sessions_counted: int = 0
    strongest: list[str] = []
    weakest: list[str] = []
    updated_at: datetime | None = None


# --- Offline answer sheets -------------------------------------------------


class TranscribedLine(ORMModel):
    index: int | None = None
    text: str
    confidence: float = 0.0


class TranscriptionOut(ORMModel):
    """The draft reading of an uploaded sheet, for the candidate to correct.

    ``slots`` is the transcription already aligned to the sitting's items, which
    is what the correction form binds to. Anything the reader could not place is
    left empty rather than guessed -- a misplaced line would attribute words to
    the wrong stimulus, and the candidate could not tell from the result.
    """

    engine: str
    available: bool
    note: str | None = None
    mean_confidence: float = 0.0
    lines: list[TranscribedLine] = []
    slots: list[str] = []
    item_count: int = 0


class SheetSubmitIn(InputModel):
    """A sitting done on paper, transcribed and confirmed by the candidate."""

    test_type: PsychTestType
    # Item ids in the order they were answered, parallel to `responses`.
    item_ids: list[int] = Field(min_length=1, max_length=100)
    responses: list[str] = Field(min_length=1, max_length=100)
    duration_sec: int = Field(default=0, ge=0, le=86_400)
    service: ServiceCode | None = None
    # Carried through from the transcribe step so the read-out can say how the
    # text was produced. Optional: a fully hand-typed sheet is legitimate.
    transcription: dict = Field(default_factory=dict)

    @field_validator("responses")
    @classmethod
    def _pairs_line_up(cls, value: list[str], info):
        item_ids = info.data.get("item_ids") or []
        if item_ids and len(item_ids) != len(value):
            raise ValueError("item_ids and responses must be the same length.")
        return value


class SheetPlanOut(ORMModel):
    """A printable practice sheet: the stimuli, without anywhere to type."""

    test_type: PsychTestType
    title: str
    instructions: list[str] = []
    seconds_per_item: int
    total_minutes: int
    items: list[PsychItemOut] = []


# --- PPDT ------------------------------------------------------------------


class PpdtPerception(InputModel):
    """The proforma a candidate fills before writing the story.

    Screening day asks for the number of characters, then age, sex, mood and
    action for the main one -- and the story has to agree with what was written
    here. That consistency is half of what is being assessed, so it is captured
    as structure rather than buried in prose.
    """

    characters: int = Field(default=1, ge=0, le=12)
    main_age: int | None = Field(default=None, ge=1, le=99)
    main_sex: str | None = Field(default=None, max_length=8)
    main_mood: str | None = Field(default=None, max_length=32)
    action: str | None = Field(default=None, max_length=400)


class PpdtSubmitIn(InputModel):
    item_id: int
    perception: PpdtPerception
    story: str = Field(min_length=1, max_length=6000)
    duration_sec: int = Field(default=0, ge=0, le=86_400)


class PpdtResultOut(ORMModel):
    id: int
    item: PsychItemReviewOut
    perception: dict = {}
    story: str
    duration_sec: int
    analysis: AnalysisOut
    consistency: list[str] = []

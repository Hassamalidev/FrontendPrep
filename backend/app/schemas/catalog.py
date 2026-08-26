"""Service / program / stage / module / topic read + write models."""

from __future__ import annotations

from pydantic import Field

from app.core.enums import ServiceCode, StageCode
from app.schemas.common import InputModel, ORMModel


class TopicOut(ORMModel):
    id: int
    module_id: int
    slug: str
    name: str
    blurb: str | None = None
    approved_question_count: int = 0
    sort_order: int = 0


class ModuleOut(ORMModel):
    id: int
    service_id: int
    stage_id: int
    slug: str
    title: str
    subtitle: str | None = None
    description: str | None = None
    icon: str | None = None
    default_question_count: int
    default_duration_min: int
    approved_question_count: int
    sort_order: int = 0


class ModuleDetailOut(ModuleOut):
    topics: list[TopicOut] = []


class StageOut(ORMModel):
    id: int
    code: StageCode
    name: str
    summary: str | None = None
    icon: str | None = None
    day_hint: str | None = None
    sort_order: int = 0


class ProgramOut(ORMModel):
    id: int
    service_id: int
    slug: str
    name: str
    short_name: str | None = None
    summary: str | None = None
    eligibility: dict = {}
    physical_standards: dict = {}
    test_blueprint: dict = {}
    intake_note: str | None = None
    sort_order: int = 0


class ServiceOut(ORMModel):
    id: int
    code: ServiceCode
    name: str
    short_name: str
    tagline: str | None = None
    description: str | None = None
    accent: str
    emblem_url: str | None = None
    hero_url: str | None = None
    test_pattern: dict = {}
    sort_order: int = 0


class ServiceDetailOut(ServiceOut):
    programs: list[ProgramOut] = []


class ServiceOverviewOut(ORMModel):
    """Everything the service hub page needs, in one round trip."""

    service: ServiceOut
    programs: list[ProgramOut] = []
    stages: list[StageOut] = []
    modules: list[ModuleOut] = []


# --- Admin write models ----------------------------------------------------


class ModuleIn(InputModel):
    service_id: int
    stage_id: int
    slug: str = Field(min_length=2, max_length=90, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=2, max_length=140)
    subtitle: str | None = Field(default=None, max_length=200)
    description: str | None = None
    icon: str | None = Field(default=None, max_length=40)
    default_question_count: int = Field(default=20, ge=1, le=200)
    default_duration_min: int = Field(default=20, ge=1, le=300)
    sort_order: int = Field(default=0, ge=0, le=9999)
    is_active: bool = True


class ModuleUpdate(InputModel):
    title: str | None = Field(default=None, min_length=2, max_length=140)
    subtitle: str | None = Field(default=None, max_length=200)
    description: str | None = None
    icon: str | None = Field(default=None, max_length=40)
    default_question_count: int | None = Field(default=None, ge=1, le=200)
    default_duration_min: int | None = Field(default=None, ge=1, le=300)
    sort_order: int | None = Field(default=None, ge=0, le=9999)
    is_active: bool | None = None


class TopicIn(InputModel):
    module_id: int
    slug: str = Field(min_length=2, max_length=90, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=2, max_length=140)
    blurb: str | None = Field(default=None, max_length=280)
    keywords: list[str] = Field(default_factory=list, max_length=40)
    sort_order: int = Field(default=0, ge=0, le=9999)
    is_active: bool = True


class TopicUpdate(InputModel):
    name: str | None = Field(default=None, min_length=2, max_length=140)
    blurb: str | None = Field(default=None, max_length=280)
    keywords: list[str] | None = Field(default=None, max_length=40)
    sort_order: int | None = Field(default=None, ge=0, le=9999)
    is_active: bool | None = None


class ProgramIn(InputModel):
    service_id: int
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=2, max_length=120)
    short_name: str | None = Field(default=None, max_length=32)
    summary: str | None = None
    eligibility: dict = Field(default_factory=dict)
    physical_standards: dict = Field(default_factory=dict)
    test_blueprint: dict = Field(default_factory=dict)
    intake_note: str | None = Field(default=None, max_length=200)
    sort_order: int = Field(default=0, ge=0, le=9999)
    is_active: bool = True


class ProgramUpdate(InputModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    short_name: str | None = Field(default=None, max_length=32)
    summary: str | None = None
    eligibility: dict | None = None
    physical_standards: dict | None = None
    test_blueprint: dict | None = None
    intake_note: str | None = Field(default=None, max_length=200)
    sort_order: int | None = Field(default=None, ge=0, le=9999)
    is_active: bool | None = None

"""Profile, stats and the admin user-management models."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import EmailStr, Field

from app.core.enums import Role, ServiceCode, UserStatus
from app.schemas.common import InputModel, ORMModel


class ProfileUpdate(InputModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=24)
    city: str | None = Field(default=None, max_length=80)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=12)
    avatar_url: str | None = Field(default=None, max_length=400)
    target_service: ServiceCode | None = None
    target_program_id: int | None = None
    height_cm: float | None = Field(default=None, ge=100, le=250)
    weight_kg: float | None = Field(default=None, ge=25, le=250)
    preferences: dict | None = None


class UserStatsOut(ORMModel):
    attempts_total: int = 0
    questions_answered: int = 0
    questions_correct: int = 0
    accuracy: float = 0.0
    study_seconds: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    last_active_on: date | None = None
    readiness: dict = {}
    topic_mastery: dict = {}
    olq_profile: dict = {}


class AdminUserOut(ORMModel):
    id: int
    email: EmailStr
    full_name: str
    phone: str | None = None
    role: Role
    status: UserStatus
    target_service: ServiceCode | None = None
    city: str | None = None
    email_verified: bool
    created_at: datetime
    last_login_at: datetime | None = None


class AdminUserUpdate(InputModel):
    role: Role | None = None
    status: UserStatus | None = None
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    email_verified: bool | None = None


class DashboardOut(ORMModel):
    """The signed-in landing page, assembled server-side to keep it one call."""

    user: dict
    stats: UserStatsOut
    recent_attempts: list[dict] = []
    due_revision: int = 0
    resume_attempt_id: int | None = None
    next_stage: dict | None = None
    announcements: list[dict] = []
    recommended: list[dict] = []

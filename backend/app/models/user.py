"""Accounts, sessions and the denormalised per-user stats row."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import Role, ServiceCode, UserStatus
from app.models.base import Base, JSONBType, TimestampMixin, enum_column


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))  # null for OAuth-only
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(24))

    role = enum_column(Role, name="user_role", default=Role.STUDENT, nullable=False, index=True)
    status = enum_column(UserStatus, name="user_status", default=UserStatus.ACTIVE, nullable=False)

    # Which service the candidate is preparing for; drives dashboard defaults.
    target_service = enum_column(ServiceCode, name="user_service", nullable=True)
    target_program_id: Mapped[int | None] = mapped_column(
        ForeignKey("programs.id", ondelete="SET NULL")
    )

    date_of_birth: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(12))
    city: Mapped[str | None] = mapped_column(String(80))
    avatar_url: Mapped[str | None] = mapped_column(String(400))

    # Anthropometrics for the physical/medical module (BMI, height bar).
    height_cm: Mapped[float | None] = mapped_column(Numeric(5, 1))
    weight_kg: Mapped[float | None] = mapped_column(Numeric(5, 1))

    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    google_sub: Mapped[str | None] = mapped_column(String(64), unique=True)

    # Small bag for preferences (theme, notification opt-ins, onboarding flags).
    preferences: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)

    stats: Mapped[UserStats | None] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_users_role_status", "role", "status"),)

    @property
    def is_staff(self) -> bool:
        return Role(self.role).rank >= Role.ADMIN.rank


class RefreshToken(Base):
    """One row per live session. Digest-only, pruned on logout and expiry."""

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_refresh_tokens_expiry", "expires_at"),)


class UserStats(Base):
    """Rolled-up progress, written on attempt submit.

    A single row per user replaces the per-request aggregate scan over the
    attempts table -- the difference between a dashboard that costs one indexed
    primary-key lookup and one that costs a sequential scan on a free-tier
    instance.
    """

    __tablename__ = "user_stats"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    attempts_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    questions_answered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    questions_correct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    study_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    current_streak: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    longest_streak: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    last_active_on: Mapped[date | None] = mapped_column(Date)

    # 0-100 per stage, e.g. {"initial_test": 72.5, "issb_psychological": 40.0}
    readiness: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)
    # {topic_slug: {"seen": n, "correct": n}} -- capped to the worst/most-seen 60
    topic_mastery: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)
    # Self/peer OLQ profile, 1-5 per quality.
    olq_profile: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)

    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="stats")

    @property
    def accuracy(self) -> float:
        return (
            round(self.questions_correct * 100 / self.questions_answered, 1)
            if self.questions_answered
            else 0.0
        )


class AuditLog(Base):
    """Staff-action trail. Pruned by the retention job, never by hand."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity: Mapped[str] = mapped_column(String(48), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(48))
    detail: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_audit_logs_created", "created_at"),
        Index("ix_audit_logs_entity", "entity", "entity_id"),
    )

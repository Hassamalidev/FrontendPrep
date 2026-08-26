"""Content taxonomy: service -> program -> stage -> module -> topic.

This is the spine the whole app hangs off. A student picks a *service* (Army,
PAF, Navy) and a *program* (PMA Long Course, GD Pilot, PN Cadet...). Every piece
of practice material is filed under a *stage* of the selection funnel and a
*module* within it, then a *topic* inside the module.
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ServiceCode, StageCode
from app.models.base import Base, JSONBType, TimestampMixin, enum_column


class Service(Base):
    """Pakistan Army / Air Force / Navy, plus a `common` bucket."""

    __tablename__ = "services"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    code = enum_column(ServiceCode, name="service_code", nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    short_name: Mapped[str] = mapped_column(String(16), nullable=False)
    tagline: Mapped[str | None] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    # Brand tokens the frontend themes each service hub with.
    accent: Mapped[str] = mapped_column(String(16), default="#2f5d3a", nullable=False)
    emblem_url: Mapped[str | None] = mapped_column(String(400))
    hero_url: Mapped[str | None] = mapped_column(String(400))
    # The initial written test pattern, which genuinely differs by service:
    # {"label": "GD Pilot", "sections": [...], "negative_marking": false,
    #  "sectional_pass": 50, "distinctive": "No General Knowledge paper."}
    test_pattern: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    programs: Mapped[list[Program]] = relationship(back_populates="service")


class Program(Base, TimestampMixin):
    """An entry scheme, e.g. PMA Long Course, Lady Cadet Course, GD(P)."""

    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True
    )
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(32))
    summary: Mapped[str | None] = mapped_column(Text)

    # {"age": {"min": 17, "max": 22}, "education": [...], "gender": "male",
    #  "marital_status": "unmarried", "height_cm": {"male": 162.5, "female": 152.4}}
    eligibility: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)
    # {"run": {"distance_m": 1600, "seconds": 480}, "push_ups": 15, ...}
    physical_standards: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)
    # Which subjects the initial written test covers for this scheme.
    test_blueprint: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)

    intake_note: Mapped[str | None] = mapped_column(String(200))
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    service: Mapped[Service] = relationship(back_populates="programs")


class Stage(Base):
    """A phase of the selection funnel. Global lookup, ~12 rows."""

    __tablename__ = "stages"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    code = enum_column(StageCode, name="stage_code", nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(String(40))
    day_hint: Mapped[str | None] = mapped_column(String(40))  # e.g. "ISSB Day 2"
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)


class Module(Base, TimestampMixin):
    """A study unit: one (service, stage) pairing with a syllabus.

    Example: ``army / initial_test / verbal-intelligence``.
    """

    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), nullable=False
    )
    stage_id: Mapped[int] = mapped_column(
        ForeignKey("stages.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String(90), nullable=False)
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(String(40))

    # Practice defaults for the module's quick-drill button.
    default_question_count: Mapped[int] = mapped_column(SmallInteger, default=20, nullable=False)
    default_duration_min: Mapped[int] = mapped_column(SmallInteger, default=20, nullable=False)

    # Denormalised counter, refreshed by the question service. Avoids a
    # COUNT(*) per module on every catalog render.
    approved_question_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    service: Mapped[Service] = relationship()
    stage: Mapped[Stage] = relationship()
    topics: Mapped[list[Topic]] = relationship(back_populates="module")

    __table_args__ = (
        UniqueConstraint("service_id", "slug", name="uq_modules_service_id"),
        Index("ix_modules_service_stage", "service_id", "stage_id", "is_active"),
    )


class Topic(Base):
    """A leaf syllabus node, e.g. "Analogies" inside Verbal Intelligence."""

    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module_id: Mapped[int] = mapped_column(
        ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    slug: Mapped[str] = mapped_column(String(90), nullable=False)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    blurb: Mapped[str | None] = mapped_column(String(280))
    # Keywords the tagger agent matches article content against.
    keywords: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)
    approved_question_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    module: Mapped[Module] = relationship(back_populates="topics")

    __table_args__ = (UniqueConstraint("module_id", "slug", name="uq_topics_module_id"),)

"""Declarative base, naming convention and shared column mixins."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON

# Deterministic constraint names keep Alembic autogenerate diffs clean.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# JSONB on Postgres, plain JSON on SQLite so the test suite runs without a server.
JSONBType = JSONB().with_variant(JSON(), "sqlite")


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    def as_dict(self) -> dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


def enum_column(python_enum: type, *, name: str, **kwargs: Any):
    """VARCHAR + CHECK constraint rather than a native PG ENUM.

    Values are stored as the enum's *value* so the wire format matches the API.
    """
    return mapped_column(
        SAEnum(
            python_enum,
            name=name,
            native_enum=False,
            validate_strings=True,
            values_callable=lambda e: [m.value for m in e],
            length=32,
        ),
        **kwargs,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

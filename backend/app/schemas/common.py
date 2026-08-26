"""Base schema classes and the shared envelopes."""

from __future__ import annotations

from collections.abc import Sequence
from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    """Read model populated straight off a SQLAlchemy row."""

    model_config = ConfigDict(from_attributes=True)


class InputModel(BaseModel):
    """Write model: unknown keys are rejected rather than silently dropped."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Msg(BaseModel):
    detail: str


class IdOut(BaseModel):
    id: int


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def build(cls, items: Sequence[T], total: int, page: int, size: int) -> Page[T]:
        return cls(
            items=list(items),
            total=total,
            page=page,
            size=size,
            pages=ceil(total / size) if size else 0,
        )


class SortOrder(BaseModel):
    sort_order: int = Field(default=0, ge=0, le=9999)

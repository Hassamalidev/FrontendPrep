"""Registration, login, token refresh and password management."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import EmailStr, Field, field_validator

from app.core.config import settings
from app.core.enums import Role, ServiceCode, UserStatus
from app.schemas.common import InputModel, ORMModel


def validate_password(value: str) -> str:
    """One rule set for register, reset and change-password."""
    if len(value) < settings.PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters."
        )
    if value.isdigit() or value.isalpha():
        raise ValueError("Password must mix letters with numbers or symbols.")
    return value


class RegisterIn(InputModel):
    email: EmailStr
    password: str = Field(max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=24)
    target_service: ServiceCode | None = None
    city: str | None = Field(default=None, max_length=80)

    @field_validator("password")
    @classmethod
    def _strong_password(cls, v: str) -> str:
        return validate_password(v)


class LoginIn(InputModel):
    email: EmailStr
    password: str = Field(max_length=128)


class RefreshIn(InputModel):
    refresh_token: str = Field(max_length=512)


class ChangePasswordIn(InputModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(max_length=128)

    @field_validator("new_password")
    @classmethod
    def _strong_password(cls, v: str) -> str:
        return validate_password(v)


class TokenPair(ORMModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until the access token expires


class UserPublic(ORMModel):
    """The account payload returned alongside a token and from ``/auth/me``."""

    id: int
    email: EmailStr
    full_name: str
    phone: str | None = None
    role: Role
    status: UserStatus
    target_service: ServiceCode | None = None
    target_program_id: int | None = None
    city: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    avatar_url: str | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    email_verified: bool
    preferences: dict = {}
    created_at: datetime
    last_login_at: datetime | None = None


class AuthOut(ORMModel):
    user: UserPublic
    tokens: TokenPair

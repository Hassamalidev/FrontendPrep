"""Shared FastAPI dependencies: session, current user, role gates, paging.

Every router imports the ``Annotated`` aliases at the bottom rather than
wiring ``Depends(...)`` by hand, so a signature reads
``async def handler(db: DbSession, user: CurrentUser)``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.enums import Role, UserStatus
from app.core.security import decode_token
from app.models.user import User

_bearer = HTTPBearer(auto_error=False, description="JWT access token")

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


async def _user_from_credentials(
    creds: HTTPAuthorizationCredentials | None,
    db: AsyncSession,
) -> User | None:
    if creds is None or not creds.credentials:
        return None
    try:
        payload = decode_token(creds.credentials, expected_type="access")
    except jwt.PyJWTError:
        return None

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        return None

    return await db.scalar(select(User).where(User.id == user_id))


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> User:
    user = await _user_from_credentials(creds, db)
    if user is None:
        raise CREDENTIALS_ERROR
    if user.status == UserStatus.SUSPENDED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been suspended.",
        )
    # Stash for the audit helper so handlers do not have to thread it through.
    request.state.user_id = user.id
    return user


async def get_optional_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> User | None:
    """For endpoints that are public but richer when signed in."""
    return await _user_from_credentials(creds, db)


def require_role(minimum: Role):
    """Dependency factory gating on the role ladder in ``Role.rank``."""

    async def _guard(user: Annotated[User, Depends(get_current_user)]) -> User:
        if Role(user.role).rank < minimum.rank:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {minimum.value} access.",
            )
        return user

    return _guard


@dataclass(slots=True)
class Pagination:
    page: int
    size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        return self.size


def pagination(
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Pagination:
    return Pagination(page=page, size=size)


DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
InstructorUser = Annotated[User, Depends(require_role(Role.INSTRUCTOR))]
AdminUser = Annotated[User, Depends(require_role(Role.ADMIN))]
SuperAdminUser = Annotated[User, Depends(require_role(Role.SUPER_ADMIN))]
PageParams = Annotated[Pagination, Depends(pagination)]

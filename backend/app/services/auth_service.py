"""Registration, login, refresh rotation and password changes.

Refresh tokens rotate on every use: the presented token is revoked and a new one
issued. Presenting an already-revoked token means it leaked, so that case drops
the whole session family for the account rather than merely failing the call.
"""

from __future__ import annotations

from datetime import UTC, datetime

import jwt
from fastapi import HTTPException, status
from sqlalchemy import delete, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import Role, UserStatus
from app.core.security import (
    create_token,
    decode_token,
    hash_password,
    hash_refresh_token,
    needs_rehash,
    verify_password,
)
from app.core.timeutil import as_utc
from app.models.user import RefreshToken, User, UserStats
from app.schemas.auth import ChangePasswordIn, LoginIn, RegisterIn, TokenPair

INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Incorrect email or password.",
)
INVALID_REFRESH = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired refresh token.",
)


def _now() -> datetime:
    return datetime.now(UTC)




async def _issue_tokens(
    db: AsyncSession, user: User, *, user_agent: str | None = None
) -> TokenPair:
    access, _, access_exp = create_token(user.id, "access", role=str(user.role))
    refresh, _, refresh_exp = create_token(user.id, "refresh")

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh),
            expires_at=refresh_exp,
            user_agent=(user_agent or "")[:200] or None,
        )
    )
    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=int((access_exp - _now()).total_seconds()),
    )


async def _prune_dead_sessions(db: AsyncSession, user_id: int) -> None:
    """Stop the session table accumulating dead rows on a tiny database."""
    await db.execute(
        delete(RefreshToken).where(
            RefreshToken.user_id == user_id,
            or_(RefreshToken.expires_at < _now(), RefreshToken.revoked_at.is_not(None)),
        )
    )


async def register(
    db: AsyncSession, data: RegisterIn, *, user_agent: str | None = None
) -> tuple[User, TokenPair]:
    email = data.email.lower().strip()
    if await db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        email=email,
        password_hash=hash_password(data.password),
        full_name=data.full_name.strip(),
        phone=data.phone,
        city=data.city,
        target_service=data.target_service,
        role=Role.STUDENT,
        status=UserStatus.ACTIVE,
        last_login_at=_now(),
    )
    user.stats = UserStats()
    db.add(user)

    try:
        await db.flush()
    except IntegrityError as exc:  # lost a race with a concurrent signup
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from exc

    tokens = await _issue_tokens(db, user, user_agent=user_agent)
    await db.commit()
    await db.refresh(user)
    return user, tokens


async def login(
    db: AsyncSession, data: LoginIn, *, user_agent: str | None = None
) -> tuple[User, TokenPair]:
    user = await db.scalar(select(User).where(User.email == data.email.lower().strip()))

    # Verify against the stored hash only when there is one, but always fail the
    # same way: a wrong email and a wrong password must be indistinguishable.
    stored = user.password_hash if user and user.password_hash else None
    if not user or not stored or not verify_password(data.password, stored):
        raise INVALID_CREDENTIALS

    if user.status == UserStatus.SUSPENDED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been suspended.",
        )

    if needs_rehash(stored):
        user.password_hash = hash_password(data.password)

    user.last_login_at = _now()
    await _prune_dead_sessions(db, user.id)
    tokens = await _issue_tokens(db, user, user_agent=user_agent)
    await db.commit()
    await db.refresh(user)
    return user, tokens


async def refresh_tokens(
    db: AsyncSession, raw_token: str, *, user_agent: str | None = None
) -> TokenPair:
    try:
        payload = decode_token(raw_token, expected_type="refresh")
    except jwt.PyJWTError as exc:
        raise INVALID_REFRESH from exc

    row = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_token))
    )
    if row is None:
        raise INVALID_REFRESH

    if row.revoked_at is not None:
        # Replay of a rotated token: treat as compromise, end every session.
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == row.user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=_now())
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session revoked. Please sign in again.",
        )

    if as_utc(row.expires_at) <= _now():
        raise INVALID_REFRESH

    user = await db.scalar(select(User).where(User.id == int(payload["sub"])))
    if user is None or user.status == UserStatus.SUSPENDED:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is not available.",
        )

    row.revoked_at = _now()
    tokens = await _issue_tokens(db, user, user_agent=user_agent)
    await db.commit()
    return tokens


async def logout(
    db: AsyncSession, user_id: int, raw_token: str | None, *, all_sessions: bool = False
) -> None:
    stmt = update(RefreshToken).where(
        RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
    )
    if not all_sessions and raw_token:
        stmt = stmt.where(RefreshToken.token_hash == hash_refresh_token(raw_token))
    await db.execute(stmt.values(revoked_at=_now()))
    await db.commit()


async def change_password(db: AsyncSession, user: User, data: ChangePasswordIn) -> None:
    if not user.password_hash or not verify_password(data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
    if data.new_password == data.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The new password must differ from the current one.",
        )

    user.password_hash = hash_password(data.new_password)
    # A password change ends every session, including this one.
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )
    await db.commit()


async def ensure_stats(db: AsyncSession, user_id: int) -> UserStats:
    stats = await db.get(UserStats, user_id)
    if stats is None:
        stats = UserStats(user_id=user_id)
        db.add(stats)
        await db.flush()
    return stats

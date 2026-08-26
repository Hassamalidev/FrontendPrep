"""Password hashing and JWT issuance.

Argon2id is used directly (no passlib) -- passlib's bcrypt backend keeps
breaking against new bcrypt releases and Argon2 is the better default anyway.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings

# Tuned down from Argon2's defaults: a 512 MB dyno cannot afford 64 MiB per
# concurrent login. The shipped values (19 MiB / 2 passes) still exceed OWASP's
# minimum; they are settings so the test suite can drop them, since a hundred
# real hashes turn a two-second suite into a two-minute one.
_hasher = PasswordHasher(
    time_cost=settings.ARGON2_TIME_COST,
    memory_cost=settings.ARGON2_MEMORY_COST,
    parallelism=settings.ARGON2_PARALLELISM,
)

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        _hasher.verify(password_hash, password)
        return True
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def _encode(payload: dict[str, Any]) -> str:
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_token(
    subject: str | int,
    token_type: TokenType,
    *,
    role: str | None = None,
    extra: dict[str, Any] | None = None,
) -> tuple[str, str, datetime]:
    """Return ``(encoded_jwt, jti, expires_at)``."""
    now = datetime.now(UTC)
    ttl = (
        timedelta(minutes=settings.ACCESS_TOKEN_TTL_MIN)
        if token_type == "access"
        else timedelta(days=settings.REFRESH_TOKEN_TTL_DAYS)
    )
    expires_at = now + ttl
    jti = uuid.uuid4().hex

    payload: dict[str, Any] = {
        "sub": str(subject),
        "typ": token_type,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    if role:
        payload["role"] = role
    if extra:
        payload.update(extra)

    return _encode(payload), jti, expires_at


def decode_token(token: str, *, expected_type: TokenType | None = None) -> dict[str, Any]:
    """Decode and validate a JWT. Raises ``jwt.PyJWTError`` on any problem."""
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    if expected_type and payload.get("typ") != expected_type:
        raise jwt.InvalidTokenError(f"expected a {expected_type} token")
    return payload


def hash_refresh_token(token: str) -> str:
    """Refresh tokens are stored as digests so a DB leak is not a session leak."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def random_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)

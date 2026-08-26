"""Async SQLAlchemy engine + session factory tuned for serverless Postgres.

Neon suspends idle compute and (on the pooled endpoint) sits behind pgbouncer.
Both facts shape the settings below:

* ``pool_pre_ping`` so a connection killed during suspend is replaced, not raised.
* ``pool_recycle`` shorter than Neon's idle timeout.
* ``statement_cache_size=0`` because pgbouncer in transaction mode breaks
  asyncpg's implicit prepared statements.
* A deliberately small pool -- Render's free dyno has 512 MB and Neon's free
  project caps concurrent connections.
"""

from __future__ import annotations

import ssl
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

_connect_args: dict = {}

if settings.DATABASE_URL.startswith("postgresql+asyncpg"):
    _connect_args = {
        "timeout": settings.DB_CONNECT_TIMEOUT,
        "statement_cache_size": settings.DB_STATEMENT_CACHE_SIZE,
        "server_settings": {
            "application_name": "issb-api",
            # Never let a runaway query pin a free-tier connection.
            "statement_timeout": "20000",
            "idle_in_transaction_session_timeout": "30000",
        },
    }
    # asyncpg wants an SSLContext, not the ?sslmode= that libpq accepts, which
    # is why the URL normaliser strips that parameter.
    _ssl_mode = settings.DB_SSL.strip().lower()
    if _ssl_mode == "auto":
        # Loopback is assumed to be a local development database with no TLS.
        _local = any(h in settings.DATABASE_URL for h in ("localhost", "127.0.0.1"))
        _use_ssl = not _local
    else:
        _use_ssl = _ssl_mode == "require"

    if _use_ssl:
        _connect_args["ssl"] = ssl.create_default_context()

_engine_kwargs: dict = {
    "echo": settings.DB_ECHO,
    "connect_args": _connect_args,
}

if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite is only used by the test suite. Its in-memory database is served by
    # StaticPool, which takes no sizing arguments at all -- passing them raises
    # rather than being ignored.
    from sqlalchemy.pool import StaticPool

    if ":memory:" in settings.DATABASE_URL:
        _engine_kwargs["poolclass"] = StaticPool
        _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs.update(
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=True,
    )

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one session per request, rolled back on error."""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Session for background jobs, seeds and CLI entry points."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    await engine.dispose()

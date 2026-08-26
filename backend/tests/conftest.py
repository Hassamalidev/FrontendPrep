"""Test fixtures.

The suite runs against in-memory SQLite, not Postgres. That is why the models
use ``JSONB().with_variant(JSON(), "sqlite")`` and VARCHAR-backed enums -- the
schema is portable enough to test without a server, while still emitting proper
Postgres DDL in the migration.

The environment variable has to be set before anything imports
``app.core.database``, because the engine is created at import time.
"""

from __future__ import annotations

import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-secret-not-used-anywhere-else"
os.environ["RATE_LIMIT_ENABLED"] = "false"
# Argon2 is deliberately expensive; at production cost the suite spends most of
# its time hashing throwaway passwords. The algorithm under test is unchanged.
os.environ["ARGON2_TIME_COST"] = "1"
os.environ["ARGON2_MEMORY_COST"] = "1024"

import asyncio  # noqa: E402
import shutil  # noqa: E402
from collections.abc import AsyncIterator  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.database import get_db  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from app.models import Base  # noqa: E402


@pytest.fixture(scope="session")
def template_db(tmp_path_factory) -> Path:
    """Build the schema and seed it once, into a template file.

    Seeding is ~400 round trips (39 modules, 183 topics, 142 psych items). Doing
    that per test cost about three seconds each and dominated the suite. Copying
    a prepared file instead keeps every test fully isolated for the price of a
    filesystem copy.
    """
    path = tmp_path_factory.mktemp("issb-template") / "template.db"

    async def build() -> None:
        from app.seed import run as seed_run

        engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            await seed_run(session)
            await session.commit()
        await engine.dispose()

    asyncio.run(build())
    return path


@pytest.fixture
async def engine(template_db, tmp_path) -> AsyncIterator:
    db_path = tmp_path / "test.db"
    shutil.copyfile(template_db, db_path)

    test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    yield test_engine
    await test_engine.dispose()


@pytest.fixture
async def session_factory(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def db(session_factory) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(session_factory) -> AsyncIterator[AsyncClient]:
    async def _override() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = _override
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as http:
        yield http
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
async def seeded(db) -> dict:
    """Catalog, ISSB content and the bootstrap admin.

    Already present via ``template_db``; this fixture stays so tests can declare
    the dependency, and returns live counts rather than a stale seed report.
    """
    from sqlalchemy import func, select

    from app.models.catalog import Module, Service
    from app.models.issb import GtoTask, InterviewQuestion, PsychItem

    async def count(model) -> int:
        return await db.scalar(select(func.count()).select_from(model)) or 0

    report = {
        "services": await count(Service),
        "modules": await count(Module),
        "psych_items": await count(PsychItem),
        "gto_tasks": await count(GtoTask),
        "interview_questions": await count(InterviewQuestion),
    }
    assert report["services"] == 4, "template database was not seeded"
    return report


REGISTRATION = {
    "email": "candidate@example.pk",
    "password": "Kakul2026!",
    "full_name": "Test Candidate",
    "target_service": "army",
}


@pytest.fixture
async def student(client) -> dict:
    """A registered student plus an auth header ready to use."""
    response = await client.post("/auth/register", json=REGISTRATION)
    assert response.status_code == 201, response.text
    body = response.json()
    return {
        "user": body["user"],
        "tokens": body["tokens"],
        "headers": {"Authorization": f"Bearer {body['tokens']['access_token']}"},
    }


@pytest.fixture
async def admin(client, db, seeded) -> dict:
    """The seeded super admin, signed in."""
    from app.core.config import settings

    response = await client.post(
        "/auth/login",
        json={
            "email": settings.BOOTSTRAP_ADMIN_EMAIL,
            "password": settings.BOOTSTRAP_ADMIN_PASSWORD,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    return {
        "user": body["user"],
        "headers": {"Authorization": f"Bearer {body['tokens']['access_token']}"},
    }

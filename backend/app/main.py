"""FastAPI application factory.

Deployment shape this is written for: one Render free dyno (512 MB, sleeps when
idle) talking to a Neon free Postgres (0.5 GB, also sleeps). Consequences visible
here -- a tiny connection pool, a health check that does not touch the database
by default, and error handlers that never leak a stack trace to the client.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import dispose_engine, engine

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("issb")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    log.info("starting %s %s (env=%s)", settings.APP_NAME, settings.APP_VERSION, settings.ENV)
    try:
        from app.agents import nlp

        log.info("question engine backend: %s (%s)", nlp.backend_name(), nlp.backend_note() or "ok")
    except Exception:  # the engine is optional at boot; the API still serves
        log.warning("question engine unavailable at startup", exc_info=settings.DEBUG)
    yield
    await dispose_engine()
    log.info("shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Backend for the ISSB preparation platform: catalog, question bank, "
            "mock tests, and the ISSB simulation suite. Question generation runs "
            "locally -- no external AI service is called."
        ),
        docs_url="/docs" if not settings.is_production or settings.DEBUG else None,
        redoc_url=None,
        openapi_url="/openapi.json" if not settings.is_production or settings.DEBUG else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=settings.CORS_ORIGIN_REGEX or None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Question payloads are text-heavy and repetitive; gzip earns its keep.
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    app.include_router(api_router, prefix=settings.API_PREFIX)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Flatten pydantic errors into something a form can display."""
        fields = []
        for error in exc.errors():
            location = [str(p) for p in error.get("loc", []) if p not in ("body", "query", "path")]
            fields.append({"field": ".".join(location) or "body", "message": error.get("msg", "")})
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Please check the highlighted fields.", "errors": fields},
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        log.exception("database error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "The database is unavailable. Please try again shortly."},
        )

    # HEAD as well as GET: platform port scanners (Render's among them) probe
    # with HEAD, and a GET-only route answers 405, which reads as "no open
    # ports" in the deploy log until a later GET succeeds.
    @app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
    async def root() -> dict:
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "api": settings.API_PREFIX,
        }

    @app.api_route("/health", methods=["GET", "HEAD"], tags=["health"])
    async def health() -> dict:
        """Liveness only. Deliberately does not wake the database."""
        return {"status": "ok", "version": settings.APP_VERSION, "env": settings.ENV}

    @app.get("/health/db", tags=["health"])
    async def health_db() -> dict:
        """Readiness. Separate from /health so the platform ping stays free."""
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return {"status": "ok", "database": "reachable"}
        except Exception as exc:
            log.warning("database health check failed: %s", exc)
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "degraded", "database": "unreachable"},
            )

    return app


app = create_app()

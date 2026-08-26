"""Application settings.

Everything is env-driven so the same image runs on Render, Fly, or a laptop.
Only DATABASE_URL and JWT_SECRET are required in production.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Identity -----------------------------------------------------------
    APP_NAME: str = "Frontline Prep API"
    APP_VERSION: str = "2.0.0"
    ENV: Literal["local", "staging", "production"] = "local"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    # --- Database -----------------------------------------------------------
    # Neon gives you a `postgresql://...` URL; we normalise it to asyncpg and
    # strip libpq-only query args that asyncpg rejects (sslmode, channel_binding).
    DATABASE_URL: str = "postgresql+asyncpg://issb:issb@localhost:5432/issb"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 0
    DB_POOL_RECYCLE: int = 280  # Neon idles connections out; recycle before that
    DB_ECHO: bool = False
    DB_CONNECT_TIMEOUT: int = 15
    DB_STATEMENT_CACHE_SIZE: int = 0  # required when behind a pgbouncer pooler

    # TLS to Postgres. "auto" requires it for any host that is not loopback,
    # which is right for Neon and wrong for a database reachable only on a
    # private network (Render's own Postgres, a Docker network, a VPC) where the
    # server may not offer TLS at all. Set "disable" there, or "require" to
    # insist on it everywhere.
    DB_SSL: str = "auto"          # auto | require | disable

    # --- Auth ---------------------------------------------------------------
    JWT_SECRET: str = "dev-only-insecure-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_TTL_MIN: int = 30
    REFRESH_TOKEN_TTL_DAYS: int = 30
    PASSWORD_MIN_LENGTH: int = 8

    # Argon2id work factor. The defaults are tuned for a 512 MB dyno: 19 MiB and
    # two passes still clears OWASP's floor, while Argon2's own default of
    # 64 MiB per concurrent login does not fit. Lowered only by the test suite.
    ARGON2_TIME_COST: int = 2
    ARGON2_MEMORY_COST: int = 19_456  # KiB
    ARGON2_PARALLELISM: int = 1

    # First super admin, created by `python -m app.seed` if absent.
    BOOTSTRAP_ADMIN_EMAIL: str = "admin@frontlineprep.pk"
    BOOTSTRAP_ADMIN_PASSWORD: str = "ChangeMe!2026"
    BOOTSTRAP_ADMIN_NAME: str = "Super Admin"

    # --- Demo access -----------------------------------------------------
    # When on, the sign-in page offers ready-made accounts so the app can be
    # tried without registering. It is off in production by default (see the
    # validator below) because publishing working credentials to a live
    # platform is exactly as bad as it sounds.
    DEMO_MODE: bool = True
    DEMO_STUDENT_EMAIL: str = "demo@frontlineprep.pk"
    DEMO_STUDENT_PASSWORD: str = "Demo!2026"
    DEMO_STUDENT_NAME: str = "Demo Candidate"

    # --- CORS ---------------------------------------------------------------
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    CORS_ORIGIN_REGEX: str = r"https://.*\.vercel\.app"

    # --- Agentic question engine -------------------------------------------
    AGENT_USE_NLP: bool = True          # try spaCy; falls back to rules if absent
    AGENT_MAX_QUESTIONS: int = 40       # hard ceiling per article run
    AGENT_MIN_QUALITY: float = 0.55     # critic score below this is discarded
    AGENT_MIN_ARTICLE_CHARS: int = 320

    # --- Answer-sheet upload -------------------------------------------
    # OCR is optional in exactly the way spaCy is: absent means the candidate
    # types their transcription instead, which still works. The image itself is
    # never stored -- it is read in memory and dropped -- so this cap protects
    # request memory, not disk.
    OCR_ENABLED: bool = True
    UPLOAD_MAX_BYTES: int = 8 * 1024 * 1024
    UPLOAD_ALLOWED_TYPES: str = "image/jpeg,image/png,image/webp,image/heic"

    # --- News ingestion --------------------------------------------------
    # Public RSS feeds, which publishers provide for exactly this purpose.
    # "Label|url" pairs, comma separated. Questions are generated from these by
    # our own pipeline; no other site's question bank is copied.
    # Verified live and carrying full item bodies -- a headline-only feed reads
    # fine but gives the question pipeline nothing to extract facts from.
    NEWS_FEEDS: str = (
        "Dawn|https://www.dawn.com/feeds/home,"
        "Dawn World|https://www.dawn.com/feeds/world,"
        "The News|https://www.thenews.com.pk/rss/1/1,"
        "Tribune|https://tribune.com.pk/feed/home,"
        "Geo News|https://www.geo.tv/rss/1/1,"
        "Business Recorder|https://www.brecorder.com/feeds/latest-news"
    )
    NEWS_WINDOW_DAYS: int = 7
    NEWS_MAX_ITEMS: int = 40
    NEWS_MIN_CHARS: int = 200
    NEWS_TIMEOUT_SEC: int = 12
    # Feeds are cached in process memory rather than stored: current affairs are
    # read once and then stale, and persisting them is the fastest way to fill a
    # free-tier database with content nobody re-reads.
    NEWS_CACHE_MINUTES: int = 30
    AGENT_MAX_ARTICLE_CHARS: int = 60_000

    # --- Storage discipline (free-tier guard rails) ------------------------
    # The DB must stay under Neon's free 0.5 GB, so we prune aggressively.
    RETAIN_AGENT_RUNS: int = 200        # keep only the N most recent traces
    RETAIN_ARTICLE_BODY_DAYS: int = 45  # then drop raw body, keep summary+hash
    RETAIN_ATTEMPT_DETAIL_DAYS: int = 180  # then drop per-answer JSON, keep score
    MAX_UPLOAD_CHARS: int = 200_000

    # --- Rate limiting ------------------------------------------------------
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_AUTH_PER_MIN: int = 10
    RATE_LIMIT_AGENT_PER_HOUR: int = 30

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"

    @property
    def demo_enabled(self) -> bool:
        """Demo accounts never advertise themselves on a production deployment.

        Requiring DEMO_MODE *and* a non-production environment means forgetting
        to flip the flag during a deploy cannot publish working credentials.
        """
        return self.DEMO_MODE and not self.is_production

    @field_validator("DATABASE_URL")
    @classmethod
    def _normalise_database_url(cls, v: str) -> str:
        from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://") :]
        if v.startswith("postgresql://"):
            v = "postgresql+asyncpg://" + v[len("postgresql://") :]

        parts = urlsplit(v)
        if parts.query:
            # asyncpg speaks its own dialect; libpq-only args raise TypeError.
            drop = {"sslmode", "channel_binding", "options", "target_session_attrs"}
            kept = [(k, val) for k, val in parse_qsl(parts.query) if k not in drop]
            v = urlunsplit(parts._replace(query=urlencode(kept)))
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

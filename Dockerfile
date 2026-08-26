# Root Dockerfile, for hosts that build from the repository root.
#
# Render's Docker runtime looks for ./Dockerfile relative to the service's Root
# Directory, and a service created by hand defaults that to the repo root -- so
# a monorepo whose Dockerfile lives in backend/ fails with
# "failed to read dockerfile" before it does anything. Rather than depend on a
# dashboard field being set correctly, this builds the backend from the root.
#
# backend/Dockerfile is kept for the case where the build context IS backend/
# (the blueprint sets rootDir there). The two do the same thing; only the paths
# differ.

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first, so editing application code does not rebuild the wheels.
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Only the backend. The frontend deploys to Vercel and has no business in this
# image -- copying it would add node_modules and the build output for nothing.
COPY backend/ .

# Run as a non-root user; nothing here writes to the image.
RUN useradd --create-home --uid 10001 issb && chown -R issb:issb /app
USER issb

EXPOSE 8000

# Migrations and the seed run at start, not at build: the database is only
# reachable at runtime. The seed is idempotent, so this creates the catalog and
# the admin account on first boot and does nothing on later ones -- without it
# the service comes up with a schema and no way to sign in.
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

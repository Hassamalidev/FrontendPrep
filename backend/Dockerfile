# Slim image for hosts that want a container rather than a buildpack.
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first, so a code change does not invalidate the wheel layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as a non-root user; nothing here needs to write to the image.
RUN useradd --create-home --uid 10001 issb && chown -R issb:issb /app
USER issb

EXPOSE 8000

# Migrations run at start rather than at build, because the database is only
# reachable at runtime.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

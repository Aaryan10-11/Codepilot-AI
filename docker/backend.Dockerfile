# syntax=docker/dockerfile:1

# ---- Build stage -----------------------------------------------------------
FROM ghcr.io/astral-sh/uv:0.11.6 AS uv

FROM python:3.12-slim AS builder

COPY --from=uv /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependency layer: cached until the lockfile changes.
COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY backend/ ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---- Runtime stage ---------------------------------------------------------
FROM python:3.12-slim AS runtime

RUN groupadd --gid 10001 codepilot \
    && useradd --uid 10001 --gid codepilot --create-home --no-log-init codepilot

WORKDIR /app

COPY --from=builder --chown=codepilot:codepilot /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER codepilot

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/v1/health/live', timeout=3)"

CMD ["uvicorn", "codepilot.app:create_app", "--factory", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--no-access-log", "--proxy-headers"]

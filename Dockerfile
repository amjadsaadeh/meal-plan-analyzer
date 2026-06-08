# Node/Vite build stage
FROM node:22-slim AS node-builder

WORKDIR /app

RUN corepack enable pnpm

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY vite.config.ts ./
COPY frontend/src/ frontend/src/

RUN pnpm build

# Python dependency build stage
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Final stage
# Try python:3.12.13-bookworm which might have newer system packages
FROM python:3.12.13-bookworm

WORKDIR /app

# Install system dependencies for WeasyPrint
# First update and dist-upgrade ALL existing packages to fix vulnerabilities
# Then install required dependencies
RUN apt-get update && apt-get dist-upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 --no-create-home --shell /sbin/nologin appuser

# Copy the Python virtualenv from the builder
COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1

ARG APP_VERSION=unknown
ENV APP_VERSION=${APP_VERSION}

# Copy the application code (deployment/ and docs/ are excluded via .dockerignore)
COPY . .

# Copy built frontend assets from node builder
COPY --from=node-builder /app/frontend/dist/ /app/frontend/dist/

# Create directory for static files and set ownership
RUN mkdir -p /app/staticfiles && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-", "--capture-output", "config.wsgi:application"]

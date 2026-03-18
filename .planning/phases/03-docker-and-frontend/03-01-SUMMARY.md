---
plan: 03-01
phase: 03-docker-and-frontend
status: complete
completed: 2026-03-18
commits:
  - 991566c
  - 1484946
---

# Summary: 03-01 — Docker Compose Infrastructure

## What was built

Updated `docker-compose.yml` with full async worker infrastructure:

- `redis:7-alpine` service with healthcheck (`redis-cli ping`, 10s interval, 5 retries)
- `worker` service reusing the built image, running `celery -A config worker --loglevel=info --concurrency=2 --max-tasks-per-child=50`
- Worker mounts only `media_files:/app/media` — no source bind-mount (code baked into image)
- `web` service gains `media_files:/app/media`, `CELERY_BROKER_URL`, `REDIS_URL`, `SITE_BASE_URL=http://web:8000`, and depends on redis healthcheck
- `media_files` named volume declared at top level
- Anonymous volume `- /app/.venv` added to web service to prevent source bind-mount from overwriting Docker's built venv (host venv symlinks to `/usr/bin/python3.12` which doesn't exist in `python:3.12-slim-bookworm`)

## Verification

Human-verified: all 4 services (`db`, `redis`, `web`, `worker`) started cleanly. Worker logged `celery@... ready.` and connected to Redis.

## Key decisions

- `SITE_BASE_URL=http://web:8000` in worker env — Docker DNS, not localhost
- Worker does NOT mount `.:/app` — pitfall avoided; production image is used as-is
- `/app/.venv` anonymous volume — fix for broken symlink in bind-mounted local venv

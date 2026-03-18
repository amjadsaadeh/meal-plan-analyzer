---
plan: 01-01
phase: 01-foundation
status: complete
completed: 2026-03-18
---

# Summary: Wire Celery into Django + Redis Cache Backend

## What Was Built

Celery 5.6.2 wired into the Django app with Redis as broker. Django's cache backend switched from LocMemCache (implicit default) to the built-in Redis backend, fixing the existing cross-worker alias cache staleness bug as a free win. SITE_BASE_URL added for WeasyPrint worker context.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| T1 | Install celery[redis]>=5.4, create config/celery.py, wire config/__init__.py, document env vars | 6ddd398 |
| T2 | Add Celery settings block, Redis CACHES, SITE_BASE_URL to config/settings.py | feefe5c |

## Key Files Created/Modified

- `config/celery.py` — Celery app with Django settings integration and autodiscover_tasks
- `config/__init__.py` — celery_app import (prevents silent @shared_task registration failures)
- `config/settings.py` — CELERY_* block, CACHES with RedisCache db/1, SITE_BASE_URL
- `.env.example` — CELERY_BROKER_URL, REDIS_URL, SITE_BASE_URL documented
- `pyproject.toml` / `uv.lock` — celery[redis]>=5.4 added

## Verification

- `celery.__version__` → 5.6.2 ✓
- `app.main` → "meal_plan_analyzer" ✓
- `from config import celery_app` → Celery instance ✓
- Cache backend → `django.core.cache.backends.redis.RedisCache` ✓
- `CELERY_WORKER_MAX_TASKS_PER_CHILD` → 50 ✓
- `SITE_BASE_URL` → "http://localhost:8000" ✓
- `manage.py check` → 0 issues ✓

## Self-Check: PASSED

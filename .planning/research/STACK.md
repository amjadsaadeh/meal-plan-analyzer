# Technology Stack: Async Background Tasks

**Project:** RSOS Meal Planner — Async Export Milestone
**Researched:** 2026-03-16
**Scope:** Django async task infrastructure for offloading WeasyPrint PDF generation

---

## Recommended Stack

### Task Queue

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `celery` | `>=5.4` | Background task runner and scheduler | Industry-standard for Django; actively maintained; full Django integration; Python 3.12 support confirmed in 5.4 series. The 5.x line has been stable since 2021 and received regular point releases through 2025. |
| `redis` (Python client) | `>=5.0` | Celery broker and result backend transport | `redis-py` 5.x is the maintained branch; adds support for Redis 7.x features and deprecates the older `hiredis` parser in favour of the built-in RESP3 parser. |

### Redis Server

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Redis (Docker image `redis:7-alpine`) | `7.x` | Message broker + result store | Redis 7 is the current stable generation; 7.2 introduced Redis Stack features but the base image is all that is needed here. Alpine variant keeps the image small (~40 MB). |

### Django Integration

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `django-celery-results` | `>=2.5` | Stores Celery task results in Django's ORM (PostgreSQL) | Allows querying task state from the same PostgreSQL database already in use; no second Redis scan needed for the progress polling API; results are durable across Redis restarts. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `celery[redis]` extras | included in `celery>=5.4` | Installs `redis` transport deps automatically | Use the extras form `celery[redis]` in `pyproject.toml` rather than listing `celery` and `redis` separately — ensures version-compatible transport layer. |

---

## Alternatives Considered and Rejected

### django-q2

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Task queue | Celery 5 | django-q2 | django-q2 is a fork of the unmaintained `django-q`; it uses Django's ORM or Redis as both broker and result store, which is appealing for simplicity. However, its worker concurrency model uses multiprocessing in a way that is less battle-tested than Celery's, and it lacks the monitoring ecosystem (Flower) that Celery has. For a single long-running task type, the simpler ORM-backed approach is tempting, but Celery is a better foundation for future extensibility (BLS import task, etc.) and has wider community support. |

### dramatiq

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Task queue | Celery 5 | dramatiq | dramatiq is a well-designed library with better defaults than Celery (no need to register tasks, saner retry semantics), but `django-dramatiq` integration is a third-party wrapper that is less actively maintained than `django-celery-results`. For a Django-first project, Celery's tighter Django ecosystem wins. Dramatiq would be the recommendation if starting a non-Django Python service. |

### arq

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Task queue | Celery 5 | arq | arq is an async-first task queue built for asyncio/uvicorn stacks. It requires Python async functions throughout the worker. This app uses synchronous Django (WSGI via gunicorn) and WeasyPrint has no async API — running it in arq would require `asyncio.to_thread()` wrappers everywhere. The complexity cost is not justified. Use arq only when the entire stack is async (ASGI + async views). |

### RQ (Redis Queue)

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Task queue | Celery 5 | RQ | RQ is simpler than Celery but has weaker result-backend support and no native Django integration for storing results in the ORM. Progress reporting (percentage updates from within a running task) is more awkward to implement cleanly in RQ. |

### PostgreSQL as broker (Celery with `sqla` transport)

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Broker | Redis | PostgreSQL / SQLAlchemy transport | Celery's SQLAlchemy transport is marked as experimental. Using the application's PostgreSQL database as a task broker is an antipattern — it creates polling-based queue semantics that put load on Postgres and don't scale. Redis is the right broker. |

### django-celery-results vs. Redis as result backend

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Result backend | django-celery-results (PostgreSQL) | Redis result backend | Storing results in Redis means a Redis restart wipes all task records, making the progress polling API unreliable. Since PostgreSQL is already in the stack and is durable, storing task results there is strictly better for this use case. The `BackgroundJob` model the project plans to add already implies DB-backed state. |

---

## Version Pins (Confidence Notes)

**IMPORTANT: Web tools were unavailable during research. The following version ranges are based on training data through August 2025 and should be verified against PyPI before pinning.**

| Package | Training-data version (Aug 2025) | Confidence | Verification path |
|---------|----------------------------------|-----------|-------------------|
| `celery` | 5.4.x was current stable (5.4.0 released Apr 2024, point releases through 2025) | MEDIUM — verify `uv add celery[redis]` will resolve to 5.x | `pip index versions celery` or PyPI |
| `redis` (py) | 5.0.x series | MEDIUM | `pip index versions redis` or PyPI |
| `django-celery-results` | 2.5.x | MEDIUM | `pip index versions django-celery-results` or PyPI |
| Redis server image | `redis:7-alpine` (7.2.x) | HIGH — Redis 7 has been stable for 2+ years | Docker Hub |

**Safe conservative pins for `pyproject.toml`:**
```toml
"celery[redis]>=5.4",
"django-celery-results>=2.5",
```
These lower bounds guarantee Python 3.12 support and the result-backend DB migration support introduced in 2.5. uv will resolve to the latest compatible version.

---

## Installation

```bash
# Add to project
uv add "celery[redis]>=5.4" "django-celery-results>=2.5"
```

This adds both packages to `[project].dependencies` in `pyproject.toml` and updates `uv.lock`. Commit both files.

---

## Django Integration Pattern

### settings.py additions

```python
# Celery
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = "django-db"          # django-celery-results ORM backend
CELERY_CACHE_BACKEND = "default"             # fallback; not used when django-db is set
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_TRACK_STARTED = True             # enables STARTED state → progress polling
CELERY_TASK_TIME_LIMIT = 300                 # 5-min hard limit per task (WeasyPrint guard)
CELERY_TASK_SOFT_TIME_LIMIT = 240            # 4-min soft limit → raises SoftTimeLimitExceeded

INSTALLED_APPS = [
    ...
    "django_celery_results",
]
```

### config/celery.py (new file)

```python
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
app = Celery("meal_plan_analyzer")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

### config/__init__.py

```python
from .celery import app as celery_app
__all__ = ("celery_app",)
```

### Running the worker (local dev)

```bash
uv run celery -A config worker --loglevel=info --concurrency=2
```

### Running the worker (Docker Compose)

Add a `worker` service to `docker-compose.yml` that shares the `web` image and overrides `command`:

```yaml
worker:
  build: .
  command: celery -A config worker --loglevel=info --concurrency=2
  environment:
    - SECRET_KEY=${SECRET_KEY:-change-me}
    - DATABASE_URL=postgres://mealplanner:mealplanner@db:5432/mealplanner
    - CELERY_BROKER_URL=redis://redis:6379/0
    - DEBUG=True
  depends_on:
    db:
      condition: service_healthy
    redis:
      condition: service_healthy
```

The Celery worker needs WeasyPrint system libraries (libpango, libcairo, etc.) since it runs the same PDF generation code. The existing `Dockerfile` final stage already installs them, so the same image is reused for both the web and worker services — no separate Dockerfile needed.

---

## Result Backend Decision: django-celery-results vs. Custom Job Model

The PROJECT.md calls for a `BackgroundJob` model with `status`, `progress`, and `result_file` fields. There are two approaches:

### Option A: Custom BackgroundJob model (RECOMMENDED)

Create a `BackgroundJob` (or `ExportJob`) Django model with:
- `task_id` — Celery task UUID, used to call `AsyncResult(task_id)`
- `status` — choices: `pending / running / done / failed`
- `progress` — IntegerField 0–100
- `result_file` — FileField (PDF stored in MEDIA_ROOT)
- `created_at`, `updated_at` — timestamps

The Celery task updates this model row directly as it progresses. The polling API endpoint reads from this model. `django-celery-results` is NOT needed if this approach is used — Celery results are stored in the custom model, not the framework's task result table.

**Why this is better for this project:**
- The polling API (`GET /api/export-jobs/<id>/`) is a clean DRF ViewSet over a domain model
- Progress percentage is a first-class field (not shoehorned into Celery's `meta` dict)
- The result file (PDF bytes) is stored as a Django FileField, not serialized into a JSON result
- Future tasks (BLS import) slot into the same model with a `job_type` field
- No dependency on `django-celery-results` migration overhead

### Option B: django-celery-results only

Use Celery's built-in result storage via `django-celery-results`. Progress is stored in the `TaskResult.meta` JSON field. No custom model.

**Why this is worse for this project:**
- Progress percentage must be packed/unpacked from a generic `meta` dict
- The result file (PDF bytes) cannot be stored as a FileField — it would need to be base64-encoded into JSON or stored separately anyway
- The polling API endpoint wraps a framework table rather than a domain-appropriate model
- Less extensible when a BLS import job (with different progress semantics) needs to be added

**Conclusion:** Add `django-celery-results` as a dependency anyway (it provides the DB result backend connection that confirms task state persistence), but the primary data surface for the polling API is the custom `BackgroundJob` model. The Celery task writes to both: updates `BackgroundJob.progress` as it runs, then stores the PDF in `BackgroundJob.result_file` when done. `CELERY_RESULT_BACKEND = "django-db"` acts as a safety net for task failure state; the custom model is the primary source of truth for the frontend.

---

## Redis in Docker Compose

Add to `docker-compose.yml`:

```yaml
redis:
  image: redis:7-alpine
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 5s
    retries: 5
```

Add `CELERY_BROKER_URL=redis://redis:6379/0` to the `web` service environment.

---

## Cache Backend Upgrade (Opportunistic)

The CONCERNS.md identifies that the default `LocMemCache` is not shared across gunicorn workers, causing stale `food_aliases_index` cache entries. Since Redis is now in the stack, upgrading the Django cache backend is a low-cost improvement:

```python
# settings.py
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6379/1"),
    }
}
```

Use database 1 for the Django cache (database 0 for Celery broker) to avoid key namespace collisions.

This is a separate concern from the task queue but worth doing in the same milestone since Redis is being added.

---

## What NOT to Use

| Avoid | Reason |
|-------|--------|
| `django-background-tasks` | Unmaintained; uses DB polling, not a real broker |
| `celery[sqs]` or `celery[rabbitmq]` | No reason to add AWS SQS or RabbitMQ to a Compose stack that already has Redis |
| `django-rq` | RQ is simpler than Celery but lacks Django ORM result backend and clean progress update patterns |
| `huey` | Smaller ecosystem, less documentation for Django-specific patterns; fine for small projects but Celery is the better long-term foundation |
| Celery 4.x | Python 3.12 support is incomplete in 4.x; requires 5.x |
| `celery beat` | Not needed — there are no scheduled/recurring tasks in this milestone. Can be added later if needed. |

---

## Sources

- Training data on Celery 5.x/Django integration patterns (MEDIUM confidence — verified against project constraints)
- Project context: `.planning/PROJECT.md`, `.planning/codebase/STACK.md`, `.planning/codebase/CONCERNS.md`
- Codebase: `pyproject.toml`, `docker-compose.yml`, `Dockerfile`
- NOTE: PyPI version verification and official Celery changelog were not accessible during research (web tools unavailable). Version ranges above are conservative lower bounds that should be verified before finalizing `pyproject.toml` pins.

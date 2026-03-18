# Phase 1: Foundation - Research

**Researched:** 2026-03-18
**Domain:** Django + Celery + Redis async infrastructure setup, BackgroundJob model, cache backend migration
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-01 | Celery app is wired into Django (`config/celery.py`, `celery_app` imported in `config/__init__.py`, `CELERY_BROKER_URL` from env) | Canonical Celery+Django wiring pattern documented; exact file structure confirmed from codebase inspection |
| INFRA-02 | Redis is the broker and Django cache backend (`django-redis` replaces `LocMemCache` for all workers) | Django built-in `RedisCache` backend sufficient (no extra package needed); Redis db/0 for Celery broker, db/1 for cache |
| INFRA-05 | `SITE_BASE_URL` env var is added to settings and `.env.example` for WeasyPrint's `base_url` in the worker context | WeasyPrint `base_url` requires an absolute URL; `request.build_absolute_uri()` not available in worker; `SITE_BASE_URL` is the correct solution |
| JOB-01 | `BackgroundJob` model exists with UUID primary key, `task_type` CharField, `status` TextChoices (`pending/running/done/failed`), `progress` PositiveSmallIntegerField (0–100), `task_kwargs` JSONField, `result_file` FileField (nullable), `error_message` TextField (blank), `expires_at` DateTimeField, `created_at`/`updated_at` auto timestamps | Full model design established; field rationale documented; UUID PK is standard security practice |
| JOB-02 | Migration is created and applied for `BackgroundJob` | Standard Django migration; next number is 0025; migration must be committed |
| TASK-04 | Worker is configured with `max_tasks_per_child` to prevent WeasyPrint CFFI memory leaks | `CELERY_WORKER_MAX_TASKS_PER_CHILD=50` and `CELERY_WORKER_MAX_MEMORY_PER_CHILD=200000` are the correct settings; documented in Celery worker configuration |
</phase_requirements>

---

## Summary

Phase 1 establishes the async infrastructure layer that all subsequent phases depend on. It has three distinct work items: (1) wire Celery into Django, (2) create the `BackgroundJob` model with migration, and (3) switch the Django cache backend from `LocMemCache` to Redis. None of these produce user-visible output; they are pure prerequisites.

The codebase is in a clean starting state. `config/__init__.py` is currently empty (one blank line). `config/celery.py` does not exist. There are no Celery-related settings in `settings.py` and no Redis dependencies in `pyproject.toml`. The existing `CACHES` setting is the Django default (`LocMemCache`). The last migration is `0024_food_data_source.py`, so the new `BackgroundJob` migration will be `0025`. The `.env.example` has no `CELERY_BROKER_URL`, `REDIS_URL`, or `SITE_BASE_URL` entries.

The patterns for this phase are canonical, well-documented, and stable. Celery 5.x has been stable since 2021. The current stable release is 5.6.x (January 2026). `django-celery-results` 2.5.1 was released March 2026. The `CELERY_WORKER_MAX_TASKS_PER_CHILD` and `CELERY_WORKER_MAX_MEMORY_PER_CHILD` settings that address the WeasyPrint CFFI memory leak (TASK-04) belong in this phase since they are part of the Celery worker configuration in `settings.py`.

**Primary recommendation:** Wire Celery using the canonical three-file pattern (`config/celery.py` + `config/__init__.py` import + settings additions), create the `BackgroundJob` model with all fields required by JOB-01 (including `task_kwargs` JSONField and `expires_at` for future cleanup), and switch `CACHES` to `django.core.cache.backends.redis.RedisCache` on Redis db/1 while Celery uses db/0.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `celery[redis]` | `>=5.4` (5.6.x current stable Jan 2026) | Task queue, worker process, broker transport | Industry-standard Django async; `[redis]` extras install `redis-py` transport; Python 3.12 support confirmed |
| Redis server (`redis:7-alpine`) | 7.x (7.2+ current) | Message broker + optional result backend | Redis 7 stable for 2+ years; Alpine image ~40 MB; `redis-cli ping` healthcheck supported |
| Django built-in `RedisCache` | Django 6.0 (included) | Django cache backend replacing LocMemCache | Built-in since Django 4.0; no extra package needed; fixes cross-worker alias cache staleness |

### Supporting (Optional)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `django-celery-results` | `>=2.5` (2.5.1 current Mar 2026) | Stores Celery task metadata in Django ORM (PostgreSQL) | Safety net for failure introspection; NOT needed if `BackgroundJob` model owns all state; decision documented below |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Django built-in `RedisCache` | `django-redis` | `django-redis` has extra features (custom serializers, connection pool configuration). Not needed for this project; built-in backend is sufficient |
| Redis result backend (`CELERY_RESULT_BACKEND=None`) | `django-celery-results` (django-db backend) | If `BackgroundJob` model is the sole source of truth, Celery result backend is not needed. Can set `CELERY_IGNORE_RESULT=True` to suppress result writes entirely. Simpler, no extra migration |
| `CELERY_RESULT_BACKEND=None` | `redis://redis:6379/0` as result backend | Redis result backend is volatile (wiped on restart). Simpler than django-db but unreliable for failure debugging. PostgreSQL via `django-celery-results` is more durable |

**Decision for this project:** Do NOT add `django-celery-results` in Phase 1. The `BackgroundJob` model is the source of truth. Set `CELERY_RESULT_BACKEND = None` (or omit). This removes an unnecessary dependency and migration. If debugging needs arise, the `BackgroundJob.error_message` field captures task failures.

**Installation:**
```bash
uv add "celery[redis]>=5.4"
```

This adds `celery` and `redis-py` (via extras) to `pyproject.toml` and updates `uv.lock`. Commit both files.

---

## Architecture Patterns

### File Structure for Phase 1

```
config/
├── __init__.py       # ADD: from .celery import app as celery_app; __all__ = ("celery_app",)
├── celery.py         # NEW: Celery app instantiation + autodiscover
└── settings.py       # MODIFY: add Celery settings block + CACHES + SITE_BASE_URL

meals/
├── models.py         # MODIFY: add BackgroundJob model
└── migrations/
    └── 0025_backgroundjob.py   # NEW: migration for BackgroundJob

.env.example          # MODIFY: add CELERY_BROKER_URL, REDIS_URL, SITE_BASE_URL
```

### Pattern 1: Canonical Celery + Django Wiring

**What:** Three-file setup that ensures `@shared_task` in `meals/tasks.py` (Phase 2) is always registered against the correct Celery app.

**When to use:** Always for Django + Celery. This is the only correct pattern.

**Example:**
```python
# config/celery.py
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("meal_plan_analyzer")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

```python
# config/__init__.py  (currently empty — must add this import)
from .celery import app as celery_app

__all__ = ("celery_app",)
```

The `config/__init__.py` import is mandatory. Without it, Django's module system never imports `config.celery`, the Celery app is never created, and `@shared_task` decorators in `meals/tasks.py` silently register against an uninitialised app.

### Pattern 2: BackgroundJob Model Design

**What:** Generic job tracking model with UUID PK, status FSM, progress field, result file, and extensibility fields.

**When to use:** This exact schema is specified in JOB-01. Build it exactly as specified, including `task_kwargs` JSONField (needed for future BLS import task) and `expires_at` (needed for future cleanup, schema must exist from day one).

```python
# meals/models.py  (add after existing models)
import uuid
from django.db import models


class BackgroundJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_type = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    progress = models.PositiveSmallIntegerField(default=0)
    task_kwargs = models.JSONField(default=dict, blank=True)
    result_file = models.FileField(
        upload_to="exports/", null=True, blank=True
    )
    error_message = models.TextField(blank=True, default="")
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
```

**Field rationale:**
- UUID PK: prevents job ID enumeration in HTTP URLs
- `task_type`: discriminator for future task types (e.g. `'pdf_export'`, `'bls_import'`)
- `task_kwargs`: JSONField allows future tasks (BLS import) to store their input parameters without a new migration
- `expires_at`: null until a cleanup mechanism sets it; schema must exist from day one per REQUIREMENTS.md
- `result_file`: `upload_to='exports/'` → files land in `MEDIA_ROOT/exports/<uuid>.pdf`

### Pattern 3: Celery Settings Block

**What:** All Celery settings in `settings.py`, namespaced with `CELERY_` prefix (read by `app.config_from_object("django.conf:settings", namespace="CELERY")`).

```python
# settings.py additions

# --- Celery ---
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = None           # BackgroundJob model is source of truth
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_TRACK_STARTED = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # prevents long tasks from starving the queue
CELERY_WORKER_MAX_TASKS_PER_CHILD = 50  # TASK-04: WeasyPrint CFFI memory leak mitigation
CELERY_WORKER_MAX_MEMORY_PER_CHILD = 200_000  # 200 MB safety net (in KB)
CELERY_TIMEZONE = "UTC"
CELERY_ENABLE_UTC = True

# --- Django cache (Redis, replaces LocMemCache) ---
# Use db/1 to isolate cache from Celery broker on db/0
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6379/1"),
    }
}

# --- WeasyPrint worker context ---
SITE_BASE_URL = env("SITE_BASE_URL", default="http://localhost:8000")
```

**Note on `CELERY_WORKER_MAX_TASKS_PER_CHILD`:** This is a `CELERY_` prefixed settings key that maps to Celery's `worker_max_tasks_per_child` setting. It goes in `settings.py` as part of the Celery namespace. The Celery worker CLI flag `--max-tasks-per-child` in Docker Compose is an alternative, but the settings-file approach is preferable for consistency and version control.

### Pattern 4: `.env.example` Additions

Add three new variables to `.env.example`:

```bash
# Async task queue (Celery + Redis)
CELERY_BROKER_URL=redis://redis:6379/0
REDIS_URL=redis://redis:6379/1

# WeasyPrint base URL (used by Celery worker — no request context)
SITE_BASE_URL=http://localhost:8000
```

### Anti-Patterns to Avoid

- **Don't create a separate `meals/celery.py`:** The Celery app belongs in `config/celery.py` (the Django project package), not in an app package. Using `@shared_task` in `meals/tasks.py` correctly binds to the app regardless.
- **Don't set `CELERY_RESULT_BACKEND = "django-db"`:** This requires `django-celery-results` and an extra migration. Since `BackgroundJob` is the source of truth, this adds complexity with no benefit.
- **Don't combine broker and cache on the same Redis db index:** Use db/0 for Celery broker, db/1 for Django cache. Key collisions between task IDs and cache keys will cause subtle bugs.
- **Don't skip adding `expires_at` to `BackgroundJob`:** Even though the cleanup mechanism comes in a later phase, the schema must be forward-compatible from day one per REQUIREMENTS.md design notes.
- **Don't add `django_celery_results` to `INSTALLED_APPS`:** If `django-celery-results` is not installed, this causes an `ImproperlyConfigured` error on startup.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Task queue and worker process management | Custom subprocess manager or threading | `celery[redis]` | Celery handles retries, worker pool, serialization, broker reconnection, graceful shutdown |
| Redis cache backend | Custom Redis cache adapter | `django.core.cache.backends.redis.RedisCache` | Built into Django 4.0+; already in the project's Django 6.0; no extra package needed |
| UUID generation for model PK | `secrets.token_hex()` or random strings | `uuid.uuid4` via `models.UUIDField(default=uuid.uuid4)` | Database-level UUID type; Django handles storage correctly for both SQLite and PostgreSQL |
| Job status transitions | Boolean flags or integer codes | `models.TextChoices` with string values | Human-readable in admin, API responses, and logs; type-safe in Python |

**Key insight:** Phase 1 is all configuration and model definition — no custom algorithms needed. The only hand-rolling risk is re-implementing what `celery[redis]` already provides.

---

## Common Pitfalls

### Pitfall 1: Missing `config/__init__.py` import
**What goes wrong:** `celery -A config worker` starts but `@shared_task` tasks in `meals/tasks.py` raise `NotRegistered` when `.delay()` is called.
**Why it happens:** `config/__init__.py` is currently empty. The Celery app created in `config/celery.py` is never imported unless explicitly pulled in.
**How to avoid:** Add `from .celery import app as celery_app; __all__ = ("celery_app",)` to `config/__init__.py`.
**Warning signs:** `celery -A config inspect registered` returns an empty task list.

### Pitfall 2: `CELERY_WORKER_MAX_TASKS_PER_CHILD` key name vs CLI flag
**What goes wrong:** The settings key `CELERY_WORKER_MAX_TASKS_PER_CHILD` (used when `namespace="CELERY"` is set) maps to Celery's `worker_max_tasks_per_child` config. The CLI flag is `--max-tasks-per-child`. Using the wrong name means the setting is silently ignored.
**Why it happens:** Celery's settings namespace strips the `CELERY_` prefix and lowercases: `CELERY_WORKER_MAX_TASKS_PER_CHILD` → `worker_max_tasks_per_child`. This is the correct key.
**How to avoid:** Use the exact key `CELERY_WORKER_MAX_TASKS_PER_CHILD` in `settings.py`. Verify by starting a worker and checking `celery -A config inspect conf` output.
**Warning signs:** Worker memory grows unboundedly in `docker stats` output.

### Pitfall 3: Using same Redis db index for broker and cache
**What goes wrong:** Cache keys and Celery task IDs occupy the same Redis keyspace. A `FLUSHDB` command clears both. More practically, keys like `food_aliases_index` could collide with Celery internal keys.
**Why it happens:** Default configuration uses db/0 for both.
**How to avoid:** Use `redis://redis:6379/0` for `CELERY_BROKER_URL` and `redis://redis:6379/1` for the cache `LOCATION`.
**Warning signs:** Cache invalidation clears Celery task state or vice versa.

### Pitfall 4: LocMemCache not replaced
**What goes wrong:** Adding Celery settings but forgetting to update `CACHES`. The `food_aliases_index` cache remains process-local. The new Celery worker process has its own isolated cache instance that is never invalidated by `FoodAlias` signals in the web worker. (INFRA-02 explicitly requires this fix.)
**Why it happens:** `CACHES` is not set in the current `settings.py`, so Django silently uses `LocMemCache`.
**How to avoid:** Add the `CACHES` block with `RedisCache` in the same PR as the Celery additions.
**Warning signs:** After the change, run `python manage.py shell -c "from django.core.cache import cache; print(cache.__class__)"` — it should print the Redis backend class.

### Pitfall 5: Migration number conflict
**What goes wrong:** The next migration number should be `0025`. If another migration is created on a feature branch simultaneously, a conflict arises.
**Why it happens:** Django migration names are sequential per app.
**How to avoid:** Verify the latest migration is `0024_food_data_source.py` (confirmed). Name the new migration `0025_backgroundjob.py`. Use `uv run python manage.py makemigrations meals --name backgroundjob`.

### Pitfall 6: `expires_at` DateTimeField — null vs default
**What goes wrong:** REQUIREMENTS.md JOB-01 specifies `expires_at` as a `DateTimeField`. If declared without `null=True`, existing rows (and `makemigrations`) will require a default value.
**Why it happens:** Non-nullable `DateTimeField` without a default cannot be added to an existing table.
**How to avoid:** Declare `expires_at = models.DateTimeField(null=True, blank=True)`. The cleanup mechanism (future phase) sets this field when creating jobs.

---

## Code Examples

### Celery App Instantiation

```python
# config/celery.py
# Source: https://docs.celeryq.dev/en/latest/django/first-steps-with-django.html
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("meal_plan_analyzer")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

### config/__init__.py (complete file after change)

```python
# config/__init__.py
# Source: https://docs.celeryq.dev/en/latest/django/first-steps-with-django.html
from .celery import app as celery_app

__all__ = ("celery_app",)
```

### BackgroundJob model (complete)

```python
# meals/models.py — add below existing models
import uuid
from django.db import models


class BackgroundJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_type = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    progress = models.PositiveSmallIntegerField(default=0)
    task_kwargs = models.JSONField(default=dict, blank=True)
    result_file = models.FileField(upload_to="exports/", null=True, blank=True)
    error_message = models.TextField(blank=True, default="")
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
```

### Generating the migration

```bash
uv run python manage.py makemigrations meals --name backgroundjob
uv run python manage.py migrate
```

### Verifying Celery wiring

```bash
# Start a worker in a separate terminal
uv run celery -A config worker --loglevel=info --concurrency=2

# In another terminal, verify tasks are discovered
uv run celery -A config inspect registered
# Expected output: meals.tasks.generate_pdf_task (once Phase 2 is done)
# Phase 1 check: empty list is OK — wiring is valid if worker starts without ImportError
```

### Verifying Redis cache backend

```bash
uv run python manage.py shell -c "
from django.core.cache import cache
print(type(cache).__module__)
# Expected: django.core.cache.backends.redis
"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `LocMemCache` (Django default) | `django.core.cache.backends.redis.RedisCache` | Django 4.0 (built-in) | Cross-process cache sharing; fixes alias index staleness |
| `django-redis` package for Redis cache | Django built-in `RedisCache` | Django 4.0+ | No extra package needed; `django-redis` only needed for advanced features |
| `CELERY_ALWAYS_EAGER = True` in tests | `task_always_eager` via pytest-celery or mock | Celery 5.x | `CELERY_ALWAYS_EAGER` still works but test-specific config is preferred |
| `celery 4.x` | `celery 5.x` (5.6.x current Jan 2026) | 2021 | Python 3.12 support requires 5.x; 4.x drops `CELERY_` namespace prefix |

**Deprecated/outdated:**
- Celery 4.x: Python 3.12 support incomplete; ALWAYS use 5.x for this project.
- `CELERY_ALWAYS_EAGER`: functional but discouraged; tasks run synchronously in tests, masking serialization errors (the primary risk this project has per PITFALLS.md Pitfall 4).
- `django-redis` package: valid and feature-rich, but not needed for this project. Django's built-in `RedisCache` is sufficient.

---

## Open Questions

1. **`django-celery-results`: include or omit?**
   - What we know: The `BackgroundJob` model is the source of truth. `django-celery-results` provides durability for Celery's own task metadata in PostgreSQL.
   - What's unclear: Whether the team wants the safety net of `django-db` backend for failure debugging (requires an extra migration and `INSTALLED_APPS` entry).
   - Recommendation: **Omit in Phase 1.** Set `CELERY_RESULT_BACKEND = None` and `CELERY_IGNORE_RESULT = True`. This is simpler. Add `django-celery-results` later if debugging needs arise. The `BackgroundJob.error_message` field is sufficient for user-facing failure information.

2. **`CELERY_WORKER_MAX_TASKS_PER_CHILD` in settings vs. Docker Compose command**
   - What we know: REQUIREMENTS.md TASK-04 says "worker is configured" — this could mean settings.py or the `command:` in docker-compose.yml.
   - What's unclear: Phase 3 (Docker Compose) adds the worker service. Setting `MAX_TASKS_PER_CHILD` in `settings.py` means it applies to local dev too.
   - Recommendation: Set in `settings.py` (applies everywhere); also set in `celery -A config worker --max-tasks-per-child=50` in docker-compose.yml command as explicit documentation. Both are redundant but clear.

---

## Sources

### Primary (HIGH confidence)
- `config/__init__.py` — confirmed empty (1 line); no existing Celery import
- `config/settings.py` — confirmed no `CACHES` block, no Celery settings, no Redis env vars
- `pyproject.toml` — confirmed no `celery` or `django-redis` in dependencies
- `.env.example` — confirmed no `CELERY_BROKER_URL`, `REDIS_URL`, `SITE_BASE_URL`
- `meals/migrations/0024_food_data_source.py` — latest migration; next number is 0025
- https://docs.celeryq.dev/en/latest/django/first-steps-with-django.html — canonical Django+Celery wiring
- `.planning/research/ARCHITECTURE.md` — full component design, data flow, field rationale
- `.planning/research/PITFALLS.md` — Pitfalls 1, 7, 8 directly relevant to Phase 1

### Secondary (MEDIUM confidence)
- WebSearch result: Celery 5.6.x stable as of January 2026 — https://pypi.org/project/celery/
- WebSearch result: `django-celery-results` 2.5.1 released March 2026 — https://github.com/celery/django-celery-results/releases
- Django built-in `RedisCache` documentation — Django 4.0+ built-in; HIGH confidence for Django 6.0 project
- `CELERY_WORKER_MAX_TASKS_PER_CHILD` settings namespace key — verified from training knowledge of Celery 5.x `namespace="CELERY"` config pattern

### Tertiary (LOW confidence — training knowledge, flag for validation)
- `CELERY_WORKER_MAX_MEMORY_PER_CHILD` exact unit (kilobytes) — verify against `celery -A config inspect conf` output after implementation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pypi.org confirmed Celery 5.6.x; codebase confirms no existing Celery/Redis dependencies
- Architecture: HIGH — all three work items follow canonical patterns; exact file paths confirmed from codebase inspection
- Pitfalls: HIGH — all Phase 1 pitfalls derived from direct codebase observation (empty `__init__.py`, no `CACHES` config, migration sequence)

**Research date:** 2026-03-18
**Valid until:** 2026-04-18 (Celery is stable; Django cache backend API is stable; 30-day window is conservative)

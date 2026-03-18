# Architecture Patterns: Django + Celery Async Job System

**Domain:** Django async background task infrastructure with DB-tracked job model
**Researched:** 2026-03-16
**Confidence:** HIGH (based on existing codebase analysis + established Django/Celery patterns)

---

## Recommended Architecture

### System Overview

The async export system introduces four new components layered on top of the existing Django monolith. The existing `meals` app gains a `BackgroundJob` model, a `ExportJobViewSet`, and a `tasks.py` module. Two new infrastructure services join Docker Compose: a Redis container (broker) and a Celery worker container (task executor).

```
Browser (Vue)
    │
    │  POST /api/export-jobs/          → create job, enqueue task
    │  GET  /api/export-jobs/<id>/     → poll status + progress
    │  GET  /api/export-jobs/<id>/result/ → download PDF bytes
    ▼
Django (gunicorn)
    ├── ExportJobViewSet  ──────────────→  BackgroundJob (DB)
    │       │                                   ▲
    │       └── task.delay(job_id, plan_pk)     │  (task writes progress/status)
    │                                           │
    ▼                                           │
Redis (broker + result backend)                 │
    │                                           │
    ▼                                           │
Celery Worker                                   │
    └── generate_pdf_task(job_id, plan_pk) ─────┘
            │
            ├── get_meal_plan_context(pk)   (re-used from views.py)
            ├── render_to_string(...)
            ├── weasyprint.HTML(...).write_pdf()
            └── job.result_file.save(...)   → MEDIA_ROOT/exports/<uuid>.pdf
```

---

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `BackgroundJob` model | Persistent record of a task: status FSM, progress %, result file path, error message | Django ORM; written by Celery worker, read by API ViewSet |
| `ExportJobViewSet` | HTTP entry points for creating a job, polling status, and downloading the result | `BackgroundJob` model; Celery task (via `.delay()`); DRF auth |
| `generate_pdf_task` (Celery task) | Renders WeasyPrint PDF in a worker process; updates job progress via DB writes | `BackgroundJob` model (direct DB write); `get_meal_plan_context()` from `views.py` |
| Redis | Celery broker (task queue) and result backend (optional) | Celery worker; Django `settings.CELERY_BROKER_URL` |
| Celery worker container | Process that dequeues and executes tasks | Redis (poll for tasks); PostgreSQL (Django ORM for job model) |
| Vue export component | Triggers job creation, drives the polling loop, presents progress bar, triggers download | `ExportJobViewSet` API |

---

## Data Flow

### Job Creation

1. User clicks "Export PDF" — Vue calls `POST /api/export-jobs/` with `{ meal_plan: <pk> }`.
2. `ExportJobViewSet.create()` creates a `BackgroundJob` row with `status='pending'`, returns `{ id, status, progress }`.
3. View immediately calls `generate_pdf_task.delay(job_id, plan_pk)` — this enqueues the task in Redis and returns a Celery `AsyncResult` (task ID stored in `BackgroundJob.celery_task_id`).
4. HTTP response returns immediately (job is pending, no work done yet).

### Task Execution

5. Celery worker dequeues the task.
6. Task sets `status='running'`, `progress=0`, saves to DB.
7. Task calls `get_meal_plan_context(plan_pk)` — pure DB read, no request context needed.
8. Task calls `render_to_string(...)` — no request context needed (static file paths resolved via `finders.find()`).
9. Task calls `weasyprint.HTML(string=html, base_url=settings.SITE_BASE_URL).write_pdf()`.
10. Task saves PDF bytes to `MEDIA_ROOT/exports/<uuid>.pdf` via `BackgroundJob.result_file.save(...)`.
11. Task sets `status='done'`, `progress=100`, saves.
12. On any exception: task sets `status='failed'`, `error_message=str(exc)`, saves. Does NOT re-raise (prevents Celery retry by default; explicit retry strategy if needed).

### Progress Reporting

Progress checkpoints during WeasyPrint rendering are coarse (WeasyPrint does not emit incremental callbacks), so progress is reported at known milestones:
- `0` — task received
- `10` — context computed
- `30` — HTML rendered
- `90` — PDF bytes written to disk
- `100` — job done

This is sufficient to move the UI meaningfully; finer granularity is not feasible without WeasyPrint internals.

### Polling

13. Vue polls `GET /api/export-jobs/<id>/` every 1.5–2 seconds.
14. `ExportJobViewSet.retrieve()` returns `{ id, status, progress, error_message }`.
15. Vue updates the progress bar.
16. When `status == 'done'`, Vue calls `GET /api/export-jobs/<id>/result/` which streams `result_file` with `Content-Disposition: attachment`.
17. When `status == 'failed'`, Vue shows error message.
18. Polling stops when status is terminal (`done` or `failed`).

---

## BackgroundJob Model Design

### Status FSM

```
pending → running → done
                 ↘ failed
```

Only forward transitions are valid. No retrying states in v1 (keeps FSM simple; add `retrying` state later if needed). Terminal states are `done` and `failed`.

```python
class JobStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    RUNNING = 'running', 'Running'
    DONE = 'done', 'Done'
    FAILED = 'failed', 'Failed'
```

### Model Fields

| Field | Type | Purpose |
|-------|------|---------|
| `id` | UUIDField (primary key, default=uuid4) | Opaque, non-enumerable job identifier — prevents job ID probing |
| `job_type` | CharField(50) | Discriminator for extensibility — `'pdf_export'`, `'bls_import'`, etc. |
| `status` | CharField(choices=JobStatus) | Current FSM state |
| `progress` | PositiveSmallIntegerField(default=0) | 0–100 percentage |
| `created_at` | DateTimeField(auto_now_add=True) | Creation timestamp |
| `updated_at` | DateTimeField(auto_now=True) | Last update (for staleness detection) |
| `celery_task_id` | CharField(255, blank, null) | Celery task UUID for debugging/revocation |
| `result_file` | FileField(upload_to='exports/', null, blank) | PDF output; null until done |
| `error_message` | TextField(blank) | Error description when status=failed |
| `meal_plan_id` | IntegerField(null, blank) | Denormalized for now; keeps the model generic (future tasks may not reference a meal plan) |

**Why UUID PK:** Job IDs are exposed in URLs polled by the browser. An auto-increment integer leaks job count and allows enumeration. UUID eliminates this.

**Why `job_type` string instead of subclasses:** Avoids multi-table inheritance complexity. The `job_type` field lets a future BLS import task reuse the same model and polling API with zero schema changes — the task writes different milestones, but the polling contract (`status`, `progress`) is identical.

**Why denormalized `meal_plan_id`:** The generic `BackgroundJob` should not force a FK to `MealPlan`. Store it as a plain integer field used by the PDF task; future task types store their own context in a `task_kwargs` JSONField if needed.

### Optional Extension: `task_kwargs` JSONField

For the BLS import use case (no `meal_plan_id` but needs file path), add:

```python
task_kwargs = models.JSONField(default=dict, blank=True)
```

The Celery task reads `job.task_kwargs` to get its inputs. This avoids adding new columns for each task type. This field is not needed for the PDF export milestone but the model should include it from day one to avoid a future migration.

---

## Celery Task Organization

### Module placement

```
meals/
    tasks.py        ← all Celery tasks for the meals app
    celery_app.py   ← (or in config/) Celery application instance
config/
    celery.py       ← Celery app instantiation + autodiscover
```

The Celery app is created in `config/celery.py` and imported in `config/__init__.py` so Django's `AppConfig.ready()` ensures task discovery without a separate import. This is the canonical Django + Celery pattern.

### Task signature

```python
@shared_task(bind=True, name='meals.tasks.generate_pdf')
def generate_pdf_task(self, job_id: str, plan_pk: int) -> None:
    ...
```

`bind=True` gives access to `self` (the task instance) for `self.update_state()`. However, since progress is tracked via DB writes (not Celery's result backend state), `self.update_state()` is not required — DB writes are sufficient and simpler. Using the DB avoids depending on Celery's result backend for the polling API.

**Do not use Celery's `result_backend` as the source of truth for progress.** The Django DB is the single source of truth. Celery result backend is optional (useful for debugging) but the polling API reads only from `BackgroundJob`.

### Worker configuration

```python
# config/celery.py
app = Celery('meal_planner')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# settings.py additions
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://redis:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://redis:6379/0')
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_TRACK_STARTED = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # important for long tasks
```

`CELERY_WORKER_PREFETCH_MULTIPLIER = 1` prevents the worker from prefetching multiple long-running tasks, which would starve other jobs.

---

## API Design

### Endpoints

| Method | URL | Purpose |
|--------|-----|---------|
| `POST` | `/api/export-jobs/` | Create job, enqueue task, return `{ id, status }` |
| `GET` | `/api/export-jobs/<uuid>/` | Poll status + progress |
| `GET` | `/api/export-jobs/<uuid>/result/` | Download result file (only when status=done) |

No `LIST` endpoint needed in v1 (no job history UI). `result/` is a custom DRF `@action`.

### ExportJobViewSet

```
ExportJobViewSet
    create()     → validates meal_plan_pk, creates BackgroundJob, calls task.delay(), returns 201
    retrieve()   → returns { id, job_type, status, progress, error_message, created_at }
    result()     → @action(detail=True, methods=['get'])
                   streams result_file as application/pdf attachment; 404 if not done
```

Authentication: `IsAuthenticated` (same as all existing API endpoints).

### Serializer

```
ExportJobSerializer
    fields: id, job_type, status, progress, error_message, created_at
    read-only: all except create input (meal_plan_pk as write-only input field)
    result_file: excluded (accessed via dedicated /result/ action, never exposed as URL)
```

---

## Result File Storage

**Storage:** Django's default `FileField` with `upload_to='exports/'` → files land in `MEDIA_ROOT/exports/<uuid>.pdf`.

**Why not serve via URL from `MEDIA_URL`:** Media URLs are publicly accessible if `MEDIA_ROOT` is served. PDF exports may contain sensitive nutritional data. Serving via a dedicated DRF action that enforces `IsAuthenticated` is safer and consistent with existing API auth.

**Cleanup strategy:** Background job files are not cleaned up in v1 (no job history UI means users can't re-download). Add a management command or periodic Celery beat task later to purge exports older than N days. The `created_at` and `updated_at` fields support this.

**File naming:** `exports/<uuid>.pdf` — UUID matches the `BackgroundJob.id`, making it easy to locate a job's file. No need for a separate filename in the model.

---

## Django Signal vs Task Hooks

**Recommendation: Do not use Django signals to trigger Celery tasks.**

Signals are synchronous, fire inside the DB transaction, and couple task dispatch to model save. If the task is dispatched inside a `post_save` signal and the enclosing transaction has not yet committed, the Celery worker may read a stale DB state (race condition).

**Pattern to use instead:** Dispatch tasks explicitly in the ViewSet's `create()` method after the DB write commits:

```python
def create(self, request, *args, **kwargs):
    job = BackgroundJob.objects.create(
        job_type='pdf_export',
        status=JobStatus.PENDING,
        meal_plan_id=plan_pk,
    )
    # task.delay() is called AFTER the job row exists in the DB
    result = generate_pdf_task.delay(str(job.id), plan_pk)
    job.celery_task_id = result.id
    job.save(update_fields=['celery_task_id'])
    ...
```

For cases where signals are unavoidable (future import command), use `transaction.on_commit(lambda: task.delay(...))` to ensure the task fires after commit.

---

## Frontend Polling Pattern

### Vue component behavior

```
ExportButton.vue
    state: idle | polling | done | error
    data: jobId, progress, errorMessage

    onClick():
        POST /api/export-jobs/  → jobId
        state = 'polling'
        startPolling()

    startPolling():
        setInterval(poll, 1500)

    poll():
        GET /api/export-jobs/<jobId>/
        update progress bar
        if status == 'done':
            clearInterval
            state = 'done'
            triggerDownload()  → window.location = /api/export-jobs/<jobId>/result/
        if status == 'failed':
            clearInterval
            state = 'error'
            errorMessage = response.error_message

    triggerDownload():
        window.location.href = `/api/export-jobs/${jobId}/result/`
        (browser follows the authenticated session cookie, triggers file download)
```

**Poll interval:** 1.5 seconds. PDF generation typically takes 3–15 seconds depending on plan size. At 1.5s interval, users get 2–10 polls before completion — responsive without excessive load.

**Timeout:** Stop polling after 120 seconds and show an error. Prevents infinite polling if a worker crashes without updating the job status.

**Progress bar:** Animate from 0 to reported `progress` value. The coarse milestones (0 → 10 → 30 → 90 → 100) are enough for users to see forward motion.

**Download trigger:** `window.location.href` assignment causes the browser to follow the URL using the existing session cookie. No need for `fetch` + Blob URL for file downloads — simpler and avoids memory management issues with large PDFs.

---

## Docker Compose Changes

Three additions to `docker-compose.yml`:

1. **Redis service** — `redis:7-alpine`, no volumes needed (broker data is ephemeral), healthcheck on `redis-cli ping`.
2. **Celery worker service** — same image as `web`, command `celery -A config worker -l info -c 2`, depends on `db` (healthy) and `redis` (healthy).
3. **Volume mount for exports** — shared `exports_data` volume mounted to `MEDIA_ROOT` in both `web` and `worker` containers so the worker can write the PDF and the web container can serve it.

The shared media volume is the key coupling point. Both the worker (writes) and the web container (serves via DRF `/result/` action) need access to the same filesystem path.

---

## Patterns to Follow

### Pattern 1: DB as single source of truth for job state

Never read Celery result backend for progress in the polling API. Write progress to `BackgroundJob` via direct ORM calls in the task. This makes the polling API a simple DB read (`BackgroundJob.objects.get(id=job_id)`), independent of Celery's result backend configuration.

### Pattern 2: UUID primary key for externally-visible job IDs

All job IDs exposed in HTTP URLs are UUIDs. This is a one-line model change that prevents enumeration attacks and is the correct default for any async job system.

### Pattern 3: Decouple render logic from request context

`get_meal_plan_context(pk)` already works without a request (takes only `pk`). The Celery task can call it directly. The one exception is `base_url` in `weasyprint.HTML(...)` — use `settings.SITE_BASE_URL` (a new env var with a fallback) instead of `request.build_absolute_uri()`. This is the only change needed to `meal_plan_pdf` logic to make it task-compatible.

### Pattern 4: `task_kwargs` JSONField for extensibility

Include a `task_kwargs = JSONField(default=dict)` on `BackgroundJob` from day one. Future task types (BLS import) store their inputs here. The PDF task uses `meal_plan_id` directly; future tasks use `task_kwargs`. No schema migration needed when adding a new task type.

### Pattern 5: `on_commit` for transactional safety

When task dispatch must happen after a model save (e.g., in a management command or signal handler), use `transaction.on_commit(lambda: task.delay(...))`. In the ViewSet `create()` path, the explicit call after `objects.create()` already occurs outside any transaction block, so `on_commit` is not strictly required but is harmless to add for defense-in-depth.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Celery chord/group for single-task jobs

The PDF export is a single task with no fan-out. Do not use Celery `chord`, `group`, or `chain` — they add complexity with no benefit here. A plain `task.delay(job_id, plan_pk)` is correct.

### Anti-Pattern 2: Storing progress in Celery result backend

The Celery result backend (Redis) is volatile and requires Celery-specific client code to read. Using `BackgroundJob.progress` (PostgreSQL) as the source of truth means the polling API is a plain ORM query — testable, debuggable, and works without a running Redis.

### Anti-Pattern 3: Streaming PDF bytes through the Celery result

Do not return the PDF bytes as the Celery task result. Task results in Redis are size-limited and ephemeral. Write the file to `MEDIA_ROOT` and record the path in `BackgroundJob.result_file`.

### Anti-Pattern 4: Signal-driven task dispatch inside transactions

Using `post_save` signals to dispatch Celery tasks creates a race: the worker may query the DB before the transaction commits. Always dispatch tasks after commit (explicit `ViewSet.create()` call or `transaction.on_commit()`).

### Anti-Pattern 5: Multiple Celery apps

Define exactly one Celery app instance in `config/celery.py`. Do not create a second `Celery()` instance in `meals/`. Use `@shared_task` decorator in `meals/tasks.py` so tasks bind to whichever app is active — this is the standard multi-app-safe pattern.

---

## Extensibility: Future BLS Import Task

When a BLS import task is added later, it slots in as:

1. `BackgroundJob.objects.create(job_type='bls_import', task_kwargs={'file_path': '...'})`.
2. `import_bls_task.delay(job_id)` — task reads `job.task_kwargs['file_path']`.
3. Task calls existing `import_foods` command logic directly (extract the importation logic from the management command into a callable function).
4. Same polling API: `GET /api/export-jobs/<id>/` returns `{ status, progress }` — no new endpoints needed.
5. `result_file` remains null (import has no downloadable result); `error_message` captures failures.

The `ExportJobViewSet` name should be renamed to `BackgroundJobViewSet` when this second task type is added, but the URL and serializer shape remain identical.

---

## Build Order (Dependency Graph)

Components must be built in this order:

```
1. BackgroundJob model + migration
        ↓
2. Celery app setup (config/celery.py, settings.py additions)
        ↓
3. generate_pdf_task (meals/tasks.py) — depends on model + celery app
        ↓
4. ExportJobViewSet + serializer + URLs — depends on model + task
        ↓
5. Docker Compose additions (Redis + worker + shared volume)
        ↓
6. Vue ExportButton component — depends on API being available
        ↓
7. Integration test (full round-trip: POST → poll → download)
```

Steps 1–5 can be developed and unit-tested without a running browser. Step 6 is pure frontend work that can start once the API contract (step 4) is stable. Step 7 requires all services running.

**Critical path:** The shared media volume (step 5) must be wired correctly before any integration test can succeed. This is the most common infrastructure mistake in this pattern — the worker writes to a path the web container cannot reach.

---

## Scalability Considerations

| Concern | At current scale (single user) | At multi-user scale |
|---------|--------------------------------|---------------------|
| Concurrency | `-c 2` workers sufficient | Increase `-c` or add worker replicas |
| Media storage | Local MEDIA_ROOT volume | Replace FileField storage backend with S3-compatible (django-storages) |
| Redis | Single Redis container | Redis Sentinel or managed Redis |
| Job cleanup | Manual | Celery beat periodic task purging old jobs + files |
| Queue isolation | Single default queue | Add dedicated `pdf` queue; route tasks via `CELERY_TASK_ROUTES` |

---

## Sources

- Existing codebase analysis: `meals/views.py` (get_meal_plan_context, meal_plan_pdf), `meals/models.py`, `docker-compose.yml`, `pyproject.toml`
- `.planning/PROJECT.md` (milestone requirements and constraints)
- `.planning/codebase/ARCHITECTURE.md` (existing system architecture)
- Celery 5.x canonical patterns: `@shared_task`, `bind=True`, `CELERY_WORKER_PREFETCH_MULTIPLIER`, `autodiscover_tasks` — HIGH confidence from training data (Celery 5.x stable since 2021, no breaking changes to these patterns through August 2025)
- Django + Celery `transaction.on_commit` pattern — documented in Django docs, HIGH confidence
- UUID primary key for job models — standard security practice, HIGH confidence

*Note: Web access was unavailable during this research session. Celery 5.x version-specific details (e.g., exact current patch version) should be verified against pypi.org/project/celery before pinning in pyproject.toml. All architectural patterns described are stable across Celery 5.x minor versions.*

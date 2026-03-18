# Domain Pitfalls: Django + Celery Async Export

**Domain:** Django 6.0 web app adding Celery + Redis for async PDF export via WeasyPrint
**Researched:** 2026-03-16
**Confidence notes:** Web search unavailable. All findings from training knowledge (Celery 5.x docs, WeasyPrint behaviour, Django 6 internals, Redis client docs) — confidence levels assigned per claim. Codebase-derived findings are HIGH confidence.

---

## Critical Pitfalls

Mistakes that cause rewrites, data loss, or silent production failures.

---

### Pitfall 1: WeasyPrint Accumulates Memory Across Worker Restarts

**What goes wrong:** WeasyPrint uses libcairo, libpango, and libharfbuzz via CFFI bindings. These native libraries allocate memory that Python's garbage collector does not reclaim between task invocations. A long-running Celery worker that processes many PDF jobs will gradually consume more and more RAM until the container is OOM-killed or starts swap-thrashing.

**Why it happens:** Each `weasyprint.HTML(...).write_pdf()` call loads fonts, CSS, and image resources. The CFFI layer retains some of these objects at the C level. The Python `del html` and GC cycle do not release native allocations. This is a known characteristic of any Python library wrapping stateful C libs.

**Consequences:** Worker OOM-kill, container restart loop, failed jobs silently mid-export, no PDF delivered to user. Especially problematic when a meal plan contains many food images or the logo file is large.

**Prevention:**
- Set `CELERY_WORKER_MAX_TASKS_PER_CHILD = 50` (or lower) in settings. This restarts the worker subprocess after N tasks, releasing all C-level memory. This is the standard mitigation for memory-leaking tasks.
- Combine with `CELERY_WORKER_MAX_MEMORY_PER_CHILD = 200000` (200 MB in KB) as a safety net — Celery will kill and restart the child if it exceeds this limit.
- Use `--concurrency=1` or `--concurrency=2` for the worker in Docker Compose. PDF generation is CPU and memory bound; more than 2 concurrent workers per container will amplify leaks.

**Detection:** Monitor container memory with `docker stats`. If the worker container grows steadily over time and never decreases, this pitfall is active.

**Phase:** Infrastructure setup (when writing `docker-compose.yml` Celery worker service and `celery.py` configuration).

**Confidence:** MEDIUM — WeasyPrint memory behaviour from training knowledge; CFFI retention is well-documented in WeasyPrint GitHub issues.

---

### Pitfall 2: `base_url` and `url_fetcher` are Missing in the Celery Task

**What goes wrong:** The existing synchronous `meal_plan_pdf` view constructs `weasyprint.HTML(string=html_string, base_url=request.build_absolute_uri(), url_fetcher=django_url_fetcher)`. The `base_url` is used by WeasyPrint to resolve relative CSS and image URLs. The `url_fetcher` (already in `views.py`) maps Django static/media URLs to local filesystem paths, bypassing HTTP.

When the task runs inside a Celery worker, there is no `request` object. If `base_url` is not passed (or is set to `None`), WeasyPrint will fail to resolve relative URLs in the template, producing a PDF with missing styles and images.

**Why it happens:** Developers copy the `write_pdf()` call into the task but forget that `request.build_absolute_uri()` does not exist in a worker context.

**Consequences:** PDF renders without CSS (unstyled, wrong layout), or WeasyPrint raises `ValueError: Relative URL '/static/meals/...'` and the task fails. The job is marked `failed` with a cryptic error.

**Prevention:**
- Pass a hardcoded `base_url` derived from settings (e.g., `settings.ALLOWED_HOSTS[0]` or a new `SITE_BASE_URL` env var) when calling WeasyPrint from the worker.
- Confirm that `django_url_fetcher` is used in the task — it already maps `file://` paths for static/media, which removes the HTTP dependency entirely for local assets. The `url_fetcher` is the important part; `base_url` just needs to be a valid absolute URL string so WeasyPrint can anchor relative paths.
- Add a `SITE_BASE_URL` environment variable to `.env.example` and `docker-compose.yml` from the start.

**Detection:** In local testing, run the Celery task directly (`task.delay(pk)`) and inspect the resulting PDF. Missing styles or a `ValueError` in task logs are the signals.

**Phase:** Task implementation (the first working version of the PDF Celery task).

**Confidence:** HIGH — derived directly from inspecting the existing `meal_plan_pdf` view in `meals/views.py` lines 810–814.

---

### Pitfall 3: Result Files Accumulate on Disk with No Cleanup

**What goes wrong:** Each export job writes a PDF file to disk (e.g., `media/exports/<job_id>.pdf`). If jobs are never cleaned up, the `media/` directory grows without bound. In Docker Compose this fills the container's writable layer or the mounted volume. In Kubernetes, it fills the PVC.

**Why it happens:** "We'll add cleanup later" never happens. The result file is written when the job completes, read once when the user downloads it, and never deleted.

**Consequences:** Disk exhaustion. New export jobs fail because the filesystem is full (`OSError: No space left on device`). In Docker Compose with `volumes: .:/app` (the current dev config), this fills the developer's local disk.

**Prevention:**
- Design the job model with a `created_at` timestamp and an `expires_at` field from day one.
- Write a periodic Celery beat task (or a simple management command) that deletes export files and job records older than N hours (e.g., 2 hours). This can be added in Phase 2 but the schema must support it from Phase 1.
- Alternatively: delete the result file immediately after the download response is sent. A dedicated `/api/export-jobs/<id>/result/` endpoint that streams the file and then marks it consumed is clean and avoids accumulation entirely.
- In the Docker Compose worker service, do NOT mount `.:/app` — use a named volume (`export_files:/app/media/exports`) so that exports are isolated and can be independently managed.

**Detection:** Watch `df -h` on the worker host. A steadily growing `media/` directory with old PDF files is the sign.

**Phase:** Job model design (Phase 1) for the `expires_at` field; cleanup mechanism (Phase 2 or later, but the field must exist from the start).

**Confidence:** HIGH — a direct consequence of writing files without a deletion strategy, confirmed by the existing `MEDIA_ROOT = BASE_DIR / "media"` config in `settings.py`.

---

### Pitfall 4: Celery Task Serializer Incompatibility with Django ORM Objects

**What goes wrong:** Passing a `MealPlan` model instance (or any ORM object) as a Celery task argument causes serialization failures. Celery's default serializer is JSON. Django model instances are not JSON-serializable.

**Why it happens:** It feels natural to write `generate_pdf.delay(meal_plan)` instead of `generate_pdf.delay(meal_plan.pk)`. The task runs fine in tests using the `task_always_eager` setting (which skips serialization) but fails in production with `TypeError: Object of type MealPlan is not JSON serializable`.

**Consequences:** Task fails silently in production but passes in tests. If pickle serialization is enabled to work around this, a new security vulnerability is introduced (arbitrary code execution via crafted Redis payloads).

**Prevention:**
- Always pass primitive types to tasks: `generate_pdf_task.delay(meal_plan_pk=pk)`. Fetch the model instance inside the task body.
- Explicitly set `CELERY_TASK_SERIALIZER = "json"` and `CELERY_ACCEPT_CONTENT = ["json"]` in settings to make any accidental ORM-object-passing fail loudly and fast, rather than silently.
- Never use pickle serialization with Redis as broker. Redis is accessible to anything with the connection string; pickle deserialization of attacker-controlled data is arbitrary code execution.

**Detection:** The failure mode is `kombu.exceptions.EncodeError` at task dispatch time, which appears immediately in the web worker's logs (not the Celery worker's logs), making it hard to miss.

**Phase:** Task implementation (when writing the first `@shared_task` function).

**Confidence:** HIGH — Celery's JSON serializer restriction is a core design principle in Celery 5.x; pickle security is documented in the Celery security guide.

---

### Pitfall 5: Django Database Connections Not Closed in Worker Children

**What goes wrong:** Django opens a database connection per thread/process. When Celery uses `prefork` concurrency (the default), each worker child process inherits the database connection state from the parent. After `CELERY_WORKER_MAX_TASKS_PER_CHILD` restarts a child process, old connections may be left open on the PostgreSQL side, or a connection may be in a bad state (inside a failed transaction) that causes the next task to silently read stale data.

**Why it happens:** The Celery worker process is not a WSGI worker — it does not go through Django's request/response cycle where `django.db.close_old_connections()` is called automatically. Without explicit connection management, connections accumulate or stay dirty.

**Consequences:** `django.db.utils.InterfaceError: connection already closed`, stale reads inside a task that started a transaction and hit an exception, PostgreSQL `max_connections` exhaustion.

**Prevention:**
- Call `django.db.close_old_connections()` at the start of every task, or use the `django_db_cleanup` Celery signal (`worker_process_init`) to close connections when a worker child starts.
- The canonical approach in Celery 5.x with Django: import `from django.db import close_old_connections` and call it at the top of long-running or infrequently-called tasks.
- Set a reasonable `CONN_MAX_AGE` (e.g., 60 seconds) in Django's database settings so that stale persistent connections are recycled.

**Detection:** `InterfaceError` or `OperationalError: server closed the connection unexpectedly` in Celery task logs.

**Phase:** Celery app configuration (when writing `config/celery.py` or `meals/tasks.py`).

**Confidence:** MEDIUM — this is a known Django+Celery interaction; the specific Celery signal name verified from training; behaviour confirmed in multiple Django deployment guides.

---

### Pitfall 6: Redis Connection Pool Exhaustion Under Concurrent Workers

**What goes wrong:** Each Celery worker child holds a Redis connection for the broker channel and another for the result backend (if Redis is used for results). With `--concurrency=4` and multiple workers, the number of simultaneous Redis connections can exceed the Redis `maxclients` limit (default: 10,000, but often set lower in constrained environments).

More practically: the `redis-py` client creates a new connection per task by default unless connection pooling is configured. With no pool settings, each task open-close-opens a connection, adding TCP handshake overhead and leaving TIME_WAIT sockets that exhaust ephemeral ports under high throughput.

**Why it happens:** The default `CELERY_BROKER_URL = "redis://redis:6379/0"` connection string has no pool parameters.

**Consequences:** `redis.exceptions.ConnectionError: Error 99 connecting to redis:6379. Cannot assign requested address.` under load. In low-traffic single-user deployment, this is unlikely to trigger — but it is a hard wall if load ever increases.

**Prevention:**
- Add connection pool configuration explicitly: `CELERY_BROKER_TRANSPORT_OPTIONS = {"max_connections": 10}` limits the broker pool. For a single-user app with 1-2 concurrent workers, this is entirely sufficient.
- Use a separate Redis database index for broker vs. result backend: `redis://redis:6379/0` for broker, `redis://redis:6379/1` for results. This prevents result-backend traffic from blocking task dispatch.
- In `docker-compose.yml`, add `command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru` to the Redis service so Redis evicts old result data under memory pressure rather than blocking.

**Detection:** `ConnectionError` in Celery logs, `MONITOR` output from `redis-cli` showing thousands of short-lived connections.

**Phase:** Docker Compose setup (when adding the Redis service and configuring broker URL in settings).

**Confidence:** MEDIUM — Redis connection pooling behaviour from training knowledge; the specific Celery transport option names verified from training.

---

## Moderate Pitfalls

---

### Pitfall 7: Using Django's Default `LocMemCache` for the Alias Index With a Separate Worker Process

**What goes wrong:** This codebase already has a known fragile area: the alias cache (`food_aliases_index`) uses Django's default `LocMemCache`, which is process-local. The `CONCERNS.md` documents this. Adding a Celery worker adds a third process type (web server, Celery worker, potentially beat scheduler). If the Celery task ever touches `get_alias_index()` (e.g., for a future BLS import task), it will have its own isolated cache that is never invalidated by web worker signals.

**Why it happens:** `LocMemCache` is the Django default when no `CACHES` setting is configured. The worker process starts with an empty cache and never receives signals from other processes.

**Consequences:** The Celery task sees a stale or empty alias index. More importantly, the Redis infrastructure being added for Celery is the correct solution for the existing alias cache problem too — but developers often miss this connection and add Redis for Celery while leaving `CACHES` unconfigured.

**Prevention:**
- When adding Redis to the project for Celery, simultaneously configure `CACHES` to use Redis: `django-redis` (`django-redis>=5.4.0`) as the cache backend. This fixes the alias cache cross-worker staleness for both gunicorn and Celery workers in one step.
- Add `REDIS_URL` as a single env var used for both `CELERY_BROKER_URL` and the `CACHES["default"]["LOCATION"]`.

**Detection:** After switching cache backend to Redis, run `python manage.py shell` and verify `cache.get("food_aliases_index")` returns data after the first web request.

**Phase:** Infrastructure setup (must be done when Redis is added; do not defer).

**Confidence:** HIGH — derived directly from `CONCERNS.md` "Cache backend defaults to Django's in-memory LocMemCache" and the known process-isolation behaviour of `LocMemCache`.

---

### Pitfall 8: Celery App Not Discovered by Django's `django-admin` / `manage.py`

**What goes wrong:** If `celery.py` is placed in the `config/` package without the correct autodiscover pattern, `manage.py` commands (including migrations) succeed but the Celery worker startup with `celery -A config worker` fails with `ImportError` or tasks registered in `meals/tasks.py` are never discovered.

**Why it happens:** The standard Celery + Django setup requires:
1. A `config/celery.py` that creates the `Celery` app instance.
2. `config/__init__.py` that imports it: `from .celery import app as celery_app; __all__ = ("celery_app",)`.
3. `app.autodiscover_tasks()` called without arguments (so Celery scans all `INSTALLED_APPS` for `tasks.py`).

Skipping step 2 means `celery_app` is never imported when Django starts, so `@shared_task` decorators in `meals/tasks.py` register against an uninitialised app.

**Consequences:** `@shared_task` decorated functions run synchronously (falling back to eager mode) or raise `celery.exceptions.NotRegistered` at dispatch time.

**Prevention:**
- Follow the canonical Celery + Django setup exactly as documented. The `config/__init__.py` import is non-optional.
- Verify with `celery -A config inspect registered` — it should list `meals.tasks.generate_pdf_task` (or whatever the task is named).

**Detection:** `celery.exceptions.NotRegistered: 'meals.tasks.generate_pdf_task'` at `.delay()` call time.

**Phase:** Initial Celery wiring (Phase 1, first task).

**Confidence:** HIGH — this is the canonical Celery Django integration documented in official Celery docs.

---

### Pitfall 9: Polling Interval Too Aggressive — Floods the Job Status Endpoint

**What goes wrong:** The frontend polls `/api/export-jobs/<id>/` every N milliseconds while a job is pending or running. If N is too small (e.g., 200ms), a single export job generates 25–150 HTTP requests over a 5–30 second export window. With multiple concurrent users (even 3–4), this creates a disproportionate load on the Django web workers for a read-only status endpoint.

**Why it happens:** Developers pick an interval that "feels responsive" without accounting for the long tail of WeasyPrint execution time.

**Consequences:** Web workers are occupied serving polling requests, slowing down the actual PDF task's DB writes (updating job status). In the worst case, status updates are not visible to the user because the web worker is busy polling.

**Prevention:**
- Use an exponential backoff polling strategy: start at 500ms, double each time up to a max of 3000ms. This front-loads responsiveness and reduces load for slow jobs.
- Cap the total polling duration at, say, 90 seconds. If no result after 90s, show an error and a retry button. This prevents zombie polls for failed jobs that were never marked `failed` due to a worker crash.
- The status endpoint must be cheap: a single `SELECT` on the `BackgroundJob` table by primary key, returning `status`, `progress`, and `result_url`. No joins, no WeasyPrint, no complex computation.

**Detection:** Open browser DevTools Network tab during an export. Count the requests to the status endpoint.

**Phase:** Frontend implementation (Vue polling logic).

**Confidence:** HIGH — polling interval design is a first-principles concern, not a library-specific one.

---

### Pitfall 10: Job Status Not Updated When the Worker Crashes Mid-Task

**What goes wrong:** A job is created with `status=pending`, transitions to `status=running` when the task starts, but the worker is OOM-killed or the container is restarted mid-export. The job record remains `status=running` forever. The frontend polls indefinitely (or until timeout). The user sees a spinner that never resolves.

**Why it happens:** Task failure is signalled by Celery's result backend, but if the worker is killed with SIGKILL (not SIGTERM), the `on_failure` callback may not fire. Jobs that transitioned to `running` but never reached `done` or `failed` are orphaned.

**Consequences:** Stuck "running" jobs in the database. Users who refresh the page see the spinner restart and poll again. No cleanup without manual DB intervention.

**Prevention:**
- Set a task `time_limit` in seconds: `@shared_task(time_limit=120)`. Celery will send SIGKILL to the worker child after 120 seconds, but the task machinery will still mark it as `FAILURE` in the result backend.
- Add a `soft_time_limit` slightly lower (e.g., `soft_time_limit=100`) that raises `SoftTimeLimitExceeded` inside the task — this gives the task a chance to catch the exception and update the job status to `failed` before the hard kill.
- Write a periodic cleanup (Celery beat or cron) that scans for jobs stuck in `running` state for more than `N * time_limit` seconds and marks them `failed`.

**Detection:** Manually stop the Celery worker container mid-export (`docker stop`). Check the job record. If it stays `running` after restart, this pitfall is present.

**Phase:** Task implementation (when writing the task body and job model).

**Confidence:** HIGH — Celery's `time_limit` / `soft_time_limit` behaviour is a documented feature; orphaned job states are a standard distributed systems concern.

---

### Pitfall 11: Docker Compose Worker Service Shares the App Volume Mount `.:/app`

**What goes wrong:** The current `docker-compose.yml` mounts the entire project directory into the web container (`volumes: .:/app`). If the Celery worker service copies this pattern, the worker writes PDF files into `./media/` on the developer's machine. This is usually fine for exports, but it means:
- Static files compiled by the web container (`sass_cache/`, `staticfiles/`) are readable by the worker (harmless but confusing).
- The worker's `media/exports/` directory is inside the project root and may get accidentally committed to git.
- In production Kubernetes, this volume pattern doesn't exist — the Celery worker Deployment needs a shared PVC with the web Deployment for `MEDIA_ROOT`, which is a separate concern from the code volume.

**Why it happens:** Copying the `web` service configuration wholesale into a `worker` service without considering that workers don't serve HTTP and have different volume requirements.

**Consequences:** Exported PDFs in the project root. Git noise. Mismatched volume assumptions between Compose and Kubernetes.

**Prevention:**
- In `docker-compose.yml`, give the worker its own `command` (the `celery -A config worker ...` invocation) but share only the `media` volume, not the code volume, if possible.
- Add `media/exports/` to `.gitignore` before writing any export logic.
- Document that in Kubernetes, the web and worker Deployments must share a `ReadWriteMany` PVC (or use S3/object storage) for `MEDIA_ROOT`.

**Detection:** `git status` shows `.pdf` files tracked or untracked after an export run.

**Phase:** Docker Compose setup.

**Confidence:** HIGH — derived from inspecting the current `docker-compose.yml`.

---

### Pitfall 12: `get_meal_plan_context` is Not Safe to Call from a Worker Without `request`

**What goes wrong:** The existing `get_meal_plan_context(pk)` function does not take a `request` argument — it takes only `pk`. The Celery task will call it directly. However, this function uses `finders.find(...)` for the logo path, which is safe in a worker. But the `csrf_token_string` key in the context is already a known empty-string placeholder (`CONCERNS.md`), and the template may reference `request` in subtle ways (via context processors if `render_to_string` is called with a real `RequestContext`).

Using `render_to_string("meals/mealplan_pdf.html.j2", context)` with a plain dict (no `RequestContext`) skips context processors. This is what the task should do. But if the template or any included template calls `{{ request.user }}` or `{% csrf_token %}`, it will silently produce empty strings.

**Why it happens:** The template was designed for a request context. Workers have no request.

**Consequences:** Subtle rendering differences between synchronous and async PDF export. The synchronous view (`meal_plan_pdf`) produces correct output; the Celery task produces a slightly different PDF for the same plan.

**Prevention:**
- Audit `mealplan_pdf.html.j2` and all included templates for any `{{ request... }}` or `{% csrf_token %}` usage before implementing the task. If found, ensure these are either removed from the PDF template or passed as explicit context values.
- Use `render_to_string` with a plain dict (not `RequestContext`) in the Celery task to make the absence of a request explicit and fast.

**Detection:** Side-by-side comparison of synchronous PDF output vs. async PDF output for the same meal plan.

**Phase:** Task implementation.

**Confidence:** HIGH — derived from inspecting `meals/views.py` lines 790–815 and `CONCERNS.md` lines 43–47.

---

## Minor Pitfalls

---

### Pitfall 13: Celery Beat Scheduler Not Wired in Docker Compose

**What goes wrong:** If result file cleanup or job expiry is implemented as a periodic Celery beat task, the beat scheduler must run as a separate process. Adding `celery -A config beat` to the worker's `command` string (combining worker + beat in one container) is convenient but causes problems: if the worker container is scaled to multiple replicas, multiple beat schedulers will run simultaneously, sending duplicate tasks.

**Prevention:**
- Run beat as a separate service in Docker Compose (`celery_beat` service). For Kubernetes, beat must be a separate Deployment with `replicas: 1` (never scale beat horizontally).
- For this project's single-user scale, a simpler alternative is a cleanup management command run as a Kubernetes CronJob or a docker-compose `cron`-style one-off, avoiding beat entirely.

**Phase:** Infrastructure setup if periodic cleanup is included; otherwise not applicable.

**Confidence:** HIGH — Celery beat duplication on multiple replicas is a documented Celery limitation.

---

### Pitfall 14: Task Result Backend and Broker Configured With Incompatible Serializers

**What goes wrong:** If `CELERY_RESULT_BACKEND` is set to the Django database (`django-db`) but the broker is Redis, task results are written to PostgreSQL synchronously inside the worker process after every task. This creates an implicit database write on task completion that is easy to forget when analysing DB connection counts.

More subtly: using `django-db` as the result backend requires the `django-celery-results` package and a migration. If this migration is missing from the Docker Compose startup sequence, task result writes silently fail.

**Prevention:**
- Use Redis as both broker and result backend for simplicity. The `BackgroundJob` model in this project stores status and progress explicitly, so the Celery result backend is only needed for error introspection — not for the happy path.
- If using `django-db` for results, ensure `celery_taskmeta` migration runs before the worker starts (add to the `web` service's startup command in Docker Compose).
- Consider whether the Celery result backend is needed at all if the `BackgroundJob` model carries all required state. It can be set to `None` (`CELERY_RESULT_BACKEND = None`) with `CELERY_IGNORE_RESULT = True` for tasks that update the `BackgroundJob` model directly.

**Phase:** Initial Celery configuration.

**Confidence:** MEDIUM — `django-celery-results` package and migration requirement from training knowledge.

---

### Pitfall 15: Missing `CELERY_TIMEZONE` Causing Incorrect Beat Schedules

**What goes wrong:** Celery's default timezone is UTC. Django's `TIME_ZONE = "UTC"` in this project matches, so this is low risk. But if either is ever changed to a local timezone without updating the other, periodic task schedules drift by the offset.

**Prevention:** Explicitly set `CELERY_TIMEZONE = "UTC"` and `CELERY_ENABLE_UTC = True` in settings even though they are the defaults, so the intent is clear.

**Phase:** Celery configuration.

**Confidence:** LOW — timezone drift is a known Celery gotcha but the project already uses UTC uniformly.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Celery app wiring (`config/celery.py`) | Task autodiscovery broken, `@shared_task` not registered | Follow canonical Django+Celery setup; verify with `inspect registered` |
| Job model design | No `expires_at` field, orphaned files | Add `expires_at` and `status` from day one; plan cleanup strategy |
| WeasyPrint task implementation | `base_url` missing, memory leak, ORM object passed as arg | Pass only `pk`, set `base_url` from settings, configure `max_tasks_per_child` |
| Docker Compose worker service | Volume mount confusion, exports committed to git | Add `media/exports/` to `.gitignore`; separate media volume |
| Redis service addition | `LocMemCache` still used for alias cache | Configure `django-redis` as `CACHES["default"]` in the same PR |
| Frontend polling | Too-aggressive interval, zombie polls on worker crash | Exponential backoff; 90-second total timeout; task `soft_time_limit` |
| Result file serving | Unbounded disk growth | Implement delete-on-download or scheduled expiry from Phase 1 |
| Kubernetes deployment | Beat scheduler on multiple replicas | Beat must be `replicas: 1`; consider CronJob alternative |

---

## Sources

- Celery 5.x documentation (training knowledge, HIGH confidence for documented features)
- WeasyPrint GitHub issues regarding CFFI/libpango memory retention (training knowledge, MEDIUM confidence)
- Django database connection lifecycle in non-WSGI processes (training knowledge, MEDIUM confidence)
- Codebase inspection: `meals/views.py`, `config/settings.py`, `docker-compose.yml`, `Dockerfile`, `pyproject.toml` (HIGH confidence — direct observation)
- `.planning/codebase/CONCERNS.md` (HIGH confidence — project-specific audit)
- Redis connection pooling behaviour with `redis-py` (training knowledge, MEDIUM confidence)

*Web verification was not available during this research session. Claims marked MEDIUM or LOW should be verified against official Celery 5.x and WeasyPrint documentation before implementation.*

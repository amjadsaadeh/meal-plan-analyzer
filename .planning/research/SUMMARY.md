# Project Research Summary

**Project:** RSOS Meal Planner — Async PDF Export Milestone
**Domain:** Django async background task infrastructure (Celery + Redis + WeasyPrint)
**Researched:** 2026-03-16
**Confidence:** HIGH

## Executive Summary

The milestone converts the existing synchronous WeasyPrint PDF export (a blocking anchor tag that freezes the tab for 5–30 seconds) into an async job system with in-page progress feedback. The canonical approach for this class of problem in a Django/WSGI stack is: Celery 5.x with a Redis broker, a custom Django model as the job state store, and a simple polling API consumed by a Vue progress bar component. WebSockets and SSE are over-engineered for a job that completes within 30 seconds — polling at 1.5-second intervals is functionally equivalent and requires no new infrastructure beyond what Celery already needs. The project is already well-positioned for this change: the existing `get_meal_plan_context()` function is stateless (no `request` argument), WeasyPrint is already installed and tested, and the Vue detail-page component can be extended with a progress bar without restructuring the frontend.

The recommended architecture introduces exactly two new infrastructure services (Redis + Celery worker container) and one new Django model (`BackgroundJob`). The custom model — not `django-celery-results` — is the source of truth for progress and status. This choice makes the polling API a plain ORM query independent of Celery internals, keeps the result file in Django storage as a `FileField`, and gives the model a `job_type` discriminator so future long-running tasks (BLS import) slot in with zero schema changes. The worker reuses the existing Docker image since WeasyPrint system libraries are already installed.

The primary risks are operational, not architectural. WeasyPrint's CFFI bindings accumulate native memory across invocations, requiring `CELERY_WORKER_MAX_TASKS_PER_CHILD` to prevent OOM kills. The `base_url` and `url_fetcher` arguments to `weasyprint.HTML()` must be adapted for the no-request worker context, or the generated PDFs will lack CSS and images. Finally, the existing alias cache bug (LocMemCache is process-local) should be fixed in the same milestone by switching to Redis as the Django cache backend — Redis is already being added, so the marginal cost is one settings change.

---

## Key Findings

### Recommended Stack

The project needs three additions: `celery[redis]>=5.4` (task queue), `django-celery-results>=2.5` (optional Django-DB result backend for debugging safety net), and a Redis 7 server (`redis:7-alpine` in Docker Compose). The `redis` Python client is bundled via the `celery[redis]` extras. No other queue libraries are competitive for this use case: Celery has the only mature Django ecosystem for ORM-backed job state, WeasyPrint's synchronous API rules out async-first alternatives like arq, and RQ/dramatiq lack sufficient Django result-backend support.

An important secondary recommendation from STACK.md: switch Django's cache backend from `LocMemCache` to Redis (`django.core.cache.backends.redis.RedisCache`) in the same change set. Redis is already being added for Celery; using it for the alias cache costs nothing extra and resolves the documented cross-worker cache staleness bug.

**Core technologies:**
- `celery[redis]>=5.4`: Task queue and worker — industry-standard Django integration, Python 3.12 support confirmed, active maintenance through 2025
- `redis:7-alpine` (Docker): Message broker — Redis 7 current stable, Alpine keeps image small (~40 MB)
- `django-celery-results>=2.5`: Optional Django-ORM result backend — safety net for task failure state; primary state lives in custom `BackgroundJob` model
- `django.core.cache.backends.redis.RedisCache`: Django cache backend — replaces LocMemCache, fixes alias index cross-worker staleness

**Version confidence note:** PyPI was not accessible during research. Pins are conservative lower bounds (`>=5.4`, `>=2.5`) that guarantee Python 3.12 support and should be verified before finalizing `pyproject.toml`.

### Expected Features

**Must have (table stakes):**
- Immediate button state change on click — user confirmation that click was received; button shows "Generating..." and is disabled
- Progress bar with numeric percentage — granular stage-based reporting (0% → 10% → 30% → 90% → 100%)
- Auto-download when done — `window.location.href` to result endpoint triggers file download without manual navigation
- Error message on failure — `status=failed` shows inline error with description; no silent failures
- Button reset after completion or error — user must be able to re-export without a page reload
- Poll timeout / stale job detection — polling stops at 120 seconds; job treated as failed if no progress change
- Correct filename on download — existing filename sanitization logic from `meal_plan_pdf` view replicated in task
- Authentication on all endpoints — `IsAuthenticated` consistent with all other API endpoints
- 404 on unknown job_id — standard DRF behavior from model-backed ViewSet

**Should have (competitive):**
- Granular progress stages (not 0→100) — 5 meaningful checkpoints in the WeasyPrint pipeline prevent a stalled progress bar
- Non-blocking UI during export — progress bar must not disable the rest of the detail page
- Extensible `BackgroundJob` model with `job_type` field — BLS import task slots in with no schema migration
- Page Visibility API pause/resume — polling pauses when tab is not visible, resumes on return

**Defer to v2+:**
- Job expiry / file cleanup — `expires_at` field should be in the schema from day one, but the cleanup mechanism (Celery beat task or management command) can come later
- Job history UI — no user requirement exists; jobs are ephemeral
- Cancel job button — non-trivial mid-flight cancellation for a 5–30s window; user can ignore and re-export
- Multi-user job ownership — explicitly deferred in PROJECT.md; UUID job IDs prevent enumeration in v1

### Architecture Approach

The system adds four new components to the existing Django monolith: a `BackgroundJob` model (FSM state + progress + result file), an `ExportJobViewSet` (create/poll/download HTTP endpoints), a `generate_pdf_task` Celery task (wraps existing `get_meal_plan_context` + WeasyPrint pipeline), and a Vue `ExportButton` component (replaces the current `<a href>` in `PageHeader.vue`). The two new infrastructure services are Redis (broker) and a Celery worker container (same Docker image as web, `--concurrency=2`). A shared named volume mounts `MEDIA_ROOT` to both web and worker containers so the worker can write PDFs that the web container can serve.

**Major components:**
1. `BackgroundJob` model — UUID PK, `status` FSM (pending/running/done/failed), `progress` 0–100, `result_file` FileField, `job_type` discriminator, `task_kwargs` JSONField, `celery_task_id`, timestamps
2. `ExportJobViewSet` — `POST` (create + dispatch), `GET` (poll), `GET /result/` (download); all `IsAuthenticated`; no LIST endpoint in v1
3. `generate_pdf_task` (Celery `@shared_task`) — receives `job_id` + `plan_pk` as primitives; calls `get_meal_plan_context(plan_pk)` + `render_to_string` + WeasyPrint; writes progress to `BackgroundJob` via ORM at 5 checkpoints; stores PDF in `result_file`
4. Redis service — broker on db/0, Django cache on db/1 (separate databases prevent key collisions)
5. Celery worker service — same image as web, `--concurrency=2`, `CELERY_WORKER_MAX_TASKS_PER_CHILD=50`
6. Vue `ExportButton` component — state machine (idle/polling/done/error), polls at 1.5s, exponential backoff on errors, `window.location.href` download trigger

**Build order (strict dependency chain):** BackgroundJob model → Celery app wiring → `generate_pdf_task` → `ExportJobViewSet` → Docker Compose additions → Vue component → integration test.

### Critical Pitfalls

1. **WeasyPrint CFFI memory leak** — Set `CELERY_WORKER_MAX_TASKS_PER_CHILD=50` and `CELERY_WORKER_MAX_MEMORY_PER_CHILD=200000` (200 MB). Without these, the worker container will be OOM-killed within hours of moderate use.

2. **Missing `base_url` / `url_fetcher` in Celery task** — The existing `meal_plan_pdf` view uses `request.build_absolute_uri()` for `base_url`. The Celery task has no request. Introduce a `SITE_BASE_URL` env var and pass it to `weasyprint.HTML(..., base_url=settings.SITE_BASE_URL)`. Use the existing `django_url_fetcher` to resolve static/media URLs without HTTP. Without this, the task produces PDFs with no CSS.

3. **Celery ORM object serialization** — Always pass `meal_plan.pk` (integer) to tasks, never the model instance. Enforce `CELERY_TASK_SERIALIZER="json"` and `CELERY_ACCEPT_CONTENT=["json"]` to make violations fail loudly at dispatch time rather than silently in production.

4. **Orphaned `running` jobs after worker crash** — Set `soft_time_limit=100` and `time_limit=120` on the task. The soft limit gives the task a chance to catch `SoftTimeLimitExceeded` and set `status=failed`. Without this, jobs that die mid-flight stay stuck as `running` forever.

5. **LocMemCache not upgraded alongside Redis** — When Redis is added for Celery, the Django cache backend must also be switched to Redis in the same change set. Leaving `LocMemCache` means the `food_aliases_index` cache remains process-local and stale across gunicorn and Celery worker processes.

---

## Implications for Roadmap

Based on the dependency graph in ARCHITECTURE.md, the build must proceed strictly bottom-up: infrastructure before tasks, tasks before API, API before frontend. The phase structure below follows this dependency chain.

### Phase 1: Infrastructure Foundation

**Rationale:** Redis and the Celery app must exist before any task can be dispatched. The `BackgroundJob` model must exist before the task can write progress. These are pure prerequisites with no user-visible output, but every subsequent phase depends on them.

**Delivers:** Redis service in Docker Compose, Celery app wiring (`config/celery.py` + `config/__init__.py` + settings additions), `BackgroundJob` model + migration, `django-redis` cache backend switch.

**Addresses:** None of the user-facing features — this phase is internal. Sets the table for all subsequent phases.

**Avoids:**
- Task autodiscovery failure (Pitfall 8) — canonical `config/__init__.py` import
- LocMemCache not upgraded (Pitfall 7) — Redis cache switch done here, not deferred
- Celery beat duplication (Pitfall 13) — no beat in Phase 1; beat added only if needed

**Research flag:** Standard patterns — no additional research needed. Celery + Django wiring is canonical and well-documented.

---

### Phase 2: Celery Task Implementation

**Rationale:** The task body can only be written after the `BackgroundJob` model exists and Celery is wired. The task is the most technically risky component (WeasyPrint in a worker context, no request, memory leaks), so it should be built and manually verified before the API layer is added.

**Delivers:** `meals/tasks.py` with `generate_pdf_task`; progress reported at 5 checkpoints; PDF written to `MEDIA_ROOT/exports/<uuid>.pdf` via FileField; `SITE_BASE_URL` env var; `django_url_fetcher` adapted for worker context.

**Addresses:** Progress granularity (differentiator from FEATURES.md), correct filename.

**Avoids:**
- Missing `base_url` / `url_fetcher` (Pitfall 2, HIGH confidence, HIGH impact)
- WeasyPrint memory leak (Pitfall 1) — `MAX_TASKS_PER_CHILD` set in Phase 1 settings but verified here
- ORM object serialization (Pitfall 4) — task only accepts primitive `job_id` + `plan_pk`
- Django DB connections not closed (Pitfall 5) — `close_old_connections()` called at task start
- `get_meal_plan_context` template rendering without request (Pitfall 12)

**Research flag:** No additional research needed. Task implementation follows patterns established in ARCHITECTURE.md with HIGH confidence.

---

### Phase 3: API Layer

**Rationale:** The `ExportJobViewSet` is a thin DRF wrapper over the `BackgroundJob` model and the task dispatch call. It can only be built after both the model (Phase 1) and the task (Phase 2) exist.

**Delivers:** `ExportJobViewSet` with `create()`, `retrieve()`, and `result()` action; `ExportJobSerializer`; URL registration; `SITE_BASE_URL` propagated to task; result file served via authenticated DRF action (not raw media URL).

**Addresses:** Authentication enforcement (table stake), 404 on unknown job_id (table stake), result file privacy (sensitive nutritional data not served from media URL).

**Avoids:**
- Signal-driven task dispatch inside transactions (Anti-Pattern 4) — explicit `task.delay()` call in ViewSet after `objects.create()` returns
- Task dispatched before job row commits (use `on_commit` if needed)
- Job enumeration via auto-increment IDs (UUID PK set in Phase 1 model)

**Research flag:** No additional research needed. Standard DRF ViewSet + `@action` patterns.

---

### Phase 4: Docker Compose Wiring

**Rationale:** End-to-end integration cannot be tested until the Redis service, Celery worker service, and shared media volume are wired in Docker Compose. This is the "most common infrastructure mistake" noted in ARCHITECTURE.md — the worker writes to a path the web container cannot reach without a shared volume.

**Delivers:** `redis:7-alpine` service with healthcheck; `worker` service (same image, `celery -A config worker -l info -c 2`); shared `exports_data` named volume mounted to `MEDIA_ROOT` in both `web` and `worker`; `CELERY_BROKER_URL`, `REDIS_URL`, `SITE_BASE_URL` added to service environments and `.env.example`.

**Addresses:** All table stakes become testable end-to-end.

**Avoids:**
- Shared volume missing (ARCHITECTURE.md critical path note)
- Exports committed to git (Pitfall 11) — `media/exports/` added to `.gitignore` here
- Redis connection pool exhaustion (Pitfall 6) — `CELERY_BROKER_TRANSPORT_OPTIONS` set
- `docker-compose.yml` volume `.:/app` copied to worker without consideration

**Research flag:** No additional research needed. Standard Docker Compose patterns.

---

### Phase 5: Vue Export Component

**Rationale:** Frontend work can only start after the API contract is stable (Phase 3). This is pure frontend: replace the `<a href>` anchor with an `ExportButton.vue` component, wire the polling loop, animate the progress bar, and trigger the auto-download.

**Delivers:** `ExportButton.vue` with idle/polling/done/error state machine; 1.5s poll interval with exponential backoff; 120-second timeout; `window.location.href` download trigger; error message display; button reset after terminal state; Page Visibility API pause/resume.

**Addresses:** All remaining table stakes (immediate button state change, auto-download, error message, button reset, poll timeout). Differentiator: non-blocking UI (rest of detail page remains interactive during export).

**Avoids:**
- Too-aggressive polling interval (Pitfall 9) — exponential backoff from 500ms to 3000ms
- Zombie polls on worker crash (Pitfall 10) — 120-second timeout; `soft_time_limit` on task side ensures job eventually reaches `failed`
- Progress bar blocked on job creation failure — POST failure resets button immediately without starting polling

**Research flag:** No additional research needed. Vue polling state machine is straightforward.

---

### Phase 6: Cleanup Strategy (Optional, Post-MVP)

**Rationale:** ARCHITECTURE.md explicitly defers file cleanup from the MVP. PITFALLS.md (Pitfall 3) calls this HIGH confidence and HIGH impact for production, but acceptable to defer if the `expires_at` field and `created_at` timestamps are in the model from Phase 1. This phase adds the actual cleanup mechanism.

**Delivers:** Management command `cleanup_export_jobs` that deletes jobs and files older than N hours; OR a Celery beat task if beat is already running for another reason; OR delete-on-download in the `result()` action (simplest option — delete the file after `FileResponse` completes).

**Addresses:** Job expiry / file cleanup (differentiator from FEATURES.md, deferred from v1).

**Avoids:** Pitfall 3 (unbounded disk growth), Pitfall 13 (beat scheduler duplication — beat only if needed).

**Research flag:** Standard patterns. Delete-on-download is the simplest approach and requires no scheduling infrastructure.

---

### Phase Ordering Rationale

- Phases 1–4 follow the strict dependency graph from ARCHITECTURE.md: model → task → API → infrastructure. These cannot be reordered.
- Phase 5 (frontend) depends only on the API contract from Phase 3 being stable; the Docker Compose wiring (Phase 4) can overlap with early Phase 5 development if the API is tested with mocks.
- Phase 6 is explicitly post-MVP because the model has the schema support from Phase 1 and can be added any time after Phase 4.

### Research Flags

Phases with standard patterns — skip research-phase for all:
- **All phases:** Architecture, stack, and patterns are well-documented with HIGH confidence. ARCHITECTURE.md provides a complete build order and component specifications. No phase has novel or uncertain technical territory that requires additional research before planning.

Phases warranting extra implementation care (not research, but careful execution):
- **Phase 2** (Celery task): The highest technical risk. Pitfalls 1, 2, 5, and 12 all land in this phase. Plan extra time for WeasyPrint in-worker testing and side-by-side PDF comparison.
- **Phase 4** (Docker Compose): The shared media volume is the most common infrastructure mistake in this pattern. Test the full round-trip before declaring Phase 4 done.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | Celery 5.x + Redis patterns are HIGH confidence; specific PyPI version numbers not verified (web unavailable). Conservative lower-bound pins should be validated against PyPI before `pyproject.toml` is finalized. |
| Features | HIGH | Based on direct codebase analysis of existing sync export + established async UX conventions. Feature scope is well-defined by PROJECT.md constraints. |
| Architecture | HIGH | All major components derived from existing codebase (`get_meal_plan_context`, `views.py`, `docker-compose.yml`). Celery 5.x `@shared_task` patterns are stable and well-documented. |
| Pitfalls | HIGH (critical) / MEDIUM (infrastructure) | Pitfalls 2, 3, 4, 7, 8, 10, 11, 12 are HIGH confidence (direct codebase observation). Pitfalls 1, 5, 6 are MEDIUM confidence (training knowledge of Celery/WeasyPrint behavior; web verification unavailable). |

**Overall confidence:** HIGH

### Gaps to Address

- **PyPI version verification:** Confirm `celery>=5.4` and `django-celery-results>=2.5` resolve to currently available versions before running `uv add`. Run `uv add "celery[redis]>=5.4" "django-celery-results>=2.5"` and check the resolved versions in `uv.lock`.
- **WeasyPrint memory leak magnitude:** PITFALLS.md notes MEDIUM confidence on this. Monitor `docker stats` during Phase 2 testing to confirm whether `MAX_TASKS_PER_CHILD` is necessary at this scale or merely precautionary.
- **`CELERY_RESULT_BACKEND` decision:** STACK.md recommends a hybrid approach (`django-db` as safety net + custom `BackgroundJob` as primary). ARCHITECTURE.md suggests Redis as both broker and result backend for simplicity. Decide during Phase 1: use Redis result backend (simpler) or `django-db` (durable). If `django-db`, ensure `django-celery-results` migrations run before the worker starts.
- **`django-redis` vs built-in Redis cache backend:** STACK.md suggests `django.core.cache.backends.redis.RedisCache` (Django built-in since Django 4.0). PITFALLS.md mentions `django-redis`. The built-in backend is sufficient; `django-redis` is not needed unless `django-redis`-specific features (e.g., custom serializers) are required.

---

## Sources

### Primary (HIGH confidence — direct codebase observation)
- `meals/views.py` — `get_meal_plan_context`, `meal_plan_pdf`, `django_url_fetcher` usage
- `docker-compose.yml` — existing service structure, volume mounts
- `Dockerfile` — WeasyPrint system library installation
- `pyproject.toml` — existing dependencies and Python version
- `config/settings.py` — MEDIA_ROOT, CACHES, ALLOWED_HOSTS
- `.planning/codebase/CONCERNS.md` — LocMemCache alias cache staleness, CSRF token in PDFs

### Secondary (MEDIUM confidence — training knowledge, Celery 5.x stable)
- Celery 5.x Django integration patterns (`@shared_task`, `autodiscover_tasks`, `config/__init__.py` import)
- `transaction.on_commit()` for post-commit task dispatch
- `CELERY_WORKER_MAX_TASKS_PER_CHILD` for WeasyPrint memory management
- Redis connection pool configuration (`CELERY_BROKER_TRANSPORT_OPTIONS`)

### Tertiary (MEDIUM confidence — training knowledge, web verification unavailable)
- WeasyPrint CFFI/libpango memory retention behavior (WeasyPrint GitHub issues)
- Django DB connection lifecycle in non-WSGI Celery worker processes
- `redis-py` 5.x connection pool defaults

---
*Research completed: 2026-03-16*
*Ready for roadmap: yes*

# Requirements: RSOS Meal Planner — Async Export

**Defined:** 2026-03-16
**Core Value:** Users can trigger PDF export and get live progress feedback — the page stays responsive, shows a progress bar, and delivers the download when ready.

## v1 Requirements

### Infrastructure

- [ ] **INFRA-01**: Celery app is wired into Django (`config/celery.py`, `celery_app` imported in `config/__init__.py`, `CELERY_BROKER_URL` from env)
- [ ] **INFRA-02**: Redis is the broker and Django cache backend (`django-redis` replaces `LocMemCache` for all workers)
- [ ] **INFRA-03**: Docker Compose runs a Redis service and a Celery worker service sharing the same image as the web container
- [ ] **INFRA-04**: Web and worker containers share a media volume so the worker can write PDFs that the web container can serve
- [ ] **INFRA-05**: `SITE_BASE_URL` env var is added to settings and `.env.example` for WeasyPrint's `base_url` in the worker context

### Job Model

- [x] **JOB-01**: `BackgroundJob` model exists with UUID primary key, `task_type` CharField, `status` TextChoices (`pending/running/done/failed`), `progress` PositiveSmallIntegerField (0–100), `task_kwargs` JSONField, `result_file` FileField (nullable), `error_message` TextField (blank), `expires_at` DateTimeField, `created_at`/`updated_at` auto timestamps
- [x] **JOB-02**: Migration is created and applied for `BackgroundJob`

### Task

- [x] **TASK-01**: `generate_pdf_task` Celery task wraps existing `get_meal_plan_context` + WeasyPrint rendering without using a request object
- [x] **TASK-02**: Task updates `BackgroundJob.progress` at meaningful milestones (context load ~25%, render start ~60%, render complete ~90%, file saved 100%)
- [x] **TASK-03**: Task sets `soft_time_limit` to prevent stuck workers; handles `SoftTimeLimitExceeded` by marking the job `failed`
- [ ] **TASK-04**: Worker is configured with `max_tasks_per_child` to prevent WeasyPrint CFFI memory leaks

### API

- [ ] **API-01**: `POST /api/export-jobs/` creates a `BackgroundJob` and dispatches `generate_pdf_task`; returns job `id` and `status`
- [ ] **API-02**: `GET /api/export-jobs/<id>/` returns current `status`, `progress`, and `error_message`
- [ ] **API-03**: `GET /api/export-jobs/<id>/result/` streams or redirects to the generated PDF file when `status=done`; returns 404 if not ready
- [ ] **API-04**: All export job endpoints require authentication

### Frontend

- [ ] **UI-01**: The PDF export link on `mealplan_detail` is replaced with an async export button component
- [ ] **UI-02**: Clicking export triggers `POST /api/export-jobs/` and starts polling `GET /api/export-jobs/<id>/` at ~1.5s intervals
- [ ] **UI-03**: An in-page progress bar shows current `progress` percentage while the job is `pending` or `running`
- [ ] **UI-04**: When `status=done`, the browser automatically triggers a file download and the progress bar clears
- [ ] **UI-05**: When `status=failed`, an error message is displayed inline with an option to retry

## v2 Requirements

### Cleanup

- **CLEAN-01**: A management command or periodic Celery beat task deletes expired job files based on `expires_at`
- **CLEAN-02**: Job history admin view for debugging failed exports

### Extended Async

- **EXT-01**: BLS food import (`import_foods` management command) migrated to async task using `BackgroundJob` infrastructure
- **EXT-02**: Import progress UI in the admin or food database page

## Out of Scope

| Feature | Reason |
|---------|--------|
| Cancel button for in-progress jobs | Celery task revocation is complex and unreliable for short-lived tasks |
| Job history UI for users | No requirement; adds complexity without clear value for single-user context |
| WebSockets / Server-Sent Events | Polling is sufficient; no new real-time infrastructure needed |
| Parallel export enforcement | Single export at a time acceptable; no concurrency UI required |
| Celery result backend as source of truth | `BackgroundJob` model owns all state; no dependency on Redis for polling |
| Multi-user job isolation | Single-user app for now; `BackgroundJob` not scoped per user in v1 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 | Pending |
| INFRA-02 | Phase 1 | Pending |
| INFRA-03 | Phase 3 | Pending |
| INFRA-04 | Phase 3 | Pending |
| INFRA-05 | Phase 1 | Pending |
| JOB-01 | Phase 1 | Complete |
| JOB-02 | Phase 1 | Complete |
| TASK-01 | Phase 2 | Complete |
| TASK-02 | Phase 2 | Complete |
| TASK-03 | Phase 2 | Complete |
| TASK-04 | Phase 1 | Pending |
| API-01 | Phase 2 | Pending |
| API-02 | Phase 2 | Pending |
| API-03 | Phase 2 | Pending |
| API-04 | Phase 2 | Pending |
| UI-01 | Phase 3 | Pending |
| UI-02 | Phase 3 | Pending |
| UI-03 | Phase 3 | Pending |
| UI-04 | Phase 3 | Pending |
| UI-05 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-16*
*Last updated: 2026-03-18 — traceability updated to reflect 3-phase roadmap*

---
phase: 02-task-and-api
plan: 01
subsystem: api
tags: [celery, weasyprint, pdf, background-jobs, redis]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: BackgroundJob model with UUID pk, status/progress/result_file fields; Celery + Redis wired into Django
provides:
  - generate_pdf_task Celery task in meals/tasks.py that wraps WeasyPrint PDF rendering
  - Progress milestones at 25/60/90/100 via direct ORM updates
  - SoftTimeLimitExceeded and generic exception handling with BackgroundJob status transitions
affects:
  - 02-02 (API endpoints that enqueue/poll this task)
  - phase 03 (frontend polling UI)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Celery task imports views inside function body to avoid circular imports"
    - "Progress tracked via .filter().update() not self.update_state() (no result backend)"
    - "File saved with save=False then explicit .save(update_fields=[...]) including updated_at"

key-files:
  created:
    - meals/tasks.py
  modified: []

key-decisions:
  - "Import get_meal_plan_context and django_url_fetcher inside function body — module-level import would create circular dependency (meals.views imports meals.models which would then import meals.tasks importing meals.views)"
  - "SoftTimeLimitExceeded caught before Exception and not re-raised — timeout is expected, job transitions to failed cleanly"
  - "Logo resolution uses finders.find() for file:// paths — worker has no HTTP request, cannot use .url"
  - "Filename sanitized via NFKD Unicode decomposition + ASCII-only filter to handle German plan names"

patterns-established:
  - "Direct ORM updates (.filter().update()) for progress milestones — no Celery result backend configured"
  - "update_fields must include updated_at when saving a model with auto_now field"

requirements-completed:
  - TASK-01
  - TASK-02
  - TASK-03

# Metrics
duration: 2min
completed: 2026-03-18
---

# Phase 2 Plan 01: generate_pdf_task Summary

**Celery task wrapping WeasyPrint PDF generation with four progress milestones, soft time limit handling, and BackgroundJob ORM state transitions**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-18T08:58:11Z
- **Completed:** 2026-03-18T09:00:19Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created `meals/tasks.py` with production-ready `generate_pdf_task` shared task
- Task uses `@shared_task(bind=True, soft_time_limit=300, time_limit=360)` decorator
- Four progress milestones: 25 (context loaded), 60 (HTML rendered), 90 (PDF bytes), 100 (file saved + done)
- Correct exception hierarchy: SoftTimeLimitExceeded caught first (no re-raise), generic Exception re-raised
- File saved via `ContentFile` with `save=False` + explicit `update_fields` including `updated_at`

## Task Commits

1. **Task 1: Create generate_pdf_task in meals/tasks.py** - `c87c407` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `meals/tasks.py` - generate_pdf_task Celery task implementing async PDF export pipeline

## Decisions Made
- Import `get_meal_plan_context` and `django_url_fetcher` inside the function body rather than at module level to avoid a circular import (meals.views imports meals.models; if meals.tasks also imports meals.views at module level, the import chain becomes circular when Celery autodiscovers tasks before apps are fully loaded)
- Used `unicodedata.normalize("NFKD", ...)` for filename sanitization to handle German plan names (e.g. "Mein Plan" → "Mein-Plan", umlauts stripped cleanly)
- `SoftTimeLimitExceeded` is NOT re-raised — the timeout is expected behavior; the job transitions to `failed` with a descriptive error_message and Celery treats the task as completed (REVOKED/SUCCESS) not FAILURE

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `meals/tasks.py` is fully implemented and importable without circular import errors
- `manage.py check` reports 0 issues
- Ready for Phase 02-02: API endpoints to enqueue the task and poll job status

---
*Phase: 02-task-and-api*
*Completed: 2026-03-18*

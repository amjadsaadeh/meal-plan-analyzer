---
phase: 02-task-and-api
plan: 02
subsystem: api
tags: [drf, celery, viewset, background-jobs, pdf, export]

# Dependency graph
requires:
  - phase: 02-task-and-api
    plan: 01
    provides: generate_pdf_task Celery task in meals/tasks.py
  - phase: 01-foundation
    provides: BackgroundJob model with UUID pk, status/progress/result_file fields

provides:
  - ExportJobViewSet with POST /api/export-jobs/, GET /api/export-jobs/<id>/, GET /api/export-jobs/<id>/result/
  - BackgroundJobCreateSerializer and BackgroundJobSerializer in meals/serializers.py
  - Router registration for export-jobs in meals/urls.py
  - API integration tests (12 tests) in tests/api/test_export_jobs.py
  - Task unit tests (4 tests) in tests/test_export_task.py

affects:
  - phase 03 (frontend polling UI — uses the three endpoints to trigger and track exports)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ExportJobViewSet uses viewsets.ViewSet (not ModelViewSet) — only create/retrieve/result exposed, no list/update/delete"
    - "Invalid UUID pk caught via (DoesNotExist, ValueError, DjangoValidationError) — UUID field raises Django ValidationError not Python ValueError"
    - "Authentication inherited globally from DEFAULT_PERMISSION_CLASSES — no per-class permission_classes needed"
    - "generate_pdf_task.delay patched at meals.views.generate_pdf_task.delay in tests — task imported there via ExportJobViewSet.create"

key-files:
  created:
    - tests/api/test_export_jobs.py
    - tests/test_export_task.py
  modified:
    - meals/serializers.py
    - meals/views.py
    - meals/urls.py

key-decisions:
  - "Catch DjangoValidationError in addition to ValueError for invalid UUID pk — Django's UUIDField raises ValidationError not ValueError on invalid hex strings"
  - "viewsets.ViewSet chosen over ModelViewSet — only three specific actions needed; no list/update/delete to avoid accidental exposure"
  - "expires_at set to timezone.now() + timedelta(hours=24) on job creation — sets cleanup window from day one"

patterns-established:
  - "DRF viewsets.ViewSet for custom non-CRUD endpoints — register normally with router, only implemented methods are routed"
  - "UUID validation error handling: catch (DoesNotExist, ValueError, DjangoValidationError) for full coverage"

requirements-completed:
  - API-01
  - API-02
  - API-03
  - API-04

# Metrics
duration: 4min
completed: 2026-03-18
---

# Phase 2 Plan 02: Export Job API Summary

**DRF ExportJobViewSet wiring POST/GET/result endpoints to BackgroundJob model with full API and task unit test coverage**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-18T09:02:08Z
- **Completed:** 2026-03-18T09:06:46Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Added `BackgroundJobCreateSerializer` and `BackgroundJobSerializer` to meals/serializers.py
- Created `ExportJobViewSet(viewsets.ViewSet)` with `create`, `retrieve`, and `result` action methods
- Registered `export-jobs` on the DRF DefaultRouter in meals/urls.py
- 12 API integration tests covering all endpoints: 403 auth, 201 create, task dispatch args, 400 invalid plan, status polling, 404 for invalid UUID/nonexistent/not-done
- 4 task unit tests covering: success path (done + progress=100 + file saved), SoftTimeLimitExceeded, generic exception, final state assertion

## Task Commits

1. **Task 1: Add serializers and ExportJobViewSet to views.py and register in urls.py** - `639130c` (feat)
2. **Task 2: Write API integration tests and task unit tests** - `638da86` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `meals/serializers.py` - Added BackgroundJobCreateSerializer and BackgroundJobSerializer
- `meals/views.py` - Added ExportJobViewSet with create/retrieve/result; added status, action, FileResponse, Http404, timezone, timedelta imports; added BackgroundJob to models import
- `meals/urls.py` - Imported ExportJobViewSet and registered export-jobs on router
- `tests/api/test_export_jobs.py` - 12 API integration tests for all three export job endpoints
- `tests/test_export_task.py` - 4 task unit tests for generate_pdf_task (success, timeout, error, progress)

## Decisions Made
- Used `viewsets.ViewSet` not `ModelViewSet` — only three specific endpoints needed; using ModelViewSet would auto-expose list/update/delete which must not be available
- `expires_at = timezone.now() + timedelta(hours=24)` set on job creation — sets the cleanup window from day one even though cleanup mechanism is deferred to a later phase
- Authentication inherited from `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]` in settings.py — no per-class `permission_classes` attribute needed (and plan explicitly warned against adding one)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Catch DjangoValidationError for invalid UUID pk in retrieve and result actions**
- **Found during:** Task 2 (test_retrieve_invalid_uuid_returns_404, test_result_404_for_invalid_uuid)
- **Issue:** Plan specified catching `(BackgroundJob.DoesNotExist, ValueError)` but Django's UUIDField raises `django.core.exceptions.ValidationError` (not Python's `ValueError`) when the pk string is not a valid UUID hex. Tests were getting 500 instead of 404.
- **Fix:** Added `DjangoValidationError` to the except tuple in both `retrieve` and `result` methods
- **Files modified:** meals/views.py
- **Verification:** Both invalid-UUID tests now pass with 404
- **Committed in:** `638da86` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fix was necessary for correctness — the plan's must_haves explicitly required "Supplying an invalid UUID to any endpoint returns 404, not 500". No scope creep.

## Issues Encountered
None beyond the UUID validation fix documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All three export job endpoints are wired and tested
- `POST /api/export-jobs/` creates a BackgroundJob and dispatches `generate_pdf_task.delay()`
- `GET /api/export-jobs/<id>/` returns current status, progress, error_message
- `GET /api/export-jobs/<id>/result/` returns FileResponse when done, 404 otherwise
- `manage.py check` reports 0 issues
- Ready for Phase 03: frontend polling UI that calls these endpoints to show progress bar and trigger download

---
*Phase: 02-task-and-api*
*Completed: 2026-03-18*

## Self-Check: PASSED

- meals/serializers.py: FOUND
- meals/views.py: FOUND
- meals/urls.py: FOUND
- tests/api/test_export_jobs.py: FOUND
- tests/test_export_task.py: FOUND
- Commit 639130c: FOUND
- Commit 638da86: FOUND

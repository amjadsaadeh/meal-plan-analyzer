# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-16)

**Core value:** Users can trigger PDF export and get live progress feedback — page stays responsive, shows a progress bar, delivers the download when ready.
**Current focus:** Phase 3 — Docker and Frontend

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-19 — Milestone v1.2.0 started (K8s Async Export)

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 7
- Average duration: ~7 min
- Total execution time: 0.35 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 2 | ~20 min | ~10 min |
| 02-task-and-api | 2 | ~6 min | ~3 min |
| 03-docker-and-frontend | 3 | ~9 min | ~3 min |

**Recent Trend:**
- Last 5 plans: 02-01, 02-02, 03-01, 03-02, 03-03
- Trend: On track

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- All phases: Celery + Redis (not DB-backed queue) — standard Django async stack
- All phases: Polling not SSE/WebSockets — simpler infra, sufficient for 5-30s export latency
- All phases: Generic BackgroundJob model — future tasks (BLS import) slot in with zero schema changes
- Phase 1: Switch Django cache to Redis in same changeset — fixes LocMemCache alias cross-worker staleness
- 01-02: UUID primary key for BackgroundJob prevents job ID enumeration in HTTP poll URLs
- 01-02: expires_at null=True schema included from day one; cleanup mechanism deferred to later phase
- 01-02: task_kwargs JSONField allows arbitrary task params without new migrations
- 02-01: Import views inside Celery task function body (not module level) to avoid circular imports
- 02-01: SoftTimeLimitExceeded not re-raised — expected timeout, job transitions to failed cleanly
- 02-01: update_fields must include updated_at when saving model with auto_now field
- 02-02: viewsets.ViewSet not ModelViewSet for ExportJobViewSet — only three specific endpoints needed
- 02-02: Catch DjangoValidationError for invalid UUID pk — UUIDField raises Django ValidationError not Python ValueError
- 02-02: expires_at set to timezone.now() + timedelta(hours=24) on job creation
- 03-02: ExportButton uses inject(planId/csrfToken/i18n) from main.js app.provide — no prop drilling needed
- 03-02: onUnmounted clears pollTimer to prevent dangling setInterval on navigation
- 03-02: pdfUrl prop kept in PageHeader.vue defineProps to avoid unnecessary breaking churn
- 03-03: Two tests only (visibility + error state) — 'done' flow excluded because mocking window.location.href assignment in Playwright adds fragility without proportional coverage value
- 03-03: POST/GET disambiguation via route.request.method in single page.route() handler prevents accidental GET poll interception

### Pending Todos

None yet.

### Blockers/Concerns

- PyPI version verification needed: confirm `celery>=5.4` and `django-celery-results>=2.5` resolve before running `uv add`
- WeasyPrint CFFI memory leak magnitude: MEDIUM confidence — monitor `docker stats` during Phase 2 testing
- Decide on Celery result backend: Redis (simpler) vs `django-db` via django-celery-results (durable) — decide in Phase 1

## Session Continuity

Last session: 2026-03-18
Stopped at: Completed 03-03-PLAN.md — Playwright tests for ExportButton with mocked API routes (project complete)
Resume file: None

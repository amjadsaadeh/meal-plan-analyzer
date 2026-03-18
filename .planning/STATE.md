# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-16)

**Core value:** Users can trigger PDF export and get live progress feedback — page stays responsive, shows a progress bar, delivers the download when ready.
**Current focus:** Phase 1 — Foundation

## Current Position

Phase: 1 of 3 (Foundation)
Plan: 2 of TBD in current phase
Status: In progress
Last activity: 2026-03-18 — Completed 01-02-PLAN.md (BackgroundJob model + migration)

Progress: [██░░░░░░░░] 20%

## Performance Metrics

**Velocity:**
- Total plans completed: 2
- Average duration: ~10 min
- Total execution time: 0.3 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 2 | ~20 min | ~10 min |

**Recent Trend:**
- Last 5 plans: 01-01, 01-02
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

### Pending Todos

None yet.

### Blockers/Concerns

- PyPI version verification needed: confirm `celery>=5.4` and `django-celery-results>=2.5` resolve before running `uv add`
- WeasyPrint CFFI memory leak magnitude: MEDIUM confidence — monitor `docker stats` during Phase 2 testing
- Decide on Celery result backend: Redis (simpler) vs `django-db` via django-celery-results (durable) — decide in Phase 1

## Session Continuity

Last session: 2026-03-18
Stopped at: Completed 01-02-PLAN.md — BackgroundJob model + migration 0025 committed
Resume file: None

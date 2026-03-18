# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-16)

**Core value:** Users can trigger PDF export and get live progress feedback — page stays responsive, shows a progress bar, delivers the download when ready.
**Current focus:** Phase 1 — Foundation

## Current Position

Phase: 1 of 3 (Foundation)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-03-18 — Roadmap created

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- All phases: Celery + Redis (not DB-backed queue) — standard Django async stack
- All phases: Polling not SSE/WebSockets — simpler infra, sufficient for 5-30s export latency
- All phases: Generic BackgroundJob model — future tasks (BLS import) slot in with zero schema changes
- Phase 1: Switch Django cache to Redis in same changeset — fixes LocMemCache alias cross-worker staleness

### Pending Todos

None yet.

### Blockers/Concerns

- PyPI version verification needed: confirm `celery>=5.4` and `django-celery-results>=2.5` resolve before running `uv add`
- WeasyPrint CFFI memory leak magnitude: MEDIUM confidence — monitor `docker stats` during Phase 2 testing
- Decide on Celery result backend: Redis (simpler) vs `django-db` via django-celery-results (durable) — decide in Phase 1

## Session Continuity

Last session: 2026-03-18
Stopped at: Roadmap created, STATE.md initialized — ready to plan Phase 1
Resume file: None

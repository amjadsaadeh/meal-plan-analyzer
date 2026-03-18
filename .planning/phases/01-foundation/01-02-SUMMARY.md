---
phase: 01-foundation
plan: 02
subsystem: data-model
tags: [django, model, migration, background-jobs]
dependency_graph:
  requires: []
  provides: [BackgroundJob model, migration 0025]
  affects: [meals/models.py, meals/migrations/]
tech_stack:
  added: []
  patterns: [UUIDField primary key, TextChoices status enum, FileField with upload_to]
key_files:
  created:
    - meals/migrations/0025_backgroundjob.py
  modified:
    - meals/models.py
decisions:
  - "UUID primary key chosen to prevent job ID enumeration in HTTP URLs"
  - "expires_at included as null=True for future cleanup mechanism without new migration"
  - "task_kwargs JSONField allows storing arbitrary task params without schema changes"
metrics:
  duration: "6 minutes"
  completed: "2026-03-18"
---

# Phase 1 Plan 2: BackgroundJob Model and Migration Summary

**One-liner:** BackgroundJob Django model with UUID PK, TextChoices status, and FileField for PDF exports, plus migration 0025 creating the database table.

## What Was Built

Added the `BackgroundJob` model to `meals/models.py` and generated + applied Django migration `0025_backgroundjob.py`.

The model tracks background task execution state: status transitions (pending → running → done/failed), progress (0-100), task input params, the resulting file path, and an expiry timestamp for future cleanup.

## Tasks Completed

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Add BackgroundJob model to meals/models.py | c1dc517 | meals/models.py |
| 2 | Generate migration 0025 and apply it | d392fa6 | meals/migrations/0025_backgroundjob.py |

## Decisions Made

1. **UUID primary key** — prevents job ID enumeration when IDs appear in HTTP poll URLs. An integer PK would allow users to probe `?job_id=1`, `?job_id=2`, etc.

2. **expires_at null=True** — schema exists from day one so future cleanup tasks require no migration; the cleanup mechanism itself is deferred to a later phase.

3. **task_kwargs JSONField** — stores arbitrary task input parameters so future task types (BLS import, etc.) slot in without adding new columns.

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

- `manage.py check` — 0 errors, 0 warnings
- `manage.py showmigrations meals` — `[X] 0025_backgroundjob` at end of list
- `BackgroundJob.Status.choices` — `[('pending', 'Pending'), ('running', 'Running'), ('done', 'Done'), ('failed', 'Failed')]`
- DB round-trip test (create/retrieve/delete) — passed
- `black --check meals/models.py` — no formatting violations

## Self-Check: PASSED

Files exist:
- FOUND: meals/models.py (BackgroundJob class present)
- FOUND: meals/migrations/0025_backgroundjob.py

Commits exist:
- c1dc517: feat(01-02): add BackgroundJob model to meals/models.py
- d392fa6: feat(01-02): generate and apply migration 0025_backgroundjob

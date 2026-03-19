# RSOS Meal Planner — K8s Async Export

## Current Milestone: v1.2.0 K8s Async Export

**Goal:** Wire Redis and the Celery PDF export worker into the Kubernetes deployment so the async export feature works in production.

**Target features:**
- Redis Deployment + Service in k8s
- Celery worker sidecar container (shares media PVC with web)
- ConfigMap additions for CELERY_BROKER_URL, REDIS_URL, SITE_BASE_URL

## What This Is

RSOS Meal Planner is a Django 6.0 web application for meal planning and nutritional analysis, using food data from the German BLS database. v1.0 added async PDF export via Celery + Redis (working in Docker Compose). v1.2.0 extends this to the Kubernetes production deployment.

## Core Value

Users can trigger a PDF export and immediately get feedback on progress — the page stays responsive, shows a live progress bar, and delivers the download when ready.

## Requirements

### Validated

- ✓ Food database management (BLS import + custom foods) — existing
- ✓ Meal plan creation, editing, and day management — existing
- ✓ Nutritional analysis with configurable thresholds — existing
- ✓ PDF export via WeasyPrint (synchronous, blocks request) — existing
- ✓ Authentication and user session management — existing
- ✓ Vue 3 frontend for meal plan list and food database — existing
- ✓ DRF REST API for all data operations — existing

### Active

- [ ] Redis Deployment + Service in k8s cluster
- [ ] Celery worker sidecar container in the meal-plan-analyzer pod (shares media PVC)
- [ ] ConfigMap additions: CELERY_BROKER_URL, REDIS_URL, SITE_BASE_URL
- [ ] Kustomize base wired to include new Redis resources

### Out of Scope

- WebSockets or Server-Sent Events — polling is sufficient for this use case; keep infra simple
- Scheduled/recurring export tasks — no requirements for this yet
- PDF import / parsing — deferred; but the job model should support it without changes
- Job history UI — no requirements to show past export jobs to the user
- Multi-user job isolation — single-user app for now; jobs not scoped per user in v1

## Context

**Current PDF export flow:** `GET /meal-plan/<pk>/pdf/` → Django view → WeasyPrint renders synchronously → response streams PDF. This blocks the request for several seconds and gives the user no feedback.

**Target flow:** Export button click → `POST /api/export-jobs/` → returns `job_id` → frontend polls `GET /api/export-jobs/<id>/` for progress → when `status=done`, frontend triggers file download from `GET /api/export-jobs/<id>/result/`.

**Stack additions needed:**
- `celery` + `redis` Python packages
- Redis service in Docker Compose
- Celery worker service in Docker Compose
- A `BackgroundJob` model (or `ExportJob`) with `status`, `progress`, `result_file` fields
- A Celery task that wraps the existing WeasyPrint PDF generation logic

**Extensibility goal:** The job model and polling pattern should be generic enough that a future BLS import task or any other long-running operation can plug in without architectural rework.

## Constraints

- **Tech stack**: Django 6.0, Python 3.12 — Celery 5.x is the standard choice
- **Redis**: Can be added; Docker Compose already has a PostgreSQL service as reference
- **WeasyPrint**: Already integrated; the async task just calls the existing rendering logic
- **Frontend**: Vue 3 + polling (no new realtime infrastructure needed)
- **Package manager**: `uv` (Python), `pnpm` (JS) — no exceptions

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Celery + Redis (not DB-backed queue) | Standard Django async stack; Redis already common in k8s deployments | — Pending |
| Polling (not SSE/WebSockets) | Simpler infra, sufficient for export latency (~5-30s), no new server setup | — Pending |
| Generic job model | Future tasks (import, etc.) should slot in without schema changes | — Pending |
| Reuse existing PDF logic | WeasyPrint task wraps `get_meal_plan_context` + existing render, no duplication | — Pending |

---
*Last updated: 2026-03-19 after milestone v1.2.0 started*

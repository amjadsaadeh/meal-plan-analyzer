# Roadmap: RSOS Meal Planner — Async Export

## Overview

This milestone adds async background task infrastructure to the existing Django/Vue meal planner. Starting from a blocking synchronous PDF export, the work proceeds bottom-up: wire Celery + Redis and create the job model, then build the task and API layer, then connect Docker Compose infrastructure and replace the export button with a Vue progress component. When complete, users get a live progress bar on export with automatic download on completion.

v1.2.0 extends this to the Kubernetes production deployment by wiring Redis and the Celery worker into the cluster manifests.

## Phases

- [x] **Phase 1: Foundation** - Celery app wiring, Redis cache backend, BackgroundJob model
- [x] **Phase 2: Task and API** - PDF Celery task with progress reporting and export job endpoints (completed 2026-03-18)
- [x] **Phase 3: Docker and Frontend** - Redis/worker services in Compose, shared volume, Vue export button
- [ ] **Phase 4: K8s Infrastructure** - Redis Deployment/Service, ConfigMap additions, Celery worker sidecar, kustomize wiring

## Phase Details

### Phase 1: Foundation
**Goal**: The async infrastructure exists and is wired — Celery connects to Redis, the BackgroundJob model is in the database, and the Django cache uses Redis instead of LocMemCache.
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-05, JOB-01, JOB-02, TASK-04
**Success Criteria** (what must be TRUE):
  1. `python manage.py shell` can import and instantiate a `BackgroundJob` with all expected fields (UUID pk, status choices, progress, result_file, expires_at)
  2. The Celery app starts without error (`celery -A config worker --dry-run`) and discovers tasks
  3. The Django cache backend is Redis — setting a cache key in one process is readable in another (no LocMemCache isolation)
  4. The worker is configured with `max_tasks_per_child` so WeasyPrint memory leaks are bounded
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — Wire Celery into Django and switch cache backend to Redis
- [x] 01-02-PLAN.md — Add BackgroundJob model and migration 0025

### Phase 2: Task and API
**Goal**: The backend is feature-complete — a Celery task generates PDFs with progress reporting, and REST endpoints let clients create jobs, poll status, and download results.
**Depends on**: Phase 1
**Requirements**: TASK-01, TASK-02, TASK-03, API-01, API-02, API-03, API-04
**Success Criteria** (what must be TRUE):
  1. `POST /api/export-jobs/` with a valid meal plan pk returns a job `id` and `status=pending` (authenticated request)
  2. After the task runs, `GET /api/export-jobs/<id>/` returns `status=done` and `progress=100`
  3. `GET /api/export-jobs/<id>/result/` returns a downloadable PDF when the job is done, and 404 when not ready
  4. If the task exceeds the soft time limit, the job transitions to `status=failed` rather than staying stuck as `running`
  5. All export job endpoints return 403 for unauthenticated requests
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — Implement generate_pdf_task Celery task with progress milestones and error handling
- [x] 02-02-PLAN.md — Add ExportJobViewSet, serializers, URL registration, and API + task tests

### Phase 3: Docker and Frontend
**Goal**: The full feature works end-to-end in Docker Compose — the export button shows a live progress bar and auto-downloads the PDF when ready.
**Depends on**: Phase 2
**Requirements**: INFRA-03, INFRA-04, UI-01, UI-02, UI-03, UI-04, UI-05
**Success Criteria** (what must be TRUE):
  1. `docker compose up` starts a Redis service, a Celery worker service, and the web service without errors
  2. The worker can write a PDF to media storage and the web container serves it — the shared volume is correctly mounted
  3. Clicking the export button on the meal plan detail page shows a progress bar that advances from 0% to 100%
  4. When the job completes, the browser automatically downloads the PDF without the user navigating to a separate URL
  5. When the job fails, an inline error message appears with a retry option — no silent failures
**Plans**: 3 plans

Plans:
- [x] 03-01-PLAN.md — Add redis/worker services and shared media_files volume to Docker Compose
- [x] 03-02-PLAN.md — Create ExportButton.vue with polling logic and add i18n strings
- [x] 03-03-PLAN.md — Playwright tests for ExportButton with mocked API routes

### Phase 4: K8s Infrastructure
**Goal**: The async PDF export feature works in the Kubernetes production deployment — Redis runs in the cluster and the Celery worker sidecar shares the media PVC with the web container.
**Depends on**: Phase 3
**Requirements**: K8S-01, K8S-02, K8S-03, K8S-04, K8S-05
**Success Criteria** (what must be TRUE):
  1. `kubectl get pods` shows the `meal-plan-analyzer` pod with two ready containers (`web` and `worker`) after applying the manifests
  2. `kubectl exec` into the worker container and running `celery inspect ping` returns a response, confirming the worker connects to Redis
  3. Triggering a PDF export via the web UI in the k8s environment shows the progress bar advancing and completes the download — the same end-to-end behavior as Docker Compose
  4. Both `dev` and `prod` overlays pick up the Redis resources without overlay-specific changes — `kubectl kustomize overlays/dev` and `kubectl kustomize overlays/prod` both include the Redis Deployment and Service
**Plans**: 2 plans

Plans:
- [ ] 04-01-PLAN.md — Create Redis Deployment/Service manifest and wire into kustomize base
- [ ] 04-02-PLAN.md — Add Celery/Redis env vars to ConfigMap and worker sidecar to Deployment

## Progress

**Execution Order:** 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 2/2 | Complete | 2026-03-18 |
| 2. Task and API | 2/2 | Complete | 2026-03-18 |
| 3. Docker and Frontend | 3/3 | Complete | 2026-03-18 |
| 4. K8s Infrastructure | 0/2 | Not started | - |

---
phase: 04-k8s-infrastructure
plan: "02"
subsystem: infra
tags: [kubernetes, celery, redis, configmap, deployment, sidecar]

requires:
  - phase: 04-k8s-infrastructure/04-01
    provides: Redis Deployment and Service manifest added to kustomize base

provides:
  - ConfigMap with CELERY_BROKER_URL, REDIS_URL, SITE_BASE_URL env vars
  - Celery worker sidecar container in the app Deployment alongside the web container
  - Worker mounts media PVC to share PDF output with the web container

affects:
  - Any phase deploying the k8s manifests
  - PDF export functionality (worker must be running to process async tasks)

tech-stack:
  added: []
  patterns:
    - "Sidecar pattern: Celery worker runs as second container in same pod, sharing network namespace and media volume with web container"
    - "localhost inter-container communication: worker reaches web via http://localhost:8000 (same pod network)"
    - "Redis DB separation: DB 0 for Celery broker, DB 1 for Django cache"

key-files:
  created: []
  modified:
    - deployment/app-deployment/k8s/base/configmap.yaml
    - deployment/app-deployment/k8s/base/deployment.yaml

key-decisions:
  - "SITE_BASE_URL=http://localhost:8000 because worker sidecar shares pod network namespace with web container (unlike Docker Compose where it was http://web:8000)"
  - "Worker mounts only media volume — not staticfiles or sass-cache — since worker writes PDFs and does not serve static files"
  - "No k8s liveness/readiness probes on worker container — Celery manages its own health; k8s probes would require a custom probe command out of scope"
  - "--max-tasks-per-child=50 limits worker memory growth by recycling after 50 tasks"

patterns-established:
  - "Sidecar containers get same envFrom (configMapRef + secretRef) as web container to share all environment config"
  - "Worker container has no ports section — Celery workers are not network-addressable directly"

requirements-completed:
  - K8S-03
  - K8S-04

duration: 1min
completed: 2026-03-19
---

# Phase 4 Plan 02: K8s Celery Worker Sidecar Summary

**Celery worker added as sidecar container sharing media PVC with web container; ConfigMap extended with CELERY_BROKER_URL, REDIS_URL, and SITE_BASE_URL for async PDF export**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-03-19T10:40:25Z
- **Completed:** 2026-03-19T10:41:18Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- ConfigMap extended with three new environment variables enabling Celery broker and Redis cache connectivity
- Worker sidecar container added to Deployment with correct Celery command, concurrency settings, and media volume mount
- Both base and overlay kustomize configurations render without error with two containers

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Celery/Redis env vars to ConfigMap** - `77aae27` (feat)
2. **Task 2: Add Celery worker sidecar to Deployment** - `86c689c` (feat)

## Files Created/Modified

- `deployment/app-deployment/k8s/base/configmap.yaml` - Added CELERY_BROKER_URL, REDIS_URL, SITE_BASE_URL to data section
- `deployment/app-deployment/k8s/base/deployment.yaml` - Added worker sidecar container after meal-plan-analyzer container

## Decisions Made

- `SITE_BASE_URL=http://localhost:8000` because the Celery worker sidecar shares the pod's network namespace with the web container — localhost is correct here (differs from Docker Compose where the hostname was `web`)
- Worker mounts only the `media` volume (not `staticfiles` or `sass-cache`) since the worker only writes PDF files to media storage
- No liveness/readiness probes on the worker container — Celery handles its own health; adding k8s probes requires custom probe commands and is out of scope for this plan
- `--concurrency=2 --max-tasks-per-child=50` balances throughput with memory safety in the sidecar

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 4 complete: Redis manifests (04-01) and Celery worker sidecar (04-02) are both committed
- All six ConfigMap keys are present (DEBUG, ALLOWED_HOSTS, PYTHONUNBUFFERED, CELERY_BROKER_URL, REDIS_URL, SITE_BASE_URL)
- K8s base + dev/prod overlays all render cleanly with kubectl kustomize
- Requirements K8S-03 (Redis wired into kustomize) and K8S-04 (worker sidecar) fulfilled
- Ready for deployment via Ansible playbook

---
*Phase: 04-k8s-infrastructure*
*Completed: 2026-03-19*

# Requirements: RSOS Meal Planner — K8s Async Export

**Defined:** 2026-03-19
**Core Value:** The async PDF export feature works in the Kubernetes production deployment — Redis and the Celery worker are wired into the cluster so users get the live progress bar in production.

## v1.2.0 Requirements

### Kubernetes Infrastructure

- [ ] **K8S-01**: Redis Deployment runs in the cluster using `redis:7-alpine`, with a liveness/readiness probe (`redis-cli ping`)
- [ ] **K8S-02**: Redis Service exposes Redis on port 6379 within the cluster (ClusterIP, named `redis`)
- [x] **K8S-03**: ConfigMap (`meal-plan-analyzer-config`) includes `CELERY_BROKER_URL=redis://redis:6379/0`, `REDIS_URL=redis://redis:6379/1`, and `SITE_BASE_URL=http://localhost:8000`
- [x] **K8S-04**: Celery worker runs as a sidecar container (`worker`) in the `meal-plan-analyzer` pod, mounting the `media` PVC, using the same image and env as the web container
- [ ] **K8S-05**: New Redis resources (`redis.yaml`) are added to the kustomize base `kustomization.yaml` so both `dev` and `prod` overlays pick them up without overlay-specific changes

## Future Requirements

### Reliability

- **REL-01**: Redis PVC for broker persistence across pod restarts (currently ephemeral — acceptable since job state is in PostgreSQL)
- **REL-02**: Redis authentication / password for the internal cluster connection
- **REL-03**: Celery worker HorizontalPodAutoscaler for scaling under load

### Observability

- **OBS-01**: Celery Flower dashboard deployed as a k8s service for monitoring task queues

## Out of Scope

| Feature | Reason |
|---------|--------|
| Redis PVC / persistence | Broker-only use; job state is in PostgreSQL; ephemeral Redis acceptable |
| Redis auth | Internal ClusterIP service; no external exposure in this cluster |
| Worker HPA | Single instance sufficient; scale later when load warrants it |
| Celery Beat / scheduled tasks | No recurring task requirements in this milestone |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| K8S-01 | Phase 4 | Pending |
| K8S-02 | Phase 4 | Pending |
| K8S-03 | Phase 4 | Complete |
| K8S-04 | Phase 4 | Complete |
| K8S-05 | Phase 4 | Pending |

**Coverage:**
- v1.2.0 requirements: 5 total
- Mapped to phases: 5
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-19*
*Last updated: 2026-03-19 after roadmap creation — all 5 requirements mapped to Phase 4*

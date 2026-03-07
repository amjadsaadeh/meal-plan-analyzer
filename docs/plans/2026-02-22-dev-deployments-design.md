---
title: Dev Deployments Design
parent: Plans
nav_order: 1
---

# Dev Deployments Design

## Overview

Add dev deployment capability for feature branch previews, with per-branch namespaces triggered by maintainer command. Includes renaming from `meal-planner` to `meal-analyzer`.

## Goals

- Feature branch preview deployments
- Per-branch isolation (no collisions)
- OSS-safe: maintainer-triggered only
- Easy to maintain with Kustomize overlays
- Minimal DNS management (wildcard)

## Non-Goals

- Automatic deployment on every PR (security risk for OSS)
- Per-branch databases (complexity not justified)

## Renaming: meal-planner → meal-analyzer

### Resources to Rename

| Current | New |
|---------|-----|
| Namespace `meal-planner` | `meal-analyzer` |
| Deployment `meal-planner` | `meal-analyzer` |
| Service `meal-planner-service` | `meal-analyzer-service` |
| ConfigMap `meal-planner-config` | `meal-analyzer-config` |
| Secret `meal-planner-secret` | `meal-analyzer-secret` |
| PVC `meal-planner-media-pvc` | `meal-analyzer-media-pvc` |
| Ingress `meal-planner-ingress` | `meal-analyzer-ingress` |
| TLS secret `meal-planner-tls` | `meal-analyzer-tls` |
| DB name `meal_planner` | `meal_analyzer` |
| DB user `meal_planner` | `meal_analyzer` |

### Migration Strategy

1. Create new namespace `meal-analyzer`
2. Apply new resources with updated names
3. Update DNS from `mealplanner.{tld}` to `mealanalyzer.{tld}`
4. Delete old namespace `meal-planner` after verification

## Kustomize Structure

```
k8s/
├── base/
│   ├── kustomization.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   ├── pvc.yaml
│   └── secrets.yaml
├── overlays/
│   ├── prod/
│   │   ├── kustomization.yaml
│   │   ├── namespace.yaml
│   │   └── ingress.yaml
│   └── dev/
│       ├── kustomization.yaml
│       ├── namespace.yaml
│       └── ingress.yaml
```

### Base Resources

- No hardcoded namespace
- Generic resource names
- Common labels

### Overlays

**Prod overlay:**
- Namespace: `meal-analyzer`
- Ingress: `mealanalyzer.{tld}` with cert-manager TLS
- Replicas: 1+

**Dev overlay:**
- Namespace: `meal-analyzer-{branch}` (generated)
- Ingress: `{branch}.mealanalyzer-dev.{tld}`
- Replicas: 1
- Resource limits enforced

## Secrets Management

Keep Ansible vault pattern:

| Environment | Vault Variables |
|-------------|-----------------|
| Prod | `meal_analyzer_prod_secret_key`, `meal_analyzer_prod_db_password` |
| Dev | `meal_analyzer_dev_secret_key`, `meal_analyzer_dev_db_password` |

Ansible generates secrets at deploy time, applied to appropriate namespace.

## Database Strategy

| Environment | Database |
|-------------|----------|
| Prod | `meal_analyzer` (production) |
| Dev | `meal_analyzer_dev` (shared) |

**Migration rules for dev:**
- Only backward-compatible (additive) migrations in feature branches
- Breaking migrations require coordination or separate testing

## GitHub Actions Workflow

### Deploy Trigger

1. Maintainer comments `/deploy` on PR
2. GitHub Action validates:
   - Commenter has write/maintain access
   - Branch name sanitization (alphanumeric + dashes only)
3. Action executes:
   - Build Docker image tagged `{branch}-dev`
   - Push to registry
   - Generate Kustomize overlay with branch namespace
   - Apply to cluster
   - Post preview URL comment

### Cleanup Trigger

1. PR closed or merged
2. Action deletes namespace `meal-analyzer-{branch}`

### Security Measures

- Maintainer-only trigger (not automatic)
- Branch name sanitization
- Resource limits on dev pods:
  ```yaml
  resources:
    limits:
      cpu: "500m"
      memory: "512Mi"
    requests:
      cpu: "100m"
      memory: "256Mi"
  ```
- Optional: TTL annotation for auto-cleanup after X days

## DNS Configuration

**Prod:** `mealanalyzer.{tld}` → A/AAAA records

**Dev:** `*.mealanalyzer-dev.{tld}` → wildcard A/AAAA record
- Single DNS entry handles all branches
- Ingress controller routes by Host header

## Deploy Commands

| Environment | Command |
|-------------|---------|
| Prod | `ansible-playbook deploy.yml -e env=prod` |
| Dev | Comment `/deploy` on PR |

## Files Changed

### New Files
- `k8s/base/kustomization.yaml`
- `k8s/base/deployment.yaml`
- `k8s/base/service.yaml`
- `k8s/base/configmap.yaml`
- `k8s/base/pvc.yaml`
- `k8s/base/secrets.yaml`
- `k8s/overlays/prod/kustomization.yaml`
- `k8s/overlays/prod/namespace.yaml`
- `k8s/overlays/prod/ingress.yaml`
- `k8s/overlays/dev/kustomization.yaml`
- `k8s/overlays/dev/namespace.yaml`
- `k8s/overlays/dev/ingress.yaml`
- `.github/workflows/deploy-dev.yml`
- `.github/workflows/cleanup-dev.yml`
- `ansible/deploy-prod.yml` (renamed from deploy.yml)
- `ansible/deploy-dev.yml`

### Modified Files
- `ansible/vars.yml` - updated variable names
- `ansible/vault.yml` - new secret entries

### Removed Files
- `k8s/deployment.yaml` (moved to base)
- `k8s/service.yaml` (moved to base)
- `k8s/configmap.yaml` (moved to base)
- `k8s/secrets.yaml` (moved to base)
- `k8s/pvc.yaml` (moved to base)
- `k8s/namespace.yaml` (moved to overlays/prod)
- `k8s/ingress.yaml` (moved to overlays/prod)

## Success Criteria

- [ ] Prod deployment works with new naming
- [ ] Dev deployment creates isolated per-branch namespace
- [ ] Preview URL accessible via `{branch}.mealanalyzer-dev.{tld}`
- [ ] Cleanup removes namespace on PR close
- [ ] Only maintainers can trigger deployments
- [ ] Dev deployments have resource limits

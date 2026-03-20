# CloudNativePG App-Managed Cluster Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a dedicated CNPG `Cluster` to the **dev** deployment (`meal-plan-analyzer-dev` namespace) so the database lifecycle is managed alongside the application. Prod is untouched throughout.

**Architecture:** A CNPG `Cluster` resource is added to the dev Kustomize overlay only. Ansible bootstrap creates a credentials Secret that CNPG reads on first boot; subsequent `kubectl apply` runs detect the existing PVC and skip `initdb` entirely — data is never reset. The `deployment.yaml` base uses `optional: true` on the `DATABASE_URL` secretKeyRef, so prod pods still work via `envFrom` from `meal-plan-analyzer-secret` (unchanged).

**Tech Stack:** CloudNativePG operator (already in `cloudnative-pg` namespace), Kustomize, Ansible, k3s/Kubernetes.

---

## Key Pitfalls and How We Prevent Them

### 1. "Will `kubectl apply` reset my database?"

**No.** CNPG only runs `bootstrap.initdb` when the cluster's PVCs do not yet exist. On every subsequent `kubectl apply`, CNPG detects the existing PVC, starts PostgreSQL normally, and leaves all data untouched.

### 2. "What if someone accidentally deletes the Cluster resource?"

CNPG attaches a finalizer (`cnpg.io/cluster`) to every `Cluster` object. Deletion is blocked until PVCs and Pods are explicitly cleaned up. Never use `kubectl delete cluster` in a deploy pipeline.

### 3. "What if the storage class reclaim policy is `Delete`?"

If the PVC is deleted (e.g. whole namespace deleted), data is gone even with CNPG finalizers. Create a `local-path-retain` storage class so the underlying volume survives PVC deletion.

### 4. "Won't changing `deployment.yaml` break prod?"

We add `DATABASE_URL` via `secretKeyRef` with **`optional: true`** in the base. If the secret `meal-plan-analyzer-db-credentials` doesn't exist (prod), Kubernetes skips that env entry and `envFrom` provides `DATABASE_URL` from `meal-plan-analyzer-secret` as before. Prod behaviour is identical.

### 5. "What about renaming the cluster?"

**Never rename the Cluster after first deployment.** CNPG ties PVC names to the cluster name. Rename = new empty PVCs = empty database.

---

## Pre-Flight Checklist

- [ ] Check storage classes: `kubectl get sc`
- [ ] Check CNPG version: `kubectl get deployment -n cloudnative-pg cnpg-controller-manager -o jsonpath='{.spec.template.spec.containers[0].image}'`
- [ ] Confirm dev namespace exists: `kubectl get ns meal-plan-analyzer-dev`
- [ ] Confirm Ansible vault access: `ansible-vault view deployment/vault.yml --vault-id ...`

---

## Task 1: Create a Retain-Policy Storage Class (if needed)

**Files:**
- Create: `deployment/bootstrap/k8s/base/cnpg-storage-class.yaml`
- Modify: `deployment/bootstrap/k8s/base/kustomization.yaml`

**Step 1: Check existing storage classes**

```bash
kubectl get sc
```

If `local-path` shows `RECLAIMPOLICY=Delete`, you need a Retain variant. If a Retain class already exists, note its name and skip to the commit — just use that name in Task 2.

**Step 2: Create the manifest**

```yaml
# deployment/bootstrap/k8s/base/cnpg-storage-class.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: local-path-retain
provisioner: rancher.io/local-path   # correct for k3s; adjust if different
reclaimPolicy: Retain
volumeBindingMode: WaitForFirstConsumer
```

**Step 3: Add to base kustomization**

```yaml
# deployment/bootstrap/k8s/base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - pvc.yaml
  - cnpg-storage-class.yaml

commonLabels:
  app: meal-plan-analyzer
```

**Step 4: Apply to dev bootstrap overlay**

```bash
kubectl apply -k deployment/bootstrap/k8s/overlays/dev/
```

Expected: `storageclass.storage.k8s.io/local-path-retain created` (or `unchanged`).

**Step 5: Commit**

```bash
git add deployment/bootstrap/k8s/base/cnpg-storage-class.yaml \
        deployment/bootstrap/k8s/base/kustomization.yaml
git commit -m "infra: add local-path-retain storage class for CNPG PVCs"
```

---

## Task 2: Create CNPG Cluster Manifests (dev only)

The base defines the cluster shape. The dev overlay patch overrides database/owner/size. No prod patch is created yet.

**Files:**
- Create: `deployment/app-deployment/k8s/base/cnpg-cluster.yaml`
- Create: `deployment/app-deployment/k8s/overlays/dev/cnpg-cluster-patch.yaml`

**Step 1: Write the base Cluster manifest**

```yaml
# deployment/app-deployment/k8s/base/cnpg-cluster.yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: meal-plan-analyzer-db
  # IMPORTANT: Never change this name after first deployment.
  # Renaming creates new empty PVCs — data loss.
spec:
  instances: 1

  bootstrap:
    initdb:
      # Runs ONLY when the PVC is brand new (first boot).
      # All subsequent kubectl apply runs skip this block entirely.
      database: meal_plan_analyzer_dev
      owner: meal_plan_analyzer_dev
      secret:
        # Ansible creates this secret before CNPG reads it.
        # CNPG enriches it with 'uri', 'host', 'port', 'dbname', etc.
        name: meal-plan-analyzer-db-credentials

  storage:
    size: 2Gi
    storageClass: local-path-retain

  postgresql:
    parameters:
      max_connections: "100"
      shared_buffers: "128MB"

  resources:
    requests:
      cpu: "100m"
      memory: "256Mi"
    limits:
      memory: "512Mi"
```

**Step 2: Write the dev overlay patch**

The dev patch is minimal — it exists to make the overlay explicit and serves as a future hook for dev-specific overrides (e.g. disabling backups, smaller limits).

```yaml
# deployment/app-deployment/k8s/overlays/dev/cnpg-cluster-patch.yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: meal-plan-analyzer-db
spec:
  storage:
    size: 2Gi
```

**Step 3: Commit**

```bash
git add deployment/app-deployment/k8s/base/cnpg-cluster.yaml \
        deployment/app-deployment/k8s/overlays/dev/cnpg-cluster-patch.yaml
git commit -m "infra: add CNPG Cluster manifest for dev"
```

---

## Task 3: Wire Cluster into Dev Kustomize Overlay Only

**Files:**
- Modify: `deployment/app-deployment/k8s/base/kustomization.yaml`
- Modify: `deployment/app-deployment/k8s/overlays/dev/kustomization.yaml`

**Step 1: Add cluster to base resources**

```yaml
# deployment/app-deployment/k8s/base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - configmap.yaml
  - deployment.yaml
  - service.yaml
  - redis.yaml
  - cnpg-cluster.yaml
```

**Step 2: Add patch to dev overlay**

Read the current dev kustomization first, then add the `patches` block:

```yaml
# deployment/app-deployment/k8s/overlays/dev/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: meal-plan-analyzer-dev

resources:
  - ingress.yaml
  - ../../base

# (keep existing images/resource-patch entries unchanged)

patches:
  - path: cnpg-cluster-patch.yaml
    target:
      kind: Cluster
      name: meal-plan-analyzer-db
```

> **Prod kustomization is not touched.** The `cnpg-cluster.yaml` resource is in base, but CNPG will simply not create a `Cluster` in the prod namespace until a prod patch is added and applied there.

Wait — actually there's a problem: including `cnpg-cluster.yaml` in base means `kubectl apply -k overlays/prod/` would also apply the Cluster to prod namespace. To avoid this, keep the Cluster out of base and put it only in the dev overlay.

**Revised Step 1: Do NOT add cluster to base — add it directly to dev overlay resources instead**

```yaml
# deployment/app-deployment/k8s/base/kustomization.yaml  — NO CHANGE
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - configmap.yaml
  - deployment.yaml
  - service.yaml
  - redis.yaml
```

```yaml
# deployment/app-deployment/k8s/overlays/dev/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: meal-plan-analyzer-dev

resources:
  - ingress.yaml      # keep existing
  - ../../base
  - ../../base/cnpg-cluster.yaml   # dev only

# (keep existing images/resource-patch entries unchanged)

patches:
  - path: cnpg-cluster-patch.yaml
    target:
      kind: Cluster
      name: meal-plan-analyzer-db
```

**Step 3: Verify dry-run — prod overlay does NOT include the Cluster**

```bash
kubectl kustomize deployment/app-deployment/k8s/overlays/prod/ | grep -c "kind: Cluster"
```

Expected: `0`

```bash
kubectl kustomize deployment/app-deployment/k8s/overlays/dev/ | grep -c "kind: Cluster"
```

Expected: `1`

**Step 4: Commit**

```bash
git add deployment/app-deployment/k8s/base/kustomization.yaml \
        deployment/app-deployment/k8s/overlays/dev/kustomization.yaml
git commit -m "infra: add CNPG Cluster to dev overlay only (prod unaffected)"
```

---

## Task 4: Update Ansible Bootstrap to Create Dev Credentials Secret

CNPG reads the Secret's `password` key on first boot, then enriches the same Secret with `uri`, `host`, `port`, `dbname`, `jdbc-uri`, `pgpass`. The secret must exist **before** the Cluster resource is applied.

We create the secret only if it doesn't already exist — this avoids clobbering CNPG's enrichment keys on subsequent bootstrap runs.

**Files:**
- Create: `deployment/bootstrap/ansible/db-secret-dev.yml`
- Modify: `deployment/bootstrap/ansible/bootstrap.yml`

**Step 1: Write the dev secret task**

```yaml
# deployment/bootstrap/ansible/db-secret-dev.yml
---
- name: Check if dev DB credentials secret exists
  shell: kubectl get secret meal-plan-analyzer-db-credentials -n meal-plan-analyzer-dev
  register: db_secret_dev_check
  failed_when: false
  changed_when: false

- name: Create dev DB credentials secret (first time only)
  shell: |
    kubectl create secret generic meal-plan-analyzer-db-credentials \
      --from-literal=username=meal_plan_analyzer_dev \
      --from-literal=password={{ db_password }} \
      -n meal-plan-analyzer-dev
  when: db_secret_dev_check.rc != 0
  changed_when: true
```

**Step 2: Add dev secret creation to bootstrap.yml**

The prod database tasks remain exactly as-is. Only the dev section is updated:

```yaml
# deployment/bootstrap/ansible/bootstrap.yml — show only the changed section
# Replace the existing "Include dev database configuration" task:

    - name: Set dev db_password from vault
      set_fact:
        db_password: "{{ meal_plan_analyzer_dev_db_password }}"

    - name: Include dev DB credentials secret creation
      include_tasks: db-secret-dev.yml
```

The `include_tasks: database-dev.yml` line is replaced by `include_tasks: db-secret-dev.yml`. The prod section (`include_tasks: database-prod.yml`) is **not changed**.

**Step 3: Commit**

```bash
git add deployment/bootstrap/ansible/db-secret-dev.yml \
        deployment/bootstrap/ansible/bootstrap.yml
git commit -m "infra: add CNPG credentials secret creation for dev bootstrap"
```

---

## Task 5: Update App Deployment to Read DATABASE_URL from CNPG Secret

`optional: true` makes this safe for prod: if `meal-plan-analyzer-db-credentials` doesn't exist in the prod namespace, Kubernetes skips the env entry and `envFrom` provides `DATABASE_URL` from `meal-plan-analyzer-secret` as before.

**Files:**
- Modify: `deployment/app-deployment/k8s/base/deployment.yaml`

**Step 1: Add DATABASE_URL env entry to every initContainer and container**

For each of the 4 initContainers (`build-scss`, `collect-static`, `migrate`, `import-foods`) and 2 containers (`meal-plan-analyzer`, `worker`), add an `env` block **before** `envFrom`:

```yaml
env:
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: meal-plan-analyzer-db-credentials
        key: uri
        optional: true   # pod starts normally if secret absent (e.g. prod)
envFrom:
  - configMapRef:
      name: meal-plan-analyzer-config
  - secretRef:
      name: meal-plan-analyzer-secret
```

The full updated `deployment.yaml` relevant sections look like:

```yaml
initContainers:
  - name: build-scss
    image: image_name
    imagePullPolicy: Always
    command: ["python", "manage.py", "build_scss"]
    env:
      - name: DATABASE_URL
        valueFrom:
          secretKeyRef:
            name: meal-plan-analyzer-db-credentials
            key: uri
            optional: true
    envFrom:
      - configMapRef:
          name: meal-plan-analyzer-config
      - secretRef:
          name: meal-plan-analyzer-secret
    volumeMounts:
      - name: sass-cache
        mountPath: /app/sass_cache

  - name: collect-static
    image: image_name
    imagePullPolicy: Always
    command: ["python", "manage.py", "collectstatic", "--noinput"]
    env:
      - name: DATABASE_URL
        valueFrom:
          secretKeyRef:
            name: meal-plan-analyzer-db-credentials
            key: uri
            optional: true
    envFrom:
      - configMapRef:
          name: meal-plan-analyzer-config
      - secretRef:
          name: meal-plan-analyzer-secret
    volumeMounts:
      - name: staticfiles
        mountPath: /app/staticfiles
      - name: sass-cache
        mountPath: /app/sass_cache

  - name: migrate
    image: image_name
    imagePullPolicy: Always
    command: ["python", "manage.py", "migrate"]
    env:
      - name: DATABASE_URL
        valueFrom:
          secretKeyRef:
            name: meal-plan-analyzer-db-credentials
            key: uri
            optional: true
    envFrom:
      - configMapRef:
          name: meal-plan-analyzer-config
      - secretRef:
          name: meal-plan-analyzer-secret

  - name: import-foods
    image: image_name
    imagePullPolicy: Always
    command: ["python", "manage.py", "import_foods", "https://blsdb.de/assets/uploads/BLS_4_0_2025_DE.zip"]
    env:
      - name: DATABASE_URL
        valueFrom:
          secretKeyRef:
            name: meal-plan-analyzer-db-credentials
            key: uri
            optional: true
    envFrom:
      - configMapRef:
          name: meal-plan-analyzer-config
      - secretRef:
          name: meal-plan-analyzer-secret

containers:
  - name: meal-plan-analyzer
    image: image_name
    imagePullPolicy: Always
    ports:
      - containerPort: 8000
    env:
      - name: DATABASE_URL
        valueFrom:
          secretKeyRef:
            name: meal-plan-analyzer-db-credentials
            key: uri
            optional: true
    envFrom:
      - configMapRef:
          name: meal-plan-analyzer-config
      - secretRef:
          name: meal-plan-analyzer-secret
    volumeMounts:
      - name: staticfiles
        mountPath: /app/staticfiles
      - name: media
        mountPath: /app/media
    livenessProbe:
      httpGet:
        path: /
        port: 8000
      initialDelaySeconds: 30
      periodSeconds: 10
    readinessProbe:
      httpGet:
        path: /
        port: 8000
      initialDelaySeconds: 5
      periodSeconds: 5

  - name: worker
    image: image_name
    imagePullPolicy: Always
    command:
      - celery
      - -A
      - config
      - worker
      - --loglevel=info
      - --concurrency=2
      - --max-tasks-per-child=50
    env:
      - name: DATABASE_URL
        valueFrom:
          secretKeyRef:
            name: meal-plan-analyzer-db-credentials
            key: uri
            optional: true
    envFrom:
      - configMapRef:
          name: meal-plan-analyzer-config
      - secretRef:
          name: meal-plan-analyzer-secret
    volumeMounts:
      - name: staticfiles
        mountPath: /app/staticfiles
      - name: media
        mountPath: /app/media
```

**Step 2: Verify prod deployment manifest renders correctly (no secret, envFrom wins)**

```bash
kubectl kustomize deployment/app-deployment/k8s/overlays/prod/ | grep -A3 "DATABASE_URL"
```

Expected: the `secretKeyRef` entry is present but `optional: true` — prod pods will start fine without the secret.

**Step 3: Commit**

```bash
git add deployment/app-deployment/k8s/base/deployment.yaml
git commit -m "infra: add optional CNPG DATABASE_URL env var to all containers"
```

---

## Task 6: Bootstrap Dev Cluster

**Step 1: Run bootstrap for dev only**

```bash
cd deployment/bootstrap/ansible
uv run ansible-playbook --vault-id ${ANSIBLE_VAULT_ID}@vault-key-client bootstrap.yml -e env=dev
```

Expected: secret `meal-plan-analyzer-db-credentials` exists in `meal-plan-analyzer-dev`.

```bash
kubectl get secret meal-plan-analyzer-db-credentials -n meal-plan-analyzer-dev
```

**Step 2: Apply dev overlay (creates Cluster + app resources)**

```bash
kubectl apply -k deployment/app-deployment/k8s/overlays/dev/
```

**Step 3: Watch the cluster come up**

```bash
kubectl get cluster meal-plan-analyzer-db -n meal-plan-analyzer-dev -w
```

Expected: status transitions to `Cluster in healthy state`, `INSTANCES: 1/1`. Takes ~1 minute.

**Step 4: Verify CNPG enriched the credentials secret**

```bash
kubectl get secret meal-plan-analyzer-db-credentials -n meal-plan-analyzer-dev \
  -o jsonpath='{.data.uri}' | base64 -d
```

Expected: `postgresql://meal_plan_analyzer_dev:<password>@meal-plan-analyzer-db-rw:5432/meal_plan_analyzer_dev`

---

## Task 7: Deploy App to Dev and Smoke Test

**Step 1: Trigger a rollout (app picks up new DATABASE_URL)**

```bash
kubectl rollout restart deployment/meal-plan-analyzer -n meal-plan-analyzer-dev
```

Or redeploy via Ansible:

```bash
cd deployment/app-deployment/ansible
uv run ansible-playbook --vault-id ${ANSIBLE_VAULT_ID}@vault-key-client deploy.yml -e env=dev
```

On first deploy, `migrate` creates all tables; `import-foods` downloads and imports BLS data (a few minutes).

**Step 2: Tail logs**

```bash
kubectl logs -n meal-plan-analyzer-dev -l app=meal-plan-analyzer --all-containers -f --since=60s
```

Expected: no `OperationalError` or `connection refused`. `migrate` initContainer logs `No migrations to apply.` (or lists applied migrations on first boot).

**Step 3: Smoke test**

- Log into the dev app
- Verify food search returns results (confirms `import-foods` ran)
- Create a meal plan and save it
- Export a PDF

**Step 4: If something is wrong — rollback**

The dev app can fall back to the old `pgcluster` by reverting the `deployment.yaml` changes (removing the `env` blocks) and redeploying. The `pgcluster` is untouched.

---

## Task 8: Archive Old Dev Bootstrap Tasks

Once dev is confirmed working:

**Step 1: Archive `database-dev.yml`**

```bash
mv deployment/bootstrap/ansible/database-dev.yml \
   deployment/bootstrap/ansible/database-dev.yml.archived
```

`database-prod.yml` is **not touched**.

**Step 2: Add a comment to vars.yml**

```yaml
# deployment/bootstrap/ansible/vars.yml
# Bootstrap variables
env: ""

# Database connection — used by prod only (dev uses CNPG-managed service)
db_host: "pgcluster-rw.cloudnative-pg.svc.cluster.local"
db_port: "5432"

# K8s namespaces
prod_namespace: "meal-plan-analyzer"
dev_namespace: "meal-plan-analyzer-dev"
```

**Step 3: Commit**

```bash
git add deployment/bootstrap/ansible/database-dev.yml.archived \
        deployment/bootstrap/ansible/vars.yml
git commit -m "infra: archive manual SQL bootstrap for dev (superseded by CNPG Cluster CRD)"
```

---

## Final Checklist

- [ ] `local-path-retain` storage class exists in cluster
- [ ] `cnpg-cluster.yaml` in base, referenced only from dev overlay
- [ ] Prod kustomize dry-run shows zero `kind: Cluster` resources
- [ ] `meal-plan-analyzer-db-credentials` secret created in `meal-plan-analyzer-dev` by Ansible
- [ ] CNPG Cluster is healthy (`INSTANCES: 1/1`)
- [ ] CNPG has enriched the credentials secret (check `uri` key)
- [ ] App connects to new cluster (no DB errors in logs)
- [ ] Food search works (BLS import ran)
- [ ] `database-dev.yml` archived; `database-prod.yml` untouched
- [ ] Existing `pgcluster` in `cloudnative-pg` namespace untouched

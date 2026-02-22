# Dev Deployments Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add dev deployment capability with per-branch namespaces, triggered by maintainer command, using Kustomize overlays.

**Architecture:** Kustomize base/overlays pattern for environment separation. Ansible handles secrets from vault. GitHub Actions responds to `/deploy` comments to create isolated per-branch deployments.

**Tech Stack:** Kustomize, Ansible, GitHub Actions, Kubernetes, cert-manager

---

## Phase 1: Rename meal-planner → meal-analyzer

### Task 1: Create Kustomize base structure

**Files:**
- Create: `k8s/base/kustomization.yaml`
- Create: `k8s/base/deployment.yaml`
- Create: `k8s/base/service.yaml`
- Create: `k8s/base/configmap.yaml`
- Create: `k8s/base/pvc.yaml`
- Create: `k8s/base/secrets.yaml`

**Step 1: Create base directory and kustomization.yaml**

```yaml
# k8s/base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - configmap.yaml
  - secrets.yaml
  - pvc.yaml
  - deployment.yaml
  - service.yaml

commonLabels:
  app: meal-analyzer
```

**Step 2: Create base configmap.yaml**

```yaml
# k8s/base/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: meal-analyzer-config
data:
  DEBUG: "False"
  ALLOWED_HOSTS: "*"
```

**Step 3: Create base secrets.yaml**

```yaml
# k8s/base/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: meal-analyzer-secret
stringData:
  SECRET_KEY: "{{ secret_key }}"
  DATABASE_URL: "{{ database_url }}"
```

**Step 4: Create base pvc.yaml**

```yaml
# k8s/base/pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: meal-analyzer-media-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
```

**Step 5: Create base deployment.yaml**

```yaml
# k8s/base/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: meal-analyzer
spec:
  replicas: 1
  selector:
    matchLabels:
      app: meal-analyzer
  template:
    metadata:
      labels:
        app: meal-analyzer
    spec:
      imagePullSecrets:
        - name: regcred
      initContainers:
        - name: collect-static
          image: {{ image_name }}
          imagePullPolicy: Always
          command: ["python", "manage.py", "collectstatic", "--noinput"]
          envFrom:
            - configMapRef:
                name: meal-analyzer-config
            - secretRef:
                name: meal-analyzer-secret
          volumeMounts:
            - name: staticfiles
              mountPath: /app/staticfiles
        - name: migrate
          image: {{ image_name }}
          imagePullPolicy: Always
          command: ["python", "manage.py", "migrate"]
          envFrom:
            - configMapRef:
                name: meal-analyzer-config
            - secretRef:
                name: meal-analyzer-secret
        - name: import-foods
          image: {{ image_name }}
          imagePullPolicy: Always
          command: ["python", "manage.py", "import_foods", "https://blsdb.de/assets/uploads/BLS_4_0_2025_DE.zip"]
          envFrom:
            - configMapRef:
                name: meal-analyzer-config
            - secretRef:
                name: meal-analyzer-secret
      containers:
        - name: meal-analyzer
          image: {{ image_name }}
          imagePullPolicy: Always
          ports:
            - containerPort: 8000
          envFrom:
            - configMapRef:
                name: meal-analyzer-config
            - secretRef:
                name: meal-analyzer-secret
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
      volumes:
        - name: staticfiles
          emptyDir: {}
        - name: media
          persistentVolumeClaim:
            claimName: meal-analyzer-media-pvc
```

**Step 6: Create base service.yaml**

```yaml
# k8s/base/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: meal-analyzer-service
spec:
  selector:
    app: meal-analyzer
  ports:
    - port: 80
      targetPort: 8000
```

**Step 7: Commit**

```bash
git add k8s/base/
git commit -m "feat(k8s): create Kustomize base with renamed resources"
```

---

### Task 2: Create prod overlay

**Files:**
- Create: `k8s/overlays/prod/kustomization.yaml`
- Create: `k8s/overlays/prod/namespace.yaml`
- Create: `k8s/overlays/prod/ingress.yaml`
- Create: `k8s/overlays/prod/kustomization.yaml`

**Step 1: Create prod directory and namespace.yaml**

```yaml
# k8s/overlays/prod/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: meal-analyzer
```

**Step 2: Create prod ingress.yaml**

```yaml
# k8s/overlays/prod/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: meal-analyzer-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-dns-issuer
spec:
  tls:
    - hosts:
        - mealanalyzer.{{ tld }}
      secretName: meal-analyzer-tls
  rules:
    - host: mealanalyzer.{{ tld }}
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: meal-analyzer-service
                port:
                  number: 80
```

**Step 3: Create prod kustomization.yaml**

```yaml
# k8s/overlays/prod/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: meal-analyzer

resources:
  - namespace.yaml
  - ../../base
  - ingress.yaml
```

**Step 4: Verify Kustomize build works**

Run: `kubectl kustomize k8s/overlays/prod/`
Expected: YAML output with namespace `meal-analyzer` on all resources

**Step 5: Commit**

```bash
git add k8s/overlays/prod/
git commit -m "feat(k8s): create prod overlay"
```

---

### Task 3: Create dev overlay

**Files:**
- Create: `k8s/overlays/dev/namespace.yaml`
- Create: `k8s/overlays/dev/ingress.yaml`
- Create: `k8s/overlays/dev/kustomization.yaml`
- Create: `k8s/overlays/dev/resource-patch.yaml`

**Step 1: Create dev namespace.yaml (template)**

```yaml
# k8s/overlays/dev/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: meal-analyzer-dev
```

**Step 2: Create dev ingress.yaml**

```yaml
# k8s/overlays/dev/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: meal-analyzer-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-dns-issuer
spec:
  tls:
    - hosts:
        - mealanalyzer-dev.{{ tld }}
      secretName: meal-analyzer-dev-tls
  rules:
    - host: mealanalyzer-dev.{{ tld }}
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: meal-analyzer-service
                port:
                  number: 80
```

**Step 3: Create dev resource-patch.yaml for limits**

```yaml
# k8s/overlays/dev/resource-patch.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: meal-analyzer
spec:
  template:
    spec:
      containers:
        - name: meal-analyzer
          resources:
            limits:
              cpu: "500m"
              memory: "512Mi"
            requests:
              cpu: "100m"
              memory: "256Mi"
```

**Step 4: Create dev kustomization.yaml**

```yaml
# k8s/overlays/dev/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: meal-analyzer-dev

resources:
  - namespace.yaml
  - ../../base
  - ingress.yaml

patches:
  - path: resource-patch.yaml
```

**Step 5: Verify Kustomize build works**

Run: `kubectl kustomize k8s/overlays/dev/`
Expected: YAML output with namespace `meal-analyzer-dev` and resource limits

**Step 6: Commit**

```bash
git add k8s/overlays/dev/
git commit -m "feat(k8s): create dev overlay with resource limits"
```

---

### Task 4: Update Ansible vars and vault

**Files:**
- Modify: `ansible/vars.yml`
- Modify: `ansible/vault.yml`

**Step 1: Update vars.yml**

```yaml
# ansible/vars.yml
tld: "{{ lookup('env', 'TLD') }}"
mealanalyzer_ipv4_addr: "{{ lookup('env', 'MEALANALYZER_IPV4_ADDR') }}"
mealanalyzer_ipv6_addr: "{{ lookup('env', 'MEALANALYZER_IPV6_ADDR') }}"
```

**Step 2: Add dev secrets to vault.yml**

Add these entries to `ansible/vault.yml`:
```yaml
# Prod secrets (renamed)
meal_analyzer_prod_secret_key: "<existing-key>"
meal_analyzer_prod_db_password: "<existing-password>"

# Dev secrets (new)
meal_analyzer_dev_secret_key: "<generate-new-key>"
meal_analyzer_dev_db_password: "<generate-new-password>"
```

**Step 3: Commit**

```bash
git add ansible/vars.yml ansible/vault.yml
git commit -m "feat(ansible): add dev secrets and rename vars"
```

---

### Task 5: Update Ansible deploy playbook for prod

**Files:**
- Create: `ansible/deploy-prod.yml`
- Modify: `ansible/database.yml`

**Step 1: Create deploy-prod.yml from deploy.yml**

Copy `ansible/deploy.yml` to `ansible/deploy-prod.yml` and update:
- Change references from `meal-planner` to `meal-analyzer`
- Update k8s paths to use Kustomize overlay
- Add `env` variable with default `prod`

```yaml
# ansible/deploy-prod.yml (key changes)
---
- name: Build, Push, and Deploy to Kubernetes (Prod)
  hosts: localhost
  gather_facts: false
  vars_files:
    - vars.yml
    - vault.yml
  vars:
    docker_user: ""
    docker_password: ""
    image_name: "{{ lookup('env', 'DOCKER_IMAGE') }}"
    project_root: "../"
    env: prod
    namespace: meal-analyzer

  tasks:
    # ... existing tasks ...

    - name: Create Docker Registry Secret using kubectl
      shell: >
        kubectl create secret docker-registry regcred -n {{ namespace }}
        --docker-server=https://index.docker.io/v1/
        --docker-username={{ docker_user }}
        --docker-password={{ docker_k8s_password }}
        --dry-run=client -o yaml | kubectl apply -f -

    - name: Apply Kubernetes manifests with Kustomize
      shell: kubectl apply -k ../k8s/overlays/{{ env }}/

    - name: Restart Deployment
      shell: kubectl rollout restart deployment/meal-analyzer -n {{ namespace }}
```

**Step 2: Update database.yml references**

Replace `meal_planner` with `meal_analyzer` in database URLs.

**Step 3: Commit**

```bash
git add ansible/deploy-prod.yml ansible/database.yml
git commit -m "feat(ansible): create deploy-prod.yml with Kustomize"
```

---

### Task 6: Create Ansible deploy-dev playbook

**Files:**
- Create: `ansible/deploy-dev.yml`

**Step 1: Create deploy-dev.yml**

```yaml
# ansible/deploy-dev.yml
---
- name: Deploy Dev Environment
  hosts: localhost
  gather_facts: false
  vars_files:
    - vars.yml
    - vault.yml
  vars:
    image_name: "{{ lookup('env', 'DOCKER_IMAGE') }}"
    project_root: "../"
    branch: ""
    namespace: "meal-analyzer-{{ branch | regex_replace('[^a-z0-9-]', '-') | lower }}"
    secret_key: "{{ meal_analyzer_dev_secret_key }}"
    db_password: "{{ meal_analyzer_dev_db_password }}"

  tasks:
    - name: Fail if branch not provided
      fail:
        msg: "Please provide 'branch' via -e 'branch=feature-x'"
      when: branch == ""

    - name: Include database configuration
      include_tasks: database.yml

    - name: Build Docker image
      community.docker.docker_image_build:
        path: "{{ project_root }}"
        name: "{{ image_name }}"
        tag: "{{ branch }}-dev"
        rebuild: "always"
        outputs:
          - type: "docker"
            name: "{{ image_name }}:{{ branch }}-dev"
            push: true

    - name: Create namespace
      kubernetes.core.k8s:
        state: present
        definition:
          apiVersion: v1
          kind: Namespace
          metadata:
            name: "{{ namespace }}"

    - name: Create Docker Registry Secret
      shell: >
        kubectl create secret docker-registry regcred -n {{ namespace }}
        --docker-server=https://index.docker.io/v1/
        --docker-username={{ lookup('env', 'DOCKER_USER') }}
        --docker-password={{ lookup('env', 'DOCKER_PASSWORD') }}
        --dry-run=client -o yaml | kubectl apply -f -

    - name: Apply dev overlay with branch-specific namespace
      shell: |
        cd ../k8s/overlays/dev
        kustomize edit set namespace {{ namespace }}
        kubectl apply -k .

    - name: Restart Deployment
      shell: kubectl rollout restart deployment/meal-analyzer -n {{ namespace }}

    - name: Get deployment URL
      debug:
        msg: "Deployed to https://{{ branch | regex_replace('[^a-z0-9-]', '-') | lower }}.mealanalyzer-dev.{{ tld }}"
```

**Step 2: Commit**

```bash
git add ansible/deploy-dev.yml
git commit -m "feat(ansible): create deploy-dev.yml for per-branch deployments"
```

---

## Phase 2: GitHub Actions

### Task 7: Create dev deploy GitHub Action

**Files:**
- Create: `.github/workflows/deploy-dev.yml`

**Step 1: Create workflow file**

```yaml
# .github/workflows/deploy-dev.yml
name: Deploy Dev

on:
  issue_comment:
    types: [created]

jobs:
  deploy:
    if: |
      github.event.issue.pull_request &&
      startsWith(github.event.comment.body, '/deploy')
    runs-on: ubuntu-latest
    steps:
      - name: Check maintainer permission
        uses: actions/github-script@v7
        with:
          script: |
            const commenter = context.actor;
            const { data: permissions } = await github.rest.repos.getCollaboratorPermissionLevel({
              owner: context.repo.owner,
              repo: context.repo.repo,
              username: commenter
            });
            if (!['write', 'admin', 'maintain'].includes(permissions.permission)) {
              core.setFailed('Only maintainers can trigger deployments');
            }

      - name: Checkout PR
        uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha || github.sha }}

      - name: Get branch name
        id: branch
        run: |
          BRANCH="${{ github.event.pull_request.head.ref || github.ref_name }}"
          SANITIZED=$(echo "$BRANCH" | sed 's/[^a-z0-9-]/-/g' | tr '[:upper:]' '[:lower:]')
          echo "name=$SANITIZED" >> $GITHUB_OUTPUT

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install Ansible
        run: pip install ansible kubernetes-core community-docker

      - name: Deploy
        env:
          DOCKER_IMAGE: ${{ secrets.DOCKER_IMAGE }}
          DOCKER_USER: ${{ secrets.DOCKER_USER }}
          DOCKER_PASSWORD: ${{ secrets.DOCKER_PASSWORD }}
          TLD: ${{ secrets.TLD }}
          ANSIBLE_VAULT_PASSWORD: ${{ secrets.ANSIBLE_VAULT_PASSWORD }}
        run: |
          echo "$ANSIBLE_VAULT_PASSWORD" > vault_pass.txt
          ansible-playbook ansible/deploy-dev.yml \
            -e "branch=${{ steps.branch.outputs.name }}" \
            --vault-password-file vault_pass.txt

      - name: Comment preview URL
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '🚀 Deployed to https://${{ steps.branch.outputs.name }}.mealanalyzer-dev.${{ secrets.TLD }}'
            });
```

**Step 2: Commit**

```bash
git add .github/workflows/deploy-dev.yml
git commit -m "feat(ci): add dev deploy workflow triggered by /deploy comment"
```

---

### Task 8: Create cleanup GitHub Action

**Files:**
- Create: `.github/workflows/cleanup-dev.yml`

**Step 1: Create workflow file**

```yaml
# .github/workflows/cleanup-dev.yml
name: Cleanup Dev Deployment

on:
  pull_request:
    types: [closed]

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - name: Sanitize branch name
        id: branch
        run: |
          BRANCH="${{ github.head_ref }}"
          SANITIZED=$(echo "$BRANCH" | sed 's/[^a-z0-9-]/-/g' | tr '[:upper:]' '[:lower:]')
          echo "name=$SANITIZED" >> $GITHUB_OUTPUT

      - name: Delete namespace
        env:
          KUBECONFIG: ${{ secrets.KUBECONFIG }}
        run: |
          kubectl delete namespace meal-analyzer-${{ steps.branch.outputs.name }} --ignore-not-found=true
```

**Step 2: Commit**

```bash
git add .github/workflows/cleanup-dev.yml
git commit -m "feat(ci): add cleanup workflow for PR close"
```

---

## Phase 3: Cleanup & Migration

### Task 9: Remove old k8s files

**Files:**
- Remove: `k8s/deployment.yaml`
- Remove: `k8s/service.yaml`
- Remove: `k8s/configmap.yaml`
- Remove: `k8s/secrets.yaml`
- Remove: `k8s/pvc.yaml`
- Remove: `k8s/namespace.yaml`
- Remove: `k8s/ingress.yaml`
- Remove: `ansible/deploy.yml`

**Step 1: Remove old files**

```bash
rm k8s/deployment.yaml k8s/service.yaml k8s/configmap.yaml k8s/secrets.yaml k8s/pvc.yaml k8s/namespace.yaml k8s/ingress.yaml ansible/deploy.yml
```

**Step 2: Commit**

```bash
git add -A
git commit -m "refactor: remove old k8s files, migrated to Kustomize overlays"
```

---

### Task 10: Update documentation

**Files:**
- Modify: `README.md` (add deploy instructions)

**Step 1: Add deployment section to README**

Add section:

```markdown
## Deployment

### Production

```bash
ansible-playbook ansible/deploy-prod.yml \
  -e "docker_user=xxx docker_password=xxx" \
  --vault-password-file vault_pass.txt
```

### Dev (Feature Branches)

Maintainers can deploy a PR for testing by commenting `/deploy` on the PR.

The preview will be available at: `https://{branch}.mealanalyzer-dev.{tld}`

Cleanup is automatic when the PR is closed or merged.
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add deployment instructions"
```

---

## Verification Checklist

- [ ] `kubectl kustomize k8s/overlays/prod/` produces valid YAML
- [ ] `kubectl kustomize k8s/overlays/dev/` produces valid YAML with resource limits
- [ ] `ansible-playbook ansible/deploy-prod.yml --check` passes syntax check
- [ ] GitHub Actions workflows are valid (check in Actions tab after push)

## Post-Deployment Tasks (Manual)

1. Create dev database: `createdb meal_analyzer_dev`
2. Add wildcard DNS: `*.mealanalyzer-dev.{tld}` → cluster IP
3. Add GitHub secrets: `DOCKER_IMAGE`, `DOCKER_USER`, `DOCKER_PASSWORD`, `TLD`, `ANSIBLE_VAULT_PASSWORD`, `KUBECONFIG`
4. Test: Open a PR, comment `/deploy`, verify namespace created

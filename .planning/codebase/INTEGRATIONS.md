# External Integrations

**Analysis Date:** 2026-03-16

## APIs & External Services

**None at runtime.** The application has no calls to external HTTP APIs during normal operation. All data is self-contained.

**BLS Data Import (offline):**
- Bundes Lebensmittel Schlüssel (BLS) — German national food composition database
- Consumed as a local Excel file (`.xlsx`) or ZIP archive
- Import command: `uv run python manage.py import_foods <path/to/bls_file.xlsx>`
- Implementation: `meals/management/commands/import_foods.py`
- Uses `openpyxl` with hard-coded BLS column mappings; performs `update_or_create` by `bls_code`
- This is a one-time offline import, not a live API integration

## Data Storage

**Databases:**
- Primary: PostgreSQL 16 (production/Docker Compose)
  - Connection: `DATABASE_URL` env var (format: `postgres://user:pass@host:5432/dbname`)
  - Client: `psycopg[binary]` 3.x adapter via Django ORM
  - Docker Compose service: `db` (image `postgres:16-alpine`, volume `postgres_data`)
- Development fallback: SQLite
  - Connection: `DATABASE_URL` defaults to `sqlite:///db.sqlite3` when env var is absent
  - CI jobs also use SQLite (`DATABASE_URL: sqlite:///test-db.sqlite3`)

**File Storage:**
- Local filesystem only
- `MEDIA_ROOT = BASE_DIR / "media"`, served at `/media/`
- Used for: `SiteSettings.logo` (uploaded to `logos/`) and `SiteSettings.minilogo` (uploaded to `logos/`)
- Storage backend: `django.core.files.storage.FileSystemStorage`
- No cloud object storage (no S3, GCS, etc.)

**Caching:**
- Django's default in-memory cache (LocMemCache)
- Used specifically for the food alias index: key `food_aliases_index`, 1-hour TTL
- Cache invalidated via `post_save`/`post_delete` signals on `FoodAlias` model
- Access pattern: `get_alias_index()` in `meals/models.py`
- No Redis or Memcached configured

## Authentication & Identity

**Auth Provider:**
- Django built-in authentication (`django.contrib.auth`)
- No OAuth, SSO, or external identity provider
- Session-based authentication for browser views (all views require `@login_required`)
- Token/session authentication for DRF API (uses `IsAuthenticated` permission class)
- Login URL: `/login/` → redirects to `meal-plan-list` on success
- Logout URL: `/logout/` → redirects to `login`
- User management via Django admin

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry, Rollbar, etc.)

**Logs:**
- Python standard `logging` module
- All output goes to stdout/stderr via `logging.StreamHandler`
- Log level controlled by `DJANGO_LOG_LEVEL` env var (default `INFO`)
- Gunicorn access logs (`--access-logfile -`) and error logs (`--error-logfile -`) also to stdout
- No structured logging, no log aggregation service

## CI/CD & Deployment

**Hosting:**
- Production/Dev: Kubernetes (k3s cluster) — manifests in `deployment/app-deployment/k8s/`
- Dev environment: separate overlay at `deployment/app-deployment/k8s/overlays/dev/`

**Container Registry:**
- DockerHub — images pushed to `amjadsaadeh/meal-plan-analyzer`
- Tags: `latest` (release), `dev` (main branch commits), `v*` (version tags)
- Credentials: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN` GitHub secrets

**CI Pipeline:**
- GitHub Actions (`.github/workflows/`)
- `tests.yml` — runs on PRs to `main`; four jobs: lint (Black), unit-tests, api-tests, frontend-tests
- `release.yml` — runs on `v*` tags; builds and pushes Docker image to DockerHub
- `deploy-dev.yml` — runs on pushes to `main`; builds Docker image + deploys to dev k8s namespace via `kubectl`
- `pages.yml` — separate workflow (purpose: likely documentation/GitHub Pages)
- Test results published as JUnit XML via `dorny/test-reporter@v1`
- Playwright failure artifacts uploaded via `actions/upload-artifact@v4` (7-day retention)

**Ansible:**
- Production deployment via Ansible playbooks in `deployment/app-deployment/ansible/`
- Uses `nc-dnsapi` for Netcup DNS automation
- Vault secrets managed via KeePassXC CLI (`keepassxc-cli`)
- Vault ID configured via `ANSIBLE_VAULT_ID` env var

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Environment Configuration

**Required env vars:**
- `SECRET_KEY` — Django secret key (only truly required var)

**Optional env vars (with defaults):**
- `DEBUG` — default `False`
- `ALLOWED_HOSTS` — default `localhost,127.0.0.1`
- `DATABASE_URL` — default SQLite at `db.sqlite3`
- `CSRF_TRUSTED_ORIGINS` — default empty
- `DJANGO_LOG_LEVEL` — default `INFO`
- `VITE_DEV_SERVER_HOST` — default `localhost` (only needed in dev)
- `VITE_ORIGIN` — default `http://localhost:5173` (only needed in dev)
- `APP_VERSION` — injected at Docker build time via `ARG`; falls back to `importlib.metadata` version

**Deployment-only env vars (not in settings.py):**
- `DOCKER_IMAGE`, `DOCKER_USER`, `DOCKER_PASSWORD` — container registry
- `TLD`, `MEALPLANALYZER_IPV4_ADDR`, `MEALPLANALYZER_IPV6_ADDR` — DNS/network
- `ANSIBLE_VAULT_ID`, `KEEPASS_CMD`, `KEEPASS_DB_PATH` — Ansible secrets management

**Secrets location:**
- Local dev: `.env` file (not committed; `.env.example` is the template)
- CI: GitHub Actions secrets (`DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `KUBECONFIG`)
- Production: Ansible vault (KeePassXC-backed)

---

*Integration audit: 2026-03-16*
